from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
from datetime import datetime

import models
import schemas
import crud
import security
from database import get_db

router = APIRouter(prefix="/api/enrollments", tags=["Enrollment"])

class UserSearchResult(BaseModel):
    id: str
    name: str
    role: str
    class Config:
        from_attributes = True

class UserEnrollmentOut(BaseModel):
    id: str
    course_id: str
    status: str
    date: str
    class Config:
        from_attributes = True

@router.get("/users/{user_id}/enrollments", response_model=List[UserEnrollmentOut])
def get_user_enrollments_list(user_id: str, db: Session = Depends(get_db)):
    """Get specific user's enrollment status per course (for students/viewers)."""
    enrollments = crud.get_user_enrollments(db, user_id)
    return [UserEnrollmentOut(id=e.id, course_id=e.course_id, status=e.status, date=e.date) for e in enrollments]

@router.get("/users/search", response_model=List[schemas.User])
def search_users(q: str = "", db: Session = Depends(get_db)):
    """Search students by name or ID and return rich profile."""
    if not q:
        return []
    base_users = crud.search_users(db, q, role="student")
    results = []
    for u in base_users:
        full_u = crud.get_user(db, u['id'])
        if full_u:
            results.append(full_u)
    return results

class RequestJoinData(BaseModel):
    user_id: str
    course_id: str

@router.post("/request")
def request_join(data: RequestJoinData, db: Session = Depends(get_db)):
    """User requests to join a course (as student or viewer)."""
    user = crud.get_user(db, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    course = crud.get_course(db, data.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Block the course owner from enrolling in their own course
    owner_id = course.professor_id
    if data.user_id == owner_id:
        raise HTTPException(status_code=400, detail="You are the owner of this course and are already part of it.")
    
    if not course.is_open:
        raise HTTPException(status_code=400, detail="This course is not accepting enrollment requests")
    
    # Check for existing enrollment
    role_in_course = security.get_course_role(db, data.user_id, data.course_id)
    if role_in_course:
        raise HTTPException(status_code=400, detail=f"You already have a role in this course: {role_in_course}")
    
    enrollment = crud.request_enrollment(db, data.user_id, data.course_id, "student")
    
    # Notify owner
    if course.professor_id:
        user_name = user['name'] if isinstance(user, dict) else user.name
        crud.create_notification(db, schemas.NotificationCreate(
            user_id=course.professor_id,
            title="New Enrollment Request",
            message=f"{user_name} has requested to join your course.",
            type="info",
            date=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    
    return {"message": "Enrollment request submitted", "status": enrollment.status, "id": enrollment.id}

@router.get("/my-status")
def get_my_status(user_id: str, db: Session = Depends(get_db)):
    """Get current user's enrollment status dict (course_id: status)."""
    enrollments = crud.get_user_enrollments(db, user_id)
    return {e.course_id: e.status for e in enrollments}

@router.post("/{enrollment_id}/approve")
def approve_enrollment(enrollment_id: str, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """Professor approves enrollment request."""
    enrollment = db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": enrollment_id}).fetchone()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Security: Must be course owner
    security.require_course_owner(db, user, enrollment.course_id)
    
    result = crud.approve_enrollment(db, enrollment_id)
    
    # Notify student
    course = crud.get_course(db, enrollment.course_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=enrollment.user_id,
        title="Enrollment Approved",
        message=f"You have been approved as {enrollment.role} for: {course.title if course else 'Unknown'}.",
        type="success",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": "Enrollment approved"}

@router.delete("/{enrollment_id}")
def reject_enrollment(enrollment_id: str, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """Professor rejects an enrollment request."""
    enrollment = db.execute(text("SELECT * FROM enrollments WHERE id=:id"), {"id": enrollment_id}).fetchone()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Security: Must be course owner
    security.require_course_owner(db, user, enrollment.course_id)
    
    db.execute(text("DELETE FROM enrollments WHERE id=:id"), {"id": enrollment_id})
    db.commit()
    
    # Notify student
    course = crud.get_course(db, enrollment.course_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=enrollment.user_id,
        title="Enrollment Rejected",
        message=f"Your request to join {course.title if course else 'the course'} has been declined.",
        type="warning",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": "Enrollment request rejected"}

@router.post("/courses/{course_id}/enroll-student")
def enroll_student(course_id: str, data: schemas.EnrollStudentRequest, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """Professor directly enrolls a user with a specific role."""
    security.require_course_owner(db, user, course_id)
    
    # Safe-guard: owner cannot enroll themselves
    owner_id = user['id'] if isinstance(user, dict) else user.id
    if data.user_id == owner_id:
        raise HTTPException(status_code=400, detail="You cannot enroll yourself — you are already the course owner.")
    
    # Also block if the target user is the course's professor_id (redundant double-check)
    course = crud.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if data.user_id == course.professor_id:
        raise HTTPException(status_code=400, detail="This user is the course owner and cannot be re-enrolled.")
    
    target_user = crud.get_user(db, data.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found. Please check the user ID.")
    
    enrollment = crud.enroll_student_directly(db, data.user_id, course_id, data.role)
    
    # Notify enrolled user
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=data.user_id,
        title="Direct Enrollment",
        message=f"You have been assigned as {data.role} in: {course.title}.",
        type="info",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    name = target_user['name'] if isinstance(target_user, dict) else target_user.name
    return {"message": f"User {name} enrolled as {data.role}", "id": enrollment.id}

@router.delete("/courses/{course_id}/students/{student_id}")
def unenroll_student(course_id: str, student_id: str, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """Professor removes a user from a course."""
    security.require_course_owner(db, user, course_id)
    
    existing = db.execute(
        text("SELECT * FROM enrollments WHERE course_id=:cid AND user_id=:uid"),
        {"cid": course_id, "uid": student_id}
    ).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="User not enrolled in this course")
    
    db.execute(text("DELETE FROM enrollments WHERE course_id=:cid AND user_id=:uid"), 
               {"cid": course_id, "uid": student_id})
    db.commit()
    
    return {"message": "User removed from course"}

class UpdateRoleRequest(BaseModel):
    role: str

@router.patch("/{enrollment_id}/role")
def update_role(enrollment_id: str, data: UpdateRoleRequest, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    """Update a user's role in a course (Owner/Instructor with limits)."""
    enrollment = db.execute(text("SELECT course_id FROM enrollments WHERE id=:id"), {"id": enrollment_id}).fetchone()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    security.can_manage_role(db, user['id'] if isinstance(user, dict) else user.id, enrollment_id, enrollment.course_id)
    
    crud.update_enrollment_role(db, enrollment_id, data.role)
    return {"message": "Role updated", "role": data.role}


