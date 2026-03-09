from flask import Blueprint, render_template, request, redirect, session
from db import get_db_connection
from datetime import date

booking_bp = Blueprint("booking", __name__)

# Dashboard Route
@booking_bp.route("/dashboard")
def dashboard():

	if 'user_id' not in session:
		return redirect('/login')

	user_name = session.get('user_name')


	conn = get_db_connection()
	cursor = conn.cursor(dictionary=True)

	# Total trips
	cursor.execute("""
	SELECT COUNT(*) AS total_trips
	FROM booking
	""")
	result = cursor.fetchone()
	total_trips = result['total_trips']

	# Confirmed bookings
	cursor.execute("""
	SELECT COUNT(*) AS confirmed
	FROM booking
	WHERE booking_status='Confirmed'
	""")
	confirmed = cursor.fetchone()['confirmed']

	# Cancelled bookings
	cursor.execute("""
	SELECT COUNT(*) AS cancelled
	FROM booking
	WHERE booking_status='Cancelled'
	""")
	cancelled = cursor.fetchone()['cancelled']

	# Total spent
	cursor.execute("""
	SELECT COALESCE(SUM(p.total_amount),0) AS total_spent
	FROM booking b
	LEFT JOIN pricing p ON b.booking_id = p.booking_id
	WHERE b.booking_status='Confirmed'
	""")
	total_spent = cursor.fetchone()['total_spent']

	# Recent bookings
	cursor.execute("""
	SELECT 
	d.destination_name,
	v.vehicle_name,
	b.travel_date,
	b.booking_status,
	p.total_amount
	FROM booking b
	JOIN destination d ON b.destination_id = d.destination_id
	JOIN vehicle v ON b.vehicle_id = v.vehicle_id
	LEFT JOIN pricing p ON b.booking_id = p.booking_id
	ORDER BY b.travel_date DESC
	LIMIT 5
	""")

	bookings = cursor.fetchall()

	conn.close()

	return render_template(
	    "dashboard.html",
	    user_name=user_name,
	    total_trips=total_trips,
	    confirmed=confirmed,
	    cancelled=cancelled,
	    total_spent=total_spent,
	    bookings=bookings
	)


# Create Booking Route
@booking_bp.route("/create_booking", methods=["POST"])
def create_booking():

    destination_id = request.form["destination_id"]
    vehicle_id = request.form["vehicle_id"]
    travel_date = request.form["travel_date"]

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bookings
        (destination_id, vehicle_id, travel_date, booking_status, user_id)
        VALUES (%s,%s,%s,'Pending',%s)
    """,(destination_id, vehicle_id, travel_date, user_id))

    conn.commit()
    conn.close()

    return redirect("/dashboard")


#========================Create New booking of book now buttons=====================================
@booking_bp.route("/new_booking")
def create_booking_page():

    selected_destination_id = request.args.get("destination_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM destination")
    destinations = cursor.fetchall()

    cursor.execute("SELECT * FROM vehicle")
    vehicles = cursor.fetchall()

    conn.close()

    return render_template(
        "new_booking.html",
        destinations=destinations,
        vehicles=vehicles,
        selected_destination_id=selected_destination_id
    )
