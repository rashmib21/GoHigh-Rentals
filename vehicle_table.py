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

Vehicle_Name = {
	    [
			'Honda Shine',
			'TVS Ntorq',
			'Maruti Alto',
			'Hyundai i20',
			'Honda City',
			'Hyundai Creta',
			'Toyota Innova',
			'Tata Nexon EV',
			'Royal Enfield Classic',
			'Mahindra Thar'
		]
}
vehcile_type={
	[
		'Bike','Scooter','Hatchback','Hatchback','Sedan','SUV','MUV','Electric SUV','Bike','Off-road SUV'
	]
}