from faker import Faker
import mysql.connector
import random
from faker_vehicle import VehicleProvider


#Initialize Faker 
fake=Faker('en_In')

#Datebase connection details
conn=mysql.connector.connect(
	host="localhost",
	username="root",
	password="1234",
	database="GoHigh")
cursor=conn.cursor()

#Define the number of records
total_records=180 
for i in range(total_records):
	#category_name = fake.add_provider(VehicleProvider)
	category_name = fake.vehicle_category()
	print(category_name)
	description=fake.vehicle.vehicle()
	base_fare=faker.random_int(min=100, max=1000)
	print(base_fare)
	

	sql="""Insert into destination(category_name, description, base_fare) values (%s, %s, %s)"""
	values=(category_name, description, base_fare)
	cursor.execute(sql, values)

# Commit changes and close connection
conn.commit()
print(f"{cursor.rowcount} records inserted.")
cursor.close()
conn.close()
