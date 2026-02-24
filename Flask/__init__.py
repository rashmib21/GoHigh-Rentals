import os
from flask import Flask, render_template, request, redirect, session
from dotenv import load_dotenv
import mysql.connector


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY")
    print("Secret Key:", app.secret_key)

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
        print("User Data:", users)

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
            name = request.form['name']   # HTML field name="username"
            email = request.form['email']
            password = request.form['password']
            phone_no = request.form.get('phone_no')  # if you add phone field later

            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
            INSERT INTO users (name, email, phone_no, password)
            VALUES (%s, %s, %s, %s)
            """

            try:
                cursor.execute(query, (name, email, phone_no, password))
                conn.commit()
                message = "Registered Successfully"
            except mysql.connector.Error as err:
                message = f"Database Error: {err}"
            finally:
                cursor.close()
                conn.close()

            return message

        return render_template('register.html')      
    
    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            query = "SELECT * FROM users WHERE email=%s AND password=%s"
            cursor.execute(query, (email, password))

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                session['user_id'] = user['user_id']   
                session['user_name'] = user['name']
                return redirect('/dashboard')
            else:
                return "Invalid email or password"

        return render_template('login.html')   


    @app.route('/dashboard')
    def dashboard():
        print("Session In Dashboard:", session)
        if 'user_id' in session:
            return f"Welcome {session['user_name']}!"
        else:
            return redirect('/login')  

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000)