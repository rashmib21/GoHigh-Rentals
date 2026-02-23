import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    try:
        print("Trying to connect...")
        print("User:", os.getenv("DB_USER"))
        print("Database:", os.getenv("DB_NAME"))

        connection = mysql.connector.connect(
            host="localhost",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

        print("Connected Successfully")
        return connection

    except Exception as e:
        print("REAL ERROR IS:", e)
        return None