from faker import Faker
import mysql.connector
import random

# Initialize faker
fake=Faker('en_IN')

# database connections

conn=mysql.connector.connect(
	host="localhost",
	user="root",
	password="1234",
	database="GoHigh")

cursor=conn.cursor()


vehicles = [
    ("Honda Shine", "Bike", "Petrol", 2),
    ("TVS Ntorq", "Scooter", "Petrol", 2),
    ("Maruti Alto", "Hatchback", "Petrol", 5),
    ("Hyundai i20", "Hatchback", "Petrol", 5),
    ("Honda City", "Sedan", "Petrol", 5),
    ("Hyundai Creta", "SUV", "Diesel", 5),
    ("Toyota Innova", "MUV", "Diesel", 7),
    ("Tata Nexon EV", "Electric SUV", "Electric", 5),
    ("Royal Enfield Classic", "Bike", "Petrol", 2),
    ("Mahindra Thar", "Off-road SUV", "Diesel", 4),
]
cursor.execute("SELECT category_id FROM vehicle_category")
category_ids = [row[0] for row in cursor.fetchall()]


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

total_records=910
for i in range(total_records):
    name, vtype, fuel, seat=random.choice(vehicles)
    vehicle_number=realistic_vehicle_no()
    availability="Available"
    count=random.randint(1,10)

    cat_id = random.choice(category_ids)


    sql="""INSERT INTO vehicle(vehicle_name, vehicle_type, vehicle_number, fuel_type, seating_capacity, 
        availability_status, category_id, vehicle_count) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    values=(name, vtype, vehicle_number, fuel, seat, availability, cat_id, count)
    # print(values)
    
    cursor.execute(sql, values)

conn.commit()
print("Records inserted successfully")

cursor.close()
conn.close()    
