import mysql.connector
from faker import Faker

#Initialize faker
fake=Faker('en_IN')

#Database connection details
conn=mysql.connector.connect(
	host="localhost",
	user="root",
	password="1234",
	database="GoHigh")

cursor=conn.cursor()

#Define the number of records to generate
total_records=910

#Loop to generate and insert data
for i in range(total_records):
	name=fake.name()
	email=fake.email()
	phone_no=fake.phone_number()
	#print(phone_no)
	password=fake.password(length=10)
	#print(password)
	created_at=fake.date_time_this_year()
	#print(created_at)

	sql="""Insert into users(name, email, phone_no, password, created_at) values (%s,%s,%s,%s,%s)"""
	values=(name, email, phone_no, password, created_at)
	cursor.execute(sql,values)

# Commit changes and close connection
conn.commit()
print(f"{cursor.rowcount} records inserted.")
cursor.close()
conn.close()	
