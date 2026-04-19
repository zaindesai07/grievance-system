from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os

from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from werkzeug.security import generate_password_hash, check_password_hash

import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- CLOUDINARY ----------------
cloudinary.config(
    cloud_name="drwksgzy5",
    api_key="781717963747153",
    api_secret="zprcBCc92QwTVnt6-u4LeE-Y-n0"
)

# ---------------- LOGIN ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- MODELS ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # 🔥 FIXED LENGTH
    role = db.Column(db.String(20), default="user")

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    location = db.Column(db.String(100))
    image = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Pending")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ---------------- HOME ----------------
@app.route('/')
def home():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect('/login')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return "Fill all fields"

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "User already exists"

        # 🔥 ADMIN LOGIC
        role = "admin" if username == "admin" else "user"

        hashed_password = generate_password_hash(password)

        user = User(username=username, password=hashed_password, role=role)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect('/')

    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()

        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect('/')
        else:
            return "Invalid credentials"

    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- SUBMIT ----------------
@app.route('/submit', methods=['POST'])
@login_required
def submit():
    desc = request.form.get('description')
    location = request.form.get('location')

    image_url = None
    file = request.files.get('image')

    if file and file.filename != "":
        try:
            result = cloudinary.uploader.upload(file)
            image_url = result['secure_url']
        except:
            image_url = None

    new_complaint = Complaint(
        description=desc,
        location=location,
        image=image_url,
        user_id=current_user.id
    )

    db.session.add(new_complaint)
    db.session.commit()

    return redirect('/')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    complaints = Complaint.query.all()

    total = len(complaints)
    pending = sum(1 for c in complaints if c.status == "Pending")
    progress = sum(1 for c in complaints if c.status == "In Progress")
    resolved = sum(1 for c in complaints if c.status == "Resolved")

    return render_template(
        'dashboard.html',
        complaints=complaints,
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved
    )

# ---------------- UPDATE STATUS ----------------
@app.route('/update_status/<int:id>/<status>')
@login_required
def update_status(id, status):
    if current_user.role != "admin":
        return "Access Denied"

    complaint = Complaint.query.get(id)
    if complaint:
        complaint.status = status
        db.session.commit()

    return redirect('/dashboard')

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
@login_required
def delete_complaint(id):
    if current_user.role != "admin":
        return "Access Denied"

    complaint = Complaint.query.get(id)
    if complaint:
        db.session.delete(complaint)
        db.session.commit()

    return redirect('/dashboard')

# ---------------- RESET DB ----------------
@app.route('/initdb')
def initdb():
    db.create_all()
    return "Database created!"

# ---------------- RUN ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=10000)