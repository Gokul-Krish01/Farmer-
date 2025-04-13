import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId

from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configurations
app.config["MONGO_URI"] = "mongodb://localhost:27017/farmersdb"
app.config["SECRET_KEY"] = "your_secret_key"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))  # Gets the project directory
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")  # Saves inside 'static/uploads'

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure subdirectories exist
os.makedirs(os.path.join(UPLOAD_FOLDER, "products"), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, "profile_pictures"), exist_ok=True)

mongo = PyMongo(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# User Model for Login Management
class User(UserMixin):
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    if user:
        return User(str(user["_id"]), user["username"], user["role"])
    return None

# Home Route
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")
# User Profile Route


@app.route("/help")
def help():
    return render_template("helpline.html")

@app.route("/profile")
@login_required
def profile():
    user = mongo.db.users.find_one({"_id": ObjectId(current_user.id)})
    return render_template("profile.html", user=user)

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        role = request.form["role"]
        age = request.form["age"]
        mobile = request.form["mobile"]
        state = request.form["state"]
        district = request.form["district"]
        pin_code = request.form["pin_code"]

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Profile Picture Upload
        profile_pic = request.files["profile_pic"]
        if profile_pic:
            filename = secure_filename(profile_pic.filename)
            profile_pic_path = os.path.join(app.config["UPLOAD_FOLDER"], "profile_pictures", filename)
            profile_pic.save(profile_pic_path)
        else:
            filename = "default.jpg"

        mongo.db.users.insert_one({
            "username": username,
            "password": hashed_password,
            "role": role,
            "age": age,
            "mobile": mobile,
            "state": state,
            "district": district,
            "pin_code": pin_code,
            "profile_pic": filename
        })
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = mongo.db.users.find_one({"username": username})

        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(str(user["_id"]), user["username"], user["role"]))
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("login.html")

# Logout Route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

# Dashboard Route

# Add Product Route (For Farmers Only)
@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        if current_user.role != "farmer":
            flash("Only farmers can add products!", "danger")
            return redirect(url_for("dashboard"))

        name = request.form["name"]
        price = float(request.form["price"])
        category = request.form["category"]
        description = request.form["description"]
        quantity = int(request.form["quantity"])
        expiry_date = request.form["expiry_date"]
        added_date = datetime.now().strftime("%Y-%m-%d")

        # Handle Image Upload
        image = request.files["image"]
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], "products", filename)
            image.save(image_path)
        else:
            filename = "default.jpg"

        mongo.db.products.insert_one({
            "farmer_id": current_user.id,
            "name": name,
            "price": price,
            "category": category,
            "quantity": quantity,
            "image": filename,
            "description": description,
            "added_date": added_date,
            "expiry_date": expiry_date
        })
        flash("Product added successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_product.html")



@app.route("/dashboard")
@login_required
def dashboard():
    products = list(mongo.db.products.find())

    # Grouping products by category
    categories = {}
    for product in products:
        category = product.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = []
        categories[category].append(product)

    return render_template("dashboard.html", username=current_user.username, role=current_user.role, categories=categories)



# View All Products
@app.route("/products")
@login_required
def products():
    products = list(mongo.db.products.find())

    # Grouping products by category
    categories = {}
    for product in products:
        category = product.get("category", "Uncategorized")
        if category not in categories:
            categories[category] = []
        categories[category].append(product)

    return render_template("products.html", username=current_user.username, role=current_user.role, categories=categories)

# Delete Product Route (For Farmers Only)
@app.route('/product/<product_id>')
def product_detail(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    if not product:
        return "Product not found", 404
    
    related_products = list(mongo.db.products.find({
        "category": product["category"],
        "_id": {"$ne": ObjectId(product_id)}
    }).limit(4))

    reviews = list(mongo.db.reviews.find({"product_id": product_id}))

    return render_template("product_detail.html", product=product, reviews=reviews, related_products=related_products)


@app.route('/delete_product/<string:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})

    if product and str(product["farmer_id"]) == current_user.id:
        mongo.db.products.delete_one({"_id": ObjectId(product_id)})
        flash("Product deleted successfully!", "success")
    else:
        flash("Unauthorized action!", "danger")

    return redirect(url_for("products"))

@app.route("/add_to_cart/<product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
    
    if not product:
        flash("Product not found!", "danger")
        return redirect(url_for("products"))

    quantity = int(request.form["quantity"])
    
    existing_cart_item = mongo.db.cart.find_one({
        "user_id": current_user.id, "product_id": product_id
    })

    if existing_cart_item:
        new_quantity = existing_cart_item["quantity"] + quantity
        mongo.db.cart.update_one(
            {"_id": existing_cart_item["_id"]},
            {"$set": {"quantity": new_quantity}}
        )
        flash(f"Quantity updated for {product['name']} in your cart!", "success")
    else:
        mongo.db.cart.insert_one({
            "user_id": current_user.id,
            "product_id": product_id,
            "quantity": quantity
        })

    flash("Product added to cart!", "success")
    return redirect(request.referrer)  
@app.route("/cart")
@login_required
def view_cart():
    cart_items = list(mongo.db.cart.find({"user_id": current_user.id}))
    
    product_ids = [ObjectId(item["product_id"]) for item in cart_items]
    products = list(mongo.db.products.find({"_id": {"$in": product_ids}}))

    cart_details = []
    total_price = 0

    for item in cart_items:
        for product in products:
            if str(product["_id"]) == item["product_id"]:
                cart_details.append({
                    "name": product["name"],
                    "price": product["price"],
                    "quantity": item["quantity"],
                    "total": product["price"] * item["quantity"],
                    "product_id": item["product_id"]
                })
                total_price += product["price"] * item["quantity"]

    return render_template("cart.html", cart_items=cart_details, total_price=total_price)

@app.route("/remove_from_cart/<product_id>", methods=["POST"])
@login_required
def remove_from_cart(product_id):
    mongo.db.cart.delete_one({"user_id": current_user.id, "product_id": product_id})
    flash("Item removed from cart.", "success")
    return redirect(url_for("view_cart"))

@app.route('/payment', methods=['GET', 'POST'])
@login_required
def payment():
    # Check if a product_id is provided for direct purchase
    product_id = request.args.get("product_id")
    quantity = int(request.args.get("quantity", 1))  # Default to 1

    cart_details = []
    total_price = 0

    if product_id:  # If direct purchase
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        if not product:
            flash("Product not found!", "danger")
            return redirect(url_for("products"))

        cart_details.append({
            "name": product["name"],
            "price": product["price"],
            "quantity": quantity,
            "total": product["price"] * quantity,
            "product_id": str(product["_id"])
        })
        total_price = product["price"] * quantity

    else:  # If proceeding with cart checkout
        cart_items = list(mongo.db.cart.find({"user_id": current_user.id}))
        if not cart_items:
            flash("Your cart is empty!", "danger")
            return redirect(url_for("view_cart"))

        product_ids = [ObjectId(item["product_id"]) for item in cart_items]
        products = list(mongo.db.products.find({"_id": {"$in": product_ids}}))

        for item in cart_items:
            for product in products:
                if str(product["_id"]) == item["product_id"]:
                    cart_details.append({
                        "name": product["name"],
                        "price": product["price"],
                        "quantity": item["quantity"],
                        "total": product["price"] * item["quantity"],
                        "product_id": item["product_id"]
                    })
                    total_price += product["price"] * item["quantity"]

    return render_template('payment.html', cart_items=cart_details, total_price=total_price)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    name = request.form['name']
    mobile = request.form['mobile']
    address = request.form['address']
    pincode = request.form['pincode']
    payment_method = request.form['payment_method']

    if payment_method == 'upi':
        upi_id = request.form['upi_id']
        flash(f"UPI Payment of ₹{session['total_price']} received from {upi_id}.", "success")
    elif payment_method == 'card':
        card_number = request.form['card_number']
        expiry = request.form['expiry']
        cvv = request.form['cvv']
        flash("Card Payment Successful!", "success")
    else:
        flash("Order placed successfully. Pay on delivery.", "success")

    return redirect(url_for('order_success'))


@app.route('/order_success')
def order_success():
    return "<h1>Payment Successful! Your Order is Confirmed 🎉</h1>"

# Run the Flask App
if __name__ == "__main__":
    app.run(debug=True)
