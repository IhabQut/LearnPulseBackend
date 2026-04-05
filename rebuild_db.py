"""
LearnPulse REBUILD_DB - Single Source of Truth
Drops all tables, creates the fresh 3-tier user schema, and seeds realistic data.
Includes specialized fields: Phone, GPA, Major, Expertise, Department.
"""
import sqlite3
import uuid
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learnpulse.db")

def rebuild():
    # Remove old DB if exists for a truly clean slate
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Deleted old database file.")
        except Exception as e:
            print(f"Warning: Could not delete DB file ({e}). Proceeding with DROP TABLE.")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    
    # ─── Schema Creation ───────────────────────────────────────
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            email TEXT DEFAULT '',
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
            points INTEGER DEFAULT 0,
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
            owner_id TEXT REFERENCES users(id),
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
            course_id TEXT REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS topics (
            id TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
            "order" INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS topic_completions (
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
            PRIMARY KEY (user_id, topic_id)
        );
        CREATE TABLE IF NOT EXISTS discussions (
            id TEXT PRIMARY KEY,
            author TEXT,
            author_id TEXT REFERENCES users(id),
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
            author_id TEXT REFERENCES users(id),
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
            is_first_attempt BOOLEAN DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
            status TEXT DEFAULT 'pending',
            role TEXT DEFAULT 'student',
            date TEXT
        );
        CREATE TABLE IF NOT EXISTS meeting_requests (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id),
            professor_id TEXT REFERENCES professors(id),
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
    """)
    print("All tables created with fresh 3-tier User/Student/Professor schema.")
    
    # ─── Seed Data ─────────────────────────────────────────────
    # Professors
    profs = [
        ("p1", "Prof. Sarah Miller", "professor", "s.miller@univ.edu", "+1-555-0101", "Focused on relational algebra and database optimization."),
        ("p2", "Dr. James Chen", "professor", "j.chen@univ.edu", "+1-555-0102", "Artificial Intelligence and Machine Learning researcher.")
    ]
    c.executemany("INSERT INTO users (id, name, role, email, phone_number, bio) VALUES (?,?,?,?,?,?)", profs)
    
    c.execute("INSERT INTO professors VALUES ('p1', 'Computer Science', 'Database Systems', 'Associate Professor', 'Room 304, Engineering Bldg', 'https://zoom.us/prof-miller', 1, 1)")
    c.execute("INSERT INTO professors VALUES ('p2', 'AI & Robotics', 'Deep Learning', 'Senior Lecturer', 'Room 412, Tech Hub', 'https://zoom.us/dr-chen', 1, 0)")
    
    c.execute("INSERT INTO user_office_hours VALUES ('oh1','p1','Monday','10:00 AM - 12:00 PM')")
    c.execute("INSERT INTO user_office_hours VALUES ('oh2','p1','Wednesday','2:00 PM - 4:00 PM')")
    c.execute("INSERT INTO user_office_hours VALUES ('oh3','p2','Tuesday','1:00 PM - 3:00 PM')")
    
    # Students
    students = [
        ("u1", "Amina Al-Farsi", "student", "amina.af@student.edu", "+1-555-0201", "Aspiring Data Scientist and avid learner."),
        ("u2", "Lucas Dubois", "student", "lucas.d@student.edu", "+1-555-0202", "Senior student specializing in Software Architecture.")
    ]
    c.executemany("INSERT INTO users (id, name, role, email, phone_number, bio) VALUES (?,?,?,?,?,?)", students)
    
    c.execute("INSERT INTO students VALUES ('u1', 450, 'Computer Science', 'Undergraduate', 3.8, 2027)")
    c.execute("INSERT INTO students VALUES ('u2', 320, 'Software Engineering', 'Undergraduate', 3.5, 2026)")
    
    # Courses
    c.execute("INSERT INTO courses VALUES ('c1','Advanced Database Design','Detailed exploration of SQL internals, NoSQL variations, and high-level indexing.','p1',1)")
    c.execute("INSERT INTO materials VALUES ('m1','Course_Syllabus.pdf','PDF','#','c1')")
    c.execute("INSERT INTO materials VALUES ('m2','Intro_to_SQL_Slides','Slides','#','c1')")
    
    # Enrollments with Roles
    c.execute("INSERT INTO enrollments VALUES (?, 'p1', 'c1', 'approved', 'owner', '2026-03-01')", (str(uuid.uuid4()),))
    c.execute("INSERT INTO enrollments VALUES (?, 'u1', 'c1', 'approved', 'student', '2026-03-01')", (str(uuid.uuid4()),))
    c.execute("INSERT INTO enrollments VALUES (?, 'u2', 'c1', 'approved', 'student', '2026-03-05')", (str(uuid.uuid4()),))
    c.execute("INSERT INTO enrollments VALUES (?, 'p2', 'c1', 'approved', 'viewer', '2026-03-10')", (str(uuid.uuid4()),))
    
    # Content Hierarchy
    c.execute("INSERT INTO chapters VALUES ('ch1','Chapter 1: Query Execution','Understand how SQL queries are parsed, optimized, and executed by the engine.','c1')")
    c.execute("INSERT INTO topics VALUES ('t1','Algebraic Optimization','Transforming SQL into relational algebra for performance.','ch1',0)")
    c.execute("INSERT INTO topics VALUES ('t2','Index Structures','B+ Trees vs Hash Indexes.','ch1',1)")
    
    c.execute("INSERT INTO topic_completions VALUES ('u1','t1')")
    
    # Discussions
    c.execute("INSERT INTO discussions VALUES ('d1','Amina Al-Farsi','u1','Index Performance Question','When should I prefer a Hash index over a B+ Tree?','2 hours ago','c1',NULL,NULL)")
    c.execute("INSERT INTO replies VALUES ('r1','Prof. Sarah Miller','p1','Hash indexes are faster for point lookups (key=val), but B+ Trees are essential for range queries (key > val).','1 hour ago','professor','d1')")
    
    # Quizzes
    def add_quiz(qz_id, title, qtype, topic_id, chapter_id):
        c.execute("INSERT INTO quizzes VALUES (?,?,?,?,?)", (qz_id, title, qtype, topic_id, chapter_id))
    def add_question(q_id, quiz_id, question, explanation, options, correct_idx):
        c.execute("INSERT INTO quiz_questions VALUES (?,?,?,?)", (q_id, quiz_id, question, explanation))
        for idx, text in enumerate(options):
            c.execute("INSERT INTO quiz_options VALUES (?,?,?,?)", (str(uuid.uuid4()), q_id, text, 1 if idx == correct_idx else 0))
    
    add_quiz("quiz1", "Optimization Basics", "topic", "t1", None)
    add_question("qq1", "quiz1", "What is the primary goal of algebraic optimization?", "Efficiency and speed.", ["Minimize table size", "Improve query performance", "Add more columns", "Secure the data"], 1)
    
    conn.commit()
    conn.close()
    print("Database REBUILD complete. Realistic seed data injected.")
    print("  -> Primary maintenance file: rebuild_db.py")

if __name__ == "__main__":
    rebuild()
