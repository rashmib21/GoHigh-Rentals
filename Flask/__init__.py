import os
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
    # print("Secret Key:", app.secret_key)

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
        # print("User Data:", users)

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
            print("Name: ", name)
            email = request.form['email']
            print("Email: ", email)
            phone_no = request.form['phone_no']
            print("Phone Number: ", phone_no)
            password = request.form['password']
            print("Password: ", password)

        
            if not name or not email or not phone_no or not password:
                return "All fields are required!"

           
            name_pattern = r'^[A-Za-z]{2,}(?:\s[A-Za-z]{2,})+$'
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$'
            phone_pattern = r'^[6-9][0-9]{9}$'
            password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&-]).{8,}$'

            if not re.match(name_pattern, name):
                return "Invalid name format"

            if not re.match(email_pattern, email):
                return "Invalid email format"

            if not re.match(phone_pattern, phone_no):
                return "Invalid phone number"

            if not re.match(password_pattern, password):
                return "Password must contain uppercase, lowercase, number and special character"

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True) #error: tuple indices must be integers or slices, not str

            cursor.execute("SELECT email, phone_no FROM users WHERE email=%s OR phone_no=%s",(email, phone_no))
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

            # 7️⃣ Insert user
            query = """
            INSERT INTO users (name, email, phone_no, password)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (name, email, phone_no, hashed_password))
            conn.commit()
            
            session['user_id'] = cursor.lastrowid
            session['user_name'] = name

            cursor.close()
            conn.close()

            flash("Registration successful!", "success")

            session['user_id'] = cursor.lastrowid
            session['user_name'] = name

            return redirect(url_for('dashboard'))

        return render_template('register.html')    
            
    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            print("Username: ", email)

            password = request.form['password']
            print("Password", password)

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM users WHERE email=%s"
            cursor.execute(query, (email,))

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                stored_password = user['password']

                # If password is hashed
                if stored_password.startswith('pbkdf2:') or stored_password.startswith('scrypt:'):
                    password_valid = check_password_hash(stored_password, password)

                # If password is plain text
                else:
                    password_valid = stored_password == password

                if password_valid:
                    session.clear()
                    session['user_id'] = user['user_id']
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

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            password = request.form['password']

            if password:
                cursor.execute("""
                    UPDATE users 
                    SET name=%s, phone=%s, password=%s 
                    WHERE user_id=%s
                """, (name, phone, password, session['user_id']))
            else:
                cursor.execute("""
                    UPDATE user 
                    SET name=%s, phone=%s 
                    WHERE user_id=%s
                """, (name, phone, session['user_id']))

            connection.commit()

        cursor.execute("SELECT * FROM users WHERE user_id=%s", (session['user_id'],))
        user = cursor.fetchone()

        cursor.close()
        connection.close()

        return render_template('profile.html', user=user)      


    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session:
            return redirect('/login')

        print("LOGGED IN USER ID:", session['user_id'])      

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

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
        JOIN vehicle v ON b.vehicle_id = v.vehicle_id
        JOIN pricing p ON b.booking_id = p.booking_id
        WHERE b.user_id = %s
        """

        cursor.execute(query, (session['user_id'],))
        bookings = cursor.fetchall()

        # Auto-update completed bookings
        today = date.today()
        for booking in bookings:
            travel_date = booking['travel_date']

            # Convert datetime to date if needed
            if hasattr(travel_date, 'date'):
                travel_date = travel_date.date()

            if travel_date < today and booking['booking_status'] == 'Confirmed':
                cursor.execute("""
                    UPDATE booking SET booking_status = 'Completed' 
                    WHERE booking_id = %s
                """, (booking['booking_id'],))
                booking['booking_status'] = 'Completed'  # update in memory too

        connection.commit()

        # Stats AFTER updating statuses
        total_trips = len(bookings)
        confirmed  = len([b for b in bookings if b['booking_status'] == 'Confirmed'])
        cancelled  = len([b for b in bookings if b['booking_status'] == 'Cancelled'])
        completed  = len([b for b in bookings if b['booking_status'] == 'Completed'])
        total_spent = sum(b['total_amount'] for b in bookings)

        cursor.close()
        connection.close()

        return render_template(
            "dashboard.html",
            user_name=session['user_name'],
            bookings=bookings,
            total_trips=total_trips,
            confirmed=confirmed,
            cancelled=cancelled,
            completed=completed,
            total_spent=total_spent
        )


    @app.route('/logout', methods=['GET','POST'])
    def logout():
        session.pop('user_id',None)
        session.pop('user_name', None) 
        return redirect(url_for('index'))


    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            message = request.form['message']

            connection = get_db_connection()
            cursor = connection.cursor()

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