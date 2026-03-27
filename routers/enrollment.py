from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

import models
import schemas
import crud
from database import get_db

router = APIRouter(prefix="/api", tags=["Enrollment"])

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
def get_my_enrollments(user_id: str, db: Session = Depends(get_db)):
    """Get current user's enrollment status per course (for students)."""
    enrollments = crud.get_user_enrollments(db, user_id)
    return [UserEnrollmentOut(id=e.id, course_id=e.course_id, status=e.status, date=e.date) for e in enrollments]

@router.get("/users/search", response_model=List[UserSearchResult])
def search_users(q: str = "", db: Session = Depends(get_db)):
    """Search students by name or ID."""
    if not q:
        return []
    users = crud.search_users(db, q, role="student")
    return users

@router.post("/courses/{course_id}/request-join")
def request_join(course_id: str, user_id: str = "u1", db: Session = Depends(get_db)):
    """Student requests to join a course."""
    enrollment = crud.request_enrollment(db, user_id, course_id)
    return {"message": "Enrollment request submitted", "status": enrollment.status, "id": enrollment.id}

@router.get("/courses/{course_id}/enrollment-requests", response_model=List[schemas.EnrollmentOut])
def get_enrollment_requests(course_id: str, status: str = None, db: Session = Depends(get_db)):
    """Get enrollment requests for a course (professor views)."""
    enrollments = crud.get_course_enrollments(db, course_id, status)
    result = []
    for e in enrollments:
        user = crud.get_user(db, e.user_id)
        result.append(schemas.EnrollmentOut(
            id=e.id, user_id=e.user_id, course_id=e.course_id,
            status=e.status, date=e.date,
            user_name=user.name if user else "Unknown"
        ))
    return result

@router.post("/enrollments/{enrollment_id}/approve")
def approve_enrollment(enrollment_id: str, db: Session = Depends(get_db)):
    """Professor approves enrollment request."""
    enrollment = crud.approve_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    # Notify student
    course = crud.get_course(db, enrollment.course_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=enrollment.user_id,
        title="Enrollment Approved",
        message=f"You have been approved to join the course: {course.title if course else 'Unknown'}.",
        type="success",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": "Enrollment approved"}

@router.post("/courses/{course_id}/enroll-student")
def enroll_student(course_id: str, data: schemas.EnrollStudentRequest, db: Session = Depends(get_db)):
    """Professor directly enrolls a student by their ID."""
    user = crud.get_user(db, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    enrollment = crud.enroll_student_directly(db, data.user_id, course_id)
    
    # Notify student
    course = crud.get_course(db, course_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=data.user_id,
        title="Direct Enrollment",
        message=f"You have been directly enrolled into the course: {course.title if course else 'Unknown'}.",
        type="info",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": f"Student {user.name} enrolled", "id": enrollment.id}
