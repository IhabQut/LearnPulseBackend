from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import datetime
import uuid

import crud
import schemas
from database import get_db

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("/{user_id}", response_model=schemas.User)
def get_profile(user_id: str, db: Session = Depends(get_db)):
    user_data = crud.get_user(db, user_id=user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate stats
    # topics
    tc = db.execute(text("SELECT COUNT(*) FROM topic_completions WHERE user_id=:id"), {"id": user_id}).scalar()
    # quizzes
    qa = db.execute(text("SELECT COUNT(*), AVG(score*100.0/total) FROM quiz_attempts WHERE user_id=:id AND total > 0"), {"id": user_id}).fetchone()
    # enrollments
    en = db.execute(text("SELECT COUNT(*) FROM enrollments WHERE user_id=:id AND status='approved'"), {"id": user_id}).scalar()
    
    # If is professor
    managed = 0
    total_courses = 0
    if user_data['role'] == 'professor':
        managed = db.execute(text("SELECT COUNT(DISTINCT user_id) FROM enrollments e JOIN courses c ON e.course_id = c.id WHERE c.professor_id=:id AND e.status='approved'"), {"id": user_id}).scalar()
        total_courses = db.execute(text("SELECT COUNT(*) FROM courses WHERE professor_id=:id"), {"id": user_id}).scalar()

    # recent activity
    recent = []
    # from topics
    acts = db.execute(text("SELECT t.title, 'topic_completion' as type, 'Completed topic' as detail FROM topic_completions tc JOIN topics t ON tc.topic_id = t.id WHERE tc.user_id=:id ORDER BY t.\"order\" DESC LIMIT 3"), {"id": user_id}).fetchall()
    for a in acts:
        recent.append({
            "id": str(uuid.uuid4()), 
            "title": a[0], 
            "type": a[1], 
            "date": "Recently", 
            "detail": a[2]
        })

    user_data['stats'] = {
        "completed_topics_count": tc or 0,
        "quizzes_taken_count": qa[0] or 0,
        "average_quiz_score": round(qa[1] or 0, 1),
        "courses_enrolled_count": en or 0,
        "managed_students_count": managed or 0,
        "total_courses_count": total_courses or 0,
        "recent_activity": recent
    }
    
    return user_data

@router.put("/{user_id}", response_model=schemas.User)
def update_profile(user_id: str, data: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    user = crud.update_user_profile(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Returns the updated user with stats
    return get_profile(user_id, db)
