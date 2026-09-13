AURELIA GRAND - SMART HOTEL MANAGEMENT SYSTEM

NEW FEATURES
1. Floating hotel chatbot (no paid AI API required)
2. Automatic booking confirmation email using Gmail SMTP
3. Google Pay / UPI payment deep link after booking
4. Existing room booking and admin management features

RUN
1. Open this folder in VS Code.
2. Terminal:
   python -m pip install -r requirements.txt
3. If hotel.db does not exist:
   python init_db.py
4. Run:
   python app.py
5. Open:
   http://127.0.0.1:5000/

ADMIN LOGIN
http://127.0.0.1:5000/admin/login
Username: admin
Password: admin123

EMAIL SETUP
1. Copy .env.example and rename the copy to .env
2. Fill:
   MAIL_USERNAME=yourgmail@gmail.com
   MAIL_APP_PASSWORD=your Gmail App Password
3. Gmail App Password requires 2-Step Verification on the Google account.
4. Never put your normal Gmail password in the project.

PAYMENT SETUP
In .env set:
UPI_ID=your_actual_upi_id
UPI_NAME=Aurelia Grand Hotel

The "Open Google Pay" button uses an Android intent targeting Google Pay.
The "Open UPI App" button uses the universal upi:// payment link.
These work best when the website is opened on an Android phone.

IMPORTANT PAYMENT NOTE
A direct UPI/GPay deep link can open the payment app but cannot securely tell
the Flask website whether the payment actually succeeded. For real verified
payments, integrate a payment gateway such as Razorpay/PhonePe/PayU with a
server-side payment verification callback/webhook.

CHATBOT
The chatbot is currently a free rule-based hotel concierge.
It answers common questions about rooms, booking, payment, check-in/out,
dining, spa, rooftop and location. It does not require an API key.
