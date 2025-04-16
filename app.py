from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///products.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Extensions that is allowed for upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable= False)
    price = db.Column(db.Float, nullable= False)
    image = db.Column(db.String(100), nullable= False)


#Routes for posting the datas

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/products")
def products():
    search = request.args.get("q")  # Get search input from URL
    if search:
        products = Product.query.filter(Product.name.ilike(f"%{search}%")).all()
    else:
        products = Product.query.all()

    return render_template("products.html", products=products, search=search)

@app.route("/upload", methods=["GET","POST"])
def upload():
    if request.method == "POST":
        name= request.form["name"]
        price= float(request.form["price"])
        image= request.files["image"]

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

            new_product = Product(name=name, price=price, image=filename)
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
    return render_template("product_detail.html", product=product)

if __name__ == "__main__":
    app.run(debug=True)