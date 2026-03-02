import os
from flask import Flask, render_template, request, redirect, session, url_for
from dotenv import load_dotenv
import mysql.connector
import re
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash



def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")
    # print("Secret Key:", app.secret_key)

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
            email = request.form['email']
            phone_no = request.form['phone_no']
            password = request.form['password']

        
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
                    return "Email already registered!"

                if existing_user['phone_no'] == phone_no:
                    cursor.close()
                    conn.close()
                    return "Phone number already registered!"

           
            hashed_password = generate_password_hash(password)

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

            return redirect(url_for('dashboard'))

        return render_template('register.html')    
        
    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            print("Username: ",email)
            password = request.form['password']
            print("Password",password)

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM users WHERE email=%s AND password=%s"
            cursor.execute(query, (email, password))

            user = cursor.fetchone()
            # print(user)

            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user['user_id']   
                session['user_name'] = user['name']
                return redirect('/dashboard')
            else:
                return "Invalid email or password"

        return render_template('login.html')   


    # @app.route('/dashboard')
    # def dashboard():
    #     print("Session In Dashboard:", session)
    #     if 'user_id' in session:
    #         return f"Welcome {session['user_name']}!"
    #     else:
    #         return redirect('/login')  
    @app.route('/dashboard')
    def dashboard():
        if 'user_id' in session:
            return render_template("dashboard.html", user=session['user_name'])
        else:
            return redirect('/login')

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            message = request.form['message']

            connection = get_db_connection()
            cursor = connection.cursor()

            cursor.execute(
                "INSERT INTO contact (name, email, message) VALUES (%s, %s, %s)",
                (name, email, message)
            )

            connection.commit()
            cursor.close()
            connection.close()

            return "Message Sent Successfully!"

        return render_template("contact.html")  

    @app.route('/logout', methods=['GET','POST'])
    def logout():
        session.pop('user',None) #Remove user from session
        return redirect(url_for('index'))


    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000)