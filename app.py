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

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

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
    all_orders = list(mongo.db.orders.find().sort("_id", -1))
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
    total_revenue = 0
    total_items_sold = 0 

    for order in today_orders:
        total_revenue += float(order.get('total_amount', 0))
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
        "most_sold": most_sold,
        "unsold_items": unsold_items,
        "server_time": now.strftime("%H:%M:%S")
    }), 200

if __name__ == '__main__':
    # Keeps local dynamic ports running smoothly if ran locally
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)