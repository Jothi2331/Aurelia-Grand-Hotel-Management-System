import hashlib
from database import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    room_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_number TEXT NOT NULL UNIQUE,
    room_type TEXT NOT NULL,
    price REAL NOT NULL,
    capacity INTEGER NOT NULL,
    bed_type TEXT NOT NULL,
    view_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Available',
    image TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    guests INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    booking_status TEXT NOT NULL DEFAULT 'Reserved',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY(room_id) REFERENCES rooms(room_id)
);
""")

password_hash = hashlib.sha256("admin123".encode()).hexdigest()
cur.execute(
    "INSERT OR IGNORE INTO users(username, password_hash) VALUES (?, ?)",
    ("admin", password_hash)
)

rooms = [
    ("101","Deluxe King",5200,2,"King Bed","Garden View","Available",
     "https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=1200&q=90",
     "Elegant interiors, king bed, soft lighting and a peaceful garden-facing stay."),
    ("201","Premium Twin",6200,3,"Twin Beds","City View","Available",
     "https://images.unsplash.com/photo-1591088398332-8a7791972843?auto=format&fit=crop&w=1200&q=90",
     "Spacious twin room designed for families, friends and business travellers."),
    ("301","Executive Suite",8600,3,"King Bed","Panoramic View","Available",
     "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=90",
     "A refined suite with lounge space, premium furnishings and skyline views."),
    ("401","Presidential Suite",14500,4,"King Bed","Skyline View","Available",
     "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=1200&q=90",
     "Our signature suite with generous space, luxury finishes and private ambience.")
]

cur.executemany("""
INSERT OR IGNORE INTO rooms
(room_number, room_type, price, capacity, bed_type, view_type, status, image, description)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", rooms)

conn.commit()
conn.close()

print("Database created successfully.")
print("Admin username: admin")
print("Admin password: admin123")
