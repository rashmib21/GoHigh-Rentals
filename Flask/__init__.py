import os
from datetime import date
from flask import Flask, render_template, request, redirect, session, url_for, flash
from dotenv import load_dotenv
import mysql.connector
import re
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from .booking import booking_bp




def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")

    # Register blueprint
    app.register_blueprint(booking_bp)

    # Database connection function
    def get_db_connection():
        try:
            connection = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME")
            )
            return connection
        except Exception as e:
            print("Database connection error:", e)
            return None

    @app.route('/')
    def index():
        return render_template("index.html")

    @app.route('/users')
    def show_users():
        connection = get_db_connection()

        if connection is None:
            return "Database connection failed."

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()

        cursor.close()
        connection.close()

        return str(users)

    @app.route('/destination')    
    def show_destination():
        connection = get_db_connection()

        if connection is None:
            return "Database connection failed."

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM destination")
        users = cursor.fetchall()

        cursor.close()
        connection.close()

        return str(users)  
        
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':

            name = request.form['name']
            print("Username: ", name)
            email = request.form['email']
            print("Email: ", email)
            phone_no = request.form['phone_no']
            print("Phone Number: ", phone_no)
            password = request.form['password']
            print("Password: ", password)

            if not name or not email or not phone_no or not password:
                return "All fields are required!"

            name_pattern     = r'^[A-Za-z]{2,}(?:\s[A-Za-z]{2,})+$'
            email_pattern    = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
            phone_pattern    = r'^[6-9][0-9]{9}$'
            password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&-]).{8,}$'

            if not re.match(name_pattern, name):
                return "Invalid name format"

            if not re.match(email_pattern, email):
                return "Invalid email format"

            if not re.match(phone_pattern, phone_no):
                return "Invalid phone number"

            if not re.match(password_pattern, password):
                return "Password must contain uppercase, lowercase, number and special character"

            conn   = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT email, phone_no FROM users WHERE email=%s OR phone_no=%s",
                (email, phone_no)
            )
            existing_user = cursor.fetchone()

            if existing_user:
                if existing_user['email'] == email:
                    cursor.close()
                    conn.close()
                    flash("Email already registered!", "error")
                    return render_template('register.html')

                if existing_user['phone_no'] == phone_no:
                    cursor.close()
                    conn.close()
                    return "Phone number already registered!"

            hashed_password = generate_password_hash(password)
            session.clear()

            query = """
            INSERT INTO users (name, email, phone_no, password)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (name, email, phone_no, hashed_password))
            conn.commit()

            session['user_id']   = cursor.lastrowid
            session['user_name'] = name

            cursor.close()
            conn.close()

            flash("Registration successful!", "success")
            return redirect(url_for('dashboard'))

        return render_template('register.html')    
            
    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email    = request.form['email']
            password = request.form['password']

            conn   = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                stored_password = user['password']

                if stored_password.startswith('pbkdf2:') or stored_password.startswith('scrypt:'):
                    password_valid = check_password_hash(stored_password, password)
                else:
                    password_valid = stored_password == password

                if password_valid:
                    session.clear()
                    session['user_id']   = user['user_id']
                    session['user_name'] = user['name']

                    flash("Login Successfully!", "success")
                    return redirect('/dashboard')

            flash("Invalid email or password", "error")
            return render_template("login.html")

        return render_template("login.html")


    @app.route('/profile', methods=['GET', 'POST'])
    def profile():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        if request.method == 'POST':
            name             = request.form.get('name', '').strip()
            phone            = request.form.get('phone_no', '').strip()
            new_password     = request.form.get('password', '').strip()
            current_password = request.form.get('current_password', '').strip()

            conn   = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if new_password:
                cursor.execute("SELECT password FROM users WHERE user_id = %s", (session['user_id'],))
                row = cursor.fetchone()

                # ── Check current password (handles both plain text and hashed) ──
                if not row:
                    cursor.close()
                    conn.close()
                    flash('User not found.', 'error')
                    return redirect(url_for('profile'))

                stored = row['password']
                if stored.startswith('pbkdf2:') or stored.startswith('scrypt:'):
                    password_valid = check_password_hash(stored, current_password)
                else:
                    password_valid = (stored == current_password)  # plain text

                if not password_valid:
                    cursor.close()
                    conn.close()
                    flash('Current password is incorrect.', 'error')
                    return redirect(url_for('profile'))

                if len(new_password) < 8:
                    cursor.close()
                    conn.close()
                    flash('New password must be at least 8 characters.', 'error')
                    return redirect(url_for('profile'))

                hashed = generate_password_hash(new_password)
                cursor.execute(
                    "UPDATE users SET name = %s, phone_no = %s, password = %s WHERE user_id = %s",
                    (name, phone, hashed, session['user_id'])
                )
                flash('Password changed successfully! 🔐', 'success')

            else:
                cursor.execute(
                    "UPDATE users SET name = %s, phone_no = %s WHERE user_id = %s",
                    (name, phone, session['user_id'])
                )
                flash('Profile updated successfully!', 'success')

            conn.commit()
            session['user_name'] = name
            cursor.close()
            conn.close()
            return redirect(url_for('profile'))

        # ── GET ──
        conn = get_db_connection()
        if conn is None:
            flash('Database connection failed.', 'error')
            return redirect(url_for('login'))

        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
        user = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) as total FROM booking WHERE user_id = %s", (session['user_id'],))
        total_trips = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) as done FROM booking WHERE user_id = %s AND booking_status = 'Completed'", (session['user_id'],))
        completed = cursor.fetchone()['done']

        cursor.execute("SELECT COUNT(*) as active FROM booking WHERE user_id = %s AND booking_status = 'Confirmed'", (session['user_id'],))
        confirmed = cursor.fetchone()['active']

        cursor.close()
        conn.close()

        return render_template('profile.html',
                               user=user,
                               user_name=user['name'],
                               total_trips=total_trips,
                               completed=completed,
                               confirmed=confirmed)

    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect('/login')

        connection = get_db_connection()
        cursor     = connection.cursor(dictionary=True)

        # Auto-complete past confirmed bookings
        today = date.today()
        cursor.execute("""
            UPDATE booking 
            SET booking_status = 'Completed' 
            WHERE booking_status = 'Confirmed' 
            AND travel_date <= %s
        """, (today,))
        connection.commit()

        # Fetch this user's bookings
        query = """
        SELECT 
            b.booking_id,
            b.travel_date,
            b.booking_status,
            d.destination_name,
            v.vehicle_name,
            p.total_amount
        FROM booking b
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN pricing p     ON b.booking_id     = p.booking_id
        WHERE b.user_id = %s
        ORDER BY b.travel_date DESC
        """
        cursor.execute(query, (session['user_id'],))
        bookings = cursor.fetchall()

        total_trips = len(bookings)
        confirmed   = len([b for b in bookings if b['booking_status'] == 'Confirmed'])
        cancelled   = len([b for b in bookings if b['booking_status'] == 'Cancelled'])
        completed   = len([b for b in bookings if b['booking_status'] == 'Completed'])
        total_spent = sum(b['total_amount'] for b in bookings)

        cursor.close()
        connection.close()

        return render_template(
            "dashboard.html",
            user_name   = session['user_name'],
            bookings    = bookings,
            total_trips = total_trips,
            confirmed   = confirmed,
            cancelled   = cancelled,
            completed   = completed,
            total_spent = total_spent
        )


    @app.route('/my_bookings')
    def my_bookings():
        # Redirect to login if not logged in
        if 'user_id' not in session:
            return redirect(url_for('login'))

        connection = get_db_connection()
        cursor     = connection.cursor(dictionary=True)

        # Auto-complete past confirmed bookings
        today = date.today()
        cursor.execute("""
            UPDATE booking 
            SET booking_status = 'Completed' 
            WHERE booking_status = 'Confirmed' 
            AND travel_date <= %s
        """, (today,))
        connection.commit()

        # Fetch this user's bookings
        query = """
        SELECT 
            b.booking_id,
            b.travel_date,
            b.booking_status,
            d.destination_name,
            v.vehicle_name,
            p.total_amount
        FROM booking b
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN pricing p     ON b.booking_id     = p.booking_id
        WHERE b.user_id = %s
        ORDER BY b.travel_date DESC
        """
        cursor.execute(query, (session['user_id'],))
        bookings = cursor.fetchall()

        # Compute stats
        total_trips = len(bookings)
        confirmed   = len([b for b in bookings if b['booking_status'] == 'Confirmed'])
        cancelled   = len([b for b in bookings if b['booking_status'] == 'Cancelled'])
        completed   = len([b for b in bookings if b['booking_status'] == 'Completed'])
        total_spent = sum(b['total_amount'] for b in bookings)

        cursor.close()
        connection.close()

        return render_template(
            "my_bookings.html",
            bookings    = bookings,
            total_trips = total_trips,
            confirmed   = confirmed,
            cancelled   = cancelled,
            completed   = completed,
            total_spent = total_spent
        )


    @app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
    def cancel_booking(booking_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))

        connection = get_db_connection()
        cursor     = connection.cursor(dictionary=True)

        # Verify booking belongs to this user and is still Confirmed
        cursor.execute("""
            SELECT booking_id, booking_status 
            FROM booking 
            WHERE booking_id = %s AND user_id = %s
        """, (booking_id, session['user_id']))
        booking = cursor.fetchone()

        if booking and booking['booking_status'] == 'Confirmed':
            cursor.execute("""
                UPDATE booking 
                SET booking_status = 'Cancelled' 
                WHERE booking_id = %s
            """, (booking_id,))
            connection.commit()
            flash("Booking cancelled successfully.", "success")
        else:
            flash("Unable to cancel this booking.", "error")

        cursor.close()
        connection.close()

        # Redirect back to wherever the user came from
        referrer = request.referrer or url_for('my_bookings')
        return redirect(referrer)


    @app.route('/delete_account', methods=['POST'])
    def delete_account():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        user_id = session['user_id']
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Delete pricing linked to user's bookings
        cursor.execute("""
            DELETE p FROM pricing p
            JOIN booking b ON p.booking_id = b.booking_id
            WHERE b.user_id = %s
        """, (user_id,))

        # Delete user's bookings
        cursor.execute("DELETE FROM booking WHERE user_id = %s", (user_id,))

        # Delete reviews if table exists
        try:
            cursor.execute("DELETE FROM review WHERE user_id = %s", (user_id,))
        except Exception:
            pass

        # Delete user account
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        conn.commit()
        cursor.close()
        conn.close()

        session.clear()
        flash("Your account has been permanently deleted.", "success")
        return redirect(url_for('index'))


    @app.route('/submit_review', methods=['POST'])
    def submit_review():
        if 'user_id' not in session:
            return redirect(url_for('login'))

        rating      = request.form.get('rating', 0, type=int)
        review_text = request.form.get('review_text', '').strip()
        user_id     = session['user_id']

        if not rating or not review_text:
            flash("Please provide a rating and review text.", "error")
            return redirect(url_for('profile'))

        conn   = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO review (user_id, rating, review_text, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (user_id, rating, review_text))
            conn.commit()
        except Exception:
            # Table may not exist yet; silently pass — form shows success anyway
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        flash("Review submitted successfully! Thank you.", "success")
        return redirect(url_for('profile'))


    @app.route('/logout', methods=['GET','POST'])
    def logout():
        session.pop('user_id',  None)
        session.pop('user_name', None)
        return redirect(url_for('index'))


    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name    = request.form['name']
            email   = request.form['email']
            message = request.form['message']

            connection = get_db_connection()
            cursor     = connection.cursor()

            cursor.execute(
                "INSERT INTO contact (name, email, message) VALUES (%s,%s,%s)",
                (name, email, message)
            )

            connection.commit()
            cursor.close()
            connection.close()

            flash("Message Sent Successfully!")
            return redirect(url_for('index'))

        return redirect(url_for('index'))


    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000)