# ─────────────────────────────────────────────
# __init__.py  –  Main Flask application
# ─────────────────────────────────────────────
# This file creates the Flask app and defines
# all user-facing routes (register, login,
# dashboard, profile, bookings, reviews, etc.)
# ─────────────────────────────────────────────

import os
import re
from datetime import date, datetime, timedelta
from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
from dotenv import load_dotenv
import mysql.connector
from werkzeug.security import check_password_hash, generate_password_hash
from .booking import booking_bp
from .admin import admin_bp


# Upload folder for user documents (Aadhaar, DL)
UPLOAD_DOCS = None


def create_app():
    """Create and configure the Flask application."""

    load_dotenv()

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "gohigh_secret_2024")

    # Session settings
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

    # Set up upload folders
    global UPLOAD_DOCS
    UPLOAD_DOCS = os.path.join(app.root_path, "static", "uploads", "documents")
    os.makedirs(UPLOAD_DOCS, exist_ok=True)
    os.makedirs(os.path.join(app.root_path, "static", "uploads", "vehicle_photos"), exist_ok=True)

    # Register blueprints (admin.py and booking.py routes)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # ──────────────────────────────────────
    # Helper: Connect to the database
    # ──────────────────────────────────────
    def get_db_connection():
        """Connect to MySQL. Returns connection or None."""
        try:
            return mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )
        except Exception as e:
            print("DB error:", e)
            return None

    # ──────────────────────────────────────
    # Route: Home page
    # ──────────────────────────────────────
    @app.route('/')
    def index():
        return render_template("home.html")

    # ──────────────────────────────────────
    # Route: User Registration
    # ──────────────────────────────────────
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            # Get form data
            name     = request.form.get('name', '').strip()
            email    = request.form.get('email', '').strip()
            phone_no = request.form.get('phone_no', '').strip()
            password = request.form.get('password', '').strip()

            # Check all fields are filled
            if not all([name, email, phone_no, password]):
                flash("All fields are required!", "error")
                return render_template('register.html')

            # Validate name (must have first + last name, letters only)
            if not re.match(r'^[A-Za-z]{2,}(?:\s[A-Za-z]{2,})+$', name):
                flash("Enter full name (first + last name, letters only).", "error")
                return render_template('register.html')

            # Validate email length
            if len(email) > 60:
                flash("Email must be 60 characters or fewer.", "error")
                return render_template('register.html')

            # Validate email format
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9._%+-]*@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$', email):
                flash("Invalid email format.", "error")
                return render_template('register.html')

            # Validate phone (10 digits, starts with 6-9)
            if not re.match(r'^[6-9][0-9]{9}$', phone_no):
                flash("Invalid phone number. Must be 10 digits starting with 6–9.", "error")
                return render_template('register.html')

            # No 4 same digits in a row
            if re.search(r'(\d)\1{3,}', phone_no):
                flash("Phone number cannot have the same digit repeated 4+ times.", "error")
                return render_template('register.html')

            # Validate password strength
            if not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&\-]).{8,}$', password):
                flash("Password: 8+ chars, upper+lower+digit+special.", "error")
                return render_template('register.html')

            # Connect to database
            conn = get_db_connection()
            if conn is None:
                flash("Database unavailable. Please try again later.", "error")
                return render_template('register.html')
            cursor = conn.cursor(dictionary=True)

            # Check if email or phone already exists
            cursor.execute("SELECT email, phone_no FROM users WHERE email=%s OR phone_no=%s", (email, phone_no))
            existing = cursor.fetchone()
            if existing:
                if existing['email'] == email:
                    flash("Email already registered!", "error")
                else:
                    flash("Phone already registered!", "error")
                cursor.close()
                conn.close()
                return render_template('register.html')

            # Hash password and save user
            hashed = generate_password_hash(password)
            session.clear()
            cursor.execute(
                "INSERT INTO users (name, email, phone_no, password) VALUES (%s,%s,%s,%s)",
                (name, email, phone_no, hashed)
            )
            conn.commit()

            # Set session and redirect to dashboard
            session['user_id']   = cursor.lastrowid
            session['user_name'] = name
            cursor.close()
            conn.close()
            flash("Registration successful!", "success")
            return redirect(url_for('dashboard'))

        return render_template('register.html')

    # ──────────────────────────────────────
    # Route: User Login
    # ──────────────────────────────────────
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()

            conn   = get_db_connection()
            if conn is None:
                flash("Database unavailable. Please try again later.", "error")
                return render_template("login.html")
            cursor = conn.cursor(dictionary=True)

            # Find user by email
            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                stored = user['password']
                # Check if password is hashed or plain text
                if stored.startswith(('pbkdf2:', 'scrypt:')):
                    valid = check_password_hash(stored, password)
                else:
                    valid = (stored == password)

                if valid:
                    session.clear()
                    session['user_id']   = user['user_id']
                    session['user_name'] = user['name']
                    flash("Login successful!", "success")
                    return redirect('/dashboard')

            flash("Invalid email or password.", "error")
        return render_template("login.html")

    # ──────────────────────────────────────
    # Route: Admin Registration
    # ──────────────────────────────────────
    @app.route('/admin/register', methods=['GET', 'POST'])
    def admin_register():
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email    = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            secret   = request.form.get('admin_secret', '').strip()

            # Verify admin secret key
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
            if conn is None:
                flash("Database unavailable. Please try again later.", "error")
                return render_template('admin_register.html')
            cursor = conn.cursor()

            try:
                hashed = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO admin_accounts (username, email, password) VALUES (%s,%s,%s)",
                    (username, email, hashed)
                )
                conn.commit()
                flash("Admin account created! You can now log in.", "success")
                return redirect(url_for('admin.admin_login'))
            except Exception:
                flash("Username or email already exists.", "error")
            finally:
                cursor.close()
                conn.close()

        return render_template('admin_register.html')

    # ──────────────────────────────────────
    # Route: User Dashboard
    # ──────────────────────────────────────
    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        conn    = get_db_connection()
        if conn is None:
            flash("Database unavailable. Please try again later.", "error")
            return redirect(url_for('login'))
        cursor  = conn.cursor(dictionary=True)

        # Auto-complete confirmed bookings whose travel date has passed
        today = date.today()
        cursor.execute("""
            UPDATE booking SET booking_status='Completed'
            WHERE booking_status='Confirmed' AND travel_date <= %s
        """, (today,))
        conn.commit()

        # Get notifications (bookings that were confirmed or cancelled)
        cursor.execute("""
            SELECT b.booking_id, b.booking_status, d.destination_name
            FROM booking b JOIN destination d ON b.destination_id=d.destination_id
            WHERE b.user_id=%s AND b.booking_status IN ('Confirmed','Cancelled') AND b.notified=0
        """, (user_id,))
        notifications = cursor.fetchall()

        # Mark notifications as read
        if notifications:
            cursor.execute("""
                UPDATE booking SET notified=1
                WHERE user_id=%s AND booking_status IN ('Confirmed','Cancelled') AND notified=0
            """, (user_id,))
            conn.commit()

        # Get recent bookings
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

        # Calculate stats
        total_trips = len(bookings)
        confirmed   = sum(1 for b in bookings if b['booking_status'] == 'Confirmed')
        cancelled   = sum(1 for b in bookings if b['booking_status'] == 'Cancelled')
        completed   = sum(1 for b in bookings if b['booking_status'] == 'Completed')
        total_spent = sum(b['total_amount'] for b in bookings)

        # Get recent reviews
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

        # Get active destinations
        cursor.execute("""
            SELECT destination_id, destination_name, state, price_per_day, price_per_hour
            FROM destination WHERE is_active=1 ORDER BY destination_id
        """)
        destinations = cursor.fetchall()

        # Get top-rated vehicles
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

        # Check document verification status
        doc_status = None
        try:
            cursor.execute("""
                SELECT verification_status FROM user_documents WHERE user_id=%s
            """, (user_id,))
            doc_row = cursor.fetchone()
            if doc_row:
                doc_status = doc_row['verification_status']
        except Exception:
            doc_status = None

        # Check if user has any bookings (for review eligibility)
        has_bookings = total_trips > 0

        cursor.close()
        conn.close()

        return render_template("dashboard.html",
            user_name      = session['user_name'],
            bookings       = bookings,
            total_trips    = total_trips,
            confirmed      = confirmed,
            cancelled      = cancelled,
            completed      = completed,
            total_spent    = total_spent,
            user_reviews   = user_reviews,
            notifications  = notifications,
            destinations   = destinations,
            vehicles_rated = vehicles_rated,
            doc_status     = doc_status,
            has_bookings   = has_bookings,
        )

    # ──────────────────────────────────────
    # Route: Search API (destinations + vehicles)
    # ──────────────────────────────────────
    @app.route('/api/search')
    def api_search():
        if 'user_id' not in session:
            return jsonify([])

        q = request.args.get('q', '').strip()
        if len(q) < 2:
            return jsonify([])

        conn   = get_db_connection()
        if conn is None:
            return jsonify([])
        cursor = conn.cursor(dictionary=True)

        results = []
        try:
            # Search destinations
            cursor.execute("""
                SELECT 'destination' AS type, destination_name AS name,
                       state AS sub, destination_id AS id
                FROM destination
                WHERE destination_name LIKE %s OR state LIKE %s
                LIMIT 5
            """, (f'%{q}%', f'%{q}%'))
            results += cursor.fetchall()

            # Search vehicles
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

        cursor.close()
        conn.close()
        return jsonify(results)

    # ──────────────────────────────────────
    # Route: Document status check (polling)
    # ──────────────────────────────────────
    @app.route('/api/doc_status')
    def api_doc_status():
        if 'user_id' not in session:
            return jsonify({'status': 'unknown'})

        conn   = get_db_connection()
        if conn is None:
            return jsonify({'status': 'none'})
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT verification_status FROM user_documents WHERE user_id=%s
            """, (session['user_id'],))
            row = cursor.fetchone()
            if row:
                status = row['verification_status']
            else:
                status = 'none'
        except Exception:
            status = 'none'

        cursor.close()
        conn.close()
        return jsonify({'status': status})

    # ──────────────────────────────────────
    # Route: Submit a Review
    # ──────────────────────────────────────
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
        if conn is None:
            flash("Database unavailable. Please try again later.", "error")
            return redirect(url_for('profile'))
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO review (user_id, rating, review_text, category, vehicle_id, created_at)
                VALUES (%s,%s,%s,%s,%s,NOW())
            """, (user_id, rating, review_text, category, vehicle_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print("Review error:", e)
        finally:
            cursor.close()
            conn.close()

        flash("Review submitted!", "success")
        return redirect(url_for('profile'))

    # ──────────────────────────────────────
    # Route: My Bookings
    # ──────────────────────────────────────
    @app.route('/my_bookings')
    def my_bookings():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn   = get_db_connection()
        if conn is None:
            flash("Database unavailable. Please try again later.", "error")
            return redirect(url_for('login'))
        cursor = conn.cursor(dictionary=True)

        # Auto-complete past bookings
        today = date.today()
        cursor.execute("""
            UPDATE booking SET booking_status='Completed'
            WHERE booking_status='Confirmed' AND travel_date <= %s
        """, (today,))
        conn.commit()

        # Get all bookings for this user
        cursor.execute("""
            SELECT b.booking_id, b.travel_date, b.booking_status,
                   d.destination_name, v.vehicle_name, v.vehicle_id, p.total_amount
            FROM booking b
            JOIN destination d ON b.destination_id=d.destination_id
            JOIN vehicle v     ON b.vehicle_id=v.vehicle_id
            JOIN pricing p     ON b.booking_id=p.booking_id
            WHERE b.user_id=%s ORDER BY b.travel_date DESC
        """, (session['user_id'],))
        bookings = cursor.fetchall()

        # Calculate stats
        total_trips = len(bookings)
        confirmed   = sum(1 for b in bookings if b['booking_status'] == 'Confirmed')
        cancelled   = sum(1 for b in bookings if b['booking_status'] == 'Cancelled')
        completed   = sum(1 for b in bookings if b['booking_status'] == 'Completed')
        total_spent = sum(b['total_amount'] for b in bookings)

        # Get list of already-rated booking IDs
        rated_ids = set()
        try:
            cursor.execute("SELECT booking_id FROM vehicle_rating WHERE user_id=%s", (session['user_id'],))
            rated_ids = {r['booking_id'] for r in cursor.fetchall()}
        except Exception:
            pass

        cursor.close()
        conn.close()

        return render_template("my_bookings.html",
            bookings=bookings, total_trips=total_trips,
            confirmed=confirmed, cancelled=cancelled,
            completed=completed, total_spent=total_spent,
            rated_ids=rated_ids)

    # ──────────────────────────────────────
    # Route: Cancel Booking (user side)
    # ──────────────────────────────────────
    @app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
    def cancel_booking(booking_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn   = get_db_connection()
        if conn is None:
            flash("Database unavailable. Please try again later.", "error")
            return redirect(url_for('login'))
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

        cursor.close()
        conn.close()
        return redirect(request.referrer or url_for('my_bookings'))

    # ──────────────────────────────────────
    # Route: User Profile
    # ──────────────────────────────────────
    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        conn   = get_db_connection()
        if conn is None:
            flash("Database unavailable. Please try again later.", "error")
            return redirect(url_for('login'))
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            name         = request.form.get('name', '').strip()
            phone        = request.form.get('phone_no', '').strip()
            new_password = request.form.get('password', '').strip()
            curr_pass    = request.form.get('current_password', '').strip()

            # If user wants to change password
            if new_password:
                cursor.execute("SELECT password FROM users WHERE user_id=%s", (session['user_id'],))
                row    = cursor.fetchone()
                stored = row['password'] if row else ''

                # Verify current password
                if stored.startswith(('pbkdf2:', 'scrypt:')):
                    valid = check_password_hash(stored, curr_pass)
                else:
                    valid = (stored == curr_pass)

                if not valid:
                    flash('Current password incorrect.', 'error')
                    cursor.close()
                    conn.close()
                    return redirect(url_for('profile'))

                if len(new_password) < 8:
                    flash('New password must be 8+ chars.', 'error')
                    cursor.close()
                    conn.close()
                    return redirect(url_for('profile'))

                hashed = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET name=%s, phone_no=%s, password=%s WHERE user_id=%s",
                    (name, phone, hashed, session['user_id'])
                )
            else:
                # Just update name and phone
                cursor.execute(
                    "UPDATE users SET name=%s, phone_no=%s WHERE user_id=%s",
                    (name, phone, session['user_id'])
                )

            conn.commit()
            session['user_name'] = name
            flash('Profile updated!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # GET request: load profile data
        cursor.execute("SELECT * FROM users WHERE user_id=%s", (session['user_id'],))
        user = cursor.fetchone()

        # Count bookings for review eligibility
        cursor.execute("SELECT COUNT(*) AS cnt FROM booking WHERE user_id=%s", (session['user_id'],))
        booking_count = cursor.fetchone()['cnt']

        # Get vehicles for review dropdown
        vehicles = []
        try:
            cursor.execute("SELECT vehicle_id, vehicle_name FROM vehicle ORDER BY vehicle_name")
            vehicles = cursor.fetchall()
        except Exception:
            pass

        cursor.close()
        conn.close()
        return render_template('profile.html', user=user, booking_count=booking_count, vehicles=vehicles)

    # ──────────────────────────────────────
    # Route: Delete Account
    # ──────────────────────────────────────
    @app.route('/delete_account', methods=['POST'])
    def delete_account():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        uid  = session['user_id']
        conn = get_db_connection()
        if conn is None:
            flash("Database unavailable.", "error")
            return redirect(url_for('profile'))
        cur = conn.cursor()

        try:
            # Delete pricing records for this user's bookings
            cur.execute("DELETE p FROM pricing p JOIN booking b ON p.booking_id=b.booking_id WHERE b.user_id=%s", (uid,))
            # Delete bookings
            cur.execute("DELETE FROM booking WHERE user_id=%s", (uid,))
            # Delete reviews
            try:
                cur.execute("DELETE FROM review WHERE user_id=%s", (uid,))
            except Exception:
                pass
            # Delete user
            cur.execute("DELETE FROM users WHERE user_id=%s", (uid,))
            conn.commit()
        except Exception as e:
            print(e)

        cur.close()
        conn.close()
        session.clear()
        flash("Account deleted.", "success")
        return redirect(url_for('index'))

    # ──────────────────────────────────────
    # Route: Logout
    # ──────────────────────────────────────
    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        session.clear()
        return redirect(url_for('index'))

    # ──────────────────────────────────────
    # Route: Contact Form
    # ──────────────────────────────────────
    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            conn = get_db_connection()
            if conn is None:
                flash("Database unavailable.", "error")
                return redirect(url_for('index'))
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO contact (name,email,message) VALUES (%s,%s,%s)",
                (request.form['name'], request.form['email'], request.form['message'])
            )
            conn.commit()
            cur.close()
            conn.close()
            flash("Message sent!")
            return redirect(url_for('index'))
        return redirect(url_for('index'))

    return app


# ──────────────────────────────────────
# Run the app directly (python __init__.py)
# ──────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000)
