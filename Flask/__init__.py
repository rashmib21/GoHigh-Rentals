import os, re, base64
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from dotenv import load_dotenv
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from .booking import booking_bp
from .admin import admin_bp

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

UPLOAD_DOCS = None   # set in create_app

def get_or_create_key(key_path):
    if os.path.exists(key_path):
        with open(key_path, 'rb') as f:
            return f.read()
    key = Fernet.generate_key()
    with open(key_path, 'wb') as f:
        f.write(key)
    return key

def encrypt_file(src_path, dest_path, fernet):
    with open(src_path, 'rb') as f:
        data = f.read()
    encrypted = fernet.encrypt(data)
    with open(dest_path, 'wb') as f:
        f.write(encrypted)

def decrypt_file_bytes(enc_path, fernet):
    with open(enc_path, 'rb') as f:
        data = f.read()
    return fernet.decrypt(data)


def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "gohigh_secret_2024")

    global UPLOAD_DOCS
    UPLOAD_DOCS = os.path.join(app.root_path, "static", "uploads", "documents")
    os.makedirs(UPLOAD_DOCS, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "static", "uploads", "vehicle_photos"), exist_ok=True)

    # Encryption key
    key_path = os.path.join(app.root_path, "instance", "doc.key")
    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    if CRYPTO_AVAILABLE:
        fernet_key = get_or_create_key(key_path)
        app.fernet = Fernet(fernet_key)
    else:
        app.fernet = None

    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    def get_db_connection():
        try:
            return mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )
        except Exception as e:
            print("DB error:", e)
            return None

    # ── ensure new columns exist ──
    def safe_migrate(conn):
        cursor = conn.cursor()
        migrations = [
            "ALTER TABLE review ADD COLUMN category VARCHAR(20) DEFAULT 'travelling'",
            "ALTER TABLE review ADD COLUMN vehicle_id INT DEFAULT NULL",
            "ALTER TABLE user_documents ADD COLUMN encrypted TINYINT(1) DEFAULT 0",
            "ALTER TABLE user_documents ADD COLUMN verified_at DATETIME DEFAULT NULL",
            "ALTER TABLE user_documents ADD COLUMN verification_status VARCHAR(20) DEFAULT 'pending'",
            """CREATE TABLE IF NOT EXISTS admin_accounts (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(60) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(256) NOT NULL,
                created_at DATETIME DEFAULT NOW()
            )""",
        ]
        for sql in migrations:
            try:
                cursor.execute(sql)
                conn.commit()
            except Exception:
                pass
        cursor.close()

    @app.route('/')
    def index():
        return render_template("home.html")

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name     = request.form.get('name', '').strip()
            email    = request.form.get('email', '').strip()
            phone_no = request.form.get('phone_no', '').strip()
            password = request.form.get('password', '').strip()

            if not all([name, email, phone_no, password]):
                flash("All fields are required!", "error")
                return render_template('register.html')

            # Validations
            if not re.match(r'^[A-Za-z]{2,}(?:\s[A-Za-z]{2,})+$', name):
                flash("Enter full name (first + last name, letters only).", "error")
                return render_template('register.html')
            if len(email) > 60:
                flash("Email must be 60 characters or fewer.", "error")
                return render_template('register.html')
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9._%+-]*@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$', email):
                flash("Invalid email format.", "error")
                return render_template('register.html')
            if not re.match(r'^[6-9][0-9]{9}$', phone_no):
                flash("Invalid phone number. Must be 10 digits starting with 6–9.", "error")
                return render_template('register.html')
            # No 4 same digits in a row
            if re.search(r'(\d)\1{3,}', phone_no):
                flash("Phone number cannot have the same digit repeated 4+ times.", "error")
                return render_template('register.html')
            if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&\-]).{8,}$', password):
                flash("Password: 8+ chars, upper+lower+digit+special.", "error")
                return render_template('register.html')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT email, phone_no FROM users WHERE email=%s OR phone_no=%s", (email, phone_no))
            existing = cursor.fetchone()
            if existing:
                msg = "Email already registered!" if existing['email'] == email else "Phone already registered!"
                flash(msg, "error")
                cursor.close(); conn.close()
                return render_template('register.html')

            hashed = generate_password_hash(password)
            session.clear()
            cursor.execute("INSERT INTO users (name, email, phone_no, password) VALUES (%s,%s,%s,%s)",
                           (name, email, phone_no, hashed))
            conn.commit()
            session['user_id']   = cursor.lastrowid
            session['user_name'] = name
            cursor.close(); conn.close()
            flash("Registration successful!", "success")
            return redirect(url_for('dashboard'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            conn     = get_db_connection()
            cursor   = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()
            cursor.close(); conn.close()
            if user:
                stored = user['password']
                valid  = check_password_hash(stored, password) if stored.startswith(('pbkdf2:', 'scrypt:')) else stored == password
                if valid:
                    session.clear()
                    session['user_id']   = user['user_id']
                    session['user_name'] = user['name']
                    flash("Login successful!", "success")
                    return redirect('/dashboard')
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    # ── ADMIN REGISTER ──
    @app.route('/admin/register', methods=['GET', 'POST'])
    def admin_register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            secret   = request.form.get('admin_secret', '').strip()

            if secret != os.getenv("ADMIN_REGISTER_SECRET", "GoHighAdmin2024"):
                flash("Invalid admin secret key.", "error")
                return render_template('admin_register.html')
            if not all([username, email, password]):
                flash("All fields required.", "error")
                return render_template('admin_register.html')
            if len(password) < 8:
                flash("Password must be 8+ characters.", "error")
                return render_template('admin_register.html')

            conn   = get_db_connection()
            cursor = conn.cursor()
            safe_migrate(conn)
            try:
                hashed = generate_password_hash(password)
                cursor.execute("INSERT INTO admin_accounts (username, email, password) VALUES (%s,%s,%s)",
                               (username, email, hashed))
                conn.commit()
                flash("Admin account created! You can now log in.", "success")
                return redirect(url_for('admin.admin_login'))
            except Exception:
                flash("Username or email already exists.", "error")
            finally:
                cursor.close(); conn.close()
        return render_template('admin_register.html')

    # ── DASHBOARD ──
    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        conn    = get_db_connection()
        cursor  = conn.cursor(dictionary=True)
        safe_migrate(conn)

        today = date.today()
        cursor.execute("""
            UPDATE booking SET booking_status='Completed'
            WHERE booking_status='Confirmed' AND travel_date <= %s
        """, (today,))
        conn.commit()

        # notifications
        cursor.execute("""
            SELECT b.booking_id, b.booking_status, d.destination_name
            FROM booking b JOIN destination d ON b.destination_id=d.destination_id
            WHERE b.user_id=%s AND b.booking_status IN ('Confirmed','Cancelled') AND b.notified=0
        """, (user_id,))
        notifications = cursor.fetchall()
        if notifications:
            cursor.execute("""
                UPDATE booking SET notified=1
                WHERE user_id=%s AND booking_status IN ('Confirmed','Cancelled') AND notified=0
            """, (user_id,))
            conn.commit()

        # recent bookings
        cursor.execute("""
            SELECT b.booking_id, b.travel_date, b.booking_status,
                   d.destination_name, v.vehicle_name, p.total_amount
            FROM booking b
            JOIN destination d ON b.destination_id=d.destination_id
            JOIN vehicle v     ON b.vehicle_id=v.vehicle_id
            JOIN pricing p     ON b.booking_id=p.booking_id
            WHERE b.user_id=%s ORDER BY b.travel_date DESC LIMIT 5
        """, (user_id,))
        bookings = cursor.fetchall()

        total_trips = len(bookings)
        confirmed  = sum(1 for b in bookings if b['booking_status']=='Confirmed')
        cancelled  = sum(1 for b in bookings if b['booking_status']=='Cancelled')
        completed  = sum(1 for b in bookings if b['booking_status']=='Completed')
        total_spent = sum(b['total_amount'] for b in bookings)

        # Reviews (with category)
        user_reviews = []
        try:
            cursor.execute("""
                SELECT r.rating, r.review_text, r.created_at,
                       IFNULL(r.category,'travelling') AS category,
                       u.name AS reviewer_name
                FROM review r JOIN users u ON r.user_id=u.user_id
                ORDER BY r.created_at DESC LIMIT 20
            """)
            user_reviews = cursor.fetchall()
        except Exception:
            user_reviews = []

        # destinations
        cursor.execute("""
            SELECT destination_id, destination_name, state, price_per_day, price_per_hour
            FROM destination WHERE is_active=1 ORDER BY destination_id
        """)
        destinations = cursor.fetchall()

        # vehicles with rating
        vehicles_rated = []
        try:
            cursor.execute("""
                SELECT vehicle_id, vehicle_name, vehicle_type,
                       IFNULL(model_number,'') AS model_number,
                       IFNULL(rating,0) AS rating,
                       IFNULL(rating_count,0) AS rating_count,
                       IFNULL(photo_url,'') AS photo_url
                FROM vehicle WHERE availability_status='Available'
                ORDER BY rating DESC LIMIT 6
            """)
            vehicles_rated = cursor.fetchall()
        except Exception:
            vehicles_rated = []

        # doc verification status
        doc_status = None
        try:
            cursor.execute("""
                SELECT verification_status FROM user_documents WHERE user_id=%s
            """, (user_id,))
            doc_row = cursor.fetchone()
            doc_status = doc_row['verification_status'] if doc_row else None
        except Exception:
            doc_status = None

        # has bookings (for review show/hide)
        has_bookings = total_trips > 0

        cursor.close(); conn.close()
        return render_template("dashboard.html",
            user_name     = session['user_name'],
            bookings      = bookings,
            total_trips   = total_trips,
            confirmed     = confirmed,
            cancelled     = cancelled,
            completed     = completed,
            total_spent   = total_spent,
            user_reviews  = user_reviews,
            notifications = notifications,
            destinations  = destinations,
            vehicles_rated = vehicles_rated,
            doc_status    = doc_status,
            has_bookings  = has_bookings,
        )

    # ── SEARCH API ──
    @app.route('/api/search')
    def api_search():
        if 'user_id' not in session:
            return jsonify([])
        q = request.args.get('q', '').strip()
        if len(q) < 2:
            return jsonify([])
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        results = []
        try:
            cursor.execute("""
                SELECT 'destination' AS type, destination_name AS name,
                       state AS sub, destination_id AS id
                FROM destination
                WHERE destination_name LIKE %s OR state LIKE %s
                LIMIT 5
            """, (f'%{q}%', f'%{q}%'))
            results += cursor.fetchall()
            cursor.execute("""
                SELECT 'vehicle' AS type, vehicle_name AS name,
                       IFNULL(vehicle_type,'') AS sub, vehicle_id AS id
                FROM vehicle
                WHERE vehicle_name LIKE %s OR vehicle_type LIKE %s
                LIMIT 5
            """, (f'%{q}%', f'%{q}%'))
            results += cursor.fetchall()
        except Exception:
            pass
        cursor.close(); conn.close()
        return jsonify(results)

    # ── DOC VERIFICATION STATUS CHECK (polling) ──
    @app.route('/api/doc_status')
    def api_doc_status():
        if 'user_id' not in session:
            return jsonify({'status': 'unknown'})
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT verification_status FROM user_documents WHERE user_id=%s
            """, (session['user_id'],))
            row = cursor.fetchone()
            status = row['verification_status'] if row else 'none'
        except Exception:
            status = 'none'
        cursor.close(); conn.close()
        return jsonify({'status': status})

    # ── SUBMIT REVIEW ──
    @app.route('/submit_review', methods=['POST'])
    def submit_review():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        rating      = request.form.get('rating', 0, type=int)
        review_text = request.form.get('review_text', '').strip()
        category    = request.form.get('category', 'travelling')
        vehicle_id  = request.form.get('vehicle_id') or None
        user_id     = session['user_id']

        if not rating or not review_text:
            flash("Please provide a rating and review text.", "error")
            return redirect(url_for('profile'))

        conn   = get_db_connection()
        cursor = conn.cursor()
        safe_migrate(conn)
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS review (
                    review_id   INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    rating      TINYINT NOT NULL,
                    review_text TEXT NOT NULL,
                    category    VARCHAR(20) DEFAULT 'travelling',
                    vehicle_id  INT DEFAULT NULL,
                    created_at  DATETIME DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                INSERT INTO review (user_id, rating, review_text, category, vehicle_id, created_at)
                VALUES (%s,%s,%s,%s,%s,NOW())
            """, (user_id, rating, review_text, category, vehicle_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Review error:", e)
        finally:
            cursor.close(); conn.close()
        flash("Review submitted!", "success")
        return redirect(url_for('profile'))

    @app.route('/my_bookings')
    def my_bookings():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        today  = date.today()
        cursor.execute("""
            UPDATE booking SET booking_status='Completed'
            WHERE booking_status='Confirmed' AND travel_date <= %s
        """, (today,))
        conn.commit()
        cursor.execute("""
            SELECT b.booking_id, b.travel_date, b.booking_status,
                   d.destination_name, v.vehicle_name, v.vehicle_id, p.total_amount
            FROM booking b
            JOIN destination d ON b.destination_id=d.destination_id
            JOIN vehicle v     ON b.vehicle_id=v.vehicle_id
            JOIN pricing p     ON b.booking_id=p.booking_id
            WHERE b.user_id=%s ORDER BY b.travel_date DESC
        """, (session['user_id'],))
        bookings    = cursor.fetchall()
        total_trips = len(bookings)
        confirmed   = sum(1 for b in bookings if b['booking_status']=='Confirmed')
        cancelled   = sum(1 for b in bookings if b['booking_status']=='Cancelled')
        completed   = sum(1 for b in bookings if b['booking_status']=='Completed')
        total_spent = sum(b['total_amount'] for b in bookings)

        # already-rated booking IDs
        rated_ids = set()
        try:
            cursor.execute("SELECT booking_id FROM vehicle_rating WHERE user_id=%s", (session['user_id'],))
            rated_ids = {r['booking_id'] for r in cursor.fetchall()}
        except Exception:
            pass

        cursor.close(); conn.close()
        return render_template("my_bookings.html",
            bookings=bookings, total_trips=total_trips,
            confirmed=confirmed, cancelled=cancelled,
            completed=completed, total_spent=total_spent,
            rated_ids=rated_ids)

    @app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
    def cancel_booking(booking_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT booking_id, booking_status FROM booking
            WHERE booking_id=%s AND user_id=%s
        """, (booking_id, session['user_id']))
        booking = cursor.fetchone()
        if booking and booking['booking_status'] == 'Confirmed':
            cursor.execute("UPDATE booking SET booking_status='Cancelled' WHERE booking_id=%s", (booking_id,))
            conn.commit()
            flash("Booking cancelled.", "success")
        else:
            flash("Unable to cancel.", "error")
        cursor.close(); conn.close()
        return redirect(request.referrer or url_for('my_bookings'))

    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            name         = request.form.get('name', '').strip()
            phone        = request.form.get('phone_no', '').strip()
            new_password = request.form.get('password', '').strip()
            curr_pass    = request.form.get('current_password', '').strip()
            if new_password:
                cursor.execute("SELECT password FROM users WHERE user_id=%s", (session['user_id'],))
                row = cursor.fetchone()
                stored = row['password'] if row else ''
                valid  = check_password_hash(stored, curr_pass) if stored.startswith(('pbkdf2:', 'scrypt:')) else stored == curr_pass
                if not valid:
                    flash('Current password incorrect.', 'error')
                    return redirect(url_for('profile'))
                if len(new_password) < 8:
                    flash('New password must be 8+ chars.', 'error')
                    return redirect(url_for('profile'))
                hashed = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET name=%s, phone_no=%s, password=%s WHERE user_id=%s",
                               (name, phone, hashed, session['user_id']))
            else:
                cursor.execute("UPDATE users SET name=%s, phone_no=%s WHERE user_id=%s",
                               (name, phone, session['user_id']))
            conn.commit()
            session['user_name'] = name
            flash('Profile updated!', 'success')
            cursor.close(); conn.close()
            return redirect(url_for('profile'))

        cursor.execute("SELECT * FROM users WHERE user_id=%s", (session['user_id'],))
        user = cursor.fetchone()
        # bookings count for review eligibility
        cursor.execute("SELECT COUNT(*) AS cnt FROM booking WHERE user_id=%s", (session['user_id'],))
        booking_count = cursor.fetchone()['cnt']
        # vehicles for review dropdown
        vehicles = []
        try:
            cursor.execute("SELECT vehicle_id, vehicle_name FROM vehicle ORDER BY vehicle_name")
            vehicles = cursor.fetchall()
        except Exception:
            pass
        cursor.close(); conn.close()
        return render_template('profile.html', user=user, booking_count=booking_count, vehicles=vehicles)

    @app.route('/delete_account', methods=['POST'])
    def delete_account():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        uid  = session['user_id']
        conn = get_db_connection()
        cur  = conn.cursor()
        try:
            cur.execute("DELETE p FROM pricing p JOIN booking b ON p.booking_id=b.booking_id WHERE b.user_id=%s", (uid,))
            cur.execute("DELETE FROM booking WHERE user_id=%s", (uid,))
            try: cur.execute("DELETE FROM review WHERE user_id=%s", (uid,))
            except: pass
            cur.execute("DELETE FROM users WHERE user_id=%s", (uid,))
            conn.commit()
        except Exception as e:
            print(e)
        cur.close(); conn.close()
        session.clear()
        flash("Account deleted.", "success")
        return redirect(url_for('index'))

    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        session.clear()
        return redirect(url_for('index'))

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            conn = get_db_connection()
            cur  = conn.cursor()
            cur.execute("INSERT INTO contact (name,email,message) VALUES (%s,%s,%s)",
                        (request.form['name'], request.form['email'], request.form['message']))
            conn.commit()
            cur.close(); conn.close()
            flash("Message sent!")
            return redirect(url_for('index'))
        return redirect(url_for('index'))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000)
