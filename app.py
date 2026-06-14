# 1. THE INGREDIENTS
import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, render_template, redirect, url_for
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId

# 2. THE SETUP
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", "campus_bites_secret_key_123") 

# --- Review File Upload Config ---
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'reviews')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Separate distinct folder configuration for Menu Images
MENU_UPLOAD_FOLDER = os.path.join('static', 'images')
os.makedirs(MENU_UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Security & Database ---
bcrypt = Bcrypt(app) 

# CORS Configuration (Adapts automatically if running on Render)
if os.environ.get("RENDER"):
    CORS(app, supports_credentials=True, origins=["*"])
else:
    CORS(app, supports_credentials=True, origins=[
        "http://127.0.0.1:5500", 
        "http://localhost:5500", 
        "http://10.230.167.148:5500"
    ])

# Cookie settings for cross-origin sessions
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False, 
)

# Production Safe Database Config
app.config["MONGO_URI"] = os.environ.get(
    "MONGO_URI", 
    "mongodb://localhost:27017/CampusBitesDB"
)

mongo = PyMongo(app)

# 3. THE ROUTES

@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login-page') 
def login_page():
    return render_template('login.html')

@app.route('/signup-page') 
def signup_page():
    return render_template('signup.html')

@app.route('/my-orders')
def my_orders():
    return render_template('my-orders.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    return render_template('admin.html')

@app.route('/admin-login')
def admin_login():
    return render_template('adminlogin.html')

@app.route('/admin-reviews-page')
def admin_reviews_page():
    return render_template('admin-reviews.html')

@app.route('/analytics-page')
def analytics_page():
    return render_template('analytics.html')

@app.route('/admin-menu')
def adminmenu_page():
    return render_template('adminmenu.html')

# --- AUTHENTICATION ---
@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    user_collection = mongo.db.users
    if user_collection.find_one({"email": email}):
        return jsonify({"message": "Email already registered!"}), 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    user_collection.insert_one({
        "name": name, 
        "email": email, 
        "password": hashed_password
    })
    return jsonify({"message": "Account created successfully!"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    found_user = mongo.db.users.find_one({"email": email})
    
    if found_user and bcrypt.check_password_hash(found_user['password'], password):
        session['user_email'] = found_user.get('email') 
        session['user_name'] = found_user.get('name')
        session.permanent = True 
        
        return jsonify({
            "message": "Login successful!",
            "user": found_user.get('name')
        }), 200
    
    return jsonify({"message": "Invalid email or password."}), 401


# --- ORDER MANAGEMENT ---
@app.route('/place-order', methods=['POST'])
def place_order():
    if 'user_email' not in session:
        return jsonify({"message": "Please login first"}), 401
    
    data = request.json
    token = "CB-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    try:
        raw_total = data.get('total', 0)
        total_val = float(raw_total)
    except (ValueError, TypeError):
        total_val = 0.0

    new_order = {
        "token_id": token,
        "customer_name": session.get('user_name'), 
        "user_email": session['user_email'],
        "items": data.get('items'),
        "total_amount": total_val,
        "status": "Pending",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S")
    }
    mongo.db.orders.insert_one(new_order)
    return jsonify({"message": "Order Placed!", "token": token}), 201

@app.route('/get-my-orders', methods=['GET'])
def get_my_orders():
    if 'user_email' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    user_orders = list(mongo.db.orders.find({"user_email": session['user_email']}))
    for order in user_orders:
        order['_id'] = str(order['_id'])
    return jsonify(user_orders), 200

# --- REVIEW MANAGEMENT ---
@app.route('/submit-review', methods=['POST'])
def submit_review():
    if 'user_email' not in session:
        return jsonify({"message": "Please login to submit a review"}), 401

    stars = request.form.get('stars', 0)
    text = request.form.get('text', "")
    
    media_path = None
    if 'media' in request.files:
        file = request.files['media']
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{datetime.now().timestamp()}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            media_path = f"static/uploads/reviews/{filename}"

    new_review = {
        "customer_name": session.get('user_name', 'Anonymous'),
        "user_email": session.get('user_email'),
        "stars": int(stars),
        "text": text,
        "media_url": media_path,
        "reply": None,
        "created_at": datetime.now()
    }

    mongo.db.reviews.insert_one(new_review)
    return jsonify({"message": "Review submitted successfully!"}), 201

# --- ADMIN ROUTES ---
@app.route('/admin/get-all-orders', methods=['GET'])
def get_all_orders():
    today_str = datetime.now().strftime("%Y-%m-%d")
    all_orders = list(mongo.db.orders.find({"date": today_str}).sort("_id", -1))
    for order in all_orders:
        order['_id'] = str(order['_id'])
    return jsonify(all_orders), 200

@app.route('/admin/get-reviews', methods=['GET'])
def get_reviews():
    reviews = list(mongo.db.reviews.find().sort("created_at", -1))
    for rev in reviews:
        rev['_id'] = str(rev['_id'])
        if rev.get('media_url'):
            rev['media_url'] = rev['media_url'].replace('\\', '/')
    return jsonify(reviews), 200

@app.route('/admin/update-status', methods=['POST'])
def update_order_status():
    data = request.json
    token_id = data.get('token_id')
    new_status = data.get('status')
    result = mongo.db.orders.update_one({"token_id": token_id}, {"$set": {"status": new_status}})
    if result.modified_count > 0:
        return jsonify({"status": "success", "message": "Updated"}), 200
    return jsonify({"status": "error", "message": "Not found"}), 404


# --- MENU MANAGEMENT DATABASE ROUTES ---

@app.route('/api/get-menu', methods=['GET'])
def get_menu():
    menu_data = mongo.db.menu.find_one({"identifier": "campus_bites_weekly_menu"})
    
    if not menu_data:
        fallback_menu = {
            "identifier": "campus_bites_weekly_menu",
            "Monday": [
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/sambar.png", "name": "Sambar Meals", "price": 100, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Tuesday": [
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/morkulambu.png", "name": "Mor kulambu Meals", "price": 50, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Wednesday": [
                { "img": "/static/images/pongal.png", "name": "Pongal", "price": 40, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/puli kulambu.png", "name": "Puli kulambu Meals", "price": 50, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Thursday": [
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vegBiryani.jpg", "name": "Veg Biriyani", "price": 80, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicken 65.png", "name": "Chicken 65", "price": 50, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Friday": [
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/sambar.png", "name": "Sambar Meals", "price": 50, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Saturday": [
                { "img": "/static/images/porrota.png", "name": "Parotta", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/sambar.png", "name": "Sambar Meals", "price": 50, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ],
            "Sunday": [
                { "img": "/static/images/porrota.png", "name": "Parotta", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.jpg", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/dosai.png", "name": "Dosai", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/idli.png", "name": "Idli", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/vadai.png", "name": "Vadai", "price": 10, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/poori.png", "name": "Poori", "price": 20, "isVeg": True, "isBreakfast": True, "available": True },
                { "img": "/static/images/Chic fried.png", "name": "Chicken Fried Rice", "price": 80, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/vegfried.png", "name": "Veg Fried Rice", "price": 60, "isVeg": True, "isBreakfast": False, "available": True },
                { "img": "/static/images/chicbiri.png", "name": "Chicken Biryani", "price": 100, "isVeg": False, "isBreakfast": False, "available": True },
                { "img": "/static/images/juice.jpg", "name": "Fresh juices", "price": 20, "isVeg": True, "isBreakfast": False, "available": True }
            ]
        }
        mongo.db.menu.insert_one(fallback_menu)
        menu_data = fallback_menu

    menu_data['_id'] = str(menu_data['_id'])
    return jsonify(menu_data), 200

@app.route('/api/admin/toggle-availability', methods=['POST'])
def toggle_availability():
    data = request.json or {}
    day = data.get('day')
    dish_name = data.get('name')
    is_available = data.get('available')

    if not day or not dish_name:
        return jsonify({"message": "Missing day or dish name parameters"}), 400

    result = mongo.db.menu.update_one(
        {"identifier": "campus_bites_weekly_menu"},
        {"$set": {f"{day}.$[elem].available": is_available}},
        array_filters=[{"elem.name": dish_name}]
    )
    
    if result.matched_count > 0:
        return jsonify({"message": "Availability updated successfully", "status": "success"}), 200
        
    return jsonify({"message": "Failed to update availability. Dish not found."}), 400

# --- FIXED: REWRITTEN TO EXTRACT MULTIPART FORM/FILE DATA AND WRITE TO MONGODB ---
@app.route('/api/admin/add-dish', methods=['POST'])
def add_dish():
    try:
        # Extract text field information via form payload dictionary
        day = request.form.get('day')
        name = request.form.get('name')
        price = int(request.form.get('price', 0))
        is_veg = request.form.get('isVeg') == 'true'
        is_breakfast = request.form.get('isBreakfast') == 'true'
        
        if not day or not name:
            return jsonify({"error": "Missing mandatory field data (day or dish name)."}), 400

        # Extract multi-part binary file data stream
        if 'img' not in request.files:
            return jsonify({"error": "No image file part provided inside request parameters."}), 400
            
        file = request.files['img']
        if file.filename == '':
            return jsonify({"error": "No file selected for file-stream transfer."}), 400
            
        if file:
            filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
            save_path = os.path.join(MENU_UPLOAD_FOLDER, filename)
            file.save(save_path)
            
            # Form relative URL targeting token link path pointing to internal disk storage
            db_image_link = f"/static/images/{filename}"
            
            # Map completely unified nested structure schema layout
            new_dish = {
                "name": name,
                "price": float(price),
                "img": db_image_link,
                "isVeg": is_veg,
                "isBreakfast": is_breakfast,
                "available": True
            }

            # Update the central weekly menu item array targeting the dynamic weekday key
            result = mongo.db.menu.update_one(
                {"identifier": "campus_bites_weekly_menu"},
                {"$push": {day: new_dish}}
            )
            
            if result.modified_count > 0:
                return jsonify({"message": f"Successfully loaded {name} into database structural matrices."}), 201
            return jsonify({"error": "Menu collection record targeting operation failure status."}), 400

    except Exception as e:
        print(f"Exception triggered during multi-part file routing intercept: {e}")
        return jsonify({"error": "Internal processing crash pipeline sequence failure"}), 500

@app.route('/admin-menu-management')
def admin_menu_management_page():
    return render_template('admin-menu.html')

# --- STUDENT CANCEL ORDER ---
@app.route('/cancel-order', methods=['POST'])
def cancel_order():
    if 'user_email' not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.json
    token_id = data.get('token_id')
    
    order = mongo.db.orders.find_one({
        "token_id": token_id, 
        "user_email": session['user_email']
    })
    
    if not order:
        return jsonify({"message": "Order not found or access denied"}), 404
        
    if order['status'] != "Pending":
        return jsonify({"message": "Only pending orders can be cancelled"}), 400

    result = mongo.db.orders.update_one(
        {"token_id": token_id}, 
        {"$set": {"status": "Cancelled"}}
    )
    
    if result.modified_count > 0:
        return jsonify({"message": f"Order {token_id} has been cancelled."}), 200
    
    return jsonify({"message": "Update failed"}), 500

@app.route('/get-session', methods=['GET'])
def get_session():
    if 'user_name' in session:
        return jsonify({
            "logged_in": True,
            "user_name": session['user_name'],
            "user_email": session['user_email']
        }), 200
    return jsonify({"logged_in": False}), 200

@app.route('/api/admin/delete-item', methods=['POST'])
def delete_menu_item():
    try:
        data = request.json or {}
        target_day = data.get('day')     
        food_name = data.get('name')      

        if not target_day or not food_name:
            return jsonify({"message": "Missing day or food name parameter"}), 400

        result = mongo.db.menu.update_one(
            {"identifier": "campus_bites_weekly_menu"}, 
            {"$pull": {target_day: {"name": food_name}}}
        )

        if result.modified_count > 0:
            return jsonify({"status": "success", "message": f"Successfully deleted {food_name} from {target_day}."}), 200
        else:
            return jsonify({"message": "Dish not found in database or menu layout remained unmodified."}), 404

    except Exception as e:
        return jsonify({"message": "Internal database exception pipeline error", "error": str(e)}), 500
    
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/admin/daily-analytics', methods=['GET'])
def get_daily_analytics():
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_day_name = now.strftime("%A")

    weekly_menu = {
        "Monday": ["Dosai", "Idli", "Vadai", "Poori", "Sambar Meals", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Tuesday": ["Dosai", "Idli", "Vadai", "Poori", "Mor kulambu Meals", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Wednesday": ["Pongal", "Dosai", "Idli", "Vadai", "Poori", "Puli kulambu Meals", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Thursday": ["Dosai", "Idli", "Vadai", "Poori", "Veg Biriyani", "Chicken 65", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Friday": ["Dosai", "Idli", "Vadai", "Poori", "Sambar Meals", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Saturday": ["Parotta", "Dosai", "Idli", "Vadai", "Poori", "Sambar Meals", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"],
        "Sunday": ["Parotta", "Vadai", "Dosai", "Idli", "Poori", "Chicken Fried Rice", "Veg Fried Rice", "Chicken Biryani", "Fresh juices"]
    }

    todays_expected_items = weekly_menu.get(current_day_name, [])
    query = {
        "date": today_str,
        "status": {"$in": ["Pending", "Ready", "Completed"]} 
    }
    today_orders = list(mongo.db.orders.find(query))
    
    item_counts = {}
    hourly_distribution = {}  
    total_revenue = 0
    total_items_sold = 0 

    for order in today_orders:
        total_revenue += float(order.get('total_amount', 0))
        
        order_time = order.get('time', '00:00:00')
        hour_block = order_time.split(':')[0] + ":00"  
        hourly_distribution[hour_block] = hourly_distribution.get(hour_block, 0) + 1
        
        for item in order.get('items', []):
            if isinstance(item, dict):
                name = item.get('name')
                qty = int(item.get('qty', 1))
            else:
                name = str(item)
                qty = 1
            if name:
                item_counts[name] = item_counts.get(name, 0) + qty
                total_items_sold += qty

    if item_counts:
        most_sold = max(item_counts, key=item_counts.get)
        unsold_items = [item for item in todays_expected_items if item not in item_counts]
    else:
        most_sold = "No sales yet"
        unsold_items = todays_expected_items

    return jsonify({
        "date": today_str,
        "day": current_day_name,
        "total_orders": len(today_orders),
        "total_items_sold": total_items_sold,
        "total_revenue": total_revenue,
        "item_counts": item_counts,
        "hourly_distribution": hourly_distribution,  
        "most_sold": most_sold,
        "unsold_items": unsold_items,
        "server_time": now.strftime("%H:%M:%S")
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)