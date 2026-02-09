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

Vehicle_Name = [ 
    'Honda Shine', 'TVS Ntorq', 'Maruti Alto', 'Hyundai i20', 'Honda City', 
    'Hyundai Creta', 'Toyota Innova', 'Tata Nexon EV', 'Royal Enfield Classic', 
    'Mahindra Thar' 
]
vehicle_type=[ 
    'Bike','Scooter','Hatchback','Hatchback','Sedan','SUV','MUV','Electric SUV','Bike','Off-road SUV' 
] 

def vehicle():
    
    index = random.randrange(len(Vehicle_Name))
    
    name = Vehicle_Name[index]
    v_type = vehicle_type[index]
    
    return name, v_type

# a = vehicle()
# print(a)

states=['HP','UK','JK','AR']
def realistic_vehicle_no():
    state=random.choice(states)
    rto=fake.random_int(min=1, max=99)
    series = fake.random_uppercase_letter() + fake.random_uppercase_letter()
    number = fake.random_int(min=1000, max=9999) 
    return f"{state} {rto:02d} {series} {number}"

# print(realistic_vehicle_no())

