from faker import Faker
import mysql.connector
import random
from datetime import timedelta

fake = Faker('en_IN')

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="GoHigh"
)

cursor = conn.cursor()

statuses = ["Confirmed", "Completed", "Cancelled"]

total_records = 910

for i in range(total_records):

    booking_date = fake.date_between(start_date="today", end_date="+30d")
    travel_date = booking_date + timedelta(days=random.randint(1, 10))

    booking_status = random.choice(statuses)
    user_id = random.randint(1, 190)
    vehicle_id = random.randint(11, 190)
    destination_id = random.randint(1, 190)

    sql = """INSERT INTO booking
    (booking_date, travel_date, booking_status, user_id, vehicle_id, destination_id)
    VALUES (%s, %s, %s, %s, %s, %s)"""

    values = (booking_date, travel_date, booking_status, user_id, vehicle_id,destination_id)

    cursor.execute(sql, values)

conn.commit()

print("Booking data inserted successfully!")

cursor.close()
conn.close()
