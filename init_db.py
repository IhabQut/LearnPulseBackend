import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine
import models
import schemas
import crud

def init_db():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # ─── Users ──────────────────────────────────────────────────
    crud.create_user(db, schemas.UserBase(id="u1", name="Sara", role="student", points=120))
    crud.create_user(db, schemas.UserBase(id="u2", name="Ahmad", role="student", points=110))
    crud.create_user(db, schemas.UserBase(id="u3", name="Lina", role="student", points=95))
    crud.create_user(db, schemas.UserBase(id="u4", name="Omar", role="student", points=30))
    crud.create_user(db, schemas.UserBase(id="p1", name="Prof. Smith", role="professor", points=0))

    # Update professor profile
    prof = db.query(models.User).filter(models.User.id == "p1").first()
    prof.bio = "Professor of Computer Science with 15 years of experience in database systems and software engineering."
    prof.office_hours = json.dumps([
        {"day": "Monday", "time": "10:00 AM - 12:00 PM"},
        {"day": "Wednesday", "time": "2:00 PM - 4:00 PM"}
    ])
    prof.meeting_link = "https://zoom.us/j/123456789"
    db.commit()

    # ─── Course ─────────────────────────────────────────────────
    course = models.Course(id="c1", title="Database Fundamentals", description="Learn the core concepts of relational databases, SQL, and database design.", professor_id="p1")
    db.add(course)
    db.commit()

    # ─── Materials ──────────────────────────────────────────────
    db.add(models.Material(id="m1", name="Syllabus.pdf", type="PDF", url="#", course_id="c1"))
    db.add(models.Material(id="m2", name="Lecture 1 Slides", type="Slides", url="#", course_id="c1"))

    # ─── Enrollments ────────────────────────────────────────────
    crud.enroll_student_directly(db, "u1", "c1")
    crud.enroll_student_directly(db, "u2", "c1")
    crud.enroll_student_directly(db, "u3", "c1")
    # u4 has a pending request
    crud.request_enrollment(db, "u4", "c1")

    # ─── Chapters ───────────────────────────────────────────────
    ch1 = models.Chapter(id="ch1", title="Chapter 1: Intro to Databases", summary="Key concepts: What is a DB, DBMS Architecture, Relational Model.", course_id="c1")
    ch2 = models.Chapter(id="ch2", title="Chapter 2: SQL Basics", summary="Key concepts: SELECT, INSERT, UPDATE, DELETE.", course_id="c1")
    db.add(ch1)
    db.add(ch2)
    db.commit()

    # ─── Topics ─────────────────────────────────────────────────
    db.add(models.Topic(id="t1", title="What is a Database", description="Basic definition and use cases.", chapter_id="ch1", order=0))
    db.add(models.Topic(id="t2", title="DBMS Architecture", description="1-tier, 2-tier, and 3-tier architecture.", chapter_id="ch1", order=1))
    db.add(models.Topic(id="t3", title="Relational Model", description="Tables, rows, and columns.", chapter_id="ch1", order=2))
    db.add(models.Topic(id="t4", title="SELECT statements", description="Querying data.", chapter_id="ch2", order=0))
    db.commit()

    # Mark one topic completed
    crud.mark_topic_completed(db, user_id="u1", topic_id="t1")

    # ─── Discussions ────────────────────────────────────────────
    crud.create_discussion(db, schemas.DiscussionBase(
        id="d1", author="Ahmad", author_id="u2", title="Error in installing MySQL",
        content="I am getting a connection refused error when trying to start the MySQL service. Any ideas?",
        date="2 hours ago", course_id="c1", chapter_id=None
    ))
    crud.create_discussion(db, schemas.DiscussionBase(
        id="d2", author="Lina", author_id="u3", title="Chapter 1 Quiz difficulty",
        content="I found the questions about DBMS architecture really confusing. Can someone explain the 3-tier model again?",
        date="1 day ago", course_id="c1", chapter_id="ch1"
    ))

    # ─── Quizzes ────────────────────────────────────────────────

    # Topic 1 Quiz
    quiz_t1 = models.Quiz(id="quiz_t1", title="What is a Database Quiz", quiz_type="topic", topic_id="t1")
    db.add(quiz_t1)
    db.commit()
    db.add(models.QuizQuestion(id="qq1", quiz_id="quiz_t1", question="What is a database?",
        options=json.dumps(["A collection of organized data", "A programming language", "A web browser", "An operating system"]),
        correct_option=0, explanation="A database is a structured collection of organized data."))
    db.add(models.QuizQuestion(id="qq2", quiz_id="quiz_t1", question="Which of these is a benefit of using a database?",
        options=json.dumps(["Data redundancy", "Data consistency", "Data loss", "Slower access"]),
        correct_option=1, explanation="Databases help ensure data consistency and reduce redundancy."))

    # Topic 2 Quiz
    quiz_t2 = models.Quiz(id="quiz_t2", title="DBMS Architecture Quiz", quiz_type="topic", topic_id="t2")
    db.add(quiz_t2)
    db.commit()
    db.add(models.QuizQuestion(id="qq3", quiz_id="quiz_t2", question="Which architecture tier contains the database itself?",
        options=json.dumps(["1-Tier", "2-Tier", "3-Tier", "N-Tier"]),
        correct_option=0, explanation="In a 1-tier architecture, the database and the application reside on the same machine."))
    db.add(models.QuizQuestion(id="qq4", quiz_id="quiz_t2", question="What does DBMS stand for?",
        options=json.dumps(["Data Base Management System", "Document Based Management System", "Data Binding Management System", "Distributed Base Management System"]),
        correct_option=0, explanation="DBMS stands for Data Base Management System."))

    # Topic 3 Quiz
    quiz_t3 = models.Quiz(id="quiz_t3", title="Relational Model Quiz", quiz_type="topic", topic_id="t3")
    db.add(quiz_t3)
    db.commit()
    db.add(models.QuizQuestion(id="qq5", quiz_id="quiz_t3", question="Which is NOT a characteristic of the Relational Model?",
        options=json.dumps(["Data is stored in tables", "Tables are connected by foreign keys", "Data is stored in JSON documents", "Every row is uniquely identified by a primary key"]),
        correct_option=2, explanation="Storing data in JSON documents is a characteristic of NoSQL Document databases, not the Relational Model."))

    # Topic 4 Quiz
    quiz_t4 = models.Quiz(id="quiz_t4", title="SELECT Statements Quiz", quiz_type="topic", topic_id="t4")
    db.add(quiz_t4)
    db.commit()
    db.add(models.QuizQuestion(id="qq6", quiz_id="quiz_t4", question="What SQL keyword is used to retrieve data from a table?",
        options=json.dumps(["INSERT", "UPDATE", "SELECT", "DELETE"]),
        correct_option=2, explanation="SELECT is used to query and retrieve data from database tables."))

    # Chapter 1 Final Quiz
    quiz_ch1 = models.Quiz(id="quiz_ch1", title="Chapter 1 Final Quiz", quiz_type="chapter", chapter_id="ch1")
    db.add(quiz_ch1)
    db.commit()
    db.add(models.QuizQuestion(id="qq7", quiz_id="quiz_ch1", question="What is a database?",
        options=json.dumps(["A collection of organized data", "A programming language", "A web browser", "An operating system"]),
        correct_option=0, explanation="A database is a structured collection of organized data."))
    db.add(models.QuizQuestion(id="qq8", quiz_id="quiz_ch1", question="What does DBMS stand for?",
        options=json.dumps(["Data Base Management System", "Document Based Management System", "Data Binding Management System", "Distributed Base Management System"]),
        correct_option=0, explanation="DBMS stands for Data Base Management System."))
    db.add(models.QuizQuestion(id="qq9", quiz_id="quiz_ch1", question="Which is NOT part of the Relational Model?",
        options=json.dumps(["Tables", "Rows", "JSON Documents", "Columns"]),
        correct_option=2, explanation="JSON Documents are not part of the Relational Model."))

    # Chapter 2 Final Quiz
    quiz_ch2 = models.Quiz(id="quiz_ch2", title="Chapter 2 Final Quiz", quiz_type="chapter", chapter_id="ch2")
    db.add(quiz_ch2)
    db.commit()
    db.add(models.QuizQuestion(id="qq10", quiz_id="quiz_ch2", question="What SQL keyword retrieves data from a table?",
        options=json.dumps(["INSERT", "SELECT", "DROP", "ALTER"]),
        correct_option=1, explanation="SELECT is used to query data from tables."))

    # ─── Sample Quiz Attempts (for AI analysis) ────────────────
    import uuid
    # Ahmad (u2) got some questions wrong on DBMS Architecture
    db.add(models.QuizAttempt(id=str(uuid.uuid4()), user_id="u2", quiz_id="quiz_t2", score=0, total=2, date="3 days ago", is_first_attempt=True))
    # Lina (u3) also struggled on DBMS Architecture
    db.add(models.QuizAttempt(id=str(uuid.uuid4()), user_id="u3", quiz_id="quiz_t2", score=1, total=2, date="2 days ago", is_first_attempt=True))
    # Sara (u1) aced everything
    db.add(models.QuizAttempt(id=str(uuid.uuid4()), user_id="u1", quiz_id="quiz_t1", score=2, total=2, date="4 days ago", is_first_attempt=True))
    db.add(models.QuizAttempt(id=str(uuid.uuid4()), user_id="u1", quiz_id="quiz_t2", score=2, total=2, date="3 days ago", is_first_attempt=True))

    db.commit()
    db.close()
    print("Database initialized with mock data, enrollments, and quiz attempts!")

if __name__ == "__main__":
    init_db()
