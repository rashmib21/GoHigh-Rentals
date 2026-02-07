from faker import Faker
import mysql.connector
import random

# Initialize Faker
fake = Faker('en_In')

# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",     
    password="1234",
    database="GoHigh"
)

cursor = conn.cursor()

Vehicle_Hierarchy = {
    "Two Wheelers": ['Bike', 'Scooter', 'Gearless Scooter', 'Royal Enfield'],
    "Four Wheeler": ['Cars', 'Thar', 'Sedan', 'SUV', 'MUV', 'Electric Four Wheelers', 'Traveller']
}

Description = { "Bike": "A two-wheeled motor vehicle, commonly used for rugged terrain and narrow mountain roads.", 
"Scooter": "A lightweight two-wheeler with a step-through frame, generally used for short-distance commuting.", 
"Gearless Scooter": "A type of scooter without manual gear shifting, easy to ride in hilly conditions.", 
"Royal Enfield": "Iconic heavy motorcycle brand, popular for its durability and suitability for mountainous terrain.", 
"Cars": "General term for four-wheeled motor vehicles used for personal transport.", 
"Thar": "Mahindra Thar, a rugged SUV designed for off-road and tough terrain, ideal for mountainous regions.", 
"Sedan": "A comfortable four-door car with a separate trunk, suitable for smooth roads.", 
"SUV": "Sport Utility Vehicle, built for both on-road comfort and off-road capability, common in Himalayan travel.", 
"MUV": "Multi Utility Vehicle, spacious 4WD vehicles suited for carrying people and luggage over rough terrain.", 
"Electric Four Wheelers": "Four-wheeled vehicles powered by electricity, emerging as eco-friendly options for hilly areas.", 
"Traveller": "A minibus or van used for group transport, popular among tourists visiting mountainous regions." }

Base_Price = {
    "Bike": 100,
    "Scooter": 120,
    "Gearless Scooter": 120,
    "Royal Enfield": 180,
    "Cars": 250,
    "Thar": 550,
    "Sedan": 300,
    "SUV": 500,
    "MUV": 450,
    "Electric Four Wheelers": 350,
    "Traveller": 450
}

def vehicle_category():
    category = random.choice(list(Vehicle_Hierarchy.keys()))
    vehicle = random.choice(Vehicle_Hierarchy[category])
    return category, vehicle

total_records = 180

for i in range(total_records):

    category, vehicle = vehicle_category()
    description = Description[vehicle]
    fare = Base_Price[vehicle]

    print(category, vehicle, fare)

    sql = """
    INSERT INTO vehicle_category(category_name, description, base_fare)
    VALUES (%s, %s, %s)
    """

    values = (category, description, fare)

    cursor.execute(sql, values)

conn.commit()
print("Records inserted successfully")

cursor.close()
conn.close()
