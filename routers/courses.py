from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

import crud
import schemas
import models
import security
from database import get_db

router = APIRouter(prefix="/api", tags=["Courses"])

@router.get("/courses", response_model=List[schemas.Course])
def read_courses(user = Depends(security.get_optional_user), enrolled_only: bool = False, db: Session = Depends(get_db)):
    user_id = user['id'] if user and isinstance(user, dict) else (user.id if user else "")
    return crud.get_courses(db, user_id=user_id, enrolled_only=enrolled_only)

@router.get("/courses/{course_id}", response_model=schemas.Course)
def read_course(course_id: str, user = Depends(security.get_optional_user), db: Session = Depends(get_db)):
    # Security: check if user is enrolled or professor/owner
    user_id = user['id'] if user and isinstance(user, dict) else (user.id if user else "")
    security.require_course_permission(db, user_id, course_id, allowed_roles=['owner', 'instructor', 'student', 'viewer'])
    
    course = crud.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.post("/courses", response_model=schemas.Course)
def create_course(data: schemas.CourseCreate, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    # Verify the user has the right role
    security.require_professor(user)
    
    uid = user['id'] if isinstance(user, dict) else user.id
    course = crud.create_course(db, data, uid)
    return course

@router.put("/courses/{course_id}", response_model=schemas.Course)
def update_course(course_id: str, data: schemas.CourseUpdate, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    # Let's say only Owners/Instructors can update.
    uid = user['id'] if isinstance(user, dict) else user.id
    security.require_course_permission(db, uid, course_id, allowed_roles=['owner', 'instructor'])
    
    course = crud.update_course(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    # Only Owners can delete
    security.require_course_owner(db, user, course_id)
    
    course = crud.delete_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted"}

@router.get("/courses/{course_id}/students")
def get_course_students(course_id: str, db: Session = Depends(get_db)):
    from sqlalchemy import text
    query = text("""
        SELECT u.id, e.id as enrollment_id, e.role as enrollment_role
        FROM users u 
        JOIN enrollments e ON e.user_id = u.id 
        WHERE e.course_id = :cid AND e.status = 'approved'
    """)
    res = db.execute(query, {"cid": course_id}).fetchall()
    results = []
    for row in res:
        user_data = crud.get_user(db, user_id=row[0])
        if user_data:
            # We want to keep the schemas.User structure but add enrollment info
            # Convert to dict if it's not already
            u_dict = dict(user_data) if not isinstance(user_data, dict) else user_data
            u_dict["enrollment_id"] = row[1]
            u_dict["role"] = row[2] # Course-specific role
            results.append(u_dict)
    return results

@router.get("/courses/{course_id}/enrollment-requests", response_model=List[schemas.EnrollmentOut])
def get_enrollment_requests(course_id: str, status: str = 'pending', db: Session = Depends(get_db)):
    """Get enrollment requests for a course (professor views)."""
    enrollments = crud.get_course_enrollments(db, course_id, status)
    result = []
    for e in enrollments:
        result.append(schemas.EnrollmentOut(
            id=e.id, user_id=e.user_id, course_id=e.course_id,
            status=e.status, role=e.role, date=e.date,
            user_name=e.user_name if hasattr(e, 'user_name') and e.user_name else "Unknown"
        ))
    return result

# ─── Chapters ────────────────────────────────────────────────

@router.post("/courses/{course_id}/chapters")
def create_chapter(course_id: str, data: schemas.ChapterCreate, db: Session = Depends(get_db)):
    chapter = crud.create_chapter(db, course_id, data)
    return schemas.Chapter.model_validate(chapter)

@router.put("/chapters/{chapter_id}")
def update_chapter(chapter_id: str, data: schemas.ChapterUpdate, db: Session = Depends(get_db)):
    chapter = crud.update_chapter(db, chapter_id, data)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return schemas.Chapter.model_validate(chapter)

@router.delete("/chapters/{chapter_id}")
def delete_chapter(chapter_id: str, db: Session = Depends(get_db)):
    chapter = crud.delete_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {"message": "Chapter deleted"}

# ─── Topics ──────────────────────────────────────────────────

@router.post("/chapters/{chapter_id}/topics")
def create_topic(chapter_id: str, data: schemas.TopicCreate, db: Session = Depends(get_db)):
    topic = crud.create_topic(db, chapter_id, data)
    return schemas.Topic.model_validate(topic)

@router.put("/topics/{topic_id}")
def update_topic(topic_id: str, data: schemas.TopicUpdate, db: Session = Depends(get_db)):
    topic = crud.update_topic(db, topic_id, data)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return schemas.Topic.model_validate(topic)

@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: str, db: Session = Depends(get_db)):
    topic = crud.delete_topic(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    return {"message": "Topic deleted"}

@router.post("/topics/{topic_id}/complete")
def complete_topic(topic_id: str, user = Depends(security.get_current_user), db: Session = Depends(get_db)):
    # Verify user is a student
    role = user['role'] if isinstance(user, dict) else user.role
    if role != "student":
        raise HTTPException(status_code=403, detail="Only students can complete topics")
    
    uid = user['id'] if isinstance(user, dict) else user.id
    crud.mark_topic_completed(db, user_id=uid, topic_id=topic_id)
    
    topic = crud.get_topic(db, topic_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=uid,
        title="Topic Completed!",
        message=f"Congratulations! You've successfully completed the topic: {topic.title if topic else 'Unknown'}.",
        type="success",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": "Topic completed successfully"}
