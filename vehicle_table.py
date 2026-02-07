from faker import Faker
import mysql.connector
import random

# Initialize faker
fake=Faker('en_IN')

# database connections

conn=mysql.connector.connect(
	host="localhost",
	username="root",
	password="1234",
	database="GoHigh")

cursor=conn.cursor()