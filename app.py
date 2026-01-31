import os  # Added missing import for handling folders
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename # For file safety

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# 1. Configuration (MUST come before routes)
app.secret_key = "hackoverflow_2026_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# 2. Initialize Database
db = SQLAlchemy(app)

# 3. Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# MUST BE AT THE TOP
class Circular(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    content = db.Column(db.Text)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20))
    room_number = db.Column(db.String(10)) # Ensure this is here
    specialty = db.Column(db.String(50), nullable=True)
    task_count = db.Column(db.Integer, default=0)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    category = db.Column(db.String(50))
    room_number = db.Column(db.String(10))
    priority = db.Column(db.String(20))
    description = db.Column(db.Text)
    image_path = db.Column(db.String(200))


    is_public = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Reported")
    
    # Relationships and Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    worker_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    # This connects the Issue to the User so you can use issue.student.room_number
    student = db.relationship('User', foreign_keys=[student_id], backref='reported_issues')
    worker = db.relationship('User', foreign_keys=[worker_id], backref='assigned_tasks')

    # Timestamps
    assigned_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LostFound(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    location = db.Column(db.String(100)) #
    status = db.Column(db.String(20), default="Lost") #
    image_path = db.Column(db.String(200))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# --- ROUTES ---

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    user = User.query.filter_by(username=username, role=role).first()
    
    if user and user.password == password:
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        
        if role == 'Student': return redirect(url_for('student_dashboard'))
        if role == 'Management': return redirect(url_for('admin_dashboard'))
        if role == 'Worker': return redirect(url_for('worker_dashboard'))
    
    flash("Invalid login credentials!")
    return redirect(url_for('login'))

@app.route('/admin/circular', methods=['POST'])
def post_circular():
    # 1. Security Check
    if session.get('role') != 'Management': 
        return redirect(url_for('login'))
        
    # 2. Get data from the form
    title = request.form.get('title')
    content = request.form.get('content')

    if title and content:
        # 3. Save to Database
        new_announcement = Circular(title=title, content=content)
        db.session.add(new_announcement)
        db.session.commit()
        flash("Circular published successfully!")
    
    # 4. Redirect back to dashboard to see changes
    return redirect(url_for('admin_dashboard'))
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
    
    # 1. Get the current logged-in student (Using modern db.session.get to avoid warnings)
    current_user = db.session.get(User, session['user_id'])
    
    # 2. Fetch Circulars (Newest first)
    announcements = Circular.query.order_by(Circular.id.desc()).all()
    
    # 3. Find roommates
    room_members = User.query.filter_by(room_number=current_user.room_number).all()
    
    # 4. Get private issues reported by THIS specific student
    my_issues = Issue.query.filter_by(student_id=session['user_id']).all()

    # ✅ 5. NEW: Get all Public Issues from across the hostel
    # This ensures that when someone clicks "Public", it shows up here for everyone
    public_feed = Issue.query.filter_by(is_public=True).all()
    
    # 6. Pass everything to the HTML template
    return render_template('student_dashboard.html', 
                           my_issues=my_issues, 
                           public_issues=public_feed, # Added this variable
                           roommates=room_members,
                           circulars=announcements)


@app.route('/report', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # 1. Get current student details (Using modern db.session.get)
        user = db.session.get(User, session['user_id'])
        cat = request.form['category']
        
        # 2. DUPLICATE CHECK (Active issues for this room + category)
        existing_issue = Issue.query.join(User, Issue.student_id == User.id)\
            .filter(User.room_number == user.room_number, 
                    Issue.category == cat, 
                    Issue.status != 'Solved').first()

        if existing_issue:
            flash(f"An active {cat} issue for Room {user.room_number} is already being processed!")
            return redirect(url_for('student_dashboard'))

        # 3. HANDLE IMAGE UPLOAD
        # Match name="item_image" from your student report form
        file = request.files.get('item_image') 
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        # 4. CREATE NEW ISSUE
        new_issue = Issue(
            title=request.form['title'],
            category=cat,
            # ✅ FIX: Explicitly save the student's room number to the issue
            room_number=user.room_number, 
            priority=request.form['priority'],
            description=request.form['description'],
            # ✅ FIX: Save the filename so the worker can see the photo
            image_path=filename, 
            is_public='is_public' in request.form,
            student_id=user.id,
            status="Reported" # Default status
        )

        # 5. AUTO-ASSIGN LOGIC (Limit to 8 tasks)
        worker = User.query.filter_by(role='Worker', specialty=cat)\
            .filter(User.task_count < 8)\
            .order_by(User.task_count.asc()).first()
            
        if worker:
            new_issue.worker_id = worker.id
            new_issue.status = "Assigned"
            new_issue.assigned_at = datetime.utcnow()
            worker.task_count += 1
            
        db.session.add(new_issue)
        db.session.commit()
        return redirect(url_for('student_dashboard'))
        
    return render_template('report_issue.html')


@app.route('/worker_dashboard')
def worker_dashboard():
    if 'user_id' not in session or session.get('role') != 'Worker':
        return redirect(url_for('login'))
    tasks = Issue.query.filter_by(worker_id=session['user_id']).all()
    return render_template('worker_dashboard.html', tasks=tasks)


@app.route('/update_status/<int:issue_id>', methods=['POST'])
def update_status(issue_id):
    issue = Issue.query.get(issue_id)
    new_status = request.form.get('new_status')
    
    # If resolving, decrease the worker's task count so they can take new ones
    if new_status == "Resolved" and issue.status != "Resolved":
        worker = User.query.get(issue.worker_id)
        if worker and worker.task_count > 0:
            worker.task_count -= 1
            
    issue.status = new_status
    db.session.commit()
    return redirect(url_for('worker_dashboard'))

@app.route('/admin_dashboard')
def admin_dashboard():
    # 1. Security Check (Matches your 'Management' role from handle_login)
    if session.get('role') != 'Management': 
        return redirect(url_for('login'))
    
    # 2. Fetch Active Staff (Fixes empty staff table)
    workers_list = User.query.filter_by(role='Worker').all() # Matches 'Worker' case
    
    # 3. Fetch All Campus Issues
    all_issues = Issue.query.all()
    
    # 4. Calculate stats for the Overview card
    pending = Issue.query.filter_by(status='Reported').count()
    resolved = Issue.query.filter_by(status='Solved').count()
    
    # 5. Overdue logic (Fixed to avoid terminal warnings)
    from datetime import timezone
    deadline = datetime.now(timezone.utc) - timedelta(days=2)
    overdue_issues = Issue.query.filter(Issue.assigned_at <= deadline, Issue.status == "Assigned").all()

    return render_template('admin_dashboard.html', 
                           workers=workers_list, 
                           issues=all_issues, 
                           pending_count=pending, 
                           resolved_count=resolved,
                           overdue=overdue_issues)



import os
from datetime import datetime  # Crucial for the timestamp
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename # Crucial for saving files
# Ensure this path is absolute for your Windows desktop
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
@app.route('/lost-found', methods=['GET', 'POST'])
def lost_found():
    # 1. ALWAYS check for login first!
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('item_image')
        filename = None
        
        if file and file.filename != '':
            # 2. Secure and timestamp the filename
            filename = secure_filename(file.filename)
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            
            # 3. Save to the absolute path
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # 4. Save to Database
        new_item = LostFound(
            item_name=request.form.get('item_name'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            status=request.form.get('status'),
            image_path=filename,
            user_id=session['user_id']
        )
        db.session.add(new_item)
        db.session.commit()
        return redirect(url_for('lost_found'))

    # 5. Fetch all items (Newest first)
    items = LostFound.query.order_by(LostFound.id.desc()).all()
    return render_template('lost_found.html', items=items)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/add_worker', methods=['POST'])
def add_worker():
    if session.get('role') != 'Management':
        return redirect(url_for('login'))
    
    # Get details from the management form
    name = request.form.get('worker_name')
    pwd = request.form.get('password')
    spec = request.form.get('specialty') # e.g., 'Electrical', 'Plumbing'
    
    # Check if worker already exists
    if User.query.filter_by(username=name).first():
        flash("Username already exists!")
    else:
        # Create the new worker
        new_worker = User(username=name, password=pwd, role='Worker', specialty=spec)
        db.session.add(new_worker)
        db.session.commit()
        flash(f"Worker {name} added successfully for {spec}!")
        
    return redirect(url_for('admin_dashboard'))
@app.route('/solve_issue/<int:issue_id>', methods=['POST'])
def solve_issue(issue_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    issue = Issue.query.get(issue_id)
    
    # Logic to free up the worker's capacity
    if issue.worker_id and issue.status != "Solved":
        worker = User.query.get(issue.worker_id)
        if worker and worker.task_count > 0:
            worker.task_count -= 1 # Reduces task count
            
    issue.status = "Solved" # Moves status to final stage
    db.session.commit()
    return redirect(url_for('student_dashboard'))

# 1. Add the function here
def setup_hostel_data():
    for floor in range(1, 4): 
        for room in range(1, 16): 
            room_id = f"{floor}{room:02d}" 
            for member in range(1, 4): 
                reg_no = f"2026HOSTEL{room_id}{member}"
                password = reg_no[-4:] 
                
                if not User.query.filter_by(username=reg_no).first():
                    new_student = User(
                        username=reg_no, 
                        password=password, 
                        role='Student', 
                        room_number=room_id
                    )
                    db.session.add(new_student)
    db.session.commit()



# 2. Call it at the very bottom of your file
if __name__ == '__main__':
    with app.app_context():
        # 1. Create the database tables
        db.create_all()
        
        # 2. Generate the 135 student accounts (3 floors, 15 rooms, 3 members)
        setup_hostel_data()
        
        # 3. Ensure an Admin (Management) account exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin = User(
                username='admin', 
                password='123', 
                role='Management'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin account created: username='admin', password='123'")

    app.run(debug=True)



@app.route('/admin/add_worker', methods=['POST'])
def add_worker():
    # These names MUST match the 'name' attributes in your HTML form
    name = request.form.get('worker_name') 
    pwd = request.form.get('password')
    spec = request.form.get('specialty')
    
    if name and pwd and spec:
        new_worker = User(username=name, password=pwd, role='worker', specialty=spec)
        db.session.add(new_worker)
        db.session.commit()
        print(f"✅ Success: Hired {name} for {spec}")
    
    return redirect(url_for('admin_dashboard'))



@app.route('/worker_dashboard')
def worker_dashboard():
    if 'user_id' not in session or session.get('role') != 'Worker':
        return redirect(url_for('login'))
    
    # ✅ FIX 1: Use db.session.get instead of .query.get to avoid LegacyAPIWarning
    worker = db.session.get(User, session['user_id'])
    
    # 2. Get issues assigned to THIS worker
    assigned_tasks = Issue.query.filter_by(worker_id=session['user_id']).all()
    
    # 3. Calculate workload (only pending tasks)
    pending_tasks = [t for t in assigned_tasks if t.status != 'Solved']
    
    # ✅ FIX 2: Ensure the variables match what you use in worker_dashboard.html
    return render_template('worker_dashboard.html', 
                           worker=worker, 
                           tasks=assigned_tasks,
                           workload=len(pending_tasks))

if __name__ == "__main__":
    app.run(debug=True)
