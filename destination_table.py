from faker import Faker
import mysql.connector
import random

#Initialize Faker 
fake=Faker('en_In')

#Datebase connection details
conn=mysql.connector.connect(
	host="localhost",
	username="root",
	password="1234",
	database="GoHigh")
cursor=conn.cursor()

#Define the number of records to generate
total_records=90

#Loop to generate and insert data
for i in range(total_records):
	destination_name=fake.city()
	state=fake.state()
	print(f"Destination: {destination_name}, {state}")
	distance_km=random.randint(0, 2000)
	print(distance_km)
	is_active=True

	sql="""Insert into destination(destination_name, state, distance_km, is_active) values (%s, %s, %s, %s)"""
	values=(destination_name, state, distance_km, is_active)
	cursor.execute(sql, values)

# Commit changes and close connection
conn.commit()
print(f"{cursor.rowcount} records inserted.")
cursor.close()
conn.close()
