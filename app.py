from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, emit
from datetime import datetime
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///products.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
socketio = SocketIO(app, cors_allowed_origins="*")

db = SQLAlchemy(app)

# Extensions that is allowed for upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#Product Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    multiple_items = db.Column(db.Boolean, default=False)

class User(db.Model):
     id       = db.Column(db.Integer, primary_key=True)
     username = db.Column(db.String(100), unique=True, nullable=False)
     email    = db.Column(db.String(120), unique=True, nullable=False)
     messages_sent     = db.relationship('Message',foreign_keys='Message.sender_id',backref='sender', lazy='dynamic')
     messages_received = db.relationship('Message',foreign_keys='Message.receiver_id',backref='receiver', lazy='dynamic')


class Message(db.Model):
     id         = db.Column(db.Integer, primary_key=True)
     content    = db.Column(db.Text, nullable=False)
     timestamp  = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
     sender_id   = db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
     receiver_id = db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
                            



#Routes for posting the datas

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def products():
    search = request.args.get("q") 
    if search:
        products = Product.query.filter(Product.name.ilike(f"%{search}%")).all()
    else:
        products = Product.query.all()

    return render_template("products.html", products=products, search=search)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        name = request.form.get("name")
        price = float(request.form.get("price"))
        category = request.form.get("category")
        condition = request.form.get("condition","Unknown")
        description = request.form.get("description")
        multiple = True if request.form.get("multiple") else False
        image = request.files["image"]

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

    return render_template("upload.html")

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    recent_products = Product.query.order_by(Product.id.desc()).limit(10).all()
    return render_template("product_detail.html", product=product, recent_products=recent_products)

# Route to send a message
@app.route("/send_message", methods=["GET", "POST"])
def send_message():
    if request.method == "POST":
        sender_id = int(request.form.get("sender_id"))
        receiver_id = int(request.form.get("receiver_id"))
        content = request.form.get("content")

        new_message = Message(content=content, sender_id=sender_id, receiver_id=receiver_id)
        db.session.add(new_message)
        db.session.commit()

        return redirect(url_for("inbox", user_id=sender_id))

    users = User.query.all()
    return render_template("send_message.html", users=users)

# Route to view inbox
@app.route("/inbox/<int:user_id>")
def inbox(user_id):
    messages = Message.query.filter_by(receiver_id=user_id).order_by(Message.timestamp.desc()).all()
    return render_template("inbox.html", messages=messages, user_id=user_id)

if __name__ == "__main__":
    app.run(debug=True)

