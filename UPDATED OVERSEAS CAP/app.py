import os, sqlite3, csv
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from werkzeug.utils import secure_filename
from io import StringIO
from flask import make_response

app = Flask(__name__)
app.secret_key = 'overse    as_cap_secret'

# Database Setup
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'overseas_cap.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static/uploads')

# Configuration for where to save photos
UPLOAD_FOLDER = 'static/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- Database Models ---

def get_db_connection():
    # MUST match your app.config['SQLALCHEMY_DATABASE_URI'] filename
    conn = sqlite3.connect(os.path.join(basedir, 'overseas_cap.db')) 
    conn.row_factory = sqlite3.Row 
    return conn

# In app.py
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_file = db.Column(db.String(100), nullable=False, default='default.jpg')
    description = db.Column(db.Text, nullable=True)
    color_variants = db.relationship('ProductColorImage', backref='product', lazy=True, cascade="all, delete-orphan")
    size_variants = db.relationship('ProductSize', backref='product', lazy=True, cascade="all, delete-orphan")

    # Relationships to get "Accurate" ratings and sales
    reviews = db.relationship('Review', backref='product', lazy=True)
    orders = db.relationship('CustomOrder', backref='product', lazy=True)
   
# NEW MODEL: Stores an image for a specific color variation
class ProductColorImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    color_name = db.Column(db.String(50), nullable=False) # e.g., 'Air Force Officer'
    price = db.Column(db.Float)
    image_file = db.Column(db.String(100), nullable=False) # The specific image for this color

# NEW MODEL: Stores available sizes for the product
class ProductSize(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    size_value = db.Column(db.String(20), nullable=False) # e.g., '53', '54', 'S', 'M'
   
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    sender_name = db.Column(db.String(100))
    message = db.Column(db.Text, nullable=False)
    admin_reply = db.Column(db.Text, nullable=True) # Stores the Admin's response
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False) 
    
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    review_image = db.Column(db.String(100), nullable=True)
   
    # THE MISSING LINK: This connects the review to a specific Product
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('custom_order.id'), nullable=False)
    product_type = db.Column(db.String(50))
    product_color = db.Column(db.String(50))
    product_size = db.Column(db.String(50))
    admin_reply = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', backref='user_reviews', lazy=True)
    
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material = db.Column(db.String(100), nullable=False)
    supplier = db.Column(db.String(100), nullable=False)
    qty = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50), default="Available")
    
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    contact = db.Column(db.String(50))
    supply = db.Column(db.String(100))
    price_range = db.Column(db.String(100))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    full_name = db.Column(db.String(120), default="NOT SET")
    contact = db.Column(db.String(20), default="NOT SET")
    email = db.Column(db.String(120), unique=True, nullable=False)
    address = db.Column(db.String(200), default="NOT SET")
    purchase_info = db.Column(db.String(500), default="NONE")
    profile_pic = db.Column(db.String(200), default="default.png")

class CustomOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    contact_number = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product_type = db.Column(db.String(50))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    color_type = db.Column(db.String(50))
    size_type = db.Column(db.String(50))
    color_variants = db.Column(db.String(50))
    size_variants = db.Column(db.String(50))
    material_type = db.Column(db.String(100))
    interlining_thickness = db.Column(db.String(100))
    order_type = db.Column(db.String(50)) 
    design_filename = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    status = db.Column(db.String(20), default="PENDING")
    payment_method = db.Column(db.String(50)) 
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    payment_proof = db.Column(db.String(100))
    price = db.Column(db.Float, default=0.0)

with app.app_context():
    db.create_all()
    
    # Check if the database is empty before adding defaults
    if not Product.query.first():
        # 1. Create the Main Product
        p1 = Product(
            name="Classic Cap", 
            price=500.00, 
            description="Our signature high-quality overseas cap, designed for comfort and style.",
            image_file="cap1.jpg"
        )
        db.session.add(p1)
        db.session.flush()  # Flush to get p1.id for the variants

        # 2. Add Default Sizes
        default_sizes = ['53', '54', 'S', 'M', 'L']
        for size in default_sizes:
            db.session.add(ProductSize(product_id=p1.id, size_value=size))

        # 3. Add Default Colors/Images
        # These represent different color options which can have their own images and prices
        colors = [
            {'name': 'Navy Blue', 'price': 500.00, 'img': 'cap1.jpg'},
            {'name': 'White', 'price': 550.00, 'img': 'cap_white.jpg'},
            {'name': 'Khaki', 'price': 500.00, 'img': 'cap_khaki.jpg'}
        ]
        
        for c in colors:
            db.session.add(ProductColorImage(
                product_id=p1.id,
                color_name=c['name'],
                price=c['price'],
                image_file=c['img']
            ))

        db.session.commit()
        print("Default products with sizes and colors added!")
    else:
        print("Products already exist, skipping duplicate creation.")
# --- ROUTES ---

@app.context_processor
def inject_stats():
    # Basic stats available globally
    admin_stats = {
        'total': CustomOrder.query.count(),
        'pending': CustomOrder.query.filter_by(status='PENDING').count(),
        'completed': CustomOrder.query.filter(CustomOrder.status.in_(['DONE', 'COMPLETED'])).count()
    }
    return dict(admin_stats=admin_stats)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Regular customer login
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user'] = user.username
            return redirect(url_for('home'))
        flash("Invalid Credentials!")
        
    return render_template('login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Specific Admin login
        if username == "ADMIN" and password == "1234":
            session['user'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        flash("Invalid Admin Credentials!")
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Collect all data from the expanded form
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        email = request.form['email']
        contact = request.form['contact']
        address = request.form['address']

        # 2. Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists!")
        else:
            # 3. Create the new user with all the profile info
            # Note: Using generate_password_hash is safer for your users
            new_user = User(
                username=username, 
                password=password, # Use generate_password_hash(password) if using Flask-Login
                full_name=full_name, 
                email=email, 
                contact=contact, 
                address=address
            )
            
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login.")
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/home')
def home():
    # 1. Start the query
    query = Product.query
    
    # 2. Get Search and Filter values from the URL
    q = request.args.get('q')
    min_p = request.args.get('min_price')
    max_p = request.args.get('max_price')

    # 3. Apply Search Filter
    if q:
        query = query.filter(Product.name.contains(q))
    
    # Apply Price Filters with robust validation
    try:
        if min_p and min_p.strip():
            query = query.filter(Product.price >= float(min_p))
        if max_p and max_p.strip():
            query = query.filter(Product.price <= float(max_p))
    except ValueError:
        # Ignore invalid price inputs without crashing
        pass

    # 4. Execute the query
    products = query.all()

    # 5. Calculate statistics for each product
    for p in products:
        # Calculate Ratings
        if p.reviews:
            # We use float() and round() to ensure the template gets a clean number
            p.avg_rating = round(sum(r.rating for r in p.reviews) / len(p.reviews), 1)
            p.review_count = len(p.reviews)
        else:
            p.avg_rating = 0
            p.review_count = 0
            
        # Calculate sold count (Only count COMPLETED or DONE orders)
        # Note: In your admin_orders route you use 'DONE', 
        # but in home you use 'COMPLETED'. Ensure these match your database.
        p.sold_count = sum(o.quantity for o in p.orders if o.status in ['COMPLETED', 'DONE'])
        
    return render_template('home.html', products=products)

@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    product_reviews = Review.query.filter_by(product_id=product_id).all()
    
    # ADD THIS LOGIC TO CALCULATE STATS FOR THE SINGLE PRODUCT
    if product_reviews:
        product.avg_rating = round(sum(r.rating for r in product_reviews) / len(product_reviews), 1)
        product.review_count = len(product_reviews)
    else:
        product.avg_rating = 0
        product.review_count = 0

    # Calculate sold count for this specific product
    product.sold_count = sum(o.quantity for o in product.orders if o.status in ['COMPLETED', 'DONE'])
    
    return render_template('product_details.html', 
                           product=product, 
                           product_id=product_id, 
                           product_reviews=product_reviews)
    
@app.route('/submit_quick_order', methods=['POST'])
def submit_quick_order():
    # Get user data if logged in
    user_data = User.query.filter_by(username=session.get('user')).first() if 'user' in session else None
    
    method = request.form.get('payment_method')
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    quantity = request.form.get('quantity')
    # Use the specific form names from your product_details.html
    selected_color = request.form.get('color_type') 
    selected_size = request.form.get('size_type')

    # Data to be saved - Ensure keys match your CustomOrder model fields
    order_info = {
        'customer_name': user_data.full_name if (user_data and user_data.full_name != "NOT SET") else (user_data.username if user_data else "Guest"),
        'contact_number': user_data.contact if user_data else "N/A",
        'address': user_data.address if user_data else "N/A",
        'quantity': quantity,
        'product_type': f"{product_name}", # Mapping to product_type field
        'color_type': selected_color if selected_color else "Default",
        'size_type': selected_size if selected_size else "Standard",
        'payment_method': method,
        'order_type': "Quick Order" # Label for source identification
    }

    # --- WITHIN submit_quick_order ---
    if method == 'Cash on Delivery':
        # Handle COD immediately
        new_order = CustomOrder(
            user_id=user_data.id if user_data else None,
            product_id=product_id,
            customer_name=order_info['customer_name'],
            contact_number=order_info['contact_number'],
            address=order_info['address'],
            quantity=order_info['quantity'],
            product_type=order_info['product_type'],
            color_type=order_info['color_type'], 
            size_type=order_info['size_type'],
            payment_method=method,
            order_type="Quick Order", # Tagging as Quick Order
            status="PENDING"
        )
        db.session.add(new_order)
        db.session.commit()
        return jsonify({"status": "success", "type": "direct"})

    # FOR GCASH/MAYA: Save to the specific "Quick Order" session key
    order_info['product_id'] = product_id 
    session['temp_quick_order'] = order_info
    session.modified = True 
    
    return jsonify({
        "status": "success", 
        "type": "redirect", 
        "method": method
    })

# --- ADD THESE NEW ROUTES TO app.py ---

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    product_name = request.form.get('product_name')
    quantity = int(request.form.get('quantity', 1))
    
    # FIX: Get price from the form, or look it up from the DB if missing
    price_val = request.form.get('price')
    if not price_val:
        product = Product.query.get(product_id)
        price = product.price if product else 0.0
    else:
        price = float(price_val)

    selected_color = request.form.get('color_type', "Default")
    selected_size = request.form.get('size_type', "Standard")

    if 'cart' not in session:
        session['cart'] = []

    cart_item = {
        'product_id': product_id,
        'name': product_name,
        'quantity': quantity,
        'price': price,
        'color': selected_color,
        'size': selected_size,
        'total': price * quantity
    }
    
    session['cart'].append(cart_item)
    session.modified = True
    return jsonify({"status": "success", "message": f"{product_name} added to cart!"})

@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('home'))

@app.route('/checkout_all', methods=['POST'])
def checkout_all():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Please login first"})

    user_data = User.query.filter_by(username=session.get('user')).first()
    cart = session.get('cart', [])
    # Get method from the fetch body
    method = request.form.get('payment_method')

    if not cart:
        return jsonify({"status": "error", "message": "Your cart is empty."})

    if method == 'Cash on Delivery':
        try:
            for item in cart:
                new_order = CustomOrder(
                    user_id=user_data.id,
                    product_id=item.get('product_id'),
                    customer_name=user_data.full_name,
                    contact_number=user_data.contact,
                    address=user_data.address,
                    quantity=item.get('quantity'),
                    product_type=item.get('name'),
                    color_type=item.get('color'),
                    size_type=item.get('size'),
                    payment_method=method,
                    status="PENDING"
                )
                db.session.add(new_order)
            
            db.session.commit()
            session.pop('cart', None) # Clear cart after success
            return jsonify({"status": "success", "type": "direct", "message": "Orders placed via COD!"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})
    
    else:
        # Digital Payment: Store cart temporarily for the gateway to process later
        session['temp_cart_checkout'] = {'items': cart}
        # Provide the redirect URL the frontend is looking for
        return jsonify({
            "status": "success", 
            "type": "redirect", 
            "redirect_url": url_for('product_payment_gateway', method=method)
        })

@app.route('/submit_custom_order', methods=['POST'])
def submit_custom_order():
    # Save the design image if provided
    file = request.files.get('design_image')
    filename = file.filename if file else None
    
    if file: 
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # Retrieve current user info
    user_data = User.query.filter_by(username=session.get('user')).first()
    
    # Create and save the order directly to the database
    new_order = CustomOrder(
        user_id=user_data.id if user_data else None,
        customer_name=request.form.get('customer_name'),
        contact_number=request.form.get('contact_number'),
        address=request.form.get('address'),
        quantity=request.form.get('quantity'),
        product_type=request.form.get('product_type'),
        color_type=request.form.get('color'),
        material_type=request.form.get('material_type'),
        interlining_thickness=request.form.get('interlining_thickness'),
        size_type=request.form.get('size'),
        remarks=request.form.get('remarks'),
        payment_method="Direct Submission", 
        design_filename=filename,
        order_type="Custom Order", # Tagging as Custom Order
        status="PENDING"
    )
    
    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Order successfully submitted!"})

@app.route('/payment_gateway', methods=['GET', 'POST'])
def payment_gateway():
    # Get details from the URL (for GET) or the Form (for POST)
    order_id = request.args.get('order_id') or request.form.get('order_id')
    method = request.args.get('method') or request.form.get('payment_method')
    
    if request.method == 'POST':
        # Aligning input name: request.files.get('payment_proof') 
        # (Ensure your HTML input name matches this)
        file = request.files.get('payment_proof')
        
        if not order_id:
            return jsonify({"status": "error", "message": "Order ID is missing."})

        if file and file.filename != '':
            try:
                # 1. Save the payment proof using your new naming convention
                filename = secure_filename(file.filename)
                # Matches the format: proof_202405201230_filename.jpg
                proof_filename = f"proof_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], proof_filename))
                
                # 2. Update the EXISTING CustomOrder in the database
                order = CustomOrder.query.get(order_id)
                if order:
                    order.payment_method = method 
                    order.payment_proof = proof_filename 
                    # Optionally update status if needed
                    # order.status = "PENDING" 
                    
                    db.session.commit()
                    return jsonify({"status": "success", "message": "Payment details updated successfully!"})
                else:
                    return jsonify({"status": "error", "message": "Order not found in database."})
            
            except Exception as e:
                db.session.rollback()
                return jsonify({"status": "error", "message": str(e)})
        
        return jsonify({"status": "error", "message": "Please upload a screenshot."})

    # For GET request: render the page with current info
    return render_template('payment_gateway.html', order_id=order_id, method=method)
   
@app.route('/product_payment_gateway', methods=['GET', 'POST'])
def product_payment_gateway():
    method = request.args.get('method')
    
    if request.method == 'POST':
        file = request.files.get('payment_screenshot')
        
        # Check both possible session keys
        cart_data = session.get('temp_cart_checkout')
        quick_order_data = session.get('temp_quick_order') 

        if not cart_data and not quick_order_data:
            return jsonify({"status": "error", "message": "Session expired. Please re-order."})

        if not file:
            return jsonify({"status": "error", "message": "Please upload a receipt."})

        try:
            # 1. Save the payment proof
            filename = secure_filename(file.filename)
            proof_filename = f"proof_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], proof_filename))
            
            user_data = User.query.filter_by(username=session.get('user')).first()
            user_id = user_data.id if user_data else None

            # 2. Process Cart Checkout (Multiple Items)
            if cart_data:
                for item in cart_data['items']:
                    new_order = CustomOrder(
                        user_id=user_id,
                        product_id=item.get('product_id'),
                        customer_name=user_data.full_name,
                        contact_number=user_data.contact,
                        address=user_data.address,
                        quantity=item.get('quantity'),
                        product_type=item.get('name'),
                        color_type=item.get('color'),
                        size_type=item.get('size'),
                        payment_method=method,
                        payment_proof=proof_filename,
                        status="PENDING"
                    )
                    db.session.add(new_order)
                
                db.session.commit()
                session.pop('temp_cart_checkout', None)
                session.pop('cart', None) # Clear the actual cart
                return jsonify({"status": "success", "message": "All cart items submitted!"})

            # 3. Process Quick Order (Single Item)
            elif quick_order_data:
                new_order = CustomOrder(
                    user_id=user_id,
                    product_id=quick_order_data.get('product_id'), 
                    customer_name=quick_order_data.get('customer_name'),
                    contact_number=quick_order_data.get('contact_number'),
                    address=quick_order_data.get('address'),
                    quantity=quick_order_data.get('quantity'),
                    product_type=quick_order_data.get('product_type'), 
                    color_type=quick_order_data.get('color_type'), 
                    size_type=quick_order_data.get('size_type'),
                    payment_method=quick_order_data.get('payment_method'),
                    payment_proof=proof_filename,
                    status="PENDING"
                )
                db.session.add(new_order)
                db.session.commit()
                session.pop('temp_quick_order', None)
                return jsonify({"status": "success", "message": "Order submitted successfully!"})

        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": str(e)})

    return render_template('product_payment_gateway.html', method=method)
    
@app.route('/customer_profile', methods=['GET', 'POST'])
def customer_profile():
    if 'user' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['user']).first()

    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.contact = request.form.get('contact')
        user.address = request.form.get('address')

        # Handle File Upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '':
                # 1. Secure the filename
                filename = secure_filename(f"user_{user.id}_{file.filename}")
                
                # 2. Define the path (Use the folder specifically for profile pics)
                profile_pics_path = os.path.join(basedir, 'static', 'profile_pics')
                
                # 3. Ensure the folder exists
                if not os.path.exists(profile_pics_path):
                    os.makedirs(profile_pics_path)
                
                # 4. Save the file
                file.save(os.path.join(profile_pics_path, filename))
                
                # 5. Update the database column
                user.profile_pic = filename 

        db.session.commit()
        flash("Profile updated successfully!")
        return redirect(url_for('customer_profile'))

    user_orders = CustomOrder.query.filter_by(user_id=user.id).order_by(CustomOrder.id.desc()).all()
    user_reviews = Review.query.filter_by(user_id=user.id).all()
    return render_template('customer_profile.html', user=user, user_orders=user_orders, reviews=user_reviews)

@app.route('/custom_order')
def custom_order():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    user = User.query.filter_by(username=session['user']).first()
    
    # Fetch only orders tagged as "Custom Order" for this specific user
    custom_orders = CustomOrder.query.filter_by(
        user_id=user.id, 
        order_type="Custom Order"
    ).order_by(CustomOrder.id.desc()).all()
    
    prev_data = session.get('temp_order', {})
    
    messages = ContactMessage.query.filter_by(user_id=user.id).order_by(ContactMessage.date_sent.desc()).all()
    
    return render_template('custom_order.html', 
                           messages=messages, 
                           prev_data=prev_data, 
                           custom_orders=custom_orders)
    
@app.route('/update_payment_method/<int:order_id>', methods=['POST'])
def update_payment_method(order_id):
    try:
        data = request.get_json()
        new_method = data.get('payment_method')

        # Use SQLAlchemy to find the order
        order = CustomOrder.query.get(order_id)
        
        if order:
            order.payment_method = new_method
            db.session.commit() # Save to overseas_cap.db
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Order not found"}), 404
            
    except Exception as e:
        db.session.rollback() # Undo changes if there's an error
        print(f"Error updating payment: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/update_order/<int:order_id>', methods=['POST'])
def update_order(order_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    order = CustomOrder.query.get_or_404(order_id)
    
    user = User.query.filter_by(username=session['user']).first()
    if not user or order.user_id != user.id:
        return jsonify({"status": "error", "message": "Permission denied"}), 403

    try:
        # Updating all fields based on the new form data
        order.customer_name = data.get('name')
        order.contact_number = data.get('contact')
        order.address = data.get('address')
        order.quantity = data.get('qty')
        order.size_type = data.get('size')
        order.product_type = data.get('type')
        order.color_type = data.get('color')
        order.material_type = data.get('material')
        order.interlining_thickness = data.get('thickness')
        order.remarks = data.get('remarks')
        
        db.session.commit()
        return jsonify({"status": "success", "message": "Order updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))

    # 1. Orders Stats
    total_orders = CustomOrder.query.count()
    pending_orders = CustomOrder.query.filter_by(status='PENDING').count()
    completed_orders = CustomOrder.query.filter(CustomOrder.status.in_(['DONE', 'COMPLETED', 'Done', 'Completed'])).count()

    # 2. Materials/Inventory Stats
    total_materials = Inventory.query.count()
    overall_stock_qty = db.session.query(db.func.sum(Inventory.qty)).scalar() or 0
    low_stock_count = Inventory.query.filter(Inventory.qty < 20).count()

    # 3. Message Count (Replacing Custom Requests)
    # This counts all messages sent by customers from the contact form
    total_messages = ContactMessage.query.count()

    # 4. Products Displayed
    total_products = Product.query.count()

    # 5. Other Overview Metrics
    total_customers = User.query.count()
    total_reviews = Review.query.count()

    stats = {
        'total': total_orders,
        'pending': pending_orders,
        'completed': completed_orders,
        'total_materials': total_materials,
        'overall_stock': overall_stock_qty,
        'low_stock': low_stock_count,
        'total_messages': total_messages, # New key for the messages
        'total_customers': total_customers,
        'total_reviews': total_reviews,
        'total_products': total_products 
    }

    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    # Sidebar stats
    stats = {
        'total': CustomOrder.query.count(),
        'pending': CustomOrder.query.filter_by(status='PENDING').count(),
        'completed': CustomOrder.query.filter_by(status='COMPLETED').count()
    }
    colors_input = request.form.get('colors', '')
    if colors_input:
            color_list = [c.strip() for c in colors_input.split(',') if c.strip()]
            for color in color_list:
                # Generate the key used in the HTML
                safe_color = color.replace(' ', '_')
                
                # Get the specific price for this color
                variant_price = request.form.get(f'color_price_{safe_color}')
                variant_image = request.files.get(f'color_image_{safe_color}')

    if request.method == 'POST':
        # ADD NEW PRODUCT LOGIC
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        file = request.files.get('image_file')
        sizes_input = request.form.get('sizes', '') 
        colors_input = request.form.get('colors', '')

        if file and name and price:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            new_product = Product(
                name=name, 
                price=float(price), 
                description=description, 
                image_file=filename
            )
            db.session.add(new_product)
            db.session.flush()
            
            # Add Size Variants
            if sizes_input:
                for s in [x.strip() for x in sizes_input.split(',') if x.strip()]:
                    new_size = ProductSize(product_id=new_product.id, size_value=s)
                    db.session.add(new_size)
            
            # Add Color Variants
            if colors_input:
                for c in [x.strip() for x in colors_input.split(',') if x.strip()]:
                    # Admin UI usually provides a specific image/price per color
                    safe_c = c.replace(' ', '_')
                    c_price = request.form.get(f'color_price_{safe_c}') or price
                    c_file = request.files.get(f'color_image_{safe_c}')
                    
                    c_filename = filename # Default to main image
                    if c_file:
                        c_filename = secure_filename(c_file.filename)
                        c_file.save(os.path.join(app.config['UPLOAD_FOLDER'], c_filename))
                    
                    new_color = ProductColorImage(
                        product_id=new_product.id,
                        color_name=c,
                        price=float(c_price),
                        image_file=c_filename
                    )
                    db.session.add(new_color)

            db.session.commit()
            flash('Product added successfully!')
            return redirect(url_for('admin_products'))

    products = Product.query.all() # This pulls all products for the table
    return render_template('admin_products.html', products=products, stats=stats)

@app.route('/admin/delete_product/<int:id>')
def delete_product(id):
    product = Product.query.get_or_404(id)
    
    # Also delete reviews linked to this product so it doesn't crash later
    Review.query.filter_by(product_id=id).delete()
    
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('admin_products'))

@app.route('/admin/update_product/<int:id>', methods=['POST'])
def update_product(id):
    product = Product.query.get_or_404(id)
    product.name = request.form.get('name')
    product.price = float(request.form.get('price', 0))
    product.description = request.form.get('description')
    
    # 1. Update Main Image
    file = request.files.get('image_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        product.image_file = filename

    # 2. Update SIZES
    new_sizes = [s.strip() for s in request.form.get('sizes', '').split(',') if s.strip()]
    ProductSize.query.filter_by(product_id=id).delete()
    for s_val in new_sizes:
        db.session.add(ProductSize(size_value=s_val, product_id=id))

    # 3. Update COLORS (The "Keep Image" logic)
    new_colors_str = request.form.get('colors', '')
    new_colors = [c.strip() for c in new_colors_str.split(',') if c.strip()]
    
    # Corrected dictionary name to match the logic below
    existing_variants = {v.color_name: v.image_file for v in ProductColorImage.query.filter_by(product_id=id).all()}
    
    ProductColorImage.query.filter_by(product_id=id).delete()
    
    for c_name in new_colors:
        # Replace spaces with underscores to match potential HTML input names
        safe_name = c_name.replace(' ', '_')
        c_file = request.files.get(f'color_image_{safe_name}')
        
        # Priority Logic: New Upload > Existing Image > Main Product Image
        if c_file and c_file.filename != '':
            c_filename = secure_filename(c_file.filename)
            c_file.save(os.path.join(app.config['UPLOAD_FOLDER'], c_filename))
        elif c_name in existing_variants:
            c_filename = existing_variants[c_name]
        else:
            c_filename = product.image_file

        c_price = request.form.get(f'color_price_{safe_name}')
        # Use color-specific price if provided, otherwise use the main product price
        final_price = float(c_price) if (c_price and c_price.strip()) else product.price

        db.session.add(ProductColorImage(
            color_name=c_name, 
            price=final_price, 
            image_file=c_filename, 
            product_id=id
        ))

    # 4. Final Save
    db.session.commit()
    flash('Product and variants updated successfully!')
    return redirect(url_for('admin_products'))

@app.route('/admin_orders')
def admin_orders():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
        
    # 1. Fetch Inventory Data
    total_materials = Inventory.query.count()
    overall_stock_qty = db.session.query(db.func.sum(Inventory.qty)).scalar() or 0
    low_stock_count = Inventory.query.filter(Inventory.qty < 20).count()

    # Fetch all orders ordered by ID ascending
    db_orders = CustomOrder.query.order_by(CustomOrder.id.asc()).all()
    
    # Calculate Revenue: Join with Product model for completed orders
    completed_orders = CustomOrder.query.filter_by(status="DONE").all()
    total_revenue = 0
    
    for order in completed_orders:
        if order.product: 
            # For quick orders linked to a registered Product
            total_revenue += (order.product.price * order.quantity)
        else:
            # For custom orders, use the 'price' set by the admin in order_view
            # We use a fallback of 0 if for some reason the admin hasn't set a price yet
            order_price = order.price if (order.price and order.price != 'Not set') else 0
            total_revenue += (float(order_price))

    # 2. Add Inventory metrics to the stats dictionary
    dashboard_stats = {
        'total': len(db_orders),
        'pending': CustomOrder.query.filter_by(status="PENDING").count(),
        'completed': len(completed_orders),
        'revenue': total_revenue,
        'total_materials': total_materials,
        'overall_stock': overall_stock_qty,
        'low_stock': low_stock_count
    }
    
    orders_list = []
    now = datetime.now()

    for o in db_orders:
        # Calculate days left (7-day fulfillment window)
        days_diff = 0
        if o.date_ordered:
            deadline_date = o.date_ordered + timedelta(days=7)
            days_diff = (deadline_date - now).days

        orders_list.append({
            "raw_id": o.id,
            "id": f"CUST-{o.id}",
            "name": o.customer_name,
            "product": o.product_type,
            "color": o.color_type,
            "size": o.size_type,   
            "qty": o.quantity,
            "date": o.date_ordered.strftime("%x") if o.date_ordered else "N/A",
            "deadline": (o.date_ordered + timedelta(days=7)).strftime("%x") if o.date_ordered else "TBD",
            "days_left": days_diff,
            "delivery": "TBD" if o.status == "PENDING" else "In Transit",
            "status": o.status,
            "payment_method": o.payment_method,
            "has_proof": True if o.payment_proof else False,
            "color_code": "#FFD700" if o.status == "PENDING" else "#FF8C00" if o.status == "ON DELIVERY" else "#00FF00"
        })

    return render_template('admin_orders.html', orders=orders_list, stats=dashboard_stats)

# NEW: Route to view specific order details
@app.route('/admin/order/<int:order_id>')
def view_order_detail(order_id):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    order = CustomOrder.query.get_or_404(order_id)
    return render_template('order_view.html', order=order)

# NEW: Route to update status
@app.route('/admin/order/update/<int:order_id>/<new_status>')
def update_order_status(order_id, new_status):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    order = CustomOrder.query.get_or_404(order_id)
    
    # 1. Capture price from query string (?price=...)
    price_input = request.args.get('price')
    
    # 2. Update status (forced to upper to match ACCEPTED)
    order.status = new_status.upper() 
    
    # 3. Save price to database if present
    if price_input:
        try:
            order.price = float(price_input)
        except (ValueError, TypeError):
            pass 

    db.session.commit()
    flash(f"Order #{order_id} updated successfully.")
    
    # After saving, we go back to the list of orders
    return redirect(url_for('admin_orders'))

@app.route('/admin/sales_report')
def sales_report():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    filter_type = request.args.get('filter', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = CustomOrder.query.filter(CustomOrder.status.in_(['DONE', 'COMPLETED']))
    now = datetime.now()
    
    # --- DATE RANGE & FILTER LOGIC ---
    if start_date and end_date:
        # Filter between two dates inclusive
        query = query.filter(db.func.date(CustomOrder.date_ordered) >= start_date)
        query = query.filter(db.func.date(CustomOrder.date_ordered) <= end_date)
        filter_type = 'custom'
    elif filter_type == 'day':
        query = query.filter(db.func.date(CustomOrder.date_ordered) == now.date())
    elif filter_type == 'week':
        one_week_ago = now - timedelta(days=7)
        query = query.filter(CustomOrder.date_ordered >= one_week_ago)
    elif filter_type == 'month':
        query = query.filter(db.func.strftime('%Y-%m', CustomOrder.date_ordered) == now.strftime('%Y-%m'))

    completed_orders = query.all()
    
    sales_data = []
    total_revenue = 0
    
    for order in completed_orders:
        if order.product: 
            # For quick orders linked to a registered Product
            unit_price = order.product.price
            order_total = unit_price * order.quantity
        else:
            # For custom orders, use the 'price' set by the admin in order_view
            raw_price = order.price if (order.price and order.price != 'Not set') else 0
            # Custom orders usually have a total price set; we derive unit_price for the table
            order_total = float(raw_price)
            unit_price = order_total / order.quantity if order.quantity > 0 else order_total

        total_revenue += order_total
        
        sales_data.append({
            'id': order.id,
            'date': order.date_ordered.strftime('%Y-%m-%d %H:%M') if order.date_ordered else "N/A",
            'customer': order.customer_name,
            'product': order.product_type,
            'quantity': order.quantity,
            'unit_price': unit_price,
            'total': order_total
        })
    
    return render_template('sales_report.html', 
                           sales=sales_data, 
                           total_revenue=total_revenue, 
                           current_filter=filter_type,
                           start_date=start_date,
                           end_date=end_date)

@app.route('/admin/export_orders_csv')
def export_orders_csv():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    orders = CustomOrder.query.all()
    si = StringIO()
    cw = csv.writer(si)
    
    # Updated Header to include Color and Size
    cw.writerow(['Order ID', 'Client Name', 'Product', 'Color', 'Size', 'Quantity', 'Date', 'Status', 'Payment'])
    
    for o in orders:
        cw.writerow([
            f"CUST-{o.id}", 
            o.customer_name, 
            o.product_type, 
            o.color_type,
            o.size_type,
            o.quantity, 
            o.date_ordered.strftime("%Y-%m-%d") if o.date_ordered else "N/A",
            o.status,
            o.payment_method
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=orders_report.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/print_orders')
def print_orders():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    all_orders = CustomOrder.query.all()
    stats = {
        "generated_at": datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        "total": len(all_orders),
        "pending": CustomOrder.query.filter_by(status="PENDING").count()
    }
    # You will need to create a simple print_orders.html template
    return render_template('print_orders.html', orders=all_orders, stats=stats)

# In app.py
@app.route('/admin/order/delete/<int:order_id>')
def delete_order(order_id):  # This name MUST be delete_order
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    order_to_delete = CustomOrder.query.get_or_404(order_id)
    try:
        db.session.delete(order_to_delete)
        db.session.commit()
        flash(f"Order #{order_id} deleted.")
    except:
        db.session.rollback()
    return redirect(url_for('admin_orders'))

@app.route('/admin/orders/bulk-delete', methods=['POST'])
def bulk_delete_orders():
    # Security check to ensure only the admin can do this
    if session.get('user') != 'admin':
        return jsonify({"status": "unauthorized"}), 403
    
    data = request.get_json()
    order_ids = data.get('ids', [])
    
    try:
        # Use the CustomOrder model defined earlier in this file
        CustomOrder.query.filter(CustomOrder.id.in_(order_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}") # This helps you see what went wrong in the terminal
        return jsonify({"status": "error"}), 500

@app.route('/admin_inventory', methods=['GET', 'POST'])
def admin_inventory():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))

    # Logic to handle adding new materials from the sidebar
    if request.method == 'POST' and 'add_material' in request.form:
        new_item = Inventory(
            material=request.form.get('material'),
            supplier=request.form.get('supplier'),
            qty=request.form.get('qty'),
            price=request.form.get('price'),
            status="In Stock"
        )
        db.session.add(new_item)
        db.session.commit()
        flash("New material added!")
        return redirect(url_for('admin_inventory'))

    # Query the database instead of using a hardcoded list
    inventory_items = Inventory.query.all()
    return render_template('admin_inventory.html', inventory=inventory_items)

@app.route('/admin/print_low_stock')
def print_low_stock():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # Filter for items with quantity below 20
    low_stock_items = Inventory.query.filter(Inventory.qty < 20).all()
    
    # Calculate valuation for this specific list
    total_val = sum(item.qty * item.price for item in low_stock_items)
    
    stats = {
        "title": "Low Stock Inventory Report",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_items": len(low_stock_items), # Changed from 'count' to match template
        "total_value": total_val             # Added to prevent 'Undefined' error
    }
    return render_template('print_inventory.html', inventory=low_stock_items, stats=stats)

@app.route('/admin/print_sufficient_stock')
def print_sufficient_stock():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # Filter for items with 20 or more
    sufficient_items = Inventory.query.filter(Inventory.qty >= 20).all()
    
    # Calculate valuation for this specific list
    total_val = sum(item.qty * item.price for item in sufficient_items)
    
    stats = {
        "title": "Sufficient Stock Report",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_items": len(sufficient_items), # Changed from 'count' to match template
        "total_value": total_val              # Added to prevent 'Undefined' error
    }
    return render_template('print_inventory.html', inventory=sufficient_items, stats=stats)

@app.route('/admin/print_overall_stock')
def print_overall_stock():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    all_items = Inventory.query.all()
    
    # Calculate total valuation
    total_val = sum(item.qty * item.price for item in all_items)
    
    stats = {
        "title": "Master Inventory Valuation",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_items": len(all_items),
        "total_value": total_val
    }
    return render_template('print_inventory.html', inventory=all_items, stats=stats)

@app.route('/admin/inventory/delete/<int:item_id>')
def delete_material(item_id):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # Locate the material in the database
    item = Inventory.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    
    flash(f"Material '{item.material}' removed.")
    return redirect(url_for('admin_inventory'))

@app.route('/admin/inventory/update_stock', methods=['POST'])
def update_stock():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    mat_id = request.form.get('id')
    new_qty = request.form.get('qty')
    
    item = Inventory.query.get(mat_id)
    if item:
        item.qty = new_qty
        db.session.commit()
        flash(f"Updated {item.material} stock successfully.")
    
    return redirect(url_for('admin_inventory'))

@app.route('/admin/suppliers', methods=['GET', 'POST'])
def admin_suppliers():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))

    # Handle Adding New Supplier
    if request.method == 'POST' and 'add_supplier' in request.form:
        new_sup = Supplier(
            name=request.form.get('name'),
            address=request.form.get('address'),
            contact=request.form.get('contact'),
            supply=request.form.get('supply'),
            price_range=request.form.get('price_range')
        )
        db.session.add(new_sup)
        db.session.commit()
        flash("New supplier added successfully!")
        return redirect(url_for('admin_suppliers'))

    suppliers_list = Supplier.query.all()
    return render_template('admin_suppliers.html', suppliers=suppliers_list)

@app.route('/admin/suppliers/delete/<int:sup_id>')
def delete_supplier(sup_id):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    sup = Supplier.query.get_or_404(sup_id)
    db.session.delete(sup)
    db.session.commit()
    flash(f"Supplier '{sup.name}' removed.")
    return redirect(url_for('admin_suppliers'))

@app.route('/admin/print_suppliers')
def print_suppliers():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # Replace 'Supplier' with your actual Model name if different
    # Assuming you have a Supplier model based on your HTML form
    all_suppliers = Supplier.query.all() 
    
    report_data = {
        "generated_at": datetime.now().strftime("%B %d, %Y - %I:%M %p"),
        "count": len(all_suppliers)
    }

    return render_template('print_suppliers.html', suppliers=all_suppliers, stats=report_data)

@app.route('/admin/export_reviews_csv')
def export_reviews_csv():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    reviews = Review.query.all()
    
    # Create a string buffer to write CSV data
    si = StringIO()
    cw = csv.writer(si)
    
    # Write Header
    cw.writerow(['Review ID', 'User', 'Product', 'Rating', 'Comment', 'Admin Reply', 'Date Posted'])
    
    # Write Data
    for r in reviews:
        cw.writerow([
            r.id, 
            r.user.username, 
            r.product_type, 
            r.rating, 
            r.comment, 
            r.admin_reply or 'No reply', 
            r.date_posted.strftime('%m/%d/%Y') if r.date_posted else 'N/A'
        ])
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=customer_reviews.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/reviews')
def admin_reviews():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # Get rating filter from URL (e.g., ?rating=5)
    rating_filter = request.args.get('rating', type=int)
    
    if rating_filter:
        reviews = Review.query.filter_by(rating=rating_filter).order_by(Review.date_posted.desc()).all()
    else:
        reviews = Review.query.order_by(Review.date_posted.desc()).all()
        
    return render_template('admin_reviews.html', reviews=reviews, current_filter=rating_filter)

@app.route('/admin/review/delete/<int:review_id>')
def delete_review(review_id):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Review deleted successfully.')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/reviews/clear-all')
def admin_clear_reviews():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    Review.query.delete()
    db.session.commit()
    flash('All reviews have been cleared.')
    return redirect(url_for('admin_reviews'))

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user' not in session:
        return redirect(url_for('login'))
        
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    order_id = request.form.get('order_id')
    
    order = CustomOrder.query.get(order_id)
    user = User.query.filter_by(username=session['user']).first()
    
    if not order:
        flash("Order not found.")
        return redirect(url_for('customer_profile'))

    # --- UPDATE ORDER STATUS HERE ---
    # You can change 'COMPLETED' to whatever status name you prefer
    order.status = 'COMPLETED' 
    
    # Handle Review Image Upload
    review_image_filename = None
    if 'review_image' in request.files:
        file = request.files['review_image']
        if file and file.filename != '':
            filename = secure_filename(f"rev_{order_id}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            review_image_filename = filename

    new_review = Review(
        rating=rating,
        comment=comment,
        order_id=order_id,
        user_id=user.id,
        product_id=order.product_id,
        product_color=order.color_type,  
        product_size=order.size_type,
        product_type=order.product_type,
        review_image=review_image_filename
    )
    
    db.session.add(new_review)
    # db.session.commit() will save both the new review AND the updated order status
    db.session.commit() 
    
    flash("Thank you for your review! Order marked as completed.")
    return redirect(url_for('customer_profile'))

@app.route('/order_status/<int:order_id>')
def order_status(order_id):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    order = CustomOrder.query.get_or_404(order_id)
    # Get the review so the "FEEDBACK SUBMITTED" section works
    order = CustomOrder.query.get_or_404(order_id)
    review = Review.query.filter_by(order_id=order_id).first()
    
    
    return render_template('order_status.html', order=order, review=review)

# Route for admin to reply
@app.route('/reply_review/<int:review_id>', methods=['POST'])
def reply_review(review_id):
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
        
    review = Review.query.get_or_404(review_id)
    reply_content = request.form.get('reply_text')
    
    print(f"DEBUG: Found Review ID {review_id}") # Check terminal
    print(f"DEBUG: Reply Content is: {reply_content}") # Check terminal
    
    if reply_content:
        review.admin_reply = reply_content
        db.session.commit()
        print("DEBUG: Database Commit Successful")
        flash("Reply sent to customer!")
        
    return redirect(url_for('admin_reviews'))

@app.route('/admin_customers')
def admin_customers():
    if session.get('user') != 'admin':
        return redirect(url_for('login'))
    
    # 1. Fetch all registered users
    users = User.query.all()
    
    # 2. Fetch all contact messages
    all_messages = ContactMessage.query.order_by(ContactMessage.date_sent.desc()).all()
    
    # 3. Prepare the 'stats' dictionary for the sidebar
    dashboard_stats = {
        'total_users': User.query.count(),
        'unread_msgs': ContactMessage.query.filter_by(is_read=False).count(),
        'bulk_clients': db.session.query(CustomOrder.user_id).filter(CustomOrder.order_type == 'Bulk Order').distinct().count()
    }
    
    # 4. Pass everything to the template
    return render_template('admin_customers.html', 
                           users=users, 
                           messages=all_messages, 
                           stats=dashboard_stats)

@app.route('/submit_admin_message', methods=['POST'])
def submit_admin_message():
    # 1. Check session safely
    username = session.get('user')
    if not username:
        return jsonify({"status": "error", "message": "Session expired. Please login again."}), 401
        
    data = request.get_json()
    if not data or not data.get('message'):
        return jsonify({"status": "error", "message": "Message content is missing."}), 400

    user_data = User.query.filter_by(username=username).first()
    if not user_data:
        return jsonify({"status": "error", "message": "User not found."}), 404
    
    try:
        new_msg = ContactMessage(
            user_id=user_data.id,
            sender_name=user_data.full_name if user_data.full_name != "NOT SET" else user_data.username,
            message=data.get('message')
        )
        db.session.add(new_msg)
        db.session.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/update_message/<int:message_id>', methods=['POST'])
def update_message(message_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    data = request.get_json()
    new_text = data.get('message')
    
    # Find the message and update it
    msg = ContactMessage.query.get_or_404(message_id)
    msg.message = new_text
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/delete_message/<int:message_id>', methods=['POST'])
def delete_message(message_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    msg = ContactMessage.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/admin/reply_customer_msg/<int:msg_id>', methods=['POST'])
def reply_customer_msg(msg_id):
    if session.get('user') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    msg = ContactMessage.query.get_or_404(msg_id)
    
    if data.get('reply'):
        msg.admin_reply = data.get('reply')
        msg.is_read = True # Mark as seen by admin
        db.session.commit()
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Reply cannot be empty"})

@app.route('/admin/get_customer_details/<int:user_id>')
def get_customer_details(user_id):
    if session.get('user') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Query the actual orders for this specific user
    # We use .all() to get every order they've made
    user_orders = CustomOrder.query.filter_by(user_id=user_id).all()
    
    # Format the orders into a list of dictionaries for JSON
    order_list = []
    for o in user_orders:
        order_list.append({
            "id": o.id,
            "product_type": o.product_type,
            "quantity": o.quantity,
            "status": o.status
        })

    return jsonify({
        "full_name": user.full_name,
        "email": user.email,
        "contact": user.contact,
        "address": user.address or "No address provided",
        "orders": order_list
    })

@app.route('/admin/get_convo_history/<int:user_id>')
def get_convo_history(user_id):
    if session.get('user') != 'admin':
        return jsonify({"status": "error"}), 403
    
    # 1. Mark all messages from this user as read
    messages = ContactMessage.query.filter_by(user_id=user_id).all()
    for m in messages:
        m.is_read = True
    db.session.commit() # Save the "Read" status
    
    # 2. Prepare history for display
    history = []
    for m in messages:
        history.append({
            "id": m.id,
            "sender": m.sender_name,
            "text": m.message,
            "reply": m.admin_reply
        })
    return jsonify({"history": history})

# --- MISSING ADMIN CUSTOMER MANAGEMENT ROUTES ---

@app.route('/admin/delete_customer/<int:id>')
def delete_customer(id):
    customer = User.query.get_or_404(id)
    
    # 1. Manually delete related reviews first
    Review.query.filter_by(user_id=id).delete()
    
    # 2. Manually delete related messages (if applicable)
    ContactMessage.query.filter_by(user_id=id).delete()
    
    # 3. Finally delete the customer
    db.session.delete(customer)
    db.session.commit()
    
    flash('Customer and all related data deleted.')
    return redirect(url_for('admin_customers'))

@app.route('/admin/edit_reply/<int:msg_id>', methods=['POST'])
def edit_admin_reply(msg_id):
    if session.get('user') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    data = request.get_json()
    msg = ContactMessage.query.get_or_404(msg_id)
    
    if data.get('reply'):
        msg.admin_reply = data.get('reply')
        db.session.commit()
        return jsonify({"status": "success"})
    
    return jsonify({"status": "error", "message": "Reply cannot be empty"})

@app.route('/admin/delete_reply/<int:msg_id>', methods=['POST'])
def delete_admin_reply(msg_id):
    if session.get('user') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
        
    msg = ContactMessage.query.get_or_404(msg_id)
    msg.admin_reply = None  # Remove only the reply, keep the customer's message
    db.session.commit()
    
    return jsonify({"status": "success"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.") # Let the user know it was successful
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True)