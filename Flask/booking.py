from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection
from datetime import date, timedelta, datetime
import re

booking_bp = Blueprint("booking", __name__)


def is_valid_email(email):
    pattern = r'^[a-zA-Z][a-zA-Z0-9._\-]*@[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


# ── CANCELLATION DEDUCTION POLICY ──
# 3+ days before  → 10% deduction
# 1–2 days before → 25% deduction
# Same day        → 50% deduction
def get_cancellation_deduction(travel_date_str, total_amount):
    travel_date = date.fromisoformat(str(travel_date_str))
    days_left   = (travel_date - date.today()).days

    if days_left >= 3:
        pct = 10
    elif days_left >= 1:
        pct = 25
    else:
        pct = 50

    deduction = round(total_amount * pct / 100, 2)
    refund    = round(total_amount - deduction, 2)
    return pct, deduction, refund


# ── CREATE BOOKING ──
@booking_bp.route("/create_booking", methods=["POST"])
def create_booking():

    if "user_id" not in session:
        return redirect("/login")

    destination_id = request.form.get("destination_id")
    vehicle_id     = request.form.get("vehicle_id")
    travel_date    = request.form.get("travel_date")
    booking_type   = request.form.get("booking_type", "day")
    duration_value = request.form.get("duration_value", 1, type=int)
    start_time     = request.form.get("start_time") or None
    end_time       = request.form.get("end_time")   or None
    terms_accepted = request.form.get("terms_accepted")

    # Terms must be accepted
    if not terms_accepted:
        flash("Please accept the Terms & Conditions to proceed.", "error")
        return redirect(url_for("booking.create_booking_page",
                                destination_id=destination_id))

    # Block past dates
    min_allowed = date.today() + timedelta(days=1)
    if date.fromisoformat(travel_date) < min_allowed:
        flash("Invalid date! Please select a future date.", "error")
        return redirect(url_for("booking.create_booking_page"))

    # ── Auto-convert 24 hours → 1 day ──
    if booking_type == "hour" and duration_value >= 24:
        days         = duration_value // 24
        duration_value = days
        booking_type = "day"
        start_time   = None
        end_time     = None

    # ── Clamp limits ──
    if booking_type == "hour":
        duration_value = max(1, min(duration_value, 24))
    else:
        duration_value = max(1, min(duration_value, 30))

    user_id = session["user_id"]
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)

    # Real price from destination
    cursor.execute("""
        SELECT price_per_day, price_per_hour
        FROM destination WHERE destination_id = %s
    """, (destination_id,))
    dest = cursor.fetchone()

    if not dest:
        conn.close()
        flash("Destination not found.", "error")
        return redirect(url_for("booking.create_booking_page"))

    rate         = float(dest['price_per_hour'] if booking_type == "hour" else dest['price_per_day'] or 0)
    pricing_type = "Hourly" if booking_type == "hour" else "Daily"
    base_amount  = round(rate * duration_value, 2)

    # GST 18%
    gst_rate     = 18
    gst_amount   = round(base_amount * gst_rate / 100, 2)
    discount     = 0.00
    total_amount = round(base_amount + gst_amount - discount, 2)

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO booking
            (destination_id, vehicle_id, travel_date, booking_status,
             user_id, booking_date, cancelled_by, admin_notified, notified,
             start_time, end_time)
        VALUES (%s,%s,%s,'Pending',%s,%s,NULL,0,0,%s,%s)
    """, (destination_id, vehicle_id, travel_date, user_id, date.today(),
          start_time, end_time))
    conn.commit()
    booking_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO pricing
            (base_amount, tax_amount, discount, total_amount,
             pricing_type, duration_value, duration_unit, gst_rate, booking_id)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (base_amount, gst_amount, discount, total_amount,
          pricing_type, duration_value,
          "hour" if booking_type == "hour" else "day",
          gst_rate, booking_id))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("booking.show_bill", booking_id=booking_id))


# ── NEW BOOKING PAGE ──
@booking_bp.route("/new_booking")
def create_booking_page():
    destination_id = request.args.get('destination_id', type=int)

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT destination_id, destination_name, state,
               price_per_day, price_per_hour
        FROM destination WHERE is_active = 1
    """)
    destinations = cursor.fetchall()
    cursor.execute("SELECT * FROM vehicle WHERE availability_status='Available'")
    vehicles = cursor.fetchall()
    conn.close()

    return render_template(
        "new_booking.html",
        destinations            = destinations,
        vehicles                = vehicles,
        selected_destination_id = str(destination_id) if destination_id else None
    )


# ── BILL PAGE ──
@booking_bp.route("/bill/<int:booking_id>")
def show_bill(booking_id):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, b.travel_date, b.booking_status, b.booking_date,
               b.booking_id, b.start_time, b.end_time,
               d.destination_name, v.vehicle_name,
               u.name AS user_name, u.phone_no
        FROM pricing p
        JOIN booking b     ON p.booking_id     = b.booking_id
        JOIN destination d ON b.destination_id = d.destination_id
        JOIN vehicle v     ON b.vehicle_id     = v.vehicle_id
        JOIN users u       ON b.user_id         = u.user_id
        WHERE p.booking_id = %s
    """, (booking_id,))
    bill = cursor.fetchone()
    cursor.close()
    conn.close()

    if bill:
        gst_rate          = bill.get('gst_rate') or 18
        bill['gst_label'] = f"GST ({int(gst_rate)}%)"
        # Format times as HH:MM strings if they exist (MySQL returns timedelta)
        for tf in ('start_time', 'end_time'):
            val = bill.get(tf)
            if val is not None:
                total_seconds = int(val.total_seconds())
                h, m = divmod(total_seconds // 60, 60)
                bill[tf] = f"{h:02d}:{m:02d}"
        # Compute end_date for display
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
                # hourly: end on the same date
                bill['end_date'] = travel_date_obj.strftime('%Y-%m-%d')

    return render_template("bill.html", bill=bill)


# ── CANCEL BOOKING BY USER (with deduction) ──
@booking_bp.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if 'user_id' not in session:
        return redirect('/login')

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT b.booking_status, b.travel_date, p.total_amount
        FROM booking b
        JOIN pricing p ON p.booking_id = b.booking_id
        WHERE b.booking_id = %s AND b.user_id = %s
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

    # FIX 4: Deduction based on days remaining
    pct, deduction, refund = get_cancellation_deduction(
        booking['travel_date'], float(booking['total_amount'])
    )

    cursor.execute("""
        UPDATE booking
        SET booking_status='Cancelled', cancelled_by='user',
            admin_notified=0, notified=0
        WHERE booking_id=%s AND user_id=%s
    """, (booking_id, session['user_id']))

    # Store deduction details
    try:
        cursor.execute("""
            UPDATE pricing
            SET cancellation_deduction=%s, refund_amount=%s, cancellation_pct=%s
            WHERE booking_id=%s
        """, (deduction, refund, pct, booking_id))
    except Exception:
        pass  # columns may not exist yet — run migration SQL

    conn.commit()
    cursor.close()
    conn.close()

    flash(
        f"Booking cancelled. A {pct}% cancellation fee (₹{deduction}) has been deducted. "
        f"Refund of ₹{refund} will be processed in 5–7 business days.",
        "warning"
    )
    return redirect('/dashboard')