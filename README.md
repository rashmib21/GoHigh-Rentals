🏔️ GoHigh Rentals — Himalayan Vehicle Rental Web App
A full-stack Flask web application for booking vehicles for Himalayan destinations. Built with Python, Flask, MySQL, HTML, CSS and JavaScript.



📋 Table of Contents

About the Project
Features
Tech Stack
Project Structure
Database Schema
Getting Started
Environment Variables
Admin Panel
Author


📖 About the Project
GoHigh Rentals is a Himalayan vehicle rental platform where users can register, browse destinations, book vehicles, view invoices, and manage their trips. An admin panel allows the site owner to manage all bookings, contact inquiries, and the vehicle fleet.

✨ Features
👤 User Side

✅ User Registration & Login with hashed passwords
✅ Book vehicles for Himalayan destinations
✅ View & cancel bookings
✅ Auto-complete past bookings to "Completed" status
✅ Invoice generation with GST breakdown
✅ User profile management (name, phone, password)
✅ Submit reviews visible on the dashboard
✅ Contact Us form
✅ Delete account

🔐 Admin Panel

✅ Secure admin login (single admin)
✅ Dashboard with live stats (users, bookings, revenue, inquiries)
✅ Accept or cancel any booking
✅ View & delete contact inquiries
✅ Add, edit, delete vehicles
✅ View all registered users
✅ Hidden admin button in website footer


🛠️ Tech Stack
LayerTechnologyBackendPython, Flask, Flask BlueprintsDatabaseMySQL, mysql-connector-pythonFrontendHTML5, CSS3, JavaScriptStylingCustom CSS (Nunito + Playfair Display)AuthWerkzeug password hashing, Flask sessionConfigpython-dotenv (.env file)

📁 Project Structure
GoHigh-Rentals/
│
├── Flask/
│   ├── __init__.py               
│   ├── admin.py                  
│   ├── booking.py                
│   ├── db.py                     
│   │
│   ├── templates/
│   │   ├── home.html            
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── my_bookings.html
│   │   ├── new_booking.html
│   │   ├── bill.html
│   │   ├── profile.html
│   │   ├── contact.html
│   │   ├── admin_login.html
│   │   ├── admin_base.html       
│   │   ├── admin_dashboard.html
│   │   ├── admin_bookings.html
│   │   ├── admin_inquiries.html
│   │   ├── admin_vehicles.html
│   │   ├── admin_add_vehicle.html
│   │   ├── admin_edit_vehicle.html
│   │   └── admin_users.html
│   │
│   └── static/
│       ├── style.css
│       └── images/
│           ├── logo.png
│           └── about.jpg
│
├── run.py
├── .env                          ← Never commit this!
├── .env.example
├── requirements.txt
└── README.md

🗄️ Database Schema
TableDescriptionusersRegistered users (name, email, phone, hashed password)destinationHimalayan destinationsvehicleVehicle fleet (name, number, type, seats, fuel, status)bookingBookings linking users, destinations and vehiclespricingPricing per booking (base, tax, discount, total)contactContact form submissionsreviewUser reviews and star ratings

🚀 Getting Started
Prerequisites

Python 3.10+
MySQL 8.0+
pip

Installation
1. Clone the repository
bashgit clone https://github.com/your-username/gohigh-rentals.git
cd gohigh-rentals
2. Create and activate a virtual environment
bashpython -m venv .venv

# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
3. Install dependencies
bashpip install -r requirements.txt
4. Set up the database
sqlCREATE DATABASE gohigh_rentals;
Then import your schema SQL file into MySQL.
5. Configure environment variables
bashcp .env.example .env
Fill in your database credentials in the .env file.
6. Run the application
bashflask run
App runs at: http://localhost:9000

⚙️ Environment Variables
Create a .env file in the root folder:
SECRET_KEY=your_secret_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=gohigh_rentals

⚠️ Never commit your .env file. Add it to .gitignore.


🔐 Admin Panel
The admin panel is accessible via a hidden button in the website footer.
DetailValueURLhttp://localhost:9000/admin/loginUsernameadminPasswordadmin123

⚠️ Change the credentials in admin.py before deploying to production.

Admin can:

View live stats — users, bookings, revenue, inquiries, vehicles
Accept or cancel any user booking
View and delete contact form messages
Add, edit and delete vehicles
View all registered users


📦 requirements.txt
Flask
mysql-connector-python
python-dotenv
Werkzeug
Generate fresh with:
bashpip freeze > requirements.txt

🙈 .gitignore
Make sure your .gitignore includes:
.env
.venv/
__pycache__/
*.pyc

👩‍💻 Author
Rashmi Barethiya

Built with ❤️ for Himalayan adventures.
GoHigh Rentals — Where every mile tells a story.


📄 License
This project is for educational purposes. Feel free to use and modify it.ShareContent__init__.pypyprofile.htmlhtmldashboard.htmlhtmlstyle.csscssbooking.py131 linespydb.py25 linespylogin.html52 lineshtmlmy_bookings.html449 lineshtmlnew_booking.html147 lineshtmlregister.html91 lineshtmlbill.html169 lineshtmlcontact.html35 lineshtmlindex.html143 lineshtmlimport os
from datetime import date
from flask import Flask, render_template, request, redirect, session, url_for, flash
from dotenv import load_dotenv
import mysql.connector
import re
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
frompastedfrom flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection

#create admin blueprint
admin_bp=Blueprint('admin', __name__)

#admin credentials
admin_username="admin"
admin_password-"admin123"

#Admin logged in or not
def adminpastedfrom flask import Blueprint, render_template, request, redirect, session, flash, url_for
from .db import get_db_connection

#create admin blueprint
admin_bp=Blueprint('admin', __name__)

#admin credentials
admin_username="admin"
admin_password="admin123"

#Admin logged in or not
def adminpasted
