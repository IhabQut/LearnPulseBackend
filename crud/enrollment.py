from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid
import datetime

def request_enrollment(db: Session, user_id: str, course_id: str, role: str = "student"):
    existing = db.execute(text("SELECT * FROM enrollments WHERE user_id=:u AND course_id=:c"),
                          {"u": user_id, "c": course_id}).fetchone()
    if existing: return existing
    
    eid = f"e{uuid.uuid4().hex[:8]}"
    db.execute(text("INSERT INTO enrollments (id, user_id, course_id, status, role, date) VALUES (:id, :u, :c, 'pending', :r, :d)"),
               {"id": eid, "u": user_id, "c": course_id, "r": role, "d": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    db.commit()
    return db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": eid}).fetchone()

def approve_enrollment(db: Session, enrollment_id: str):
    db.execute(text("UPDATE enrollments SET status='approved' WHERE id=:id"), {"id": enrollment_id})
    db.commit()
    return db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": enrollment_id}).fetchone()

def enroll_student_directly(db: Session, user_id: str, course_id: str, role: str = "student"):
    existing = db.execute(text("SELECT * FROM enrollments WHERE user_id=:u AND course_id=:c"),
                          {"u": user_id, "c": course_id}).fetchone()
    if existing:
        db.execute(text("UPDATE enrollments SET status='approved', role=:r WHERE id=:id"), {"id": existing.id, "r": role})
        db.commit()
        return existing
    
    eid = f"e{uuid.uuid4().hex[:8]}"
    db.execute(text("INSERT INTO enrollments (id, user_id, course_id, status, role, date) VALUES (:id, :u, :c, 'approved', :r, :d)"),
               {"id": eid, "u": user_id, "c": course_id, "r": role, "d": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")})
    db.commit()
    return db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": eid}).fetchone()

def get_course_enrollments(db: Session, course_id: str, status: str = None):
    query = """
        SELECT e.id, e.user_id, e.course_id, e.status, e.role, e.date, u.name as user_name 
        FROM enrollments e
        LEFT JOIN users u ON e.user_id = u.id
        WHERE e.course_id=:c
    """
    params = {"c": course_id}
    if status:
        query += " AND e.status=:s"
        params["s"] = status
    return db.execute(text(query), params).fetchall()

def get_user_enrollments(db: Session, user_id: str):
    return db.execute(text("SELECT * FROM enrollments WHERE user_id=:u"), {"u": user_id}).fetchall()

def update_enrollment_role(db: Session, enrollment_id: str, role: str):
    db.execute(text("UPDATE enrollments SET role=:r WHERE id=:id"), {"id": enrollment_id, "r": role})
    db.commit()
    return db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": enrollment_id}).fetchone()
