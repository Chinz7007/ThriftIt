from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit, send
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'chin-ethan-aaron'

# ensure upload folder exists
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///products.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

socketio = SocketIO(app, cors_allowed_origins="*")
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- file upload helper ---
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- models ---
class Product(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    name           = db.Column(db.String(100), nullable=False)
    price          = db.Column(db.Float, nullable=False)
    image          = db.Column(db.String(100), nullable=False)
    description    = db.Column(db.Text, nullable=True)
    category       = db.Column(db.String(50), nullable=False)
    condition      = db.Column(db.String(50), nullable=False)
    multiple_items = db.Column(db.Boolean, default=False)

class User(db.Model, UserMixin):
    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.String(50), unique=True, nullable=False)
    student_email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    messages_sent     = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sid = request.form['student_id']
        pwd = request.form['password']
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
        sid   = request.form['student_id']
        email = request.form['email']
        pwd   = request.form['password']
        # check if already exists
        if User.query.filter_by(student_id=sid).first():
            flash('Student ID already taken.', 'error')
        elif User.query.filter_by(student_email=email).first():
            flash('Email already registered.', 'error')
        else:
            new_user = User(student_id=sid, student_email=email)
            new_user.set_password(pwd)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))



# --- application routes ---
    
@app.route('/')
@login_required
def home():
    return render_template("home.html")

@app.route("/products")
@login_required
def products():
    search = request.args.get("q")
    if search:
        products = Product.query.filter(Product.name.ilike(f"%{search}%")).all()
    else:
        products = Product.query.all()
    return render_template("products.html", products=products, search=search)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        name        = request.form.get("name")
        price       = float(request.form.get("price"))
        category    = request.form.get("category")
        condition   = request.form.get("condition", "Unknown")
        description = request.form.get("description")
        multiple    = bool(request.form.get("multiple"))
        image       = request.files.get("image")
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            new_product = Product(
                name=name,
                price=price,
                image=filename,
                description=description,
                category=category,
                condition=condition,
                multiple_items=multiple
            )
            db.session.add(new_product)
            db.session.commit()
            return redirect(url_for("products"))
        else:
            flash('Please upload a valid image file', 'error')
    return render_template("upload.html")

@app.route("/uploads/<filename>")
@login_required
def uploads(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/product/<int:product_id>")
@login_required
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    recent_products = Product.query.order_by(Product.id.desc()).limit(10).all()
    return render_template("product_detail.html", product=product, recent_products=recent_products)

@app.route("/send_message", methods=["GET"])
@login_required
def send_message():
    users = User.query.all()
    return render_template("send_message.html", users=users)

@app.route("/inbox")
@login_required
def inbox():
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

@app.route("/api/conversations/<int:user_id>")
@login_required
def get_conversation(user_id):
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

@app.route("/chat/<int:user_id>")
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    return render_template("chat.html", other_user=other_user)

@app.route('/wishlist')
@login_required
def wishlist():
    # Get all wishlist items for the current user with product details
    wishlist_items = db.session.query(Wishlist, Product).join(
        Product, Wishlist.product_id == Product.id
    ).filter(Wishlist.user_id == current_user.id).all()
    
    return render_template('wishlist.html', wishlist_items=wishlist_items)

@app.route('/api/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_wishlist(product_id):
    try:
        # Check if product exists
        product = Product.query.get_or_404(product_id)
        
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
        return jsonify({'success': False, 'message': str(e)})

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
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/wishlist/clear', methods=['DELETE'])
@login_required
def clear_wishlist():
    try:
        Wishlist.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Wishlist cleared'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/wishlist/check/<int:product_id>')
@login_required
def check_wishlist_status(product_id):
    """Check if a product is in the user's wishlist"""
    exists = Wishlist.query.filter_by(
        user_id=current_user.id, 
        product_id=product_id
    ).first() is not None
    
    return jsonify({'in_wishlist': exists})

#Message Feature
@socketio.on('join')
def handle_join(data):
    """Client tells us who they are so we can put them in their personal room."""
    user_id = data.get('user_id')
    if user_id:
        room = f"user_{user_id}"
        join_room(room)
        print(f"User {user_id} joined room {room}")

@socketio.on('send_message')
def handle_socket_message(data):
    """
    Data contains: sender_id, receiver_id, content.
    Save to DB, then emit to the receiver's room.
    """
    sender_id = int(data['sender_id'])
    receiver_id = int(data['receiver_id'])
    content = data['content']

    print(f"Received message: {content} from {sender_id} to {receiver_id}")

    # 1) save to database
    msg = Message(content=content, sender_id=sender_id, receiver_id=receiver_id)
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

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    socketio.run(app, debug=True)
