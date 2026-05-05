import sqlite3
import uuid
import os
import datetime
from security import hash_password

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "learnpulse.db")

def seed():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}. Please run create schema first.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("--- SEEDING COMPREHENSIVE TEST DATA ---")

    # 1. Clear existing data to avoid primary key conflicts if re-seeding
    tables = [
        "users", "professors", "students", "user_office_hours", "courses", 
        "materials", "chapters", "topics", "topic_completions", "discussions", 
        "replies", "discussion_votes", "reply_votes", "quizzes", "quiz_questions", 
        "quiz_options", "quiz_attempts", "enrollments", "meeting_requests", 
        "notifications", "course_textbooks", "grading_components", "semester_weeks"
    ]
    for table in tables:
        c.execute(f"DELETE FROM {table}")
    
    hashed_pw = hash_password("password123")

    # 2. Users (Professors and Students)
    # IDs: prof_1, prof_2, student_1, student_2
    users = [
        ("prof_1", "Dr.Rushdi hamamreh", "professor", "rushdi@univ.edu", hashed_pw, "+1-555-0101", "Expert in Database Systems and Big Data architecture."),
        ("student_1", "ihab qutmera", "student", "ihab@student.edu", hashed_pw, "+1-555-0201", "Aspiring Data Scientist, currently in her junior year."),
        ("student_2", "noor tamimi", "student", "noor@student.edu", hashed_pw, "+1-555-0202", "Senior Software Engineering student focusing on cloud native apps."),
    ]
    c.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?)", users)

    # 3. Professor Profiles
    prof_profiles = [
        ("prof_1", "Computer Science", "Database Systems", "Associate Professor", "Engineering Bldg, Room 304", "https://zoom.us/rushdi", 1, 1),
    ]
    c.executemany("INSERT INTO professors VALUES (?,?,?,?,?,?,?,?)", prof_profiles)

    # 4. Student Profiles
    student_profiles = [
        ("student_1", "Data Science", "Undergraduate", 3.9, 2026),
        ("student_2", "Software Engineering", "Undergraduate", 3.7, 2025),
    ]
    c.executemany("INSERT INTO students VALUES (?,?,?,?,?)", student_profiles)

    # 5. Office Hours
    office_hours = [
        (str(uuid.uuid4()), "prof_1", "Monday", "10:00 AM - 12:00 PM"),
        (str(uuid.uuid4()), "prof_1", "Wednesday", "2:00 PM - 4:00 PM"),
    ]
    c.executemany("INSERT INTO user_office_hours VALUES (?,?,?,?)", office_hours)

    # 6. Courses
    courses = [
        ("course_db", "Advanced Database Systems", "Deep dive into SQL, NoSQL, and query optimization.", "Computer Science", "https://images.unsplash.com/photo-1544383335-c533c44eba31", "prof_1", 1),
    ]
    c.executemany("INSERT INTO courses VALUES (?,?,?,?,?,?,?)", courses)

    # 7. Enrollments
    # Status: 'approved', Role: 'owner', 'instructor', 'student', 'viewer'
    enrollments = [
        ("en_1", "prof_1", "course_db", "approved", "owner", "2024-01-01", 0),
        ("en_2", "student_1", "course_db", "approved", "student", "2024-01-05", 150),
        ("en_3", "student_2", "course_db", "approved", "student", "2024-01-06", 80),
    ]
    c.executemany("INSERT INTO enrollments VALUES (?,?,?,?,?,?,?)", enrollments)

    # 8. Content Hierarchy (Chapters -> Topics)
    # DB Course
    chapters_db = [
        ("ch_db_1", "Query Processing", "Understanding how engines execute SQL.", "course_db", 0),
        ("ch_db_2", "Transaction Management", "ACID properties and concurrency control.", "course_db", 0)
    ]
    c.executemany("INSERT INTO chapters VALUES (?,?,?,?,?)", chapters_db)

    topics_db = [
        ("top_db_1", "Parsing and Translation", "Converting SQL to relational algebra.", "ch_db_1", 1, 1),
        ("top_db_2", "Optimization", "Cost-based optimization strategies.", "ch_db_1", 2, 0),
        ("top_db_3", "Locking Protocols", "Two-phase locking and deadlocks.", "ch_db_2", 1, 0)
    ]
    c.executemany("INSERT INTO topics VALUES (?,?,?,?,?,?)", topics_db)

    # 9. Topic Completions
    completions = [
        ("student_1", "top_db_1"),
        ("student_1", "top_db_2"),
        ("student_2", "top_db_1")
    ]
    c.executemany("INSERT INTO topic_completions VALUES (?,?)", completions)

    # 10. Materials
    materials = [
        ("mat_1", "Syllabus_DB.pdf", "pdf", "#", "course_db"),
        ("mat_2", "Lecture_Notes_1.docx", "docx", "#", "course_db"),
        ("mat_3", "AI_Fundamentals_Slides.pptx", "slides", "#", "course_ai")
    ]
    c.executemany("INSERT INTO materials VALUES (?,?,?,?,?)", materials)

    # 11. Discussions and Replies
    discussions = [
        ("disc_1", "ihab qutmera", "student_1", "Locking vs Versioning", "When should we use MVCC instead of strict 2PL?", "2024-04-30 10:00", "course_db", "ch_db_2", "top_db_3"),
        ("disc_2", "noor tamimi", "student_2", "Cost Estimation", "How does the optimizer handle skewed data distribution?", "2024-04-30 11:30", "course_db", "ch_db_1", "top_db_2")
    ]
    c.executemany("INSERT INTO discussions VALUES (?,?,?,?,?,?,?,?,?)", discussions)

    replies = [
        ("rep_1", "Dr. Rushdi hamamreh", "prof_1", "Great question! MVCC is preferred in read-heavy systems as it prevents readers from blocking writers.", "2024-04-30 10:45", "professor", "disc_1"),
        ("rep_2", "ihab qutmera", "student_1", "Thanks Prof! That makes sense for Postgres especially.", "2024-04-30 11:00", "student", "disc_1")
    ]
    c.executemany("INSERT INTO replies VALUES (?,?,?,?,?,?,?)", replies)

    # 12. Quizzes, Questions, Options
    # Quiz 1: DB Optimization
    c.execute("INSERT INTO quizzes VALUES (?,?,?,?,?)", ("qz_db_1", "Database Optimization Quiz", "topic", "top_db_2", None))
    
    questions_db = [
        ("qq_db_1", "qz_db_1", "What is the primary factor in cost-based optimization?", "I/O and CPU are both considered."),
        ("qq_db_2", "qz_db_1", "Which index type is best for range queries?", "B+ Trees maintain order.")
    ]
    c.executemany("INSERT INTO quiz_questions VALUES (?,?,?,?)", questions_db)

    options_db = [
        (str(uuid.uuid4()), "qq_db_1", "Disk I/O", 1),
        (str(uuid.uuid4()), "qq_db_1", "Number of columns", 0),
        (str(uuid.uuid4()), "qq_db_1", "Table name length", 0),
        (str(uuid.uuid4()), "qq_db_2", "Hash Index", 0),
        (str(uuid.uuid4()), "qq_db_2", "B+ Tree Index", 1),
        (str(uuid.uuid4()), "qq_db_2", "Linear List", 0)
    ]
    c.executemany("INSERT INTO quiz_options VALUES (?,?,?,?)", options_db)

    # 13. Quiz Attempts
    attempts = [
        ("att_1", "student_1", "qz_db_1", 2, 2, "2024-04-29", 1, 10),
        ("att_2", "student_2", "qz_db_1", 1, 2, "2024-04-29", 1, 5)
    ]
    c.executemany("INSERT INTO quiz_attempts VALUES (?,?,?,?,?,?,?,?)", attempts)

    # 14. Meeting Requests
    meetings = [
        ("meet_1", "student_1", "prof_1", "Need help with indexing concepts.", "Monday 10:30 AM", "In-person", "approved", "2024-04-30"),
        ("meet_2", "student_2", "prof_1", "Discussion about the final project.", "Wednesday 2:15 PM", "Zoom", "pending", "2024-04-30")
    ]
    c.executemany("INSERT INTO meeting_requests VALUES (?,?,?,?,?,?,?,?)", meetings)

    # 15. Notifications
    notifs = [
        ("not_1", "student_1", "Welcome to DB Course", "You have been successfully enrolled.", "success", 0, "2024-04-30"),
        ("not_2", "student_1", "Meeting Approved", "Dr. Sarah Miller approved your meeting request.", "info", 0, "2024-04-30"),
        ("not_3", "prof_1", "New Discussion Post", "Amina Al-Farsi posted in 'Advanced Database Systems'.", "info", 0, "2024-04-30")
    ]
    c.executemany("INSERT INTO notifications VALUES (?,?,?,?,?,?,?)", notifs)

    # 16. AI Course Builder Data (Textbooks, Grading, Semester Weeks)
    textbooks = [
        ("txt_1", "course_db", "Database_System_Concepts_7th_Ed.pdf", "pdf", "done"),
        ("txt_2", "course_ai", "AI_Modern_Approach.txt", "txt", "done")
    ]
    c.executemany("INSERT INTO course_textbooks VALUES (?,?,?,?,?)", textbooks)

    grading = [
        ("gr_1", "course_db", "Quizzes", 30.0, "assessment"),
        ("gr_2", "course_db", "Final Exam", 50.0, "exam"),
        ("gr_3", "course_db", "Participation", 20.0, "other")
    ]
    c.executemany("INSERT INTO grading_components VALUES (?,?,?,?,?)", grading)

    weeks = [
        ("wk_1", "course_db", 1, "Introduction and Query Processing", '["SQL Basics", "Query Trees", "Parsing"]', "Read Chapter 1 before class."),
        ("wk_2", "course_db", 2, "Optimization and Indexing", '["B+ Trees", "Cost Estimation", "Plan selection"]', "Lab 1 due on Friday.")
    ]
    c.executemany("INSERT INTO semester_weeks VALUES (?,?,?,?,?,?)", weeks)

    conn.commit()
    conn.close()
    print("--- SEEDING COMPLETE: Database populated with realistic test data ---")

if __name__ == "__main__":
    seed()
