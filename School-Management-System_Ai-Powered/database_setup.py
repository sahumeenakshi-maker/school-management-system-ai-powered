import sqlite3
import os

DB_NAME = 'school_portal.db'

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def initialize_db():
    """Create all necessary tables and populate initial data."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()

            # --- 1. Users Table (For Login/Signup) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'teacher', 'student'))
                );
            """)

            # --- 2. Students Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    student_name TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    class_name TEXT NOT NULL,
                    section TEXT NOT NULL,
                    roll_number TEXT UNIQUE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );
            """)

            # --- 3. Teachers Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teachers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    teacher_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    subject_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (subject_id) REFERENCES subjects (id)
                );
            """)

            # --- 4. Subjects Table ---
            # Subjects are tied to streams for easy lookup
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subject_name TEXT NOT NULL,
                    stream TEXT NOT NULL
                );
            """)

            # --- 5. Marks Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS marks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    marks_obtained REAL NOT NULL,
                    total_marks INTEGER DEFAULT 100,
                    FOREIGN KEY (student_id) REFERENCES students (id),
                    FOREIGN KEY (subject_id) REFERENCES subjects (id),
                    UNIQUE(student_id, subject_id)
                );
            """)

            # --- Populate Streams, Classes, and Subjects (Required Structure) ---
            streams = ['Science', 'Commerce', 'Arts']
            classes = ['11th', '12th']
            sections = ['A', 'B']

            # Define subjects per stream
            subject_data = [
                ('Science', 'Physics'), ('Science', 'Chemistry'), ('Science', 'Biology'), 
                ('Science', 'Mathematics'), ('Science', 'Computer Science'), ('Science', 'English'),
                ('Commerce', 'Accountancy'), ('Commerce', 'Business Studies (BST)'), ('Commerce', 'Economics'),
                ('Commerce', 'Applied Mathematics'), ('Commerce', 'Computer Science'), ('Commerce', 'English'),
                ('Arts', 'History'), ('Arts', 'Geography'), ('Arts', 'Sociology'),
                ('Arts', 'Political Science'), ('Arts', 'Psychology'), ('Arts', 'English')
            ]

            # Insert Subjects
            for stream, subject in subject_data:
                cursor.execute("INSERT OR IGNORE INTO subjects (subject_name, stream) VALUES (?, ?)", (subject, stream))

            conn.commit()
            print(f"Database '{DB_NAME}' initialized successfully.")

        except sqlite3.Error as e:
            print(f"Error during database initialization: {e}")
        finally:
            if conn:
                conn.close()
    else:
        print("Could not establish a database connection.")

if __name__ == '__main__':
    # Remove old database file if it exists (for fresh setup)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Existing database '{DB_NAME}' removed.")

    initialize_db()
    print("Run 'python app.py' to start the application.")

# Note: All teacher/student/user data will be added via the 'Register' page
# or administrative panel created in 'app.py' after initial setup.