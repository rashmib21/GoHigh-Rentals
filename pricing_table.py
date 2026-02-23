from faker import Faker
import mysql.connector
import random

fake = Faker('en_IN')

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1234",
    database="GoHigh"
)

cursor = conn.cursor()

total_records = 910   

cursor.execute("SELECT vehicle_id, category_id FROM vehicle")
vehicle_map = {}

for row in cursor.fetchall():
    vehicle_map[row[0]] = row[1]

cursor.execute("SELECT category_id, base_fare FROM vehicle_category")
fare_map = {}

for row in cursor.fetchall():
    fare_map[row[0]] = row[1]

cursor.execute("SELECT booking_id, vehicle_id FROM booking")
bookings = cursor.fetchall()

inserted = 0

for row in bookings:

    if inserted >= total_records:
        break

    booking_id = row[0]
    vehicle_id = row[1]

    category_id = vehicle_map[vehicle_id]
    base = fare_map[category_id]

    tax = random.randint(10, 60)
    discount = random.choice([0, 10, 20, 25, 50])
    total = base + tax - discount

    sql = """INSERT INTO pricing
    (base_amount, tax_amount, discount, total_amount, pricing_type, booking_id)
    VALUES (%s, %s, %s, %s, %s, %s)"""

    values = (base, tax, discount, total, "Distance", booking_id)

    cursor.execute(sql, values)

    inserted += 1

conn.commit()

print(inserted, "records inserted successfully!")

cursor.close()
conn.close()
