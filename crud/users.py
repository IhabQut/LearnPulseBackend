from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import schemas
import models
import uuid
import json
import traceback


# ---------------------------------------------------------------------------
# Small focused helpers
# ---------------------------------------------------------------------------

def _fetch_professor_profile(db: Session, user_id: str) -> Optional[dict]:
    """Return professor-specific fields, including office hours."""
    prof = db.execute(
        text("SELECT * FROM professors WHERE id = :id"), {"id": user_id}
    ).fetchone()
    if not prof:
        return None

    office_hours = db.execute(
        text("SELECT day, time FROM user_office_hours WHERE professor_id = :id"),
        {"id": user_id}
    ).fetchall()

    result = dict(prof._mapping)
    result["office_hours"] = json.dumps([dict(oh._mapping) for oh in office_hours])
    return result


def _fetch_student_profile(db: Session, user_id: str) -> Optional[dict]:
    """Return student-specific fields."""
    stud = db.execute(
        text("SELECT * FROM students WHERE id = :id"), {"id": user_id}
    ).fetchone()
    return dict(stud._mapping) if stud else None


def _update_base_user(db: Session, user_id: str, data: schemas.ProfileUpdate):
    """Update the users table with any provided base fields."""
    updates, params = [], {"id": user_id}

    if data.name         is not None: updates.append("name = :name");               params["name"]  = data.name
    if data.email        is not None: updates.append("email = :email");             params["email"] = data.email
    if data.phone_number is not None: updates.append("phone_number = :phone");      params["phone"] = data.phone_number
    if data.bio          is not None: updates.append("bio = :bio");                 params["bio"]   = data.bio

    if updates:
        db.execute(text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id"), params)


def _update_professor(db: Session, user_id: str, data: schemas.ProfileUpdate):
    """Update professors table and rebuild office hours if provided."""
    updates, params = [], {"id": user_id}

    if data.department      is not None: updates.append("department = :dept");           params["dept"]  = data.department
    if data.expertise       is not None: updates.append("expertise = :exp");             params["exp"]   = data.expertise
    if data.academic_rank   is not None: updates.append("academic_rank = :rank");        params["rank"]  = data.academic_rank
    if data.office_location is not None: updates.append("office_location = :loc");       params["loc"]   = data.office_location
    if data.meeting_link    is not None: updates.append("meeting_link = :mlink");        params["mlink"] = data.meeting_link
    if data.zoom_enabled    is not None: updates.append("zoom_enabled = :zoom");         params["zoom"]  = data.zoom_enabled
    if data.in_person_enabled is not None: updates.append("in_person_enabled = :ip");    params["ip"]    = data.in_person_enabled

    if updates:
        db.execute(text(f"UPDATE professors SET {', '.join(updates)} WHERE id = :id"), params)

    if data.office_hours is not None:
        _replace_office_hours(db, user_id, data.office_hours)


def _replace_office_hours(db: Session, user_id: str, office_hours_json: str):
    """Delete and re-insert office hours from a JSON string."""
    db.execute(text("DELETE FROM user_office_hours WHERE professor_id = :id"), {"id": user_id})
    try:
        hours = json.loads(office_hours_json)
        for oh in hours:
            start, end = oh.get("start"), oh.get("end")
            time_val = f"{start} - {end}" if (start and end) else oh.get("time", "")
            db.execute(
                text("INSERT INTO user_office_hours (id, professor_id, day, time) VALUES (:uid, :id, :day, :time)"),
                {"uid": f"oh_{uuid.uuid4().hex[:8]}", "id": user_id, "day": oh.get("day", ""), "time": time_val}
            )
    except Exception:
        traceback.print_exc()


def _update_student(db: Session, user_id: str, data: schemas.ProfileUpdate):
    """Update students table with any provided student-specific fields."""
    updates, params = [], {"id": user_id}

    if data.major           is not None: updates.append("major = :major");           params["major"]  = data.major
    if data.level           is not None: updates.append("level = :level");           params["level"]  = data.level
    if data.graduation_year is not None: updates.append("graduation_year = :gyear"); params["gyear"]  = data.graduation_year

    if updates:
        db.execute(text(f"UPDATE students SET {', '.join(updates)} WHERE id = :id"), params)


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------

def get_user_by_email(db: Session, email: str) -> Optional[dict]:
    """Fetch user by email address."""
    user = db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": email.lower().strip()}
    ).fetchone()
    return dict(user._mapping) if user else None


def get_user(db: Session, user_id: str):
    """Fetch user with their role-specific profile attached."""
    user = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not user:
        return None

    result = dict(user._mapping)

    if user.role == "professor":
        prof = _fetch_professor_profile(db, user_id)
        if prof:
            result["professor"] = prof
    else:
        stud = _fetch_student_profile(db, user_id)
        if stud:
            result["student"] = stud

    return result


def create_user(db: Session, user_data: schemas.UserBase):
    """Create a user and their role-specific profile row."""
    db.execute(text(
        "INSERT INTO users (id, name, role, email, phone_number, bio) "
        "VALUES (:id, :name, :role, :email, :phone, :bio)"
    ), {
        "id":    user_data.id,
        "name":  user_data.name,
        "role":  user_data.role,
        "email": user_data.email or "",
        "phone": user_data.phone_number or "",
        "bio":   user_data.bio or "",
    })

    if user_data.role == "professor":
        db.execute(
            text("INSERT INTO professors (id, department, expertise, academic_rank) VALUES (:id, '', '', '')"),
            {"id": user_data.id}
        )
    else:
        db.execute(
            text("INSERT INTO students (id, major, level, gpa) VALUES (:id, '', 'Undergraduate', 0.0)"),
            {"id": user_data.id}
        )

    db.commit()
    return get_user(db, user_data.id)


def update_user_profile(db: Session, user_id: str, data: schemas.ProfileUpdate):
    """Update base and role-specific profile fields."""
    user = db.execute(text("SELECT role FROM users WHERE id = :id"), {"id": user_id}).fetchone()
    if not user:
        return None

    _update_base_user(db, user_id, data)

    if user.role == "professor":
        _update_professor(db, user_id, data)
    else:
        _update_student(db, user_id, data)

    db.commit()
    return get_user(db, user_id)


def award_course_points(db: Session, user_id: str, course_id: str, points: int):
    db.execute(
        text("UPDATE enrollments SET points = points + :p WHERE user_id = :u AND course_id = :c"),
        {"p": points, "u": user_id, "c": course_id}
    )
    db.commit()


def search_users(db: Session, query: str, role: str = "student"):
    rows = db.execute(
        text("SELECT * FROM users WHERE role = :role AND (name LIKE :q OR id LIKE :q)"),
        {"role": role, "q": f"%{query}%"}
    ).fetchall()
    return [dict(r._mapping) for r in rows]
