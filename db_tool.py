import sqlite3
import os
import sys
from seed_data import seed

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learnpulse.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT,
    role TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    phone_number TEXT DEFAULT '',
    bio TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS professors (
    id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    department TEXT DEFAULT '',
    expertise TEXT DEFAULT '',
    academic_rank TEXT DEFAULT '',
    office_location TEXT DEFAULT '',
    meeting_link TEXT DEFAULT '',
    zoom_enabled BOOLEAN DEFAULT 1,
    in_person_enabled BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    major TEXT DEFAULT '',
    level TEXT DEFAULT 'Undergraduate',
    gpa REAL DEFAULT 0.0,
    graduation_year INTEGER
);

CREATE TABLE IF NOT EXISTS user_office_hours (
    id TEXT PRIMARY KEY,
    professor_id TEXT REFERENCES professors(id) ON DELETE CASCADE,
    day TEXT,
    time TEXT
);

CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    category TEXT DEFAULT 'General',
    image TEXT DEFAULT '',
    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    is_open BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS materials (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    url TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chapters (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    is_final_quiz_open BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
    "order" INTEGER DEFAULT 0,
    is_open BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topic_completions (
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, topic_id)
);

CREATE TABLE IF NOT EXISTS discussions (
    id TEXT PRIMARY KEY,
    author TEXT,
    author_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    content TEXT,
    date TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE SET NULL,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE SET NULL,
    topic_id TEXT REFERENCES topics(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS replies (
    id TEXT PRIMARY KEY,
    author TEXT,
    author_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    text TEXT,
    date TEXT,
    role TEXT,
    discussion_id TEXT REFERENCES discussions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS discussion_votes (
    discussion_id TEXT REFERENCES discussions(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    vote_type INTEGER DEFAULT 0,
    PRIMARY KEY (discussion_id, user_id)
);

CREATE TABLE IF NOT EXISTS reply_votes (
    reply_id TEXT REFERENCES replies(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    vote_type INTEGER DEFAULT 0,
    PRIMARY KEY (reply_id, user_id)
);

CREATE TABLE IF NOT EXISTS quizzes (
    id TEXT PRIMARY KEY,
    title TEXT,
    quiz_type TEXT,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id TEXT PRIMARY KEY,
    quiz_id TEXT REFERENCES quizzes(id) ON DELETE CASCADE,
    question TEXT,
    explanation TEXT
);

CREATE TABLE IF NOT EXISTS quiz_options (
    id TEXT PRIMARY KEY,
    question_id TEXT REFERENCES quiz_questions(id) ON DELETE CASCADE,
    text TEXT,
    is_correct BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    quiz_id TEXT REFERENCES quizzes(id) ON DELETE CASCADE,
    score INTEGER,
    total INTEGER,
    date TEXT,
    is_first_attempt BOOLEAN DEFAULT 1,
    points_awarded INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrollments (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    role TEXT DEFAULT 'student',
    date TEXT,
    points INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meeting_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    professor_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    note TEXT,
    slot TEXT,
    meeting_type TEXT,
    status TEXT DEFAULT 'pending',
    date TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    message TEXT,
    type TEXT,
    is_read BOOLEAN DEFAULT 0,
    date TEXT
);

CREATE TABLE IF NOT EXISTS course_textbooks (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    filename TEXT,
    file_type TEXT,
    status TEXT DEFAULT 'done'
);

CREATE TABLE IF NOT EXISTS grading_components (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    name TEXT,
    weight REAL,
    component_type TEXT DEFAULT 'assessment'
);

CREATE TABLE IF NOT EXISTS semester_weeks (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    week_num INTEGER,
    chapter_title TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS semester_week_topics (
    id TEXT PRIMARY KEY,
    week_id TEXT REFERENCES semester_weeks(id) ON DELETE CASCADE,
    title TEXT
);

CREATE TABLE IF NOT EXISTS course_syllabi (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    course_code TEXT,
    semester TEXT,
    instructor_name TEXT,
    instructor_email TEXT,
    instructor_phone TEXT,
    office_hours TEXT,
    class_time_location TEXT,
    zoom_link TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS syllabus_objectives (
    id TEXT PRIMARY KEY,
    syllabus_id TEXT REFERENCES course_syllabi(id) ON DELETE CASCADE,
    text TEXT
);

CREATE TABLE IF NOT EXISTS syllabus_textbooks (
    id TEXT PRIMARY KEY,
    syllabus_id TEXT REFERENCES course_syllabi(id) ON DELETE CASCADE,
    title TEXT,
    author TEXT
);

CREATE TABLE IF NOT EXISTS syllabus_outcomes (
    id TEXT PRIMARY KEY,
    syllabus_id TEXT REFERENCES course_syllabi(id) ON DELETE CASCADE,
    text TEXT
);
"""

def drop_tables():
    print("Dropping all tables...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in c.fetchall()]
    for table in tables:
        c.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"  - {table} dropped.")
    conn.commit()
    conn.close()
    print("Done.")

def clear_data():
    print("Clearing all data from tables...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Get all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in c.fetchall()]
    for table in tables:
        c.execute(f"DELETE FROM {table}")
        print(f"  - {table} cleared.")
    conn.commit()
    conn.close()
    print("Done.")

def delete_db():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"Database file {DB_PATH} deleted.")
        except Exception as e:
            print(f"Error deleting database file: {e}")
    else:
        print("Database file does not exist.")

def create_schema():
    print("Creating database schema...")
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        print("Schema created successfully.")
    except Exception as e:
        print(f"Error creating schema: {e}")
    finally:
        conn.close()

def main_menu():
    print("\n--- LearnPulse Database Tool ---")
    print("1. Clear Data (Keep tables)")
    print("2. Delete Database (Remove file)")
    print("3. Create Schema (Raw SQL strings)")
    print("4. Full Seed (Inject test data)")
    print("5. Rebuild Everything (Delete -> Create -> Seed)")
    print("0. Exit")
    
    choice = input("\nSelect an option: ")
    
    if choice == '1':
        clear_data()
    elif choice == '2':
        delete_db()
    elif choice == '3':
        create_schema()
    elif choice == '4':
        seed()
    elif choice == '5':
        delete_db()
        create_schema()
        seed()
    elif choice == '0':
        sys.exit()
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "--clear":
            clear_data()
        elif cmd == "--delete":
            delete_db()
        elif cmd == "--create":
            create_schema()
        elif cmd == "--seed":
            seed()
        elif cmd == "--rebuild":
            drop_tables()
            create_schema()
            seed()
        elif cmd == "--drop":
            drop_tables()
        else:
            print(f"Unknown command: {cmd}")
    else:
        while True:
            main_menu()
