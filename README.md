# 🍔 Campus Bites

An e-commerce canteen pre-order web application designed to eliminate long queues, streamline order management, and reduce food waste on campus.

---

## 🚀 Features

### **For Students**
* **Browse & Filter Menu:** View available food items in real-time with an intuitive, dynamic interface.
* **Pre-order System:** Place food orders and select pickup slots to avoid peak-hour rush.
* **Order History:** Track current orders and view past meal history seamlessly.
* **Secure Authentication:** Dedicated login and signup systems for security.

### **For Admin / Canteen Management**
* **Live Order Dashboard:** View, track, and update order statuses (Pending, Preparing, Completed) in real-time.
* **Menu Management:** Easily add, update, or remove items based on daily availability.
* **Analytics & Reviews:** Monitor customer feedback and sales trends to optimize daily food preparation.

---

## 🛠️ Tech Stack

* **Frontend:** HTML5, CSS3 (Modern responsive layouts, Glassmorphism UI components, Custom animations), JavaScript (ES6)
* **Backend:** Python, Flask (Micro-framework)
* **Database:** MongoDB (NoSQL database for flexible data modeling)
* **Version Control:** Git & GitHub

---

## 📂 Project Structure

```text
Campus Bites/
│
├── static/
│   ├── css/          # Custom stylesheets (Animations, Glassmorphism layout)
│   ├── images/       # Static UI assets and icons
│   └── uploads/      # Dynamic menu item food images
│
├── templates/        # Jinja2 HTML Templates
│   ├── about.html
│   ├── admin-reviews.html
│   ├── admin.html
│   ├── adminlogin.html
│   ├── analytics.html
│   ├── contact.html
│   ├── home.html
│   ├── login.html
│   ├── menu.html
│   ├── my-orders.html
│   └── signup.html
│
├── .gitignore        # Files ignored by Git (venv, local envs, pycache)
├── app.py            # Main Flask application entry point & routing logic
└── requirements.txt  # Python package dependencies
