import os
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection
from werkzeug.utils import secure_filename

admin_bp = Blueprint('admin', __name__)

admin_username = "admin"
admin_password = "admin123"

VEHICLE_PHOTO_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads", "vehicle_photos")
ALLOWED_PHOTO_EXT    = {"png", "jpg", "jpeg", "webp"}


def allowed_photo(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PHOTO_EXT


def admin_required():
    return session.get('admin_logged_in') == True


@admin_bp.route("/admin/login", methods=['GET', 'POST'])
def admin_login():
    if admin_required():
        return redirect(url_for("admin.admin_dashboard"))
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        # Try DB-based admin accounts first
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        admin_found = False
        try:
            cursor.execute("SELECT * FROM admin_accounts WHERE username=%s OR email=%s", (username, username))
            admin = cursor.fetchone()
            if admin:
                from werkzeug.security import check_password_hash
                stored = admin['password']
                if check_password_hash(stored, password) or stored == password:
                    session["admin_logged_in"] = True
                    session["admin_username"]  = admin['username']
                    flash(f"Welcome back, {admin['username']}!", "success")
                    admin_found = True
        except Exception:
            pass
        finally:
            cursor.close(); conn.close()
        # Fallback to hardcoded admin
        if not admin_found:
            if username == admin_username and password == admin_password:
                session["admin_logged_in"] = True
                session["admin_username"]  = "admin"
                flash("Welcome back, Admin!", "success")
                admin_found = True
        if admin_found:
            return redirect(url_for("admin.admin_dashboard"))
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
    # Pending document verifications
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM user_documents WHERE verified=0")
        pending_docs = cursor.fetchone()['total']
    except Exception:
        pending_docs = 0
    cursor.close(); conn.close()
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
        pending_docs         = pending_docs,
    )


# ── MANAGE BOOKINGS ──
@admin_bp.route("/admin/bookings")
def admin_bookings():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    f_status    = request.args.get("status",    "")
    f_vehicle   = request.args.get("vehicle",   "")
    f_date_from = request.args.get("date_from", "")
    f_date_to   = request.args.get("date_to",   "")
    query = """
        SELECT b.booking_id, b.travel_date, b.booking_status, b.booking_date,
               b.cancelled_by, b.admin_notified,
               IFNULL(b.security_deposit, 0) AS security_deposit,
               IFNULL(b.agreement_signed, 0) AS agreement_signed,
               u.name AS user_name, u.email AS user_email,
               d.destination_name, v.vehicle_name,
               IFNULL(v.vehicle_type, '') AS vehicle_type,
               p.total_amount, p.pricing_type, p.duration_value, p.duration_unit,
               IFNULL(p.payment_mode, 'Online') AS payment_mode,
               p.cancellation_deduction, p.refund_amount, p.cancellation_pct
        FROM booking b
        JOIN users u       ON b.user_id       = u.user_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN pricing p     ON b.booking_id     = p.booking_id
        WHERE 1=1
    """
    params = []
    if f_status:    query += " AND b.booking_status=%s"; params.append(f_status)
    if f_vehicle:   query += " AND v.vehicle_name=%s";   params.append(f_vehicle)
    if f_date_from: query += " AND b.travel_date>=%s";   params.append(f_date_from)
    if f_date_to:   query += " AND b.travel_date<=%s";   params.append(f_date_to)
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
    cursor.close(); conn.close()
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


@admin_bp.route("/admin/booking/accept/<int:booking_id>", methods=["POST"])
def admin_accept_booking(booking_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT booking_status, cancelled_by FROM booking WHERE booking_id=%s", (booking_id,))
    booking = cursor.fetchone()
    if booking and booking['booking_status'] == 'Cancelled' and booking['cancelled_by'] == 'user':
        flash(f"Booking #{booking_id} was cancelled by the user and cannot be modified.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))
    if booking and booking['booking_status'] != 'Pending':
        flash(f"Only Pending bookings can be accepted.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))
    cursor.execute("UPDATE booking SET booking_status='Confirmed' WHERE booking_id=%s", (booking_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash(f"Booking #{booking_id} confirmed.", "success")
    return redirect(url_for("admin.admin_bookings"))


@admin_bp.route("/admin/booking/cancel/<int:booking_id>", methods=["POST"])
def admin_cancel_booking(booking_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT booking_status, cancelled_by FROM booking WHERE booking_id=%s", (booking_id,))
    booking = cursor.fetchone()
    if booking and booking['booking_status'] == 'Cancelled' and booking['cancelled_by'] == 'user':
        flash(f"Booking #{booking_id} was cancelled by user.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))
    if booking and booking['booking_status'] == 'Confirmed':
        flash(f"Booking #{booking_id} is Confirmed and cannot be cancelled by admin.", "error")
        cursor.close(); conn.close()
        return redirect(url_for("admin.admin_bookings"))
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
    flash(f"Booking #{booking_id} cancelled.", "success")
    return redirect(url_for("admin.admin_bookings"))


# ── MANAGE VEHICLES ──
@admin_bp.route("/admin/vehicles")
def admin_vehicles():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT vehicle_id, vehicle_name, vehicle_number, vehicle_type,
               seating_capacity, fuel_type, availability_status, vehicle_count,
               IFNULL(model_number, '') AS model_number,
               IFNULL(vehicle_condition, 'Good') AS vehicle_condition,
               IFNULL(known_faults, '') AS known_faults,
               IFNULL(photo_url, '') AS photo_url,
               IFNULL(rating, 0) AS rating,
               IFNULL(rating_count, 0) AS rating_count,
               IFNULL(price_per_day, 0) AS price_per_day,
               IFNULL(price_per_hour, 0) AS price_per_hour
        FROM vehicle ORDER BY vehicle_id DESC
    """)
    vehicles = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template("admin_vehicles.html", vehicles=vehicles)


@admin_bp.route("/admin/vehicle/add", methods=["GET", "POST"])
def admin_add_vehicle():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    if request.method == "POST":
        os.makedirs(VEHICLE_PHOTO_FOLDER, exist_ok=True)
        photo_filename = None
        photo_file = request.files.get("photo_file")
        if photo_file and photo_file.filename and allowed_photo(photo_file.filename):
            ext            = photo_file.filename.rsplit(".", 1)[1].lower()
            photo_filename = secure_filename(f"vehicle_{request.form.get('vehicle_number','unknown')}.{ext}")
            photo_file.save(os.path.join(VEHICLE_PHOTO_FOLDER, photo_filename))
            photo_url = f"/static/uploads/vehicle_photos/{photo_filename}"
        else:
            photo_url = None

        conn   = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO vehicle
                    (vehicle_name, vehicle_number, vehicle_type, seating_capacity,
                     fuel_type, availability_status, vehicle_count, category_id,
                     model_number, vehicle_condition, known_faults, photo_url,
                     price_per_day, price_per_hour)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                request.form.get("vehicle_name"),
                request.form.get("vehicle_number"),
                request.form.get("vehicle_type"),
                request.form.get("seating_capacity"),
                request.form.get("fuel_type"),
                request.form.get("availability_status", "Available"),
                request.form.get("vehicle_count", 1),
                request.form.get("category_id") or None,
                request.form.get("model_number") or None,
                request.form.get("vehicle_condition", "Good"),
                request.form.get("known_faults") or None,
                photo_url,
                request.form.get("price_per_day") or None,
                request.form.get("price_per_hour") or None,
            ))
        except Exception:
            # Fallback: insert without new columns (run migration_v2.sql to enable all features)
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
                request.form.get("category_id") or None,
            ))
        conn.commit()
        cursor.close(); conn.close()
        flash("Vehicle added successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))
    return render_template("admin_add_vehicle.html")


@admin_bp.route("/admin/vehicle/edit/<int:vehicle_id>", methods=["GET", "POST"])
def admin_edit_vehicle(vehicle_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        os.makedirs(VEHICLE_PHOTO_FOLDER, exist_ok=True)
        photo_url = None
        photo_file = request.files.get("photo_file")
        if photo_file and photo_file.filename and allowed_photo(photo_file.filename):
            ext       = photo_file.filename.rsplit(".", 1)[1].lower()
            fname     = secure_filename(f"vehicle_{vehicle_id}.{ext}")
            photo_file.save(os.path.join(VEHICLE_PHOTO_FOLDER, fname))
            photo_url = f"/static/uploads/vehicle_photos/{fname}"

        try:
            if photo_url:
                cursor.execute("""
                    UPDATE vehicle
                    SET vehicle_name=%s, vehicle_number=%s, vehicle_type=%s,
                        seating_capacity=%s, fuel_type=%s, availability_status=%s,
                        vehicle_count=%s, category_id=%s,
                        model_number=%s, vehicle_condition=%s, known_faults=%s,
                        photo_url=%s, price_per_day=%s, price_per_hour=%s
                    WHERE vehicle_id=%s
                """, (
                    request.form.get("vehicle_name"), request.form.get("vehicle_number"),
                    request.form.get("vehicle_type"), request.form.get("seating_capacity"),
                    request.form.get("fuel_type"),    request.form.get("availability_status"),
                    request.form.get("vehicle_count"), request.form.get("category_id") or None,
                    request.form.get("model_number") or None,
                    request.form.get("vehicle_condition", "Good"),
                    request.form.get("known_faults") or None,
                    photo_url,
                    request.form.get("price_per_day") or None,
                    request.form.get("price_per_hour") or None,
                    vehicle_id
                ))
            else:
                cursor.execute("""
                    UPDATE vehicle
                    SET vehicle_name=%s, vehicle_number=%s, vehicle_type=%s,
                        seating_capacity=%s, fuel_type=%s, availability_status=%s,
                        vehicle_count=%s, category_id=%s,
                        model_number=%s, vehicle_condition=%s, known_faults=%s,
                        price_per_day=%s, price_per_hour=%s
                    WHERE vehicle_id=%s
                """, (
                    request.form.get("vehicle_name"), request.form.get("vehicle_number"),
                    request.form.get("vehicle_type"), request.form.get("seating_capacity"),
                    request.form.get("fuel_type"),    request.form.get("availability_status"),
                    request.form.get("vehicle_count"), request.form.get("category_id") or None,
                    request.form.get("model_number") or None,
                    request.form.get("vehicle_condition", "Good"),
                    request.form.get("known_faults") or None,
                    request.form.get("price_per_day") or None,
                    request.form.get("price_per_hour") or None,
                    vehicle_id
                ))
        except Exception:
            # Fallback without new columns
            cursor.execute("""
                UPDATE vehicle
                SET vehicle_name=%s, vehicle_number=%s, vehicle_type=%s,
                    seating_capacity=%s, fuel_type=%s, availability_status=%s,
                    vehicle_count=%s, category_id=%s
                WHERE vehicle_id=%s
            """, (
                request.form.get("vehicle_name"), request.form.get("vehicle_number"),
                request.form.get("vehicle_type"), request.form.get("seating_capacity"),
                request.form.get("fuel_type"),    request.form.get("availability_status"),
                request.form.get("vehicle_count"), request.form.get("category_id") or None,
                vehicle_id
            ))
        conn.commit()
        cursor.close(); conn.close()
        flash("Vehicle updated successfully!", "success")
        return redirect(url_for("admin.admin_vehicles"))

    cursor.execute("""
        SELECT vehicle_id, vehicle_name, vehicle_number, vehicle_type,
               seating_capacity, fuel_type, availability_status, vehicle_count, category_id,
               IFNULL(model_number, '') AS model_number,
               IFNULL(vehicle_condition, 'Good') AS vehicle_condition,
               IFNULL(known_faults, '') AS known_faults,
               IFNULL(photo_url, '') AS photo_url,
               IFNULL(rating, 0) AS rating,
               IFNULL(rating_count, 0) AS rating_count,
               IFNULL(price_per_day, 0) AS price_per_day,
               IFNULL(price_per_hour, 0) AS price_per_hour
        FROM vehicle WHERE vehicle_id=%s
    """, (vehicle_id,))
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


# ── DOCUMENTS ADMIN ──
@admin_bp.route("/admin/documents")
def admin_documents():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_documents (
                doc_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                full_name VARCHAR(200) NOT NULL,
                aadhar_number VARCHAR(12) NOT NULL,
                aadhar_file VARCHAR(300) DEFAULT NULL,
                dl_number VARCHAR(20) NOT NULL,
                dl_file VARCHAR(300) DEFAULT NULL,
                verified TINYINT(1) DEFAULT 0,
                submitted_at DATETIME DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            SELECT d.*, u.name AS user_name, u.email AS user_email
            FROM user_documents d
            JOIN users u ON d.user_id = u.user_id
            ORDER BY d.submitted_at DESC
        """)
        docs = cursor.fetchall()
    except Exception:
        docs = []
    cursor.close(); conn.close()
    return render_template("admin_documents.html", docs=docs)


@admin_bp.route("/admin/document/verify/<int:doc_id>", methods=["POST"])
def admin_verify_document(doc_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_documents SET verified=1 WHERE doc_id=%s", (doc_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash("Document verified.", "success")
    return redirect(url_for("admin.admin_documents"))


# ── INQUIRIES ──
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


# ── USERS ──
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


# ── REVIEWS ──
@admin_bp.route("/admin/reviews")
def admin_reviews():
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT r.review_id, r.rating, r.review_text, r.created_at,
                   u.name AS user_name, u.email AS user_email
            FROM review r
            JOIN users u ON r.user_id = u.user_id
            ORDER BY r.created_at DESC
        """)
        reviews = cursor.fetchall()
    except Exception:
        reviews = []
    cursor.close(); conn.close()
    return render_template("admin_reviews.html", reviews=reviews)


@admin_bp.route("/admin/review/delete/<int:review_id>", methods=["POST"])
def admin_delete_review(review_id):
    if not admin_required():
        return redirect(url_for("admin.admin_login"))
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM review WHERE review_id=%s", (review_id,))
    conn.commit()
    cursor.close(); conn.close()
    flash("Review deleted successfully.", "success")
    return redirect(url_for("admin.admin_reviews"))
