from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection

#create admin blueprint
admin_bp=Blueprint('admin', __name__)

#admin credentials
admin_username="admin"
admin_password="admin123"

#Admin logged in or not
def admin_required():
	return session.get('admin_logged_in')==True


#Login page of admin

@admin_bp.route("/admin/login", methods=['GET', 'POST'])
def admin_login():

	#if already logged in go to dashboard
	if admin_required():
		return redirect(url_for("admin.admin_dashboard"))

	if request.method=='POST':
		username=request.form.get("username")
		password=request.form.get("password")

		#Check credentials
		if username==admin_username and password==admin_password:
			session["admin_logged_in"]=True
			flash("Welcome back, Admin!", "success")
			return redirect(url_for("admin.admin_dashboard"))
		else:
			flash("Incorrect username or password", "error")

	return render_template("admin_login.html")	


# Logout of admin
@admin_bp.route("/admin/logout")
def admin_logout():
	session.pop("admin_logged_in", None)		
	flash("Logged out from admin panel.","success")
	return redirect(url_for("admin.admin_login"))

#Admin Dashboard

@admin_bp.route("/admin/dashboard")
def admin_dashboard():
	if not admin_required():
		return redirect(url_for("admin.admin_login"))

	conn=get_db_connection()
	cursor=conn.cursor(dictionary=True)

	#Count total users
	cursor.execute("SELECT COUNT(*) As total FROM users")
	total_users=cursor.fetchone()['total']	

	#Count all bookings
	cursor.execute("SELECT COUNT(*) As total from booking")
	total_bookings=cursor.fetchone()['total']

	#Count confirmed bookings
	cursor.execute("SELECT COUNT(*) As total from booking WHERE booking_status='Confirmed'")
	confirmed_bookings=cursor.fetchone()['total']

	#Count cancelled bookings
	cursor.execute("SELECT COUNT(*) As total from booking WHERE booking_status='Cancelled'")
	cancelled_bookings=cursor.fetchone()['total']

	#Count completed bookings 
	cursor.execute("SELECT COUNT(*) As total from booking WHERE booking_status='Completed'")
	completed_bookings=cursor.fetchone()['total']

	#Total amount from all bookings
	cursor.execute("SELECT SUM(total_amount) as revenue FROM pricing")
	result=cursor.fetchone()
	if result['revenue']:
	    total_revenue = result['revenue']
	else:
	    total_revenue = 0


	#Count contact inquires
	cursor.execute("SELECT COUNT(*) As total from contact")
	total_inquiries=cursor.fetchone()['total']

	#Count Vehicles
	cursor.execute("SELECT COUNT(*) As total from vehicle")
	total_vehicles=cursor.fetchone()['total']

	# Recent 5 bookings for dashboard preview
	cursor.execute("""
	    SELECT b.booking_id, b.travel_date, b.booking_status, b.booking_date,
	           u.name AS user_name,
	           d.destination_name,
	           v.vehicle_name
	    FROM booking b
	    JOIN users u ON b.user_id = u.user_id
	    JOIN destination d ON b.destination_id = d.destination_id
	    JOIN vehicle v ON b.vehicle_id = v.vehicle_id
	    ORDER BY b.booking_date DESC
	    LIMIT 5
	""")

	recent_bookings = cursor.fetchall()

	# Recent 5 contact inquiries for dashboard preview
	cursor.execute("SELECT * FROM contact ORDER BY id DESC LIMIT 5")
	recent_inquiries = cursor.fetchall()

	cursor.close()
	conn.close()

	return render_template("admin_dashboard.html",
	    total_users        = total_users,
	    total_bookings     = total_bookings,
	    confirmed_bookings = confirmed_bookings,
	    cancelled_bookings = cancelled_bookings,
	    completed_bookings = completed_bookings,
	    total_revenue      = total_revenue,
	    total_inquiries    = total_inquiries,
	    total_vehicles     = total_vehicles,
	    recent_bookings    = recent_bookings,
	    recent_inquiries   = recent_inquiries
	)
 
 
#Manage all booking
@admin_bp.route("/admin/bookings")
def admin_bookings():
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
 
    cursor.execute("""
        SELECT b.booking_id, b.travel_date, b.booking_status, b.booking_date,
               u.name  AS user_name,
               u.email AS user_email,
               d.destination_name,
               v.vehicle_name,
               p.total_amount
        FROM booking b
        JOIN users u       ON b.user_id       = u.user_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN pricing p     ON b.booking_id     = p.booking_id
        ORDER BY b.booking_date DESC
    """)
    bookings = cursor.fetchall()
 
    cursor.close()
    conn.close()
 
    return render_template("admin_bookings.html", bookings=bookings)
 
 
# Accept a booking
@admin_bp.route("/admin/booking/accept/<int:booking_id>", methods=["POST"])
def admin_accept_booking(booking_id):
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE booking
        SET booking_status = 'Confirmed',
        notified = 0
        WHERE booking_id = %s
    """, (booking_id,))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    flash(f"Booking #{booking_id} has been accepted!", "success")
    return redirect(url_for("admin.admin_bookings"))
 
 
#Cancel a booking
@admin_bp.route("/admin/booking/cancel/<int:booking_id>", methods=["POST"])
def admin_cancel_booking(booking_id):
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor()
 
    cursor.execute("""
        UPDATE booking
        SET booking_status = 'Cancelled',
        notified = 0
        WHERE booking_id = %s
    """, (booking_id,))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    flash(f"Booking #{booking_id} has been cancelled.", "success")
    return redirect(url_for("admin.admin_bookings"))
 
 
# Contact inquiry
@admin_bp.route("/admin/inquiries")
def admin_inquiries():
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
 
    cursor.execute("SELECT * FROM contact ORDER BY id DESC")
    inquiries = cursor.fetchall()
 
    cursor.close()
    conn.close()
 
    return render_template("admin_inquiries.html", inquiries=inquiries)
 
 
# Delete inquiry
@admin_bp.route("/admin/inquiry/delete/<int:inquiry_id>", methods=["POST"])
def admin_delete_inquiry(inquiry_id):
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor()
 
    cursor.execute("DELETE FROM contact WHERE id = %s", (inquiry_id,))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    flash("Inquiry deleted.", "success")
    return redirect(url_for("admin.admin_inquiries"))
 
 
#Manage Vehicle
@admin_bp.route("/admin/vehicles")
def admin_vehicles():
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
 
    # Real columns: vehicle_id, vehicle_name, vehicle_number, fuel_type,
    #               seating_capacity, availability_status, category_id,
    #               vehicle_count, vehicle_type
    cursor.execute("SELECT * FROM vehicle ORDER BY vehicle_id DESC")
    vehicles = cursor.fetchall()
 
    cursor.close()
    conn.close()
 
    return render_template("admin_vehicles.html", vehicles=vehicles)
 
 
#Add a new vehicle
@admin_bp.route("/admin/vehicle/add", methods=["GET", "POST"])
def admin_add_vehicle():
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    if request.method == "POST":
 
        # Form field names match vehicle table columns exactly
        vehicle_name        = request.form.get("vehicle_name")
        vehicle_number      = request.form.get("vehicle_number")
        vehicle_type        = request.form.get("vehicle_type")
        seating_capacity    = request.form.get("seating_capacity")
        fuel_type           = request.form.get("fuel_type")
        availability_status = request.form.get("availability_status", "Available")
        vehicle_count       = request.form.get("vehicle_count", 1)
        category_id         = request.form.get("category_id") or None  # optional
 
        conn   = get_db_connection()
        cursor = conn.cursor()
 
        cursor.execute("""
            INSERT INTO vehicle
                (vehicle_name, vehicle_number, vehicle_type, seating_capacity,
                 fuel_type, availability_status, vehicle_count, category_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (vehicle_name, vehicle_number, vehicle_type, seating_capacity,
              fuel_type, availability_status, vehicle_count, category_id))
 
        conn.commit()
        cursor.close()
        conn.close()
 
        flash(f"Vehicle '{vehicle_name}' added successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))
 
    return render_template("admin_add_vehicle.html")
 
 
# Edit a vehicle
@admin_bp.route("/admin/vehicle/edit/<int:vehicle_id>", methods=["GET", "POST"])
def admin_edit_vehicle(vehicle_id):
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
 
    if request.method == "POST":
 
        # Form field names match vehicle table columns exactly
        vehicle_name        = request.form.get("vehicle_name")
        vehicle_number      = request.form.get("vehicle_number")
        vehicle_type        = request.form.get("vehicle_type")
        seating_capacity    = request.form.get("seating_capacity")
        fuel_type           = request.form.get("fuel_type")
        availability_status = request.form.get("availability_status")
        vehicle_count       = request.form.get("vehicle_count")
        category_id         = request.form.get("category_id") or None
 
        cursor.execute("""
            UPDATE vehicle
            SET vehicle_name        = %s,
                vehicle_number      = %s,
                vehicle_type        = %s,
                seating_capacity    = %s,
                fuel_type           = %s,
                availability_status = %s,
                vehicle_count       = %s,
                category_id         = %s
            WHERE vehicle_id = %s
        """, (vehicle_name, vehicle_number, vehicle_type, seating_capacity,
              fuel_type, availability_status, vehicle_count, category_id,
              vehicle_id))
 
        conn.commit()
        cursor.close()
        conn.close()
 
        flash("Vehicle updated successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))
 
    # GET — load existing vehicle data to pre-fill the edit form
    cursor.execute("SELECT * FROM vehicle WHERE vehicle_id = %s", (vehicle_id,))
    vehicle = cursor.fetchone()
 
    cursor.close()
    conn.close()
 
    if not vehicle:
        flash("Vehicle not found.", "error")
        return redirect(url_for("admin.admin_vehicles"))
 
    return render_template("admin_edit_vehicle.html", vehicle=vehicle)
 
 

# Delete vehicle

@admin_bp.route("/admin/vehicle/delete/<int:vehicle_id>", methods=["POST"])
def admin_delete_vehicle(vehicle_id):
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor()
 
    cursor.execute("DELETE FROM vehicle WHERE vehicle_id = %s", (vehicle_id,))
 
    conn.commit()
    cursor.close()
    conn.close()
 
    flash("Vehicle deleted.", "success")
    return redirect(url_for("admin.admin_vehicles"))
 
 
#   MANAGE USERS (View Only)
@admin_bp.route("/admin/users")
def admin_users():
 
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
 
    cursor.execute("SELECT user_id, name, email, phone_no FROM users ORDER BY user_id DESC")
    users = cursor.fetchall()
 
    cursor.close()
    conn.close()
 
    return render_template("admin_users.html", users=users)
 
