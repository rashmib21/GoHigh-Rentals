from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection

admin_bp = Blueprint('admin', __name__)

admin_username = "admin"
admin_password = "admin123"


def admin_required():
    return session.get('admin_logged_in') == True


@admin_bp.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if admin_required():
        return redirect(url_for("admin.admin_dashboard"))

    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        if username == admin_username and password == admin_password:
            session["admin_logged_in"] = True
            flash("Welcome back, Admin!", "success")
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("Incorrect username or password", "error")

    return render_template("admin_login.html")


@admin_bp.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("Logged out from admin panel.", "success")
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM booking")
    total_bookings = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM booking WHERE booking_status='Confirmed'")
    confirmed_bookings = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM booking WHERE booking_status='Cancelled'")
    cancelled_bookings = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM booking WHERE booking_status='Completed'")
    completed_bookings = cursor.fetchone()['total']

    cursor.execute("SELECT SUM(total_amount) AS revenue FROM pricing")
    result = cursor.fetchone()
    total_revenue = result['revenue'] if result['revenue'] else 0

    cursor.execute("SELECT COUNT(*) AS total FROM contact")
    total_inquiries = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM vehicle")
    total_vehicles = cursor.fetchone()['total']

    cursor.execute("""
        SELECT b.booking_id, b.travel_date, b.booking_status, b.booking_date,
               u.name AS user_name, d.destination_name, v.vehicle_name
        FROM booking b
        JOIN users u       ON b.user_id       = u.user_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        ORDER BY b.booking_date DESC LIMIT 5
    """)
    recent_bookings = cursor.fetchall()

    cursor.execute("SELECT * FROM contact ORDER BY id DESC LIMIT 5")
    recent_inquiries = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total FROM booking
        WHERE booking_status='Cancelled' AND cancelled_by='user' AND admin_notified=0
    """)
    user_cancelled_count = cursor.fetchone()['total']

    cursor.close()
    conn.close()

    return render_template("admin_dashboard.html",
        total_users          = total_users,
        total_bookings       = total_bookings,
        confirmed_bookings   = confirmed_bookings,
        cancelled_bookings   = cancelled_bookings,
        completed_bookings   = completed_bookings,
        total_revenue        = total_revenue,
        total_inquiries      = total_inquiries,
        total_vehicles       = total_vehicles,
        recent_bookings      = recent_bookings,
        recent_inquiries     = recent_inquiries,
        user_cancelled_count = user_cancelled_count,
    )


# ── MANAGE BOOKINGS WITH FILTERS ──
@admin_bp.route("/admin/bookings")
def admin_bookings():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    f_status    = request.args.get("status", "")
    f_vehicle   = request.args.get("vehicle", "")
    f_date_from = request.args.get("date_from", "")
    f_date_to   = request.args.get("date_to", "")

    query = """
        SELECT b.booking_id, b.travel_date, b.booking_status, b.booking_date,
               b.cancelled_by, b.admin_notified,
               u.name AS user_name, u.email AS user_email,
               d.destination_name, v.vehicle_name,
               p.total_amount, p.pricing_type,
               p.duration_value, p.duration_unit,
               p.cancellation_deduction, p.refund_amount, p.cancellation_pct
        FROM booking b
        JOIN users u       ON b.user_id       = u.user_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN pricing p     ON b.booking_id     = p.booking_id
        WHERE 1=1
    """
    params = []

    if f_status:
        query += " AND b.booking_status = %s"; params.append(f_status)
    if f_vehicle:
        query += " AND v.vehicle_name = %s";   params.append(f_vehicle)
    if f_date_from:
        query += " AND b.travel_date >= %s";   params.append(f_date_from)
    if f_date_to:
        query += " AND b.travel_date <= %s";   params.append(f_date_to)

    query += " ORDER BY b.booking_date DESC"
    cursor.execute(query, params)
    bookings = cursor.fetchall()

    cursor.execute("SELECT DISTINCT vehicle_name FROM vehicle ORDER BY vehicle_name")
    vehicles = cursor.fetchall()

    cursor.execute("""
        SELECT b.booking_id, u.name AS user_name, b.travel_date, d.destination_name
        FROM booking b
        JOIN users u       ON b.user_id       = u.user_id
        JOIN destination d ON b.destination_id = d.destination_id
        WHERE b.booking_status='Cancelled' AND b.cancelled_by='user' AND b.admin_notified=0
    """)
    pending_cancel_notices = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_bookings.html",
        bookings               = bookings,
        vehicles               = vehicles,
        pending_cancel_notices = pending_cancel_notices,
        f_status               = f_status,
        f_vehicle              = f_vehicle,
        f_date_from            = f_date_from,
        f_date_to              = f_date_to,
    )


@admin_bp.route("/admin/booking/dismiss_cancel/<int:booking_id>", methods=["POST"])
def admin_dismiss_cancel(booking_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE booking SET admin_notified=1 WHERE booking_id=%s", (booking_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash(f"Notification for booking #{booking_id} dismissed.", "success")
    return redirect(url_for("admin.admin_bookings"))


# ── FIX 2: ACCEPT — only for Pending bookings ──
@admin_bp.route("/admin/booking/accept/<int:booking_id>", methods=["POST"])
def admin_accept_booking(booking_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT booking_status, cancelled_by FROM booking WHERE booking_id=%s", (booking_id,))
    booking = cursor.fetchone()

    # Block if user cancelled
    if booking and booking['booking_status'] == 'Cancelled' and booking['cancelled_by'] == 'user':
        flash(f"Booking #{booking_id} was cancelled by the user and cannot be modified.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))

    # Only Pending can be accepted
    if booking and booking['booking_status'] != 'Pending':
        flash(f"Only Pending bookings can be accepted.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))

    cursor.execute("""
        UPDATE booking SET booking_status='Confirmed', notified=0
        WHERE booking_id=%s
    """, (booking_id,))
    conn.commit()
    cursor.close(); conn.close()

    flash(f"Booking #{booking_id} has been accepted!", "success")
    return redirect(url_for("admin.admin_bookings"))


# ── FIX 2: ADMIN CANCEL — only for Pending, NOT after Confirmed ──
@admin_bp.route("/admin/booking/cancel/<int:booking_id>", methods=["POST"])
def admin_cancel_booking(booking_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT booking_status, cancelled_by FROM booking WHERE booking_id=%s", (booking_id,))
    booking = cursor.fetchone()

    # Block if user cancelled
    if booking and booking['booking_status'] == 'Cancelled' and booking['cancelled_by'] == 'user':
        flash(f"Booking #{booking_id} was already cancelled by the user.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))

    # FIX 2: Admin CANNOT cancel after Confirmed
    if booking and booking['booking_status'] == 'Confirmed':
        flash(f"Booking #{booking_id} is already Confirmed and cannot be cancelled by admin.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))

    # FIX 2: Only Pending can be cancelled by admin
    if booking and booking['booking_status'] != 'Pending':
        flash(f"Only Pending bookings can be cancelled.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))

    cursor.execute("""
        UPDATE booking SET booking_status='Cancelled', cancelled_by='admin', notified=0
        WHERE booking_id=%s
    """, (booking_id,))
    conn.commit()
    cursor.close(); conn.close()

    flash(f"Booking #{booking_id} has been cancelled.", "success")
    return redirect(url_for("admin.admin_bookings"))


@admin_bp.route("/admin/inquiries")
def admin_inquiries():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM contact ORDER BY id DESC")
    inquiries = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template("admin_inquiries.html", inquiries=inquiries)


@admin_bp.route("/admin/inquiry/delete/<int:inquiry_id>", methods=["POST"])
def admin_delete_inquiry(inquiry_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM contact WHERE id=%s", (inquiry_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash("Inquiry deleted.", "success")
    return redirect(url_for("admin.admin_inquiries"))


@admin_bp.route("/admin/vehicles")
def admin_vehicles():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vehicle ORDER BY vehicle_id DESC")
    vehicles = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template("admin_vehicles.html", vehicles=vehicles)


@admin_bp.route("/admin/vehicle/add", methods=["GET", "POST"])
def admin_add_vehicle():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    if request.method == "POST":
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehicle
                (vehicle_name, vehicle_number, vehicle_type, seating_capacity,
                 fuel_type, availability_status, vehicle_count, category_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form.get("vehicle_name"),
            request.form.get("vehicle_number"),
            request.form.get("vehicle_type"),
            request.form.get("seating_capacity"),
            request.form.get("fuel_type"),
            request.form.get("availability_status", "Available"),
            request.form.get("vehicle_count", 1),
            request.form.get("category_id") or None
        ))
        conn.commit()
        cursor.close(); conn.close()
        flash(f"Vehicle added successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))
    return render_template("admin_add_vehicle.html")


@admin_bp.route("/admin/vehicle/edit/<int:vehicle_id>", methods=["GET", "POST"])
def admin_edit_vehicle(vehicle_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        cursor.execute("""
            UPDATE vehicle
            SET vehicle_name=%s, vehicle_number=%s, vehicle_type=%s,
                seating_capacity=%s, fuel_type=%s, availability_status=%s,
                vehicle_count=%s, category_id=%s
            WHERE vehicle_id=%s
        """, (
            request.form.get("vehicle_name"),
            request.form.get("vehicle_number"),
            request.form.get("vehicle_type"),
            request.form.get("seating_capacity"),
            request.form.get("fuel_type"),
            request.form.get("availability_status"),
            request.form.get("vehicle_count"),
            request.form.get("category_id") or None,
            vehicle_id
        ))
        conn.commit()
        cursor.close(); conn.close()
        flash("Vehicle updated successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))
    cursor.execute("SELECT * FROM vehicle WHERE vehicle_id=%s", (vehicle_id,))
    vehicle = cursor.fetchone()
    cursor.close(); conn.close()
    if not vehicle:
        flash("Vehicle not found.", "error")
        return redirect(url_for("admin.admin_vehicles"))
    return render_template("admin_edit_vehicle.html", vehicle=vehicle)


@admin_bp.route("/admin/vehicle/delete/<int:vehicle_id>", methods=["POST"])
def admin_delete_vehicle(vehicle_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM vehicle WHERE vehicle_id=%s", (vehicle_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash("Vehicle deleted.", "success")
    return redirect(url_for("admin.admin_vehicles"))


@admin_bp.route("/admin/users")
def admin_users():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name, email, phone_no FROM users ORDER BY user_id DESC")
    users = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template("admin_users.html", users=users)


@admin_bp.route("/admin/user/delete/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE p FROM pricing p
        JOIN booking b ON p.booking_id = b.booking_id
        WHERE b.user_id=%s
    """, (user_id,))
    cursor.execute("DELETE FROM booking WHERE user_id=%s", (user_id,))
    cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash("User and all associated bookings deleted.", "success")
    return redirect(url_for("admin.admin_users"))