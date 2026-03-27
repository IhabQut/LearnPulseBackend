from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel

import models
from database import get_db

router = APIRouter(prefix="/api/courses", tags=["Leaderboard"])

class LeaderboardEntry(BaseModel):
    rank: int
    student: str
    points: int
    id: str

    class Config:
        from_attributes = True

@router.get("/{course_id}/leaderboard", response_model=List[LeaderboardEntry])
def get_course_leaderboard(course_id: str, db: Session = Depends(get_db)):
    """
    Returns a leaderboard for a specific course.
    Points = (topic completions in this course * 10) + (quiz scores in this course * 5)
    """
    # Get all chapters for this course
    chapters = db.query(models.Chapter).filter(models.Chapter.course_id == course_id).all()
    chapter_ids = [ch.id for ch in chapters]

    # Get all topics for these chapters
    topics = db.query(models.Topic).filter(models.Topic.chapter_id.in_(chapter_ids)).all()
    topic_ids = [t.id for t in topics]

    # Get all students
    students = db.query(models.User).filter(models.User.role == "student").all()

    entries = []
    for student in students:
        # Count topic completions in this course
        completions = db.query(models.TopicCompletion).filter(
            models.TopicCompletion.user_id == student.id,
            models.TopicCompletion.topic_id.in_(topic_ids)
        ).count()

        # Count quiz attempt scores for quizzes in this course
        quiz_ids = []
        quizzes = db.query(models.Quiz).filter(
            (models.Quiz.topic_id.in_(topic_ids)) | (models.Quiz.chapter_id.in_(chapter_ids))
        ).all()
        quiz_ids = [q.id for q in quizzes]

        total_score = 0
        if quiz_ids:
            result = db.query(func.sum(models.QuizAttempt.score)).filter(
                models.QuizAttempt.user_id == student.id,
                models.QuizAttempt.quiz_id.in_(quiz_ids)
            ).scalar()
            total_score = result or 0

        points = (completions * 10) + (total_score * 5)
        entries.append({
            "id": student.id,
            "student": student.name,
            "points": points
        })

    # Sort and rank
    entries.sort(key=lambda x: x["points"], reverse=True)
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1

    return entries
