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
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'database.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
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
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="user")

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    location = db.Column(db.String(100))
    image = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Pending")
    votes = db.Column(db.Integer, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    complaint_id = db.Column(db.Integer)

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

        if User.query.filter_by(username=username).first():
            return "User already exists"

        role = "admin" if username == "admin" else "user"
        hashed = generate_password_hash(password)

        user = User(username=username, password=hashed, role=role)
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

    complaint = Complaint(
        description=desc,
        location=location,
        image=image_url,
        user_id=current_user.id
    )

    db.session.add(complaint)
    db.session.commit()

    return redirect('/dashboard')

# ---------------- UPVOTE ----------------
@app.route('/upvote/<int:id>')
@login_required
def upvote(id):
    existing = Vote.query.filter_by(
        user_id=current_user.id,
        complaint_id=id
    ).first()

    if existing:
        return redirect('/dashboard')

    vote = Vote(user_id=current_user.id, complaint_id=id)
    db.session.add(vote)

    complaint = Complaint.query.get(id)
    if complaint:
        complaint.votes += 1

    db.session.commit()
    return redirect('/dashboard')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    complaints = Complaint.query.order_by(Complaint.votes.desc()).all()
    return render_template('dashboard.html', complaints=complaints)

# ---------------- ADMIN ----------------
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        return "Access Denied"

    complaints = Complaint.query.all()
    return render_template('admin.html', complaints=complaints)

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

    return redirect('/admin')

# ---------------- DELETE ----------------
@app.route('/delete/<int:id>')
@login_required
def delete(id):
    if current_user.role != "admin":
        return "Access Denied"

    complaint = Complaint.query.get(id)
    if complaint:
        db.session.delete(complaint)
        db.session.commit()

    return redirect('/admin')

# ---------------- RESET DB ----------------
@app.route('/initdb')
def initdb():
    db.drop_all()
    db.create_all()
    return "Database Reset Done!"

# ---------------- RUN ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)