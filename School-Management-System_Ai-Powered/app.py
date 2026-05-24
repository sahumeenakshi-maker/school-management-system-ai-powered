import sqlite3
import os
import csv
from io import StringIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash

# For Gemini Chatbot Integration
# NOTE: The user requested a generic implementation matching the prompt guidelines.
# We will use the provided API structure within the static script for client-side calls.
# The server side will only handle API key provision securely.
# For simplicity and security in this example, we'll assume the API key is passed securely
# to the frontend (though in a real app, this should be proxied or managed server-side).

# --- Configuration ---
app = Flask(__name__)
# IMPORTANT: Use a strong secret key for session management
app.secret_key = 'super_secret_key_change_me_in_production'

# Database Configuration (SQLite3)
DB_NAME = 'school_portal.db'

# Gemini API Key (Required for Chatbot)
# !!! IMPORTANT: REPLACE THIS WITH YOUR ACTUAL GEMINI API KEY !!!
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

# --- Database Connection and Utility Functions ---

def get_db_connection():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def is_database_initialized():
    """Checks if the database file exists."""
    return os.path.exists(DB_NAME)

# Ensure database is initialized on first run if it doesn't exist
if not is_database_initialized():
    # If the database file is missing, the user must run database_setup.py first.
    print(f"\n--- WARNING: Database file '{DB_NAME}' not found. ---")
    print("Please run 'python database_setup.py' first to create the schema and tables.\n")
    # You might want to automatically call initialize_db from database_setup here,
    # but for structured setup, we require the user to run it explicitly.

# --- Security and Authentication Handlers ---

def get_user_role():
    """Utility to get the current user's role from the session."""
    return session.get('role')

def login_required(role=None):
    """Decorator to check login status and optionally user role."""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('index'))
            if role and session.get('role') != role:
                flash(f'Access denied. Only {role} can view this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__  # Fix for Flask route naming
        return decorated_function
    return decorator

# --- Utility: Get Subjects for Admin Panel ---
def get_subjects():
    conn = get_db_connection()
    subjects = conn.execute('SELECT id, subject_name, stream FROM subjects').fetchall()
    conn.close()
    return subjects

# --- Route Handlers ---

@app.route('/')
def index():
    """Landing page with login/signup modals."""
    return render_template('index.html', role=get_user_role())

@app.route('/signup', methods=['POST'])
def signup():
    """Handles new user registration."""
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role'] # student, teacher, or admin (admin should be restricted in a real app)

    conn = get_db_connection()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.cursor()
        
        # 1. Insert into users table
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, password_hash, role)
        )
        user_id = cursor.lastrowid
        
        # 2. Additional setup based on role (e.g., creating a corresponding student/teacher entry)
        if role == 'student':
            # Note: For simplicity, we add student details in the admin panel later. 
            # This is just a placeholder user account for login.
            pass

        if role == 'teacher':
            # Note: Teachers are linked to subjects in the admin panel later.
            pass

        conn.commit()
        flash('Registration successful! Please log in.', 'success')

    except sqlite3.IntegrityError:
        flash('Email address is already registered.', 'error')
    except Exception as e:
        flash(f'An error occurred during registration: {e}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """Handles user login."""
    email = request.form['email']
    password = request.form['password']
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        # Successful Login
        session['user_id'] = user['id']
        session['email'] = user['email']
        session['name'] = user['name']
        session['role'] = user['role']
        flash(f'Welcome back, {user["name"]}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        # Failed Login
        flash('Invalid email or password.', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logs out the current user."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Forgot Password (OTP in VS Code Console) ---

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Handles password reset request."""
    if request.method == 'POST':
        email = request.form.get('email')
        otp_submitted = request.form.get('otp')
        new_password = request.form.get('new_password')
        
        if email and not otp_submitted and not new_password:
            # Step 1: Generate and Send (Log) OTP
            # In a real application, this would send an email. 
            # As requested, we simulate sending by logging to the console.
            import random
            otp = str(random.randint(100000, 999999))
            session['reset_otp'] = otp
            session['reset_email'] = email
            session['otp_generated_time'] = os.environ.get('TIME_ENV', '2025-11-30 10:40:00') # Placeholder time logic
            
            # --- IMPORTANT: OTP is printed to the VS Code Console as requested ---
            print(f"\n--- PASSWORD RESET OTP for {email}: {otp} ---\n")
            
            flash('An OTP has been generated and logged to your VS Code/Terminal console.', 'info')
            return render_template('forgot_password.html', email=email, step='verify_otp')
        
        elif otp_submitted and new_password and session.get('reset_email') == email:
            # Step 2: Verify OTP and Reset Password
            if session.get('reset_otp') == otp_submitted:
                conn = get_db_connection()
                try:
                    password_hash = generate_password_hash(new_password)
                    conn.execute(
                        "UPDATE users SET password_hash = ? WHERE email = ?",
                        (password_hash, email)
                    )
                    conn.commit()
                    flash('Password reset successful! You can now log in.', 'success')
                    session.pop('reset_otp', None)
                    session.pop('reset_email', None)
                    session.pop('otp_generated_time', None)
                    return redirect(url_for('index'))
                except Exception as e:
                    flash(f'Database error during password reset: {e}', 'error')
                finally:
                    conn.close()
            else:
                flash('Invalid or expired OTP. Please try again.', 'error')
                return render_template('forgot_password.html', email=email, step='verify_otp')

        else:
            flash('Invalid request for password reset.', 'error')
            
    return render_template('forgot_password.html', step='request_email')

# --- Dashboard and Admin Panel ---

@app.route('/dashboard')
@login_required()
def dashboard():
    """User-specific dashboard."""
    role = session.get('role')
    user_id = session.get('user_id')
    conn = get_db_connection()
    data = {}
    
    if role == 'admin':
        # Admin: Show counts and management links
        data['student_count'] = conn.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        data['teacher_count'] = conn.execute('SELECT COUNT(*) FROM teachers').fetchone()[0]
        data['subjects'] = get_subjects()
        data['classes'] = ['11th Science', '11th Commerce', '11th Arts', 
                           '12th Science', '12th Commerce', '12th Arts']
        data['streams'] = ['Science', 'Commerce', 'Arts']
        
    elif role == 'student':
        # Student: Show personal data and quick links
        student_data = conn.execute('SELECT * FROM students WHERE user_id = ?', (user_id,)).fetchone()
        data['student'] = student_data
        
    elif role == 'teacher':
        # Teacher: Show assigned subject and quick links
        teacher_data = conn.execute("""
            SELECT t.teacher_name, s.subject_name, s.stream 
            FROM teachers t 
            JOIN subjects s ON t.subject_id = s.id 
            WHERE t.user_id = ?
        """, (user_id,)).fetchone()
        data['teacher'] = teacher_data
    
    conn.close()
    
    return render_template('dashboard.html', role=role, data=data)

# --- Admin Functionality: Add Student/Teacher ---

@app.route('/add_student', methods=['POST'])
@login_required(role='admin')
def add_student():
    """Admin route to add a new student entry."""
    conn = get_db_connection()
    try:
        # Get data from form
        student_name = request.form['student_name']
        email = request.form['email']
        password = request.form['password']
        stream = request.form['stream']
        class_name = request.form['class_name']
        section = request.form['section']
        roll_number = request.form['roll_number']
        
        # Determine the full class/stream name for storage
        full_class_name = f"{class_name} {stream}"

        # 1. Create User account for the student
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'student')",
            (student_name, email, password_hash)
        )
        user_id = cursor.lastrowid
        
        # 2. Insert into students table
        cursor.execute(
            "INSERT INTO students (user_id, student_name, stream, class_name, section, roll_number) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, student_name, stream, full_class_name, section, roll_number)
        )
        conn.commit()
        flash(f'Student {student_name} added successfully.', 'success')

    except sqlite3.IntegrityError:
        flash('Email or Roll Number already exists.', 'error')
    except Exception as e:
        flash(f'Error adding student: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('dashboard'))

@app.route('/add_teacher', methods=['POST'])
@login_required(role='admin')
def add_teacher():
    """Admin route to add a new teacher entry."""
    conn = get_db_connection()
    try:
        # Get data from form
        teacher_name = request.form['teacher_name']
        email = request.form['email']
        password = request.form['password']
        subject_id = request.form['subject_id'] # ID of the subject they teach
        
        # 1. Create User account for the teacher
        cursor = conn.cursor()
        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'teacher')",
            (teacher_name, email, password_hash)
        )
        user_id = cursor.lastrowid
        
        # 2. Insert into teachers table
        cursor.execute(
            "INSERT INTO teachers (user_id, teacher_name, email, subject_id) VALUES (?, ?, ?, ?)",
            (user_id, teacher_name, email, subject_id)
        )
        conn.commit()
        flash(f'Teacher {teacher_name} added successfully.', 'success')

    except sqlite3.IntegrityError:
        flash('Email address already exists for a user or teacher.', 'error')
    except Exception as e:
        flash(f'Error adding teacher: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('dashboard'))

# --- Marks Management ---

@app.route('/marks')
@login_required()
def marks_page():
    """Displays marks data for students/teachers/admin."""
    role = session.get('role')
    user_id = session.get('user_id')
    conn = get_db_connection()
    data = {'students': []}
    
    if role == 'admin' or role == 'teacher':
        # Get list of all students for selection/management
        data['students'] = conn.execute('SELECT id, student_name, class_name, section, roll_number, stream FROM students ORDER BY class_name, section, student_name').fetchall()
        data['subjects'] = get_subjects()
        
    elif role == 'student':
        # Student views their own marks
        student = conn.execute('SELECT id FROM students WHERE user_id = ?', (user_id,)).fetchone()
        if student:
            data['student_id'] = student['id']
            # Fetch marks for the current student
            marks_query = """
                SELECT s.subject_name, m.marks_obtained, m.total_marks
                FROM marks m
                JOIN subjects s ON m.subject_id = s.id
                WHERE m.student_id = ?
            """
            data['marks'] = conn.execute(marks_query, (student['id'],)).fetchall()
            
            # Calculate total percentage for the student
            total_obtained = sum(m['marks_obtained'] for m in data['marks'])
            total_possible = sum(m['total_marks'] for m in data['marks'])
            data['percentage'] = (total_obtained / total_possible) * 100 if total_possible > 0 else 0
        else:
            flash('Your student profile is incomplete. Please contact the administrator.', 'error')
    
    conn.close()
    return render_template('marks.html', role=role, data=data)

@app.route('/add_marks', methods=['POST'])
@login_required(role='admin') # Teacher role could also be added here, but sticking to admin for simplicity
def add_marks():
    """Admin route to add or update marks for a student/subject."""
    student_id = request.form['student_id']
    subject_id = request.form['subject_id']
    marks_obtained = request.form['marks_obtained']
    
    conn = get_db_connection()
    try:
        # Use INSERT OR REPLACE to handle both insert (new) and update (existing)
        conn.execute("""
            INSERT OR REPLACE INTO marks 
            (student_id, subject_id, marks_obtained, total_marks) 
            VALUES (?, ?, ?, 100)
        """, (student_id, subject_id, marks_obtained))
        conn.commit()
        flash('Marks updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating marks: {e}', 'error')
    finally:
        conn.close()
        
    return redirect(url_for('marks_page'))

@app.route('/get_student_marks/<int:student_id>')
@login_required()
def get_student_marks(student_id):
    """AJAX endpoint to fetch a single student's marks (used for table rendering)."""
    conn = get_db_connection()
    
    # Check if the user is authorized (admin, teacher, or the student themselves)
    role = session.get('role')
    authorized = (role in ['admin', 'teacher'])
    if role == 'student':
        student_user_id = conn.execute('SELECT user_id FROM students WHERE id = ?', (student_id,)).fetchone()
        if student_user_id and student_user_id['user_id'] == session.get('user_id'):
            authorized = True
    
    if not authorized:
        conn.close()
        return {'error': 'Unauthorized access'}, 403

    marks_query = """
        SELECT s.subject_name, m.marks_obtained, m.total_marks
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ?
    """
    marks = conn.execute(marks_query, (student_id,)).fetchall()
    conn.close()
    
    # Calculate percentage
    total_obtained = sum(m['marks_obtained'] for m in marks)
    total_possible = sum(m['total_marks'] for m in marks)
    percentage = (total_obtained / total_possible) * 100 if total_possible > 0 else 0
    
    # Format the data for JSON response
    marks_list = [{
        'subject_name': m['subject_name'],
        'marks_obtained': m['marks_obtained'],
        'total_marks': m['total_marks']
    } for m in marks]
    
    return {'marks': marks_list, 'percentage': f"{percentage:.2f}"}

@app.route('/download_marks/<int:student_id>')
@login_required()
def download_marks(student_id):
    """Downloads marks for a specific student as a CSV file."""
    conn = get_db_connection()
    
    # Authorization check (same as get_student_marks)
    role = session.get('role')
    authorized = (role in ['admin', 'teacher'])
    student_name = "Student"
    
    student_record = conn.execute('SELECT student_name, user_id FROM students WHERE id = ?', (student_id,)).fetchone()
    
    if student_record:
        student_name = student_record['student_name'].replace(' ', '_')
        if role == 'student' and student_record['user_id'] == session.get('user_id'):
            authorized = True
        elif role in ['admin', 'teacher']:
            authorized = True
    
    if not authorized:
        conn.close()
        return 'Unauthorized access', 403

    marks_query = """
        SELECT s.subject_name, m.marks_obtained, m.total_marks
        FROM marks m
        JOIN subjects s ON m.subject_id = s.id
        WHERE m.student_id = ?
    """
    marks = conn.execute(marks_query, (student_id,)).fetchall()
    conn.close()

    if not marks:
        return 'No marks data found for this student.', 404

    # Calculate percentage
    total_obtained = sum(m['marks_obtained'] for m in marks)
    total_possible = sum(m['total_marks'] for m in marks)
    percentage = (total_obtained / total_possible) * 100 if total_possible > 0 else 0
    
    # Create CSV content
    si = StringIO()
    cw = csv.writer(si)

    # Write headers
    cw.writerow(['Subject', 'Marks Obtained', 'Total Marks', 'Percentage (Overall)'])
    
    # Write marks data
    for m in marks:
        cw.writerow([m['subject_name'], m['marks_obtained'], m['total_marks'], ''])
    
    # Write overall percentage
    cw.writerow(['', '', 'Total Percentage:', f'{percentage:.2f}%'])

    output = si.getvalue()
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={student_name}_Marks_Report.csv"}
    )

# --- Chatbot Route ---

@app.route('/chatbot')
@login_required()
def chatbot_page():
    """Chatbot interface page."""
    # Pass the API key securely to the template (for simplicity in this single-file setup)
    return render_template('chatbot.html', gemini_api_key=GEMINI_API_KEY)


if __name__ == '__main__':
    # Initialize the database if it doesn't exist (it should be run by user first)
    if not is_database_initialized():
        print("Please run 'python database_setup.py' first.")
    else:
        app.run(debug=True)