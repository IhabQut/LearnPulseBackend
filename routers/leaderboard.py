from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
import crud
from database import get_db

router = APIRouter(prefix="/api/courses", tags=["Leaderboard"])

class LeaderboardEntry(BaseModel):
    rank: int
    student: str
    points: int
    id: str

@router.get("/{course_id}/leaderboard", response_model=List[LeaderboardEntry])
def get_course_leaderboard(course_id: str, db: Session = Depends(get_db)):
    """Returns leaderboard for ENROLLED students only, ranked by topic completions + quiz scores."""
    query = text("""
        SELECT u.id, u.name, 
        (
            SELECT COUNT(tc.topic_id) * 10 FROM topic_completions tc 
            JOIN topics t ON t.id = tc.topic_id
            JOIN chapters ch ON ch.id = t.chapter_id
            WHERE tc.user_id = u.id AND ch.course_id = :cid
        ) + 
        COALESCE(
            (
                SELECT SUM(qa.score) * 5 FROM quiz_attempts qa
                JOIN quizzes q ON q.id = qa.quiz_id
                WHERE qa.user_id = u.id 
                AND EXISTS (
                    SELECT 1 FROM topics t 
                    JOIN chapters c ON c.id = t.chapter_id
                    WHERE (t.id = q.topic_id OR c.id = q.chapter_id) AND c.course_id = :cid
                )
            ), 0
        ) AS total_points
        FROM users u
        JOIN enrollments e ON e.user_id = u.id AND e.course_id = :cid AND e.status = 'approved'
        WHERE u.role = 'student'
        ORDER BY total_points DESC
    """)
    res = db.execute(query, {"cid": course_id}).fetchall()
    
    entries = []
    for i, r in enumerate(res):
        entries.append({"rank": i+1, "student": r.name, "points": r.total_points, "id": r.id})
    return entries
