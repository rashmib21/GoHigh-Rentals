from faker import Faker
import mysql.connector

# Initialize faker
fake=Faker('en_IN')

# database connections

conn=mysql.connector.connect(
	host="localhost",
	user="root",
	password="1234",
	database="GoHigh")

cursor=conn.cursor()

prices = [
()]