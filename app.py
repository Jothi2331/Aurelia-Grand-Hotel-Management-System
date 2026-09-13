from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime
from email.message import EmailMessage
from urllib.parse import quote
import hashlib
import os
import smtplib

from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

app = Flask(__name__)
app.secret_key = "aurelia-grand-final-demo-key"

MAIL_USERNAME = os.getenv("MAIL_USERNAME", "").strip()
MAIL_APP_PASSWORD = os.getenv("MAIL_APP_PASSWORD", "").replace(" ", "").strip()
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Aurelia Grand Hotel").strip()
UPI_ID = os.getenv("UPI_ID", "yourupiid@okaxis").strip()
UPI_NAME = os.getenv("UPI_NAME", "Aurelia Grand Hotel").strip()


def parse_dates(check_in, check_out):
    try:
        start = datetime.strptime(check_in, "%Y-%m-%d")
        end = datetime.strptime(check_out, "%Y-%m-%d")
        if end <= start:
            return None
        return (end - start).days
    except Exception:
        return None


def room_available(conn, room_id, check_in, check_out):
    row = conn.execute("""
        SELECT COUNT(*) AS c
        FROM bookings
        WHERE room_id = ?
          AND booking_status IN ('Reserved','Checked-In')
          AND check_in < ?
          AND check_out > ?
    """, (room_id, check_out, check_in)).fetchone()
    return row["c"] == 0


def admin_required():
    return session.get("admin") is not None


def build_upi_links(booking):
    amount = f"{float(booking['total_amount']):.2f}"
    note = f"Aurelia Grand Booking AG{int(booking['booking_id']):04d}"
    params = (
        f"pa={quote(UPI_ID)}"
        f"&pn={quote(UPI_NAME)}"
        f"&am={quote(amount)}"
        f"&cu=INR"
        f"&tn={quote(note)}"
    )
    # Universal UPI link (opens installed UPI app)
    upi_link = f"upi://pay?{params}"
    # Android Chrome intent specifically targeting Google Pay package.
    gpay_link = (
        f"intent://upi/pay?{params}"
        "#Intent;scheme=upi;package=com.google.android.apps.nbu.paisa.user;end"
    )
    return upi_link, gpay_link


def send_booking_email(booking):
    if not MAIL_USERNAME or not MAIL_APP_PASSWORD or not booking["email"]:
        return False, "Email not configured"

    msg = EmailMessage()
    msg["Subject"] = f"Booking Confirmed - Aurelia Grand - AG{int(booking['booking_id']):04d}"
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_USERNAME}>"
    msg["To"] = booking["email"]

    body = f"""Dear {booking['customer_name']},

Your stay at Aurelia Grand Hotel has been booked successfully.

Booking ID: AG{int(booking['booking_id']):04d}
Room: {booking['room_number']} - {booking['room_type']}
Check-in: {booking['check_in']}
Check-out: {booking['check_out']}
Guests: {booking['guests']}
Total Amount: ₹{float(booking['total_amount']):,.0f}

Payment can be completed using the Google Pay / UPI option shown on the booking confirmation page.

Thank you,
Aurelia Grand Hotel
Chennai
"""
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(MAIL_USERNAME, MAIL_APP_PASSWORD)
            smtp.send_message(msg)
        return True, "Confirmation email sent"
    except Exception as exc:
        print("EMAIL ERROR:", exc)
        return False, "Email could not be sent"


def chatbot_reply(message):
    text = (message or "").strip().lower()

    if not text:
        return "Please type your question. I can help with rooms, booking, payment, check-in, dining, spa and location."

    if any(x in text for x in ["hello", "hi", "hey", "vanakkam"]):
        return "Hello! Welcome to Aurelia Grand. How can I help with your stay today?"

    if any(x in text for x in ["room", "suite", "price", "cost", "rate"]):
        return "Our demo room categories start from ₹5,200 per night. Use the booking bar on the homepage to check exact availability for your dates."

    if any(x in text for x in ["book", "reservation", "reserve", "available"]):
        return "Select your check-in date, check-out date and number of guests in the booking bar, then choose an available room and enter your guest details."

    if any(x in text for x in ["payment", "gpay", "google pay", "upi", "pay"]):
        return "After booking, the confirmation page shows a Google Pay / UPI button. On an Android phone, it can open Google Pay directly. Payment verification is kept as a demo feature unless a payment gateway is connected."

    if any(x in text for x in ["check in", "check-in", "checkin"]):
        return "Standard demo check-in time is 2:00 PM. The hotel admin can mark your reservation as Checked-In from the staff dashboard."

    if any(x in text for x in ["check out", "check-out", "checkout"]):
        return "Standard demo check-out time is 11:00 AM. After checkout, the room automatically moves to Cleaning status."

    if any(x in text for x in ["spa", "wellness"]):
        return "The Still Spa is our wellness experience with a calm, premium setting for restorative treatments."

    if any(x in text for x in ["food", "restaurant", "dining", "breakfast"]):
        return "Ember & Leaf is the hotel's signature dining concept, inspired by modern coastal Tamil flavours."

    if any(x in text for x in ["pool", "rooftop"]):
        return "Afterlight is the rooftop experience with poolside evenings and city views."

    if any(x in text for x in ["location", "where", "address"]):
        return "Aurelia Grand is a fictional project hotel located in the Nungambakkam, Chennai demo area."

    if any(x in text for x in ["email", "mail", "confirmation"]):
        return "If the hotel Gmail settings are configured, a booking confirmation email is automatically sent after a reservation is created."

    if any(x in text for x in ["thank", "thanks"]):
        return "You're welcome. I hope you enjoy your Aurelia Grand experience!"

    return "I can help with rooms, booking, prices, Google Pay/UPI, confirmation email, check-in, check-out, dining, spa, rooftop and location."


@app.route("/")
def home():
    conn = get_db_connection()
    rooms = conn.execute("SELECT * FROM rooms ORDER BY price ASC").fetchall()
    conn.close()
    return render_template("index.html", rooms=rooms)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    return jsonify({"reply": chatbot_reply(data.get("message", ""))})


@app.route("/availability", methods=["POST"])
def availability():
    check_in = request.form.get("check_in", "")
    check_out = request.form.get("check_out", "")
    guests = int(request.form.get("guests", 1))
    nights = parse_dates(check_in, check_out)

    if nights is None:
        flash("Please choose valid check-in and check-out dates.", "error")
        return redirect(url_for("home") + "#booking")

    conn = get_db_connection()
    rooms = conn.execute("""
        SELECT * FROM rooms
        WHERE capacity >= ?
          AND status != 'Maintenance'
          AND room_id NOT IN (
              SELECT room_id FROM bookings
              WHERE booking_status IN ('Reserved','Checked-In')
                AND check_in < ?
                AND check_out > ?
          )
        ORDER BY price
    """, (guests, check_out, check_in)).fetchall()
    conn.close()

    return render_template(
        "availability.html",
        rooms=rooms,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        nights=nights,
    )


@app.route("/book/<int:room_id>", methods=["POST"])
def book(room_id):
    check_in = request.form.get("check_in", "")
    check_out = request.form.get("check_out", "")
    guests = int(request.form.get("guests", 1))
    nights = parse_dates(check_in, check_out)

    if nights is None:
        return redirect(url_for("home"))

    conn = get_db_connection()
    room = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()
    if room is None or not room_available(conn, room_id, check_in, check_out):
        conn.close()
        return "Room is no longer available.", 400

    total = nights * room["price"]
    conn.close()

    return render_template(
        "booking.html",
        room=room,
        check_in=check_in,
        check_out=check_out,
        guests=guests,
        nights=nights,
        total=total,
    )


@app.route("/confirm/<int:room_id>", methods=["POST"])
def confirm(room_id):
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    check_in = request.form.get("check_in", "")
    check_out = request.form.get("check_out", "")
    guests = int(request.form.get("guests", 1))
    nights = parse_dates(check_in, check_out)

    if not name or not phone or nights is None:
        return "Invalid booking details.", 400

    conn = get_db_connection()
    room = conn.execute("SELECT * FROM rooms WHERE room_id=?", (room_id,)).fetchone()

    if room is None or not room_available(conn, room_id, check_in, check_out):
        conn.close()
        return "Room is not available.", 400

    total = nights * room["price"]

    cur = conn.execute(
        "INSERT INTO customers(name,phone,email) VALUES (?,?,?)",
        (name, phone, email),
    )
    customer_id = cur.lastrowid

    cur = conn.execute("""
        INSERT INTO bookings(customer_id,room_id,check_in,check_out,guests,total_amount,booking_status)
        VALUES (?,?,?,?,?,?,'Reserved')
    """, (customer_id, room_id, check_in, check_out, guests, total))

    booking_id = cur.lastrowid
    conn.commit()

    booking = conn.execute("""
        SELECT b.*, c.name AS customer_name, c.phone, c.email,
               r.room_number, r.room_type, r.image
        FROM bookings b
        JOIN customers c ON c.customer_id=b.customer_id
        JOIN rooms r ON r.room_id=b.room_id
        WHERE b.booking_id=?
    """, (booking_id,)).fetchone()

    conn.close()

    email_sent, email_message = send_booking_email(booking)
    upi_link, gpay_link = build_upi_links(booking)

    return render_template(
        "success.html",
        booking=booking,
        email_sent=email_sent,
        email_message=email_message,
        upi_link=upi_link,
        gpay_link=gpay_link,
        upi_id=UPI_ID,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,),
        ).fetchone()
        conn.close()

        if user and user["password_hash"] == hashlib.sha256(password.encode()).hexdigest():
            session["admin"] = username
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
def dashboard():
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    stats = {
        "total_rooms": conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0],
        "available": conn.execute("SELECT COUNT(*) FROM rooms WHERE status='Available'").fetchone()[0],
        "occupied": conn.execute("SELECT COUNT(*) FROM rooms WHERE status='Occupied'").fetchone()[0],
        "cleaning": conn.execute("SELECT COUNT(*) FROM rooms WHERE status='Cleaning'").fetchone()[0],
        "guests": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "bookings": conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        "revenue": conn.execute(
            "SELECT COALESCE(SUM(total_amount),0) FROM bookings WHERE booking_status!='Cancelled'"
        ).fetchone()[0],
    }

    recent = conn.execute("""
        SELECT b.*, c.name AS customer_name, r.room_number, r.room_type
        FROM bookings b
        JOIN customers c ON c.customer_id=b.customer_id
        JOIN rooms r ON r.room_id=b.room_id
        ORDER BY b.booking_id DESC LIMIT 8
    """).fetchall()

    conn.close()
    return render_template("dashboard.html", recent=recent, **stats)


@app.route("/admin/rooms")
def admin_rooms():
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    rooms = conn.execute("SELECT * FROM rooms ORDER BY room_number").fetchall()
    conn.close()

    return render_template("admin_rooms.html", rooms=rooms)


@app.route("/admin/rooms/<int:room_id>", methods=["POST"])
def update_room(room_id):
    if not admin_required():
        return redirect(url_for("admin_login"))

    status = request.form.get("status", "Available")

    if status not in {"Available", "Cleaning", "Maintenance"}:
        return "Invalid status", 400

    conn = get_db_connection()
    current = conn.execute(
        "SELECT status FROM rooms WHERE room_id=?",
        (room_id,),
    ).fetchone()

    if current and current["status"] != "Occupied":
        conn.execute(
            "UPDATE rooms SET status=? WHERE room_id=?",
            (status, room_id),
        )
        conn.commit()

    conn.close()
    return redirect(url_for("admin_rooms"))


@app.route("/admin/bookings")
def admin_bookings():
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()

    bookings = conn.execute("""
        SELECT b.*, c.name AS customer_name, r.room_number, r.room_type
        FROM bookings b
        JOIN customers c ON c.customer_id=b.customer_id
        JOIN rooms r ON r.room_id=b.room_id
        ORDER BY b.booking_id DESC
    """).fetchall()

    conn.close()
    return render_template("admin_bookings.html", bookings=bookings)


@app.route("/admin/checkin/<int:booking_id>", methods=["POST"])
def checkin(booking_id):
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    b = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,),
    ).fetchone()

    if b and b["booking_status"] == "Reserved":
        conn.execute(
            "UPDATE bookings SET booking_status='Checked-In' WHERE booking_id=?",
            (booking_id,),
        )
        conn.execute(
            "UPDATE rooms SET status='Occupied' WHERE room_id=?",
            (b["room_id"],),
        )
        conn.commit()

    conn.close()
    return redirect(url_for("admin_bookings"))


@app.route("/admin/checkout/<int:booking_id>", methods=["POST"])
def checkout(booking_id):
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    b = conn.execute(
        "SELECT * FROM bookings WHERE booking_id=?",
        (booking_id,),
    ).fetchone()

    if b and b["booking_status"] == "Checked-In":
        conn.execute(
            "UPDATE bookings SET booking_status='Checked-Out' WHERE booking_id=?",
            (booking_id,),
        )
        conn.execute(
            "UPDATE rooms SET status='Cleaning' WHERE room_id=?",
            (b["room_id"],),
        )
        conn.commit()

    conn.close()
    return redirect(url_for("admin_bookings"))


@app.route("/admin/cancel/<int:booking_id>", methods=["POST"])
def cancel(booking_id):
    if not admin_required():
        return redirect(url_for("admin_login"))

    conn = get_db_connection()
    conn.execute(
        """
        UPDATE bookings
        SET booking_status='Cancelled'
        WHERE booking_id=? AND booking_status='Reserved'
        """,
        (booking_id,),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("admin_bookings"))


if __name__ == "__main__":
    app.run(debug=True)
