from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os

# LOGIN IMPORTS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# CLOUDINARY IMPORTS
import cloudinary
import cloudinary.uploader

app = Flask(__name__)
app.secret_key = "secret123"

# DATABASE CONFIG
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- CLOUDINARY CONFIG ----------------
cloudinary.config(
    cloud_name="drwksgzy5",
    api_key="781717963747153",
    api_secret="zprcBCc92QwTVnt6-u4LeE-Y-n0"
)

# ---------------- LOGIN SETUP ----------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    location = db.Column(db.String(100))
    image = db.Column(db.String(200))
    status = db.Column(db.String(50), default="Pending")

# ---------------- ROUTES ----------------

# HOME
@app.route('/')
def home():
    return render_template('index.html')

# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            password=request.form['password']
        )
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and user.password == request.form['password']:
            login_user(user)
            return redirect('/dashboard')
        else:
            return "Invalid credentials"

    return render_template('login.html')

# LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# SUBMIT COMPLAINT
@app.route('/submit', methods=['POST'])
def submit():
    desc = request.form['description']
    location = request.form['location']

    file = request.files['image']
    result = cloudinary.uploader.upload(file)
    image_url = result['secure_url']

    new_complaint = Complaint(
        description=desc,
        location=location,
        image=image_url
    )

    db.session.add(new_complaint)
    db.session.commit()

    return redirect('/')

# DASHBOARD
@app.route('/dashboard')
@login_required
def dashboard():
    complaints = Complaint.query.all()

    complaints_data = []

    # COUNTS
    total = len(complaints)
    pending = 0
    progress = 0
    resolved = 0

    for c in complaints:
        # convert to dict
        complaints_data.append({
            "id": c.id,
            "description": c.description,
            "location": c.location,
            "status": c.status,
            "image": c.image
        })

        # counting
        if c.status == "Pending":
            pending += 1
        elif c.status == "In Progress":
            progress += 1
        elif c.status == "Resolved":
            resolved += 1

    return render_template(
        'dashboard.html',
        complaints=complaints_data,
        total=total,
        pending=pending,
        progress=progress,
        resolved=resolved
    )

# DELETE COMPLAINT
@app.route('/delete/<int:id>')
@login_required
def delete_complaint(id):
    complaint = Complaint.query.get(id)

    if complaint:
        db.session.delete(complaint)
        db.session.commit()

    return redirect('/dashboard')

# ---------------- RUN APP (ALWAYS LAST) ----------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)