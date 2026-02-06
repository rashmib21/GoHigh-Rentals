from faker import Faker
import mysql.connector

#Initialize Faker 
fake=Faker('en_In')

#Datebase connection details
conn=mysql.connector('GoHigh')
cursor=conn.cursor()