from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import datetime

import crud
import schemas
import models
from database import get_db

router = APIRouter(prefix="/api/profile", tags=["Profile"])

@router.get("/{user_id}", response_model=schemas.User)
def get_profile(user_id: str, db: Session = Depends(get_db)):
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Calculate Stats
    completed_topics = db.query(models.TopicCompletion).filter(models.TopicCompletion.user_id == user_id).count()
    
    quiz_stats = db.query(
        func.count(models.QuizAttempt.id),
        func.avg(models.QuizAttempt.score),
        func.avg(models.QuizAttempt.total)
    ).filter(models.QuizAttempt.user_id == user_id).first()
    
    quizzes_taken = quiz_stats[0] or 0
    avg_score = 0.0
    if quizzes_taken > 0 and quiz_stats[2] and quiz_stats[2] > 0:
        avg_score = (quiz_stats[1] / quiz_stats[2]) * 100
    
    enrollments_count = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == user_id, 
        models.Enrollment.status == "approved"
    ).count()

    # Recent Activity
    recent_activity = []
    
    # Recent Quizzes
    recent_quizzes = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == user_id
    ).order_by(models.QuizAttempt.date.desc()).limit(5).all()
    
    for q in recent_quizzes:
        quiz = db.query(models.Quiz).filter(models.Quiz.id == q.quiz_id).first()
        recent_activity.append(schemas.RecentActivity(
            id=q.id,
            type="quiz_attempt",
            title=quiz.title if quiz else "Quiz",
            date=q.date,
            detail=f"Scored {q.score}/{q.total}"
        ))
    
    # Sort activity by date (parsing date string)
    # Since topic completions don't have dates, we'll just prioritize quizzes for now 
    # or add a dummy date for completions if we want them there.
    
    # Professor Stats
    managed_students = 0
    total_courses = 0
    if user.role == "professor":
        courses = db.query(models.Course).filter(models.Course.professor_id == user_id).all()
        total_courses = len(courses)
        course_ids = [c.id for c in courses]
        managed_students = db.query(models.Enrollment).filter(
            models.Enrollment.course_id.in_(course_ids),
            models.Enrollment.status == "approved"
        ).count() if course_ids else 0

    user_stats = schemas.UserStats(
        completed_topics_count=completed_topics,
        quizzes_taken_count=quizzes_taken,
        average_quiz_score=round(float(avg_score or 0), 1),
        courses_enrolled_count=enrollments_count,
        managed_students_count=managed_students,
        total_courses_count=total_courses,
        recent_activity=recent_activity
    )
    
    user_schema = schemas.User.model_validate(user)
    user_schema.stats = user_stats
    return user_schema

@router.put("/{user_id}", response_model=schemas.User)
def update_profile(user_id: str, data: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    user = crud.update_user_profile(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
