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
        SELECT u.id, u.name, e.points AS total_points
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
