import os
from flask import Flask, render_template
from dotenv import load_dotenv
import mysql.connector

def create_app(test_config=None):
    load_dotenv()
    
    app = Flask(__name__)

    #  Set secret key (from .env file)
    app.secret_key = os.getenv("SECRET_KEY")

    # Get values from .env
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")

    # Connect to database
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    app.db = connection

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    @app.route('/')
    def index():
        return render_template("index.html")

    @app.route('/register', methods=['get', 'post'])
    def register():
        return render_template('register.html')    

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=9000)   