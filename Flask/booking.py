@app.route('/dashboard')
def dashboard():
	conn=get_db_connection()
	cursor=conn.cursor()

	#number of trips 
	cursor.execute("SELECT COUNT(*) FROM bookings")
	total_trips=cursor.fetchone()[0]

	#Confirmed 
	cursor.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'")
	confirmed=cursor.fetchone()[0]

	#Cancelled 
	cursor.execute("SELECT COUNT(*) FROM bookings WHERE status='Cancelled'")
	cancelled=cursor.fetchone()[0]

	#Total Spent Money
	cursor.execute("SELECT SUM(amount)FROM bookings WHERE status='Confirmed'")
	total_spent=cursor.fetchone()[0]

	#Recent bookings
	cursor.execute("SELECT destination, vehicle, travel_date, status, amount from bookings ORDER By travel_date DESC LIMIT 5")
	bookings=cursor.fetchall()

	conn.close()

	return render_template('dashboard.html', 
		total_trips=total_trips,
		confirmed=confirmed,
		cancelled=cancelled,
		total_spent=total_spent,
		bookings=bookings
		)
