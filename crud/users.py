from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas
import models
import uuid
import json
from typing import List

def get_user(db: Session, user_id: str):
    """Fetch user with specialized profile based on role."""
    user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    if not user:
        return None
    
    # Convert to dictionary for easy manipulation
    res = dict(user._mapping)
    
    if user.role == 'professor':
        prof = db.execute(text("SELECT * FROM professors WHERE id=:id"), {"id": user_id}).fetchone()
        if prof:
            res['professor'] = dict(prof._mapping)
            # Office hours are on a separate table but linked to professor
            ohs = db.execute(text("SELECT day, time FROM user_office_hours WHERE professor_id=:id"), {"id": user_id}).fetchall()
            res['professor']['office_hours'] = json.dumps([dict(oh._mapping) for oh in ohs])
    else:
        stud = db.execute(text("SELECT * FROM students WHERE id=:id"), {"id": user_id}).fetchone()
        if stud:
            res['student'] = dict(stud._mapping)
            # Hoist points for easier frontend access
            res['points'] = stud.points
            
    return res

def create_user(db: Session, user_data: schemas.UserBase):
    """Create a user and their specialized profile."""
    # Insert base user
    db.execute(text(
        "INSERT INTO users (id, name, role, email, phone_number, bio) VALUES (:id, :name, :role, :email, :phone, :bio)"
    ), {
        "id": user_data.id, 
        "name": user_data.name, 
        "role": user_data.role, 
        "email": user_data.email or "",
        "phone": user_data.phone_number or "",
        "bio": user_data.bio or ""
    })
    
    # Insert specialized profile
    if user_data.role == 'professor':
        db.execute(text(
            "INSERT INTO professors (id, department, expertise, academic_rank) VALUES (:id, '', '', '')"
        ), {"id": user_data.id})
    else:
        db.execute(text(
            "INSERT INTO students (id, points, major, level, gpa) VALUES (:id, 0, '', 'Undergraduate', 0.0)"
        ), {"id": user_data.id})
        
    db.commit()
    return get_user(db, user_data.id)

def update_user_profile(db: Session, user_id: str, data: schemas.ProfileUpdate):
    """Update base and specialized profile fields."""
    user = db.execute(text("SELECT role FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    if not user:
        return None

    # Update base User table
    base_updates = []
    base_params = {"id": user_id}
    if data.name is not None:
        base_updates.append("name = :name"); base_params["name"] = data.name
    if data.email is not None:
        base_updates.append("email = :email"); base_params["email"] = data.email
    if data.phone_number is not None:
        base_updates.append("phone_number = :phone"); base_params["phone"] = data.phone_number
    if data.bio is not None:
        base_updates.append("bio = :bio"); base_params["bio"] = data.bio
        
    if base_updates:
        db.execute(text(f"UPDATE users SET {', '.join(base_updates)} WHERE id = :id"), base_params)

    # Update specialized table
    if user.role == 'professor':
        prof_updates = []
        prof_params = {"id": user_id}
        if data.department is not None:
            prof_updates.append("department = :dept"); prof_params["dept"] = data.department
        if data.expertise is not None:
            prof_updates.append("expertise = :exp"); prof_params["exp"] = data.expertise
        if data.academic_rank is not None:
            prof_updates.append("academic_rank = :rank"); prof_params["rank"] = data.academic_rank
        if data.office_location is not None:
            prof_updates.append("office_location = :loc"); prof_params["loc"] = data.office_location
        if data.meeting_link is not None:
            prof_updates.append("meeting_link = :mlink"); prof_params["mlink"] = data.meeting_link
        if data.zoom_enabled is not None:
            prof_updates.append("zoom_enabled = :zoom"); prof_params["zoom"] = data.zoom_enabled
        if data.in_person_enabled is not None:
            prof_updates.append("in_person_enabled = :ip"); prof_params["ip"] = data.in_person_enabled
            
        if prof_updates:
            db.execute(text(f"UPDATE professors SET {', '.join(prof_updates)} WHERE id = :id"), prof_params)
            
        if data.office_hours is not None:
            db.execute(text("DELETE FROM user_office_hours WHERE professor_id=:id"), {"id": user_id})
            try:
                ohs = json.loads(data.office_hours)
                for oh in ohs:
                    db.execute(text("INSERT INTO user_office_hours (id, professor_id, day, time) VALUES (:uid, :id, :day, :time)"),
                               {"uid": f"oh_{uuid.uuid4().hex[:8]}", "id": user_id, "day": oh.get("day", ""), "time": oh.get("time", "")})
            except:
                pass
    else:
        stud_updates = []
        stud_params = {"id": user_id}
        if data.major is not None:
            stud_updates.append("major = :major"); stud_params["major"] = data.major
        if data.level is not None:
            stud_updates.append("level = :level"); stud_params["level"] = data.level
        if data.graduation_year is not None:
            stud_updates.append("graduation_year = :gyear"); stud_params["gyear"] = data.graduation_year
            
        if stud_updates:
            db.execute(text(f"UPDATE students SET {', '.join(stud_updates)} WHERE id = :id"), stud_params)

    db.commit()
    return get_user(db, user_id)

def award_points(db: Session, user_id: str, points: int):
    db.execute(text("UPDATE students SET points = points + :p WHERE id=:id"), {"p": points, "id": user_id})
    db.commit()

def search_users(db: Session, query: str, role: str = "student"):
    res = db.execute(text("SELECT * FROM users WHERE role=:role AND (name LIKE :q OR id LIKE :q)"),
                     {"role": role, "q": f"%{query}%"}).fetchall()
    # For search results, we often just need the base info
    return [dict(r._mapping) for r in res]
