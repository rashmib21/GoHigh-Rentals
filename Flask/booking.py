import os
from flask import (Blueprint, render_template, request,
                   redirect, session, flash, url_for, jsonify)
from .db import get_db_connection
from datetime import date, timedelta, datetime
import re

booking_bp = Blueprint("booking", __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads", "documents")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ── CANCELLATION DEDUCTION POLICY (REDUCED) ──
# 3+ days before  →  5% deduction
# 1–2 days before → 10% deduction
# Same day        → 20% deduction
def get_cancellation_deduction(travel_date_str, total_amount):
    travel_date = date.fromisoformat(str(travel_date_str))
    days_left   = (travel_date - date.today()).days
    if days_left >= 3:
        pct = 5
    elif days_left >= 1:
        pct = 10
    else:
        pct = 20
    deduction = round(total_amount * pct / 100, 2)
    refund    = round(total_amount - deduction, 2)
    return pct, deduction, refund


# ── SECURITY DEPOSIT BY VEHICLE TYPE ──
SECURITY_DEPOSIT = {
    "Bike": 2000, "Scooter": 1500, "Car": 5000,
    "SUV": 8000, "Tempo": 10000, "Bus": 15000,
}

def get_security_deposit(vehicle_type):
    return SECURITY_DEPOSIT.get(vehicle_type, 3000)


# ── DOCUMENT SUBMISSION ──
@booking_bp.route("/submit_documents", methods=["GET", "POST"])
def submit_documents():
    if "user_id" not in session:
        return redirect("/login")
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == "POST":
        full_name     = request.form.get("full_name", "").strip()
        aadhar_number = request.form.get("aadhar_number", "").strip()
        dl_number     = request.form.get("dl_number", "").strip().upper()
        if not full_name or not aadhar_number or not dl_number:
            flash("All fields are required.", "error")
            return redirect(url_for("booking.submit_documents"))
        if not re.match(r"^\d{12}$", aadhar_number):
            flash("Aadhaar number must be exactly 12 digits.", "error")
            return redirect(url_for("booking.submit_documents"))
        aadhar_filename = None
        dl_filename     = None
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        aadhar_file = request.files.get("aadhar_file")
        dl_file     = request.files.get("dl_file")
        if aadhar_file and aadhar_file.filename and allowed_file(aadhar_file.filename):
            ext             = aadhar_file.filename.rsplit(".", 1)[1].lower()
            aadhar_filename = f"aadhar_{session['user_id']}.{ext}"
            aadhar_file.save(os.path.join(UPLOAD_FOLDER, aadhar_filename))
        if dl_file and dl_file.filename and allowed_file(dl_file.filename):
            ext         = dl_file.filename.rsplit(".", 1)[1].lower()
            dl_filename = f"dl_{session['user_id']}.{ext}"
            dl_file.save(os.path.join(UPLOAD_FOLDER, dl_filename))
        cursor.execute("SELECT doc_id FROM user_documents WHERE user_id=%s", (session['user_id'],))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
                UPDATE user_documents
                SET full_name=%s, aadhar_number=%s, dl_number=%s,
                    aadhar_file=COALESCE(%s, aadhar_file),
                    dl_file=COALESCE(%s, dl_file),
                    verified=0, submitted_at=NOW()
                WHERE user_id=%s
            """, (full_name, aadhar_number, dl_number,
                  aadhar_filename, dl_filename, session['user_id']))
        else:
            cursor.execute("""
                INSERT INTO user_documents
                    (user_id, full_name, aadhar_number, aadhar_file, dl_number, dl_file)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (session['user_id'], full_name, aadhar_number,
                  aadhar_filename, dl_number, dl_filename))
        conn.commit()
        cursor.close(); conn.close()
        flash("Documents submitted! You can now proceed with booking.", "success")
        return redirect(url_for("booking.create_booking_page"))
    cursor.execute("SELECT * FROM user_documents WHERE user_id=%s", (session['user_id'],))
    existing_docs = cursor.fetchone()
    cursor.close(); conn.close()
    return render_template("submit_documents.html", existing_docs=existing_docs)


# ── NEW BOOKING PAGE ──
@booking_bp.route("/new_booking")
def create_booking_page():
    if "user_id" not in session:
        return redirect("/login")
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doc_id FROM user_documents WHERE user_id=%s", (session['user_id'],))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        flash("Please submit your Aadhaar & Driving Licence before booking.", "warning")
        return redirect(url_for("booking.submit_documents"))
    destination_id = request.args.get('destination_id', type=int)
    cursor.execute("""
        SELECT destination_id, destination_name, state, price_per_day, price_per_hour
        FROM destination WHERE is_active=1
    """)
    destinations = cursor.fetchall()
    cursor.execute("""
        SELECT vehicle_id, vehicle_name, vehicle_number, vehicle_type,
               seating_capacity, fuel_type, availability_status,
               model_number, vehicle_condition, known_faults,
               photo_url, rating, rating_count, price_per_day, price_per_hour
        FROM vehicle WHERE availability_status='Available'
        ORDER BY vehicle_type, vehicle_name
    """)
    vehicles = cursor.fetchall()
    conn.close()
    return render_template(
        "new_booking.html",
        destinations            = destinations,
        vehicles                = vehicles,
        selected_destination_id = str(destination_id) if destination_id else None
    )


# ── API: vehicle details ──
@booking_bp.route("/api/vehicle/<int:vehicle_id>")
def api_vehicle_detail(vehicle_id):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT vehicle_id, vehicle_name, vehicle_number, vehicle_type,
               seating_capacity, fuel_type, model_number,
               vehicle_condition, known_faults, photo_url,
               rating, rating_count, price_per_day, price_per_hour
        FROM vehicle WHERE vehicle_id=%s
    """, (vehicle_id,))
    v = cursor.fetchone()
    cursor.close(); conn.close()
    if not v:
        return jsonify({}), 404
    for k in ('rating', 'price_per_day', 'price_per_hour'):
        if v.get(k) is not None:
            v[k] = float(v[k])
    v['security_deposit'] = get_security_deposit(v.get('vehicle_type', ''))
    return jsonify(v)


# ── CREATE BOOKING ──
@booking_bp.route("/create_booking", methods=["POST"])
def create_booking():
    if "user_id" not in session:
        return redirect("/login")
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT doc_id FROM user_documents WHERE user_id=%s", (session['user_id'],))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        flash("Please submit your documents before booking.", "warning")
        return redirect(url_for("booking.submit_documents"))

    destination_id   = request.form.get("destination_id")
    vehicle_id       = request.form.get("vehicle_id")
    travel_date      = request.form.get("travel_date")
    booking_type     = request.form.get("booking_type", "day")
    duration_value   = request.form.get("duration_value", 2, type=int)
    start_time       = request.form.get("start_time") or None
    end_time         = request.form.get("end_time")   or None
    terms_accepted   = request.form.get("terms_accepted")
    agreement_signed = request.form.get("agreement_signed")
    signature_data   = request.form.get("signature_data", "").strip()
    payment_mode     = request.form.get("payment_mode", "Online")

    if not terms_accepted:
        flash("Please accept the Terms & Conditions to proceed.", "error")
        return redirect(url_for("booking.create_booking_page", destination_id=destination_id))
    if not agreement_signed or not signature_data:
        flash("Please sign the rental agreement to proceed.", "error")
        return redirect(url_for("booking.create_booking_page", destination_id=destination_id))

    min_allowed = date.today() + timedelta(days=1)
    if date.fromisoformat(travel_date) < min_allowed:
        flash("Invalid date! Please select a future date.", "error")
        return redirect(url_for("booking.create_booking_page"))

    # Minimum 2 hours
    if booking_type == "hour" and duration_value < 2:
        flash("Minimum booking duration is 2 hours.", "error")
        return redirect(url_for("booking.create_booking_page", destination_id=destination_id))

    # Auto-convert 24h → 1 day
    if booking_type == "hour" and duration_value >= 24:
        duration_value = duration_value // 24
        booking_type   = "day"
        start_time = end_time = None

    # Clamp
    if booking_type == "hour":
        duration_value = max(2, min(duration_value, 23))
    else:
        duration_value = max(1, min(duration_value, 30))

    user_id = session["user_id"]

    # Vehicle-level pricing (overrides destination)
    cursor.execute("""
        SELECT vehicle_type, price_per_day, price_per_hour FROM vehicle WHERE vehicle_id=%s
    """, (vehicle_id,))
    vehicle = cursor.fetchone()

    if vehicle and vehicle.get('price_per_day'):
        rate_day  = float(vehicle['price_per_day'])
        rate_hour = float(vehicle['price_per_hour'] or 0)
    else:
        cursor.execute("""
            SELECT price_per_day, price_per_hour FROM destination WHERE destination_id=%s
        """, (destination_id,))
        dest = cursor.fetchone()
        if not dest:
            cursor.close(); conn.close()
            flash("Destination not found.", "error")
            return redirect(url_for("booking.create_booking_page"))
        rate_day  = float(dest['price_per_day']  or 0)
        rate_hour = float(dest['price_per_hour'] or 0)

    rate         = rate_hour if booking_type == "hour" else rate_day
    pricing_type = "Hourly" if booking_type == "hour" else "Daily"
    base_amount  = round(rate * duration_value, 2)
    gst_amount   = round(base_amount * 0.18, 2)
    total_amount = round(base_amount + gst_amount, 2)
    security_deposit = get_security_deposit(vehicle.get('vehicle_type', '') if vehicle else '')

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO booking
            (destination_id, vehicle_id, travel_date, booking_status,
             user_id, booking_date, cancelled_by, admin_notified, notified,
             start_time, end_time, security_deposit, agreement_signed,
             signature_data, agreement_signed_at)
        VALUES (%s,%s,%s,'Pending',%s,%s,NULL,0,0,%s,%s,%s,1,%s,NOW())
    """, (destination_id, vehicle_id, travel_date, user_id, date.today(),
          start_time, end_time, security_deposit,
          signature_data[:5000] if signature_data else None))
    conn.commit()
    booking_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO pricing
            (base_amount, tax_amount, discount, total_amount,
             pricing_type, duration_value, duration_unit, gst_rate,
             booking_id, payment_mode)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (base_amount, gst_amount, 0.00, total_amount,
          pricing_type, duration_value,
          "hour" if booking_type == "hour" else "day",
          18, booking_id, payment_mode))
    conn.commit()
    cursor.close(); conn.close()
    return redirect(url_for("booking.show_bill", booking_id=booking_id))


# ── BILL PAGE ──
@booking_bp.route("/bill/<int:booking_id>")
def show_bill(booking_id):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, b.travel_date, b.booking_status, b.booking_date,
               b.booking_id, b.start_time, b.end_time,
               b.security_deposit, b.agreement_signed,
               d.destination_name, v.vehicle_name, v.vehicle_type, v.model_number,
               u.name AS user_name, u.phone_no
        FROM pricing p
        JOIN booking b     ON p.booking_id     = b.booking_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN users u       ON b.user_id         = u.user_id
        WHERE p.booking_id = %s
    """, (booking_id,))
    bill = cursor.fetchone()
    cursor.close(); conn.close()
    if bill:
        gst_rate          = bill.get('gst_rate') or 18
        bill['gst_label'] = f"GST ({int(gst_rate)}%)"
        for tf in ('start_time', 'end_time'):
            val = bill.get(tf)
            if val is not None and hasattr(val, 'total_seconds'):
                total_seconds = int(val.total_seconds())
                h, m = divmod(total_seconds // 60, 60)
                bill[tf] = f"{h:02d}:{m:02d}"
        travel_date   = bill.get('travel_date')
        duration_val  = bill.get('duration_value') or 1
        duration_unit = bill.get('duration_unit') or 'day'
        if travel_date:
            if isinstance(travel_date, str):
                travel_date_obj = date.fromisoformat(travel_date)
            else:
                travel_date_obj = travel_date
            if duration_unit == 'day':
                bill['end_date'] = (travel_date_obj + timedelta(days=int(duration_val))).strftime('%Y-%m-%d')
            else:
                bill['end_date'] = travel_date_obj.strftime('%Y-%m-%d')
    return render_template("bill.html", bill=bill)


# ── CANCEL BOOKING ──
@booking_bp.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    if 'user_id' not in session:
        return redirect('/login')
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.booking_status, b.travel_date, p.total_amount
        FROM booking b JOIN pricing p ON p.booking_id=b.booking_id
        WHERE b.booking_id=%s AND b.user_id=%s
    """, (booking_id, session['user_id']))
    booking = cursor.fetchone()
    if not booking:
        cursor.close(); conn.close()
        flash("Booking not found.", "error")
        return redirect('/dashboard')
    if booking['booking_status'] in ('Cancelled', 'Completed'):
        cursor.close(); conn.close()
        flash("This booking cannot be cancelled.", "error")
        return redirect('/dashboard')
    pct, deduction, refund = get_cancellation_deduction(
        booking['travel_date'], float(booking['total_amount']))
    cursor.execute("""
        UPDATE booking SET booking_status='Cancelled', cancelled_by='user',
            admin_notified=0, notified=0
        WHERE booking_id=%s AND user_id=%s
    """, (booking_id, session['user_id']))
    try:
        cursor.execute("""
            UPDATE pricing SET cancellation_deduction=%s, refund_amount=%s, cancellation_pct=%s
            WHERE booking_id=%s
        """, (deduction, refund, pct, booking_id))
    except Exception:
        pass
    conn.commit()
    cursor.close(); conn.close()
    flash(f"Booking cancelled. {pct}% fee (₹{deduction}) deducted. "
          f"Refund ₹{refund} in 5–7 business days.", "warning")
    return redirect('/dashboard')


# ── RATE A VEHICLE ──
@booking_bp.route("/rate_vehicle/<int:booking_id>", methods=["POST"])
def rate_vehicle(booking_id):
    if "user_id" not in session:
        return redirect("/login")
    rating      = request.form.get("rating", type=int)
    review_text = request.form.get("review_text", "").strip()
    if not rating or rating < 1 or rating > 5:
        flash("Please select a valid rating (1–5).", "error")
        return redirect("/my_bookings")
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.vehicle_id, b.booking_status FROM booking b
        WHERE b.booking_id=%s AND b.user_id=%s
    """, (booking_id, session['user_id']))
    booking = cursor.fetchone()
    if not booking or booking['booking_status'] != 'Completed':
        cursor.close(); conn.close()
        flash("You can only rate completed bookings.", "error")
        return redirect("/my_bookings")
    vehicle_id = booking['vehicle_id']
    try:
        cursor.execute("""
            INSERT IGNORE INTO vehicle_rating
                (vehicle_id, user_id, booking_id, rating, review_text)
            VALUES (%s,%s,%s,%s,%s)
        """, (vehicle_id, session['user_id'], booking_id, rating, review_text))
        cursor.execute("""
            SELECT AVG(rating) AS avg_r, COUNT(*) AS cnt
            FROM vehicle_rating WHERE vehicle_id=%s
        """, (vehicle_id,))
        stats = cursor.fetchone()
        cursor.execute("""
            UPDATE vehicle SET rating=%s, rating_count=%s WHERE vehicle_id=%s
        """, (round(float(stats['avg_r']), 2), stats['cnt'], vehicle_id))
        conn.commit()
        flash("Thank you! Your vehicle rating has been saved.", "success")
    except Exception as e:
        conn.rollback()
        flash("Rating could not be saved.", "error")
    finally:
        cursor.close(); conn.close()
    return redirect("/my_bookings")
