from sqlalchemy.orm import Session
from sqlalchemy import text
import schemas

def get_next_recommended_topic(db: Session, user_id: str):
    query = text("""
        SELECT c.id AS course_id, c.title AS course_title, ch.id AS chapter_id, t.id AS topic_id, t.title AS topic_title
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        JOIN chapters ch ON ch.course_id = c.id
        JOIN topics t ON t.chapter_id = ch.id
        LEFT JOIN topic_completions tc ON tc.topic_id = t.id AND tc.user_id = :u
        WHERE e.user_id = :u AND e.status = 'approved' AND tc.user_id IS NULL
        ORDER BY c.id, ch.id, t.`order`
        LIMIT 1
    """)
    res = db.execute(query, {"u": user_id}).fetchone()
    if res:
        return [{
            "course_id": res.course_id, "course_title": res.course_title,
            "chapter_id": res.chapter_id, "topic_id": res.topic_id, "topic_title": res.topic_title
        }]
    return []
