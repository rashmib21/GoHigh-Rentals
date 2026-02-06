from faker import Faker
import mysql.connector

#Initialize Faker 
fake=Faker('en_In')

#Datebase connection details
conn=mysql.connector('GoHigh')
cursor=conn.cursor()

#Define the number of records to generate
total_records=90

#Loop to generate and insert data
for i in range(total_records):

