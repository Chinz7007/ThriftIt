from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit
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

@app.route("/send_message", methods=["GET", "POST"])
@login_required
def send_message():
    if request.method == "POST":
        sender_id   = int(request.form.get("sender_id"))
        receiver_id = int(request.form.get("receiver_id"))
        content     = request.form.get("content")
        message     = Message(content=content, sender_id=sender_id, receiver_id=receiver_id)
        db.session.add(message)
        db.session.commit()
        room = f"user_{receiver_id}"
        socketio.emit("new_message", {"content": content, "sender_id": sender_id}, room=room)
        return redirect(url_for("inbox", user_id=sender_id))
    users = User.query.all()
    return render_template("send_message.html", users=users)

@app.route("/inbox/<int:user_id>")
@login_required
def inbox(user_id):
    messages = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()
    return render_template("inbox.html", messages=messages, user_id=user_id)

if __name__ == "__main__":
    socketio.run(app, debug=True)
