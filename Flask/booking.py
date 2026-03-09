from flask import Blueprint, render_template, request, redirect, session
from .db import get_db_connection
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
from flask import url_for

@booking_bp.route("/create_booking", methods=["POST"])
def create_booking():

    if "user_id" not in session:
        return redirect("/login")

    destination_id = request.form.get("destination_id")
    vehicle_id = request.form.get("vehicle_id")
    travel_date = request.form.get("travel_date")

    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert booking
    cursor.execute("""
    INSERT INTO booking
    (destination_id, vehicle_id, travel_date, booking_status, user_id, booking_date)
    VALUES (%s,%s,%s,'Confirmed',%s,%s)
    """,(destination_id, vehicle_id, travel_date, user_id, date.today()))

    conn.commit()

    booking_id = cursor.lastrowid   # get inserted booking id

    # Example pricing calculation
    base_amount = 300
    tax_amount = base_amount * 0.10
    discount = 0
    total_amount = base_amount + tax_amount - discount

    # Insert pricing
    cursor.execute("""
    INSERT INTO pricing
    (base_amount, tax_amount, discount, total_amount, pricing_type, booking_id)
    VALUES (%s,%s,%s,%s,'Distance',%s)
    """,(base_amount, tax_amount, discount, total_amount, booking_id))

    conn.commit()
    conn.close()

    # Redirect to bill page
    return redirect(url_for("booking.show_bill", booking_id=booking_id))


#========================Create New booking of book now buttons=====================================
@booking_bp.route("/new_booking")
def create_booking_page():

    destination_id = request.args.get('destination_id', type=int)

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
        selected_destination_id=str(destination_id) if destination_id else None
    )


#==========Generate bill all calculations are displayed here========

@booking_bp.route("/bill/<int:booking_id>")
def show_bill(booking_id):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, b.travel_date, d.destination_name, v.vehicle_name
        FROM pricing p
        JOIN booking b ON p.booking_id = b.booking_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v ON b.vehicle_id = v.vehicle_id
        WHERE p.booking_id=%s
    """, (booking_id,))

    bill = cursor.fetchone()

    conn.close()

    return render_template("bill.html", bill=bill) 