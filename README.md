# 🍽️ JustEat — Food Ordering Web Application

JustEat is a Flask + MySQL based food ordering application with role-based login for Customers and Restaurant Owners. Users can browse restaurants/menus, add items to cart, and place orders, while restaurant owners can manage menu items and process customer orders.

---

## 🚀 How to Run the Application

1. **Clone the repository**
   git clone https://github.com/Avinash238/JustEat.git
   cd JustEat

2. **Install dependencies**
   pip install -r requirements.txt

3. **Configure MySQL**
   Ensure MySQL server is running locally and update DB credentials inside the project (app.py / config file) to match your local setup.

4. **Seed the database**
   python seed.py

5. **Start the application**
   python app.py

6. **Open in browser**
   http://127.0.0.1:5000/

---

## 🛠 Tech Stack
- Python (Flask)
- MySQL
- HTML, CSS, Bootstrap

---

## 📌 Notes
- Login is role-based (Customer and Restaurant Owner).
- MySQL must be running locally before launching the app.
