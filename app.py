from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import logging
from logging.handlers import RotatingFileHandler
import os

app = Flask(__name__, template_folder="templates")
app.secret_key = "your_secret_key"

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",   # change if needed
        password="root",
        database="justeat"
    )


# ---------------- Routes ----------------

# Home Page
@app.route('/')
def home():
    return render_template("home.html")

# Login Selection Page
@app.route('/login')
def login():
    return render_template("login.html")

# Signup Selection Page
@app.route('/signup')
def signup():
    return render_template("signup.html")

# Create a logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.mkdir('logs')

# Configure logging
handler = RotatingFileHandler('logs/app.log', maxBytes=100000, backupCount=3)
handler.setLevel(logging.INFO)  # logs INFO, WARNING, ERROR, CRITICAL
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# ---------------- Customer Login ----------------
@app.route('/login_user', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        role = request.form['role']   # "customer" or "owner"
        email = request.form['email']
        password = request.form['password']

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        if role == 'customer':
            cursor.execute("SELECT * FROM customers WHERE email=%s", (email,))
        elif role == 'owner':
            cursor.execute("SELECT * FROM owners WHERE email=%s", (email,))
        else:
            flash("Invalid role selected!", "danger")
            return redirect(url_for("login"))

        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user[f"{role}_id"]  # customer_id or owner_id
            session['user'] = user['name']
            session['role'] = role
            flash(f"{role.capitalize()} login successful!", "success")

            if role == 'customer':
                return redirect(url_for("customer_dashboard"))
            else:
                return redirect(url_for("owner_dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("login_user.html")

@app.route('/customer/signup', methods=['GET', 'POST'])
def customer_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.execute(
                "INSERT INTO customers (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)
            )
            db.commit()
            flash("Customer account created successfully! Please login.", "success")
            return redirect(url_for('customer_login'))
        except mysql.connector.Error as err:
            flash()
        finally:
            cursor.close()
            db.close()

    return render_template("customer/customer_signup.html")

# ---------------- Restaurant Signup ----------------
from werkzeug.security import generate_password_hash

# ---------------- Owner Signup ----------------
@app.route('/owner/signup', methods=['GET', 'POST'])
def owner_signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        db = get_db_connection()
        cursor = db.cursor()

        try:
            cursor.execute(
                "INSERT INTO owners (name, email, password) VALUES (%s, %s, %s)",
                (name, email, password)
            )
            db.commit()
            flash("Owner account created successfully! Please login.", "success")
            return redirect(url_for('owner_login'))
        except mysql.connector.Error as err:
            flash(f"Error: {err}", "danger")
        finally:
            cursor.close()
            db.close()

    return render_template("owner/owner_signup.html")

# ---------------- Dashboards (dummy for now) ----------------
@app.route('/customer/reviews', methods=['GET', 'POST'])
def customer_reviews():
    pass
    
@app.route('/customer/profile', methods=['GET', 'POST'])
def customer_profile():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('customer_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form.get('password')  # optional
        dietary_restrictions = request.form.get('dietary_restrictions')
        favourite_restaurant = request.form.get('favourite_restaurant')
        favourite_cuisine = request.form.get('favourite_cuisine')

        # If password provided, include it
        if password:
            cursor.execute(
                """
                UPDATE customers 
                SET name=%s, email=%s, phone=%s, password=%s,
                    dietary_restrictions=%s, favourite_restaurant=%s, favourite_cuisine=%s
                WHERE customer_id=%s
                """,
                (name, email, phone, password, dietary_restrictions, favourite_restaurant, favourite_cuisine, session['user_id'])
            )
        else:
            cursor.execute(
                """
                UPDATE customers 
                SET name=%s, email=%s, phone=%s,
                    dietary_restrictions=%s, favourite_restaurant=%s, favourite_cuisine=%s
                WHERE customer_id=%s
                """,
                (name, email, phone, dietary_restrictions, favourite_restaurant, favourite_cuisine, session['user_id'])
            )

        db.commit()
        flash("Profile updated successfully!", "success")

    # Fetch customer details again
    cursor.execute("SELECT * FROM customers WHERE customer_id=%s", (session['user_id'],))
    customer = cursor.fetchone()
    cursor.close()
    db.close()

    return render_template('customer/customer_profile.html', customer=customer)

@app.route('/customer/dashboard')
def customer_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # --- Get filter values from request ---
    name_filter = request.args.get('name', '').strip()
    address_filter = request.args.get('address', '').strip()
    cuisine_filter = request.args.get('cuisine', '').strip()

    # --- Fetch unique cuisines for filter dropdown ---
    cursor.execute("SELECT DISTINCT cuisine FROM menu_items WHERE cuisine IS NOT NULL")
    cuisines = [row['cuisine'] for row in cursor.fetchall()]

    # --- Fetch restaurants with optional filters ---
    query = """
        SELECT r.restaurant_id, r.name, r.address,
               COALESCE(ROUND(AVG(rr.rating),1),0) AS avg_rating
        FROM restaurants r
        LEFT JOIN restaurant_reviews rr ON r.restaurant_id = rr.restaurant_id
        LEFT JOIN menu_items m ON r.restaurant_id = m.restaurant_id
        WHERE 1=1
    """
    params = []

    if name_filter:
        query += " AND r.name LIKE %s"
        params.append(f"%{name_filter}%")
    if address_filter:
        query += " AND r.address LIKE %s"
        params.append(f"%{address_filter}%")
    if cuisine_filter:
        query += " AND m.cuisine LIKE %s"
        params.append(f"%{cuisine_filter}%")

    query += " GROUP BY r.restaurant_id"
    cursor.execute(query, params)
    restaurants = cursor.fetchall()

    # --- Deal of the Day ---
    cursor.execute("""
        SELECT m.item_id, m.name, m.price, r.name AS restaurant_name
        FROM menu_items m
        JOIN restaurants r ON m.restaurant_id = r.restaurant_id
        WHERE m.is_deal_of_day = 1
    """)
    deals = cursor.fetchall()

    # --- Recommended Items ---
    cursor.execute("""
        SELECT m.item_id, m.name, m.price, r.name AS restaurant_name
        FROM menu_items m
        JOIN restaurants r ON m.restaurant_id = r.restaurant_id
        WHERE m.is_recommended = 1
    """)
    recommendations = cursor.fetchall()

    conn.close()

    return render_template(
        'customer/customer_dashboard.html',
        restaurants=restaurants,
        deals=deals,
        recommendations=recommendations,
        cuisines=cuisines,
        selected_cuisine=cuisine_filter,
        name_filter=name_filter,
        address_filter=address_filter
    )

# ---------------- Customer Cart ----------------
@app.route('/customer/cart')
def customer_cart():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    cart = session.get('cart', [])
    total = sum(float(item['price']) * int(item['quantity']) for item in cart)
    return render_template('customer/customer_cart.html', cart=cart, total=total)

# ---------------- Add Item to Cart ----------------
@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu_items WHERE item_id=%s", (item_id,))
    item = cursor.fetchone()
    cursor.close()
    db.close()

    if not item:
        flash("Item not found!", "danger")
        return redirect(request.referrer)

    cart = session.get('cart', [])
    for c in cart:
        if c['item_id'] == item_id:
            c['quantity'] += 1
            break
    else:
        cart.append({
            'item_id': item['item_id'],
            'restaurant_id': item['restaurant_id'],
            'name': item['name'],
            'price': float(item['price']),
            'quantity': 1
        })

    session['cart'] = cart
    flash("Item added to cart!", "success")
    return redirect(request.referrer)

# ---------------- Increase Quantity ----------------
@app.route('/increase_quantity/<int:item_id>')
def increase_quantity(item_id):
    cart = session.get('cart', [])
    for c in cart:
        if c['item_id'] == item_id:
            c['quantity'] += 1
            break
    session['cart'] = cart
    return redirect(url_for('customer_cart'))

# ---------------- Decrease Quantity ----------------
@app.route('/decrease_quantity/<int:item_id>')
def decrease_quantity(item_id):
    cart = session.get('cart', [])
    for c in cart:
        if c['item_id'] == item_id:
            c['quantity'] -= 1
            if c['quantity'] <= 0:
                cart.remove(c)
            break
    session['cart'] = cart
    return redirect(url_for('customer_cart'))

# ---------------- Remove Item from Cart ----------------
@app.route('/remove_from_cart/<int:item_id>')
def remove_from_cart(item_id):
    cart = session.get('cart', [])
    cart = [c for c in cart if c['item_id'] != item_id]
    session['cart'] = cart
    return redirect(url_for('customer_cart'))

# ---------------- Checkout ----------------
@app.route('/customer/checkout')
def checkout():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    cart = session.get('cart', [])
    if not cart:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('customer_cart'))

    customer_id = session['user_id']

    # Ensure single restaurant per order
    restaurant_ids = set(item['restaurant_id'] for item in cart)
    if len(restaurant_ids) > 1:
        flash("You can only order from one restaurant at a time!", "warning")
        return redirect(url_for('customer_cart'))
    restaurant_id = cart[0]['restaurant_id']

    total_amount = sum(float(item['price']) * int(item['quantity']) for item in cart)

    # Prepare items_summary
    items_summary = ", ".join([f"[{item['quantity']} {item['name']}]" for item in cart])

    db = get_db_connection()
    cursor = db.cursor()

    # Insert order with items_summary
    cursor.execute(
        "INSERT INTO orders (customer_id, restaurant_id, total_amount, items_summary) VALUES (%s, %s, %s, %s)",
        (customer_id, restaurant_id, total_amount, items_summary)
    )
    order_id = cursor.lastrowid

    # Insert order items as before (optional, if you still want a detailed table)
    for item in cart:
        cursor.execute(
            "INSERT INTO order_items (order_id, item_id, quantity, price) VALUES (%s, %s, %s, %s)",
            (order_id, item['item_id'], item['quantity'], item['price'])
        )

    db.commit()
    cursor.close()
    db.close()

    session['cart'] = []
    flash("Order placed successfully!", "success")
    return redirect(url_for('customer_orders_history'))

@app.route('/customer/orders_history')
def customer_orders_history():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    customer_id = session['user_id']
    search = request.args.get('search', '')

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Base query
    query = """
        SELECT 
            o.order_id, 
            o.restaurant_id, 
            r.name AS restaurant_name, 
            o.total_amount, 
            o.status, 
            o.items_summary, 
            o.created_at
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        WHERE o.customer_id = %s
    """
    params = [customer_id]

    # Apply search filter
    if search:
        query += """
            AND (r.name LIKE %s OR o.status LIKE %s OR o.order_id LIKE %s)
        """
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    query += " ORDER BY o.created_at DESC"

    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('customer/customer_orders_history.html', orders=orders, search=search)

# ---------------- Order Reviews ----------------
@app.route('/customer/order_reviews', methods=['GET', 'POST'])
def customer_order_reviews():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    customer_id = session['user_id']
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        # Save or update review
        order_id = request.form['order_id']
        rating = int(request.form['rating'])
        feedback = request.form.get('feedback', '')

        # Check if review exists
        cursor.execute("SELECT * FROM order_reviews WHERE order_id=%s AND customer_id=%s", (order_id, customer_id))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                "UPDATE order_reviews SET rating=%s, feedback=%s WHERE order_id=%s AND customer_id=%s",
                (rating, feedback, order_id, customer_id)
            )
        else:
            cursor.execute(
                "INSERT INTO order_reviews (order_id, customer_id, rating, feedback) VALUES (%s,%s,%s,%s)",
                (order_id, customer_id, rating, feedback)
            )
        db.commit()
        flash("Review saved successfully!", "success")
        return redirect(url_for('customer_order_reviews'))

    # GET request: Fetch orders and existing reviews
    cursor.execute("""
        SELECT o.order_id, o.items_summary, r.name AS restaurant_name, o.status,
               orv.rating, orv.feedback
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        LEFT JOIN order_reviews orv ON o.order_id = orv.order_id AND orv.customer_id=%s
        WHERE o.customer_id=%s
        ORDER BY o.created_at DESC
    """, (customer_id, customer_id))
    orders = cursor.fetchall()
    
    cursor.close()
    db.close()

    return render_template('customer/customer_order_reviews.html', orders=orders)

# ---------------- Restaurant Ratings ----------------
@app.route('/customer/restaurant_ratings', methods=['GET', 'POST'])
def customer_restaurant_ratings():
    if 'user_id' not in session or session.get('role') != 'customer':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    customer_id = session['user_id']
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Handle form submission
    if request.method == 'POST':
        restaurant_id = int(request.form['restaurant_id'])
        rating = int(request.form['rating'])
        feedback = request.form['feedback']

        # Check if review exists
        cursor.execute("SELECT * FROM restaurant_reviews WHERE restaurant_id=%s AND customer_id=%s",
                       (restaurant_id, customer_id))
        review = cursor.fetchone()

        if review:
            # Update existing review
            cursor.execute("""
                UPDATE restaurant_reviews
                SET rating=%s, feedback=%s
                WHERE restaurant_id=%s AND customer_id=%s
            """, (rating, feedback, restaurant_id, customer_id))
            flash("Review updated successfully!", "success")
        else:
            # Insert new review
            cursor.execute("""
                INSERT INTO restaurant_reviews (restaurant_id, customer_id, rating, feedback)
                VALUES (%s, %s, %s, %s)
            """, (restaurant_id, customer_id, rating, feedback))
            flash("Review added successfully!", "success")
        db.commit()

    # Fetch all restaurants with existing reviews (if any) by this customer
    cursor.execute("""
        SELECT r.restaurant_id, r.name AS restaurant_name, rr.rating, rr.feedback
        FROM restaurants r
        LEFT JOIN restaurant_reviews rr 
        ON r.restaurant_id = rr.restaurant_id AND rr.customer_id=%s
    """, (customer_id,))
    restaurants = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template('customer/customer_restaurant_ratings.html', restaurants=restaurants)

@app.route('/restaurant/<int:restaurant_id>/menu')
def restaurant_menu(restaurant_id):
    if 'user_id' not in session:
        flash("Please login first!", "warning")
        return redirect(url_for('customer_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Get restaurant info
    cursor.execute("SELECT * FROM restaurants WHERE restaurant_id=%s", (restaurant_id,))
    restaurant = cursor.fetchone()
    if not restaurant:
        flash("Restaurant not found!", "danger")
        return redirect(url_for('customer_dashboard'))

    # Get menu items
    cursor.execute("SELECT * FROM menu_items WHERE restaurant_id=%s", (restaurant_id,))
    menu_items = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template('customer/restaurant_menu.html', restaurant=restaurant, menu_items=menu_items)

@app.route('/owner/dashboard')
def owner_dashboard():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    owner_id = session['user_id']

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch restaurants owned by this owner
    cursor.execute("SELECT * FROM restaurants WHERE owner_id = %s", (owner_id,))
    restaurants = cursor.fetchall()

    # Fetch most ordered items today for all restaurants of this owner
    cursor.execute("""
        SELECT mi.item_id, mi.name, r.name AS restaurant_name, SUM(oi.quantity) AS total_ordered
        FROM menu_items mi
        JOIN order_items oi ON mi.item_id = oi.item_id
        JOIN orders o ON oi.order_id = o.order_id
        JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
        WHERE r.owner_id = %s
          AND DATE(o.created_at) = CURDATE()
        GROUP BY mi.item_id
        HAVING total_ordered > 10
        ORDER BY total_ordered DESC
    """, (owner_id,))
    most_ordered_items = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "owner/owner_dashboard.html",
        restaurants=restaurants,
        most_ordered_items=most_ordered_items
    )

# ---------------- Add Restaurant ----------------
@app.route('/owner/restaurant/add', methods=['GET', 'POST'])
def add_restaurant():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO restaurants (owner_id, name, address, phone) VALUES (%s, %s, %s, %s)",
            (session['user_id'], name, address, phone)
        )
        db.commit()
        cursor.close()
        db.close()

        flash("Restaurant added successfully!", "success")
        return redirect(url_for('owner_dashboard'))

    return render_template("owner/add_restaurant.html")


# ---------------- Edit Restaurant ----------------
@app.route('/owner/restaurant/edit/<int:restaurant_id>', methods=['GET', 'POST'])
def edit_restaurant(restaurant_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM restaurants WHERE restaurant_id=%s AND owner_id=%s",
        (restaurant_id, session['user_id'])
    )
    restaurant = cursor.fetchone()

    if not restaurant:
        flash("Restaurant not found!", "danger")
        cursor.close()
        db.close()
        return redirect(url_for('owner_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']

        cursor.execute(
            "UPDATE restaurants SET name=%s, address=%s, phone=%s WHERE restaurant_id=%s AND owner_id=%s",
            (name, address, phone, restaurant_id, session['user_id'])
        )
        db.commit()
        flash("Restaurant updated successfully!", "success")
        cursor.close()
        db.close()
        return redirect(url_for('owner_dashboard'))

    cursor.close()
    db.close()
    return render_template("owner/edit_restaurant.html", restaurant=restaurant)


# ---------------- Delete Restaurant ----------------
@app.route('/owner/restaurant/delete/<int:restaurant_id>')
def delete_restaurant(restaurant_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    db = get_db_connection()
    cursor = db.cursor()
    # Delete only if restaurant belongs to logged-in owner
    cursor.execute(
        "DELETE FROM restaurants WHERE restaurant_id=%s AND owner_id=%s",
        (restaurant_id, session['user_id'])
    )
    db.commit()
    cursor.close()
    db.close()

    flash("Restaurant deleted successfully!", "success")
    return redirect(url_for('owner_dashboard'))

# ---------------- Restaurant Profile / Menu ----------------
@app.route('/owner/restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
def restaurant_profile(restaurant_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch restaurant details
    cursor.execute("SELECT * FROM restaurants WHERE restaurant_id = %s", (restaurant_id,))
    restaurant = cursor.fetchone()
    if not restaurant:
        flash("Restaurant not found!", "danger")
        return redirect(url_for('owner_dashboard'))

    # Fetch menu items for this restaurant
    cursor.execute("SELECT * FROM menu_items WHERE restaurant_id = %s", (restaurant_id,))
    menu_items = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("owner/restaurant_profile.html", restaurant=restaurant, menu_items=menu_items)

# Toggle recommended
@app.route('/menu/toggle_recommended/<int:item_id>')
def toggle_recommended(item_id):
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("UPDATE menu_items SET is_recommended = NOT is_recommended WHERE item_id = %s", (item_id,))
    db.commit()
    cursor.close()
    db.close()
    flash("Recommendation status updated!", "success")
    return redirect(request.referrer)

# Set Deal of the Day (only one per restaurant)
@app.route('/menu/set_deal_of_day/<int:item_id>/<int:restaurant_id>')
def set_deal_of_day(item_id, restaurant_id):
    db = get_db_connection()
    cursor = db.cursor()
    # Reset all items in that restaurant
    cursor.execute("UPDATE menu_items SET is_deal_of_day = 0 WHERE restaurant_id = %s", (restaurant_id,))
    # Mark selected one
    cursor.execute("UPDATE menu_items SET is_deal_of_day = 1 WHERE item_id = %s", (item_id,))
    db.commit()
    cursor.close()
    db.close()
    flash("Deal of the Day updated!", "success")
    return redirect(request.referrer)


# ---------------- Owner Profile ----------------
@app.route('/owner/profile', methods=['GET', 'POST'])
def owner_profile():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    owner_id = session['user_id']
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        if password:  # update password if provided
            hashed_pw = generate_password_hash(password)
            cursor.execute("""
                UPDATE owners 
                SET name=%s, email=%s, phone=%s, password=%s 
                WHERE owner_id=%s
            """, (name, email, phone, hashed_pw, owner_id))
        else:
            cursor.execute("""
                UPDATE owners 
                SET name=%s, email=%s, phone=%s 
                WHERE owner_id=%s
            """, (name, email, phone, owner_id))

        db.commit()
        flash("Profile updated successfully!", "success")

    cursor.execute("SELECT * FROM owners WHERE owner_id = %s", (owner_id,))
    owner = cursor.fetchone()
    cursor.close()
    db.close()

    return render_template("owner/owner_profile.html", owner=owner)

@app.route('/owner/restaurant/<int:restaurant_id>/add', methods=['GET', 'POST'])
def add_menu_item(restaurant_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        cuisine = request.form.get('cuisine', None)
        is_recommended = 1 if request.form.get('is_recommended') else 0
        is_deal_of_day = 1 if request.form.get('is_deal_of_day') else 0

        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO menu_items (restaurant_id, name, description, price, cuisine, is_recommended, is_deal_of_day)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (restaurant_id, name, description, price, cuisine, is_recommended, is_deal_of_day))
        db.commit()
        cursor.close()
        db.close()
        flash("Menu item added successfully!", "success")
        return redirect(url_for('restaurant_profile', restaurant_id=restaurant_id))

    return render_template('owner/add_menu_item.html', restaurant_id=restaurant_id)

@app.route('/owner/menu_item/<int:item_id>/edit', methods=['GET', 'POST'])
def edit_menu_item(item_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM menu_items WHERE item_id = %s", (item_id,))
    item = cursor.fetchone()
    if not item:
        flash("Menu item not found!", "danger")
        return redirect(url_for('owner_dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']

        cursor.execute("""
            UPDATE menu_items
            SET name=%s, description=%s, price=%s
            WHERE item_id=%s
        """, (name, description, price, item_id))
        db.commit()
        cursor.close()
        db.close()
        flash("Menu item updated successfully!", "success")
        return redirect(url_for('restaurant_profile', restaurant_id=item['restaurant_id']))

    cursor.close()
    db.close()
    return render_template('owner/edit_menu_item.html', item=item)

@app.route('/owner/menu_item/<int:item_id>/delete')
def delete_menu_item(item_id):
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('owner_login'))

    db = get_db_connection()
    cursor = db.cursor()
    # Fetch restaurant id before deleting
    cursor.execute("SELECT restaurant_id FROM menu_items WHERE item_id = %s", (item_id,))
    result = cursor.fetchone()
    if result:
        restaurant_id = result[0]
        cursor.execute("DELETE FROM menu_items WHERE item_id = %s", (item_id,))
        db.commit()
        flash("Menu item deleted successfully!", "success")
    else:
        flash("Menu item not found!", "danger")

    cursor.close()
    db.close()
    return redirect(url_for('restaurant_profile', restaurant_id=restaurant_id))

@app.route('/owner/track_orders', methods=['GET', 'POST'])
def owner_track_orders():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    owner_id = session['user_id']
    search = request.args.get('search', '')

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Handle status update
    if request.method == 'POST':
        order_id = request.form.get('order_id')
        new_status = request.form.get('status')
        if order_id and new_status:
            cursor.execute("UPDATE orders SET status=%s WHERE order_id=%s", (new_status, order_id))
            db.commit()
            flash(f"Order {order_id} status updated to {new_status}!", "success")

    # Fetch all orders for restaurants owned by this owner
    query = """
        SELECT o.order_id, o.customer_id, o.restaurant_id, r.name AS restaurant_name, 
               o.total_amount, o.status, o.items_summary, o.created_at
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        WHERE r.owner_id = %s
    """
    params = [owner_id]

    if search:
        query += " AND (r.name LIKE %s OR o.status LIKE %s OR o.order_id LIKE %s)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param])

    query += " ORDER BY o.created_at DESC"

    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('owner/owner_track_orders.html', orders=orders, search=search)

@app.route('/owner/reviews')
def owner_reviews():
    if 'user_id' not in session or session.get('role') != 'owner':
        flash("Please login first!", "warning")
        return redirect(url_for('login_user'))

    owner_id = session['user_id']
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch all restaurants of this owner
    cursor.execute("""
        SELECT restaurant_id, name FROM restaurants
        WHERE owner_id=%s
    """, (owner_id,))
    restaurants = cursor.fetchall()
    restaurant_ids = [r['restaurant_id'] for r in restaurants]

    reviews_data = {}

    if restaurant_ids:
        # Restaurant Reviews
        format_ids = ','.join(str(i) for i in restaurant_ids)
        cursor.execute(f"""
            SELECT rr.review_id, rr.restaurant_id, c.name AS customer_name,
                   rr.rating, rr.feedback, rr.created_at, r.name AS restaurant_name
            FROM restaurant_reviews rr
            JOIN customers c ON rr.customer_id = c.customer_id
            JOIN restaurants r ON rr.restaurant_id = r.restaurant_id
            WHERE rr.restaurant_id IN ({format_ids})
            ORDER BY rr.created_at DESC
        """)
        reviews_data['restaurant_reviews'] = cursor.fetchall()

        # Order Reviews
        cursor.execute(f"""
            SELECT orv.review_id, orv.order_id, o.items_summary, r.name AS restaurant_name,
                   c.name AS customer_name, orv.rating, orv.feedback, orv.created_at
            FROM order_reviews orv
            JOIN orders o ON orv.order_id = o.order_id
            JOIN customers c ON orv.customer_id = c.customer_id
            JOIN restaurants r ON o.restaurant_id = r.restaurant_id
            WHERE o.restaurant_id IN ({format_ids})
            ORDER BY orv.created_at DESC
        """)
        reviews_data['order_reviews'] = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('owner/owner_reviews.html', reviews_data=reviews_data)

# ---------------- Owner Logout ----------------
@app.route('/logout')
def logout():
    role = session.get('role')
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login_user"))

if __name__ == "__main__":
    app.run(debug=True)