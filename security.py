"""
Role-based access control for LearnPulse API.
Provides dependency functions for FastAPI routes to validate user identity and permissions.
"""
from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db


def get_current_user(user_id: str = Query(None, alias="user_id"), db: Session = Depends(get_db)):
    """Validate that user_id exists in the database and return the user row."""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required. Provide user_id.")
    
    user = db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail=f"User '{user_id}' not found.")
    return user


def get_course_role(db: Session, user_id: str, course_id: str):
    """Fetch the specific role of a user in a course."""
    enrollment = db.execute(
        text("SELECT role, status FROM enrollments WHERE user_id=:uid AND course_id=:cid"),
        {"uid": user_id, "cid": course_id}
    ).fetchone()
    if not enrollment or enrollment.status != 'approved':
        return None
    return enrollment.role

def require_course_permission(db: Session, user_id: str, course_id: str, allowed_roles: list):
    """Verify if user has one of the allowed roles in the course."""
    role = get_course_role(db, user_id, course_id)
    if not role:
        raise HTTPException(status_code=403, detail="You are not enrolled in this course.")
    
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Required roles: {allowed_roles}. Your role: {role}")
    return role

def require_professor(user):
    """Global professor check."""
    role = user['role'] if isinstance(user, dict) else user.role
    if role != "professor":
        raise HTTPException(status_code=403, detail="Only professors can perform this action.")
    return user

def require_course_owner(db: Session, user, course_id: str):
    """Strict ownership check for course administration (delete course, manage instructors)."""
    uid = user['id'] if isinstance(user, dict) else user.id
    role = get_course_role(db, uid, course_id)
    if role != 'owner':
        raise HTTPException(status_code=403, detail="Only the course owner can perform this action.")
    return True

def can_manage_role(db: Session, manager_id: str, target_enrollment_id: str, course_id: str):
    """
    Check if manager_id can change the role of target_enrollment_id.
    - Owner can manage anyone except themselves.
    - Instructor can manage students and viewers.
    - Student/Viewer can't manage anyone.
    """
    manager_role = get_course_role(db, manager_id, course_id)
    if not manager_role or manager_role not in ['owner', 'instructor']:
        raise HTTPException(status_code=403, detail="Unauthorized to manage roles.")
    
    target = db.execute(text("SELECT id, user_id, role FROM enrollments WHERE id=:id"), {"id": target_enrollment_id}).fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="Target enrollment not found.")
    
    if target.user_id == manager_id:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")
        
    if manager_role == 'owner':
        return True # Owner can manage all other roles
        
    if manager_role == 'instructor':
        if target.role in ['owner', 'instructor']:
             raise HTTPException(status_code=403, detail="Instructors cannot manage roles of other instructors or owners.")
        return True
        
    return False
