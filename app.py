from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit, send
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import secrets
import logging

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("python-dotenv not installed. Install with: pip install python-dotenv")

app = Flask(__name__)

# ============================================================================
# SECURITY CONFIGURATION - UPDATED
# ============================================================================

# Secure secret key configuration
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generate a random key if not set (for development only)
    SECRET_KEY = secrets.token_urlsafe(32)
    print("⚠️  WARNING: Using auto-generated secret key. Set SECRET_KEY environment variable for production!")

app.secret_key = SECRET_KEY

# Enhanced security configuration
app.config.update(
    # File upload security
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5MB max file size
    
    # Session security
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SECURE=os.environ.get('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    
# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///products.db')
# Handle postgres:// vs postgresql:// issue for Render
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
SQLALCHEMY_DATABASE_URI=DATABASE_URL,
SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# File upload configuration - Production ready
if os.environ.get('RENDER') or os.environ.get('FLASK_ENV') == 'production':
    # On Render and other cloud platforms, use /tmp directory
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
    print("📁 Using production upload folder: /tmp/uploads")
else:
    # Local development - use uploads folder in project
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
    print(f"📁 Using development upload folder: {app.config['UPLOAD_FOLDER']}")

# Create the upload directory
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================================================
# SECURITY VALIDATION FUNCTION
# ============================================================================

def validate_security_config():
    """
    Validate that security configuration is properly set
    """
    # Check if we're using default/weak secret key
    if app.config['SECRET_KEY'] == 'chin-ethan-aaron':
        app.logger.error("⚠️  SECURITY WARNING: Default secret key detected!")
        if not app.debug:
            raise RuntimeError("Production deployment with default secret key is not allowed!")
    
    # Ensure secret key is strong enough
    if isinstance(app.config['SECRET_KEY'], str) and len(app.config['SECRET_KEY']) < 16:
        app.logger.warning("⚠️  SECRET_KEY should be at least 16 characters long")
    
    # Check environment configuration
    env = os.environ.get('FLASK_ENV', 'default')
    if env == 'production':
        if not app.config.get('SESSION_COOKIE_SECURE'):
            app.logger.warning("⚠️  HTTPS cookies should be enabled in production")
        
        if app.debug:
            app.logger.warning("⚠️  Debug mode should be disabled in production")
    
    # Log security status
    app.logger.info("🔒 Security Configuration Status:")
    app.logger.info(f"   - Environment: {env}")
    app.logger.info(f"   - Debug Mode: {app.debug}")
    app.logger.info(f"   - Secret Key: {'✓ Set' if app.config['SECRET_KEY'] else '✗ Missing'}")
    app.logger.info(f"   - HTTPS Cookies: {app.config.get('SESSION_COOKIE_SECURE', False)}")
    app.logger.info(f"   - HttpOnly Cookies: {app.config.get('SESSION_COOKIE_HTTPONLY', False)}")
    app.logger.info(f"   - Max Upload Size: {app.config.get('MAX_CONTENT_LENGTH', 0) / (1024*1024):.1f}MB")
    
    # Check upload folder permissions
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        if not os.path.exists(upload_folder):
            app.logger.warning(f"⚠️  Upload folder does not exist: {upload_folder}")
        elif not os.access(upload_folder, os.W_OK):
            app.logger.warning(f"⚠️  Upload folder is not writable: {upload_folder}")
        else:
            app.logger.info(f"   - Upload Folder: ✓ {upload_folder}")

# ============================================================================
# ENHANCED FILE UPLOAD SECURITY
# ============================================================================

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    """Enhanced file validation with security checks"""
    if not filename or '.' not in filename:
        return False
    
    # Get file extension
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Check if extension is allowed
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    # Security: Check for suspicious filenames
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(char in filename for char in dangerous_chars):
        return False
    
    # Check filename length
    if len(filename) > 255:
        return False
    
    return True

def validate_file_upload(file):
    """Validate file upload with size and content checks"""
    if not file or file.filename == '':
        return False, "No file selected"
    
    if not allowed_file(file.filename):
        return False, "Invalid file type. Only PNG, JPG, JPEG, GIF, and WEBP files are allowed."
    
    # Check file size (Flask's MAX_CONTENT_LENGTH handles this automatically)
    # But we can add additional validation here if needed
    
    return True, "File is valid"

# ============================================================================
# INPUT VALIDATION HELPERS
# ============================================================================

def validate_price(price_str):
    """Validate price input"""
    try:
        price = float(price_str)
        if price <= 0:
            return False, "Price must be greater than 0"
        if price > 999999:
            return False, "Price is too high"
        return True, price
    except (ValueError, TypeError):
        return False, "Invalid price format"

def validate_student_id(student_id):
    """Validate student ID format"""
    if not student_id or len(student_id.strip()) < 3:
        return False, "Student ID must be at least 3 characters"
    if len(student_id) > 50:
        return False, "Student ID is too long"
    return True, student_id.strip()

def validate_email(email):
    """Basic email validation"""
    if not email or '@' not in email or '.' not in email:
        return False, "Invalid email format"
    if len(email) > 120:
        return False, "Email is too long"
    return True, email.strip().lower()

def validate_password(password):
    """Validate password strength"""
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long"
    if len(password) > 128:
        return False, "Password is too long"
    return True, password

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Product(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    price          = db.Column(db.Float, nullable=False)
    image          = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    category       = db.Column(db.String(50), nullable=False)
    condition      = db.Column(db.String(50), nullable=False)
    multiple_items = db.Column(db.Boolean, default=False)
    seller_id      = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationship to User (seller)
    seller = db.relationship('User', backref=db.backref('products', lazy=True))

class User(db.Model, UserMixin):
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.String(50), unique=True, nullable=False)
    student_email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name     = db.Column(db.String(100), nullable=True)
    profile_picture = db.Column(db.String(100), nullable=True, default='default-avatar.png')
    messages_sent     = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_profile_picture(self):
        """Return the profile picture filename or default"""
        return self.profile_picture if self.profile_picture else 'default-avatar.png'
    
    def get_display_name(self):
        """Return full name if available, otherwise student ID"""
        return self.full_name if self.full_name else self.student_id

class Message(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    content     = db.Column(db.Text, nullable=False)
    timestamp   = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sender_id   = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    date_added = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('wishlisted_by', lazy=True))
    
    # Ensure a user can't add the same product twice
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)

# ============================================================================
# AUTHENTICATION ROUTES - ENHANCED WITH VALIDATION
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sid = request.form.get('student_id', '').strip()
        pwd = request.form.get('password', '')
        
        # Validate inputs
        if not sid or not pwd:
            flash('Please fill in all fields.', 'error')
            return render_template('login.html')
        
        # Rate limiting could be added here
        user = User.query.filter_by(student_id=sid).first()
        if user and user.check_password(pwd):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid Student ID or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        sid = request.form.get('student_id', '').strip()
        email = request.form.get('email', '').strip()
        pwd = request.form.get('password', '')
        
        # Enhanced validation
        sid_valid, sid_msg = validate_student_id(sid)
        if not sid_valid:
            flash(sid_msg, 'error')
            return render_template('login.html')
        
        email_valid, email_msg = validate_email(email)
        if not email_valid:
            flash(email_msg, 'error')
            return render_template('login.html')
        
        pwd_valid, pwd_msg = validate_password(pwd)
        if not pwd_valid:
            flash(pwd_msg, 'error')
            return render_template('login.html')
        
        # Check if already exists
        if User.query.filter_by(student_id=sid).first():
            flash('Student ID already taken.', 'error')
            return render_template('login.html')
        elif User.query.filter_by(student_email=email).first():
            flash('Email already registered.', 'error')
            return render_template('login.html')
        
        try:
            new_user = User(student_id=sid, student_email=email)
            new_user.set_password(pwd)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Registration error: {str(e)}")
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ============================================================================
# APPLICATION ROUTES - ENHANCED WITH ERROR HANDLING
# ============================================================================
    
@app.route('/')
@login_required
def home():
    try:
        # grab the latest 4 products
        featured_items = Product.query.order_by(Product.id.desc()).limit(4).all()
        return render_template("home.html", featured_items=featured_items)
    except Exception as e:
        app.logger.error(f"Home page error: {str(e)}")
        flash('Error loading homepage. Please try again.', 'error')
        return render_template("home.html", featured_items=[])

@app.route("/products")
@login_required
def products():
    try:
        # grab search **and** category query-params
        search = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()

        # start building the base query
        qry = Product.query

        # filter by category if provided
        if category:
            qry = qry.filter_by(category=category)

        # filter by name search if provided
        if search:
            # Sanitize search input
            search = search[:100]  # Limit search length
            qry = qry.filter(Product.name.ilike(f"%{search}%"))

        # finally, order & execute
        products = qry.order_by(Product.id.desc()).all()

        return render_template(
            "products.html",
            products=products,
            search=search,
            active_category=category
        )
    except Exception as e:
        app.logger.error(f"Products page error: {str(e)}")
        flash('Error loading products. Please try again.', 'error')
        return render_template("products.html", products=[], search="", active_category="")

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        try:
            # Get form data
            name = request.form.get("name", "").strip()
            price_str = request.form.get("price", "")
            category = request.form.get("category", "").strip()
            condition = request.form.get("condition", "Unknown").strip()
            description = request.form.get("description", "").strip()
            multiple = bool(request.form.get("multiple"))
            image = request.files.get("image")
            
            # Validate inputs
            if not name or len(name) > 100:
                flash('Product name is required and must be less than 100 characters.', 'error')
                return render_template("upload.html")
            
            price_valid, price_result = validate_price(price_str)
            if not price_valid:
                flash(price_result, 'error')
                return render_template("upload.html")
            
            if not category or category not in ['Books', 'Tech', 'Clothes', 'Others']:
                flash('Please select a valid category.', 'error')
                return render_template("upload.html")
            
            # Validate file
            file_valid, file_msg = validate_file_upload(image)
            if not file_valid:
                flash(file_msg, 'error')
                return render_template("upload.html")
            
            # Process file upload
            filename = secure_filename(image.filename)
            # Add timestamp to prevent conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            
            # Create product
            new_product = Product(
                name=name,
                price=price_result,
                image=filename,
                description=description[:500],  # Limit description length
                category=category,
                condition=condition,
                multiple_items=multiple,
                seller_id=current_user.id
            )
            
            db.session.add(new_product)
            db.session.commit()
            flash('Product uploaded successfully!', 'success')
            return redirect(url_for("products"))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Upload error: {str(e)}")
            flash('Error uploading product. Please try again.', 'error')
    
    return render_template("upload.html")

@app.route("/uploads/<filename>")
@login_required
def uploads(filename):
    # Security: Validate filename
    if not filename or '..' in filename or '/' in filename:
        flash('Invalid file request.', 'error')
        return redirect(url_for('home'))
    
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except FileNotFoundError:
        flash('File not found.', 'error')
        return redirect(url_for('home'))

@app.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        recent_products = Product.query.order_by(Product.id.desc()).limit(10).all()
        
        # Check if current user is the seller
        is_own_product = (product.seller_id == current_user.id)
        
        return render_template("product_detail.html", 
                             product=product, 
                             recent_products=recent_products,
                             is_own_product=is_own_product)
    except Exception as e:
        app.logger.error(f"Product detail error: {str(e)}")
        flash('Error loading product details.', 'error')
        return redirect(url_for('products'))

@app.route("/chat_with_seller/<int:product_id>")
@login_required
def chat_with_seller(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if user is trying to chat with themselves
        if product.seller_id == current_user.id:
            flash("You cannot chat with yourself about your own product!", "warning")
            return redirect(url_for('product_detail', product_id=product_id))
        
        # Redirect to chat with the seller
        return redirect(url_for('chat', user_id=product.seller_id))
    except Exception as e:
        app.logger.error(f"Chat with seller error: {str(e)}")
        flash('Error starting chat.', 'error')
        return redirect(url_for('products'))

@app.route("/send_message", methods=["GET"])
@login_required
def send_message():
    try:
        users = User.query.filter(User.id != current_user.id).all()
        return render_template("send_message.html", users=users)
    except Exception as e:
        app.logger.error(f"Send message error: {str(e)}")
        flash('Error loading users.', 'error')
        return render_template("send_message.html", users=[])

@app.route("/inbox")
@login_required
def inbox():
    try:
        # Get all users for the conversation list
        users = User.query.filter(User.id != current_user.id).all()
        
        # For each user, get the most recent message (if any)
        conversations = []
        for user in users:
            # Find the most recent message between current_user and this user
            last_message = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == user.id)) |
                ((Message.sender_id == user.id) & (Message.receiver_id == current_user.id))
            ).order_by(Message.timestamp.desc()).first()
            
            if last_message:
                conversations.append({
                    'user': user,
                    'last_message': last_message,
                    'unread_count': Message.query.filter_by(
                        sender_id=user.id, 
                        receiver_id=current_user.id
                    ).count()  # Simple unread count implementation
                })
            else:
                conversations.append({
                    'user': user,
                    'last_message': None,
                    'unread_count': 0
                })
        
        # Sort by most recent message
        conversations.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else datetime.min, reverse=True)
        
        return render_template("inbox.html", conversations=conversations)
    except Exception as e:
        app.logger.error(f"Inbox error: {str(e)}")
        flash('Error loading inbox.', 'error')
        return render_template("inbox.html", conversations=[])

@app.route("/api/conversations/<int:user_id>")
@login_required
def get_conversation(user_id):
    try:
        # Validate user_id
        if user_id == current_user.id:
            return jsonify({'error': 'Cannot get conversation with yourself'}), 400
        
        # Get all messages between current_user and the specified user
        messages = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
            ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
        ).order_by(Message.timestamp).all()
        
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg.id,
                'content': msg.content,
                'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'is_sender': msg.sender_id == current_user.id,
                'sender_name': msg.sender.student_id
            })
        
        return jsonify(message_list)
    except Exception as e:
        app.logger.error(f"Get conversation error: {str(e)}")
        return jsonify({'error': 'Error loading conversation'}), 500

@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):
    try:
        if user_id == current_user.id:
            flash("You cannot chat with yourself!", "warning")
            return redirect(url_for('inbox'))
        
        other_user = User.query.get_or_404(user_id)
        return render_template("chat.html", other_user=other_user)
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        flash('Error loading chat.', 'error')
        return redirect(url_for('inbox'))

@app.route('/wishlist')
@login_required
def wishlist():
    try:
        # Get all wishlist items for the current user with product details
        wishlist_items = db.session.query(Wishlist, Product).join(
            Product, Wishlist.product_id == Product.id
        ).filter(Wishlist.user_id == current_user.id).all()
        
        return render_template('wishlist.html', wishlist_items=wishlist_items)
    except Exception as e:
        app.logger.error(f"Wishlist error: {str(e)}")
        flash('Error loading wishlist.', 'error')
        return render_template('wishlist.html', wishlist_items=[])

@app.route('/api/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    try:
        # Check if product exists
        product = Product.query.get_or_404(product_id)
        
        # Check if it's user's own product
        if product.seller_id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot add your own product to wishlist'})
        
        # Check if already in wishlist
        existing = Wishlist.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Item already in wishlist'})
        
        # Add to wishlist
        wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(wishlist_item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Add to wishlist error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error adding to wishlist'})

@app.route('/api/wishlist/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_wishlist(product_id):
    try:
        wishlist_item = Wishlist.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first()
        
        if not wishlist_item:
            return jsonify({'success': False, 'message': 'Item not in wishlist'})
        
        db.session.delete(wishlist_item)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Remove from wishlist error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error removing from wishlist'})

@app.route('/api/wishlist/clear', methods=['DELETE'])
@login_required
def clear_wishlist():
    try:
        Wishlist.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Wishlist cleared'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Clear wishlist error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error clearing wishlist'})

@app.route('/api/wishlist/check/<int:product_id>')
@login_required
def check_wishlist_status(product_id):
    """Check if a product is in the user's wishlist"""
    try:
        exists = Wishlist.query.filter_by(
            user_id=current_user.id, 
            product_id=product_id
        ).first() is not None
        
        return jsonify({'in_wishlist': exists})
    except Exception as e:
        app.logger.error(f"Check wishlist error: {str(e)}")
        return jsonify({'in_wishlist': False})

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            # Handle full name update
            full_name = request.form.get('full_name', '').strip()
            if full_name and len(full_name) <= 100:
                current_user.full_name = full_name
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename != '':
                    file_valid, file_msg = validate_file_upload(file)
                    if file_valid:
                        # Delete old profile picture if it's not the default
                        if current_user.profile_picture and current_user.profile_picture != 'default-avatar.png':
                            old_file_path = os.path.join(app.config["UPLOAD_FOLDER"], current_user.profile_picture)
                            try:
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                            except OSError:
                                pass  # Ignore file deletion errors
                        
                        # Save new profile picture
                        filename = secure_filename(file.filename)
                        # Add timestamp to avoid conflicts
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                        filename = timestamp + filename
                        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                        
                        # Update user's profile picture
                        current_user.profile_picture = filename
                    else:
                        flash(file_msg, 'error')
                        return render_template('edit_profile.html')
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Edit profile error: {str(e)}")
            flash('Error updating profile. Please try again.', 'error')
        
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html')

@app.route('/api/upload_profile_picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """API endpoint for AJAX profile picture upload"""
    try:
        if 'profile_picture' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'})
        
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
        
        file_valid, file_msg = validate_file_upload(file)
        if not file_valid:
            return jsonify({'success': False, 'message': file_msg})
        
        # Delete old profile picture if it's not the default
        if current_user.profile_picture and current_user.profile_picture != 'default-avatar.png':
            old_file_path = os.path.join(app.config["UPLOAD_FOLDER"], current_user.profile_picture)
            try:
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
            except OSError:
                pass  # Ignore file deletion errors
        
        # Save new profile picture
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        
        # Update user's profile picture
        current_user.profile_picture = filename
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Profile picture updated successfully!',
            'new_image_url': url_for('uploads', filename=filename)
        })
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Upload profile picture error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error uploading profile picture'})
    
@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    """API endpoint for AJAX password change"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request data'})
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validate current password
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Current password is incorrect.'})
        
        # Validate new password
        pwd_valid, pwd_msg = validate_password(new_password)
        if not pwd_valid:
            return jsonify({'success': False, 'message': pwd_msg})
        
        # Check if new passwords match
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': 'New passwords do not match.'})
        
        # Check if new password is different from current
        if current_user.check_password(new_password):
            return jsonify({'success': False, 'message': 'New password must be different from current password.'})
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Password changed successfully!'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error changing password. Please try again.'})

# ============================================================================
# SOCKET.IO MESSAGE FEATURE - ENHANCED WITH ERROR HANDLING
# ============================================================================

@socketio.on('join')
def handle_join(data):
    """Client tells us who they are so we can put them in their personal room."""
    try:
        user_id = data.get('user_id')
        if user_id:
            room = f"user_{user_id}"
            join_room(room)
            app.logger.info(f"User {user_id} joined room {room}")
    except Exception as e:
        app.logger.error(f"Socket join error: {str(e)}")

@socketio.on('send_message')
def handle_socket_message(data):
    """
    Data contains: sender_id, receiver_id, content.
    Save to DB, then emit to the receiver's room.
    """
    try:
        sender_id = int(data['sender_id'])
        receiver_id = int(data['receiver_id'])
        content = data['content']

        # Basic validation
        if not content or not content.strip():
            emit('error', {'message': 'Message content cannot be empty'})
            return
            
        if len(content) > 1000:  # Limit message length
            emit('error', {'message': 'Message too long'})
            return
            
        if sender_id == receiver_id:
            emit('error', {'message': 'Cannot send message to yourself'})
            return

        app.logger.info(f"Received message: {content[:50]}... from {sender_id} to {receiver_id}")

        # 1) save to database
        msg = Message(content=content.strip(), sender_id=sender_id, receiver_id=receiver_id)
        db.session.add(msg)
        db.session.commit()

        # 2) emit to the receiver's room
        room = f"user_{receiver_id}"
        emit('new_message', {
            'id': msg.id,
            'content': content,
            'sender_id': sender_id,
            'receiver_id': receiver_id,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }, room=room)
        
        # 3) Also emit back to the sender for confirmation
        sender_room = f"user_{sender_id}"
        emit('message_sent', {
            'id': msg.id,
            'content': content,
            'receiver_id': receiver_id,
            'timestamp': msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        }, room=sender_room)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Socket message error: {str(e)}")
        emit('error', {'message': 'Failed to send message'})


if os.environ.get('FLASK_ENV') == 'production':
    # Production CORS settings
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
else:
    # Development settings
    socketio = SocketIO(app, cors_allowed_origins="*")

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Maximum size is 5MB.', 'error')
    return redirect(request.url)

# ============================================================================
# INITIALIZATION AND STARTUP
# ============================================================================

# Create database tables
with app.app_context():
    try:
        db.create_all()
        app.logger.info("✓ Database tables created successfully")
    except Exception as e:
        app.logger.error(f"✗ Database initialization error: {str(e)}")

# Validate security configuration on startup
try:
    validate_security_config()
except Exception as e:
    app.logger.error(f"Security validation failed: {str(e)}")
    if not app.debug:
        raise

# Configure logging for production
if not app.debug:
    # Create logs directory
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Set up file logging
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'thriftit.log'), 
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('ThriftIt startup - Production mode')

if __name__ == "__main__":
    # Development server configuration
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    
    # Startup messages
    app.logger.info("🚀 ThriftIt application started successfully!")
    app.logger.info(f"   Environment: {os.environ.get('FLASK_ENV', 'default')}")
    app.logger.info(f"   Debug mode: {debug_mode}")
    app.logger.info(f"🔧 Starting development server on port {port}")
    app.logger.info(f"   Secret key: {'✓ Custom' if os.environ.get('SECRET_KEY') else '⚠️  Auto-generated'}")
    
    # Use different host based on environment
    host = 'localhost' if debug_mode else '0.0.0.0'
    
    socketio.run(
        app, 
        debug=debug_mode,
        host=host,  # This will be 0.0.0.0 in production
        port=port
    )
else:
    # For production WSGI servers (Gunicorn)
    application = app