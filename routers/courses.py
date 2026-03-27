from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

import crud
import schemas
import models
from database import get_db

router = APIRouter(prefix="/api", tags=["Courses"])

@router.get("/courses", response_model=List[schemas.Course])
def read_courses(user_id: str = "u1", db: Session = Depends(get_db)):
    return crud.get_courses(db, user_id=user_id)

@router.post("/courses", response_model=schemas.Course)
def create_course(data: schemas.CourseCreate, professor_id: str = "p1", db: Session = Depends(get_db)):
    course = crud.create_course(db, data, professor_id)
    return schemas.Course.model_validate(course)

@router.put("/courses/{course_id}", response_model=schemas.Course)
def update_course(course_id: str, data: schemas.CourseUpdate, db: Session = Depends(get_db)):
    course = crud.update_course(db, course_id, data)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return schemas.Course.model_validate(course)

@router.delete("/courses/{course_id}")
def delete_course(course_id: str, db: Session = Depends(get_db)):
    course = crud.delete_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"message": "Course deleted"}

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

@router.post("/topics/{topic_id}/complete")
def complete_topic(topic_id: str, user_id: str = "u1", db: Session = Depends(get_db)):
    crud.mark_topic_completed(db, user_id=user_id, topic_id=topic_id)
    
    # Notify student
    topic = crud.get_topic(db, topic_id)
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=user_id,
        title="Topic Completed!",
        message=f"Congratulations! You've successfully completed the topic: {topic.title if topic else 'Unknown'}.",
        type="success",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": "Topic completed successfully"}
