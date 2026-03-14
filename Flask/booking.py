from flask import Blueprint, render_template, request, redirect, session
from .db import get_db_connection
from datetime import date, timedelta

booking_bp = Blueprint("booking", __name__)

# Dashboard Route
@booking_bp.route("/dashboard")
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    user_name = session.get('user_name')
    user_id = session['user_id']  

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Auto-update past confirmed bookings to Completed
    today = date.today()
    cursor.execute("""
        UPDATE booking 
        SET booking_status = 'Completed' 
        WHERE booking_status = 'Confirmed' 
        AND travel_date <= %s
    """, (today,))
    conn.commit()

    # Recent bookings - filtered by user
    cursor.execute("""
        SELECT 
            b.booking_id,        
            b.travel_date,
            b.booking_status,
            d.destination_name,
            v.vehicle_name,
            p.total_amount
        FROM booking b
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v ON b.vehicle_id = v.vehicle_id
        LEFT JOIN pricing p ON b.booking_id = p.booking_id
        WHERE b.user_id = %s
        ORDER BY b.travel_date DESC
        LIMIT 5
    """, (user_id,))
    bookings = cursor.fetchall()

    #  Stats calculated from bookings list
    total_trips = len(bookings)
    confirmed   = len([b for b in bookings if b['booking_status'] == 'Confirmed'])
    cancelled   = len([b for b in bookings if b['booking_status'] == 'Cancelled'])
    completed   = len([b for b in bookings if b['booking_status'] == 'Completed'])
    total_spent = sum(b['total_amount'] for b in bookings if b['total_amount'])

    conn.close()

    return render_template(
        "dashboard.html",
        user_name=user_name,
        total_trips=total_trips,
        confirmed=confirmed,
        cancelled=cancelled,
        completed=completed,   
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

    #Block past and previous dates
    min_allowed = date.today() + timedelta(days=1)
    if date.fromisoformat(travel_date) < min_allowed:
        return "Invalid date! Please select a future date.", 400


    user_id = session["user_id"]

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # ── Booking limit: max 3 confirmed bookings per user ──
    cursor.execute("""
        SELECT COUNT(*) as active_count FROM booking
        WHERE user_id = %s AND booking_status = 'Confirmed'
    """, (user_id,))
    count = cursor.fetchone()['active_count']
    if count >= 3:
        cursor.close()
        conn.close()
        return """
        <html><body style="font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#f0f5f8;">
        <div style="text-align:center;background:#fff;padding:40px;border-radius:20px;box-shadow:0 8px 32px rgba(0,0,0,.1);max-width:420px;">
          <div style="font-size:3rem;margin-bottom:12px;">⚠️</div>
          <h2 style="color:#c0392b;margin-bottom:8px;">Booking Limit Reached</h2>
          <p style="color:#888;margin-bottom:24px;">You already have 3 active bookings. Please cancel an existing booking before making a new one.</p>
          <a href="/my_bookings" style="display:inline-block;padding:12px 28px;background:#1C2B3A;color:#fff;border-radius:12px;text-decoration:none;font-weight:700;">View My Bookings</a>
        </div></body></html>
        """, 400

    cursor = conn.cursor()
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


#===========Cancel the booking by user==============
@booking_bp.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Only cancel if it belongs to the logged-in user
    cursor.execute("""
        UPDATE booking 
        SET booking_status = 'Cancelled'
        WHERE booking_id = %s AND user_id = %s
    """, (booking_id, session['user_id']))

    conn.commit()
    conn.close()

    return redirect('/dashboard')