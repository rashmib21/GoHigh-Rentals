import os
from flask import Flask
from dotenv import load_dotenv
import mysql.connector

def create_app(test_config=None):
    load_dotenv()
    
    app = Flask(__name__)

    # Get values from .env
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")


    # print("Host:", host)
    # print("User:", user)

    # Connect to database
    connection = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )

    app.db = connection   # Attach DB to app

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    @app.route('/')
    def welcome():
        return "Welcome to GoHigh Rentals"

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port="9000")