from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import math
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'clothes.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder and allowed extensions
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# --- Models ---

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Category {self.name}>"

class Clothing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('clothes', lazy=True))
    color = db.Column(db.String(20), nullable=False)       # hex color
    location = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.String(200))
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Clothing {self.name}>"

# --- Helper Functions ---

def hex_to_rgb(hex_value):
    hex_value = hex_value.lstrip('#')
    return tuple(int(hex_value[i:i+2], 16) for i in (0, 2, 4))

# Expanded named colors dictionary
named_colors = {
    "Red": (255, 0, 0),
    "Green": (0, 128, 0),
    "Blue": (0, 0, 255),
    "Yellow": (255, 255, 0),
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Orange": (255, 165, 0),
    "Purple": (128, 0, 128),
    "Brown": (165, 42, 42),
    "Black": (0, 0, 0),
    "White": (255, 255, 255),
    "Gray": (128, 128, 128),
    "Beige": (245, 245, 220),
    "Navy blue": (0, 0, 128)
}

def get_color_name(hex_value):
    r, g, b = hex_to_rgb(hex_value)
    best_color_name = None
    min_distance = float('inf')
    for color_name, (cr, cg, cb) in named_colors.items():
        distance = math.sqrt((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2)
        if distance < min_distance:
            min_distance = distance
            best_color_name = color_name
    return best_color_name

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---

# Home page with search and filter
@app.route('/')
def index():
    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    query = Clothing.query
    if search_query:
        query = query.filter(Clothing.name.ilike(f'%{search_query}%'))
    if category_filter:
        try:
            cat_id = int(category_filter)
            query = query.filter(Clothing.category_id == cat_id)
        except ValueError:
            pass
    clothes = query.order_by(Clothing.last_updated.desc()).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('index.html', clothes=clothes, categories=categories,
                           search_query=search_query, category_filter=category_filter)

# Add new clothing item (dynamic categories & file upload)
@app.route('/add', methods=['GET', 'POST'])
def add():
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category')
        category = Category.query.get(category_id)
        color = request.form['color']
        location = request.form['location']
        status = request.form['status']
        image_url = request.form.get('image_url')
        
        # Check file upload
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            # Generate a unique filename by appending a UUID
            unique_prefix = str(uuid.uuid4())
            filename = unique_prefix + "_" + secure_filename(image_file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(file_path)
            # Create a URL to access the uploaded file
            image_url = url_for('static', filename='uploads/' + filename)
        
        if not name:
            default_color_name = get_color_name(color)
            name = f"{default_color_name} {category.name}"
        
        clothing_item = Clothing(
            name=name,
            category_id=category.id,
            color=color,
            location=location,
            status=status,
            image_url=image_url,
            last_updated=datetime.utcnow()
        )
        db.session.add(clothing_item)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add.html', categories=categories)

# Edit clothing item
@app.route('/edit/<int:clothing_id>', methods=['GET', 'POST'])
def edit(clothing_id):
    clothing_item = Clothing.query.get_or_404(clothing_id)
    categories = Category.query.order_by(Category.name).all()
    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if new_name:
            clothing_item.name = new_name
        category_id = request.form.get('category')
        category = Category.query.get(category_id)
        clothing_item.category_id = category.id
        clothing_item.color = request.form['color']
        clothing_item.location = request.form['location']
        clothing_item.status = request.form['status']
        clothing_item.image_url = request.form.get('image_url')
        image_file = request.files.get('image_file')
        image_file = request.files.get('image_file')
        if image_file and allowed_file(image_file.filename):
            unique_prefix = str(uuid.uuid4())
            filename = unique_prefix + "_" + secure_filename(image_file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(file_path)
            # Update the clothing item's image_url field with the new URL
            clothing_item.image_url = url_for('static', filename='uploads/' + filename)
        clothing_item.last_updated = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', clothing=clothing_item, categories=categories)

# Delete clothing item
@app.route('/delete/<int:clothing_id>', methods=['POST'])
def delete(clothing_id):
    clothing_item = Clothing.query.get_or_404(clothing_id)
    db.session.delete(clothing_item)
    db.session.commit()
    return redirect(url_for('index'))

# Category management
@app.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    if request.method == 'POST':
        category_name = request.form.get('name', '').strip()
        if category_name:
            existing = Category.query.filter_by(name=category_name).first()
            if not existing:
                new_category = Category(name=category_name)
                db.session.add(new_category)
                db.session.commit()
        return redirect(url_for('manage_categories'))
    categories = Category.query.order_by(Category.name).all()
    return render_template('categories.html', categories=categories)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add default categories if none exist
        if Category.query.count() == 0:
            default_cats = ["Jeans", "Chinos", "Piké", "T-Shirt", "Shirt", "Jacket", "Hoodie", "Sweater", "Shorts"]
            for cat_name in default_cats:
                db.session.add(Category(name=cat_name))
            db.session.commit()
    app.run(host='0.0.0.0', port=5000, debug=True)
