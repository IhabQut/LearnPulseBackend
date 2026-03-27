from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel

import models
import schemas
import crud
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.post("/chapter/{chapter_id}/summary")
def generate_chapter_summary(chapter_id: str, db: Session = Depends(get_db)):
    """Simulate AI summary generation based on chapter topics."""
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        return {"summary": "Chapter not found."}
    
    topics = db.query(models.Topic).filter(models.Topic.chapter_id == chapter_id).all()
    if not topics:
        return {"summary": "No topics found in this chapter to summarize."}
    
    topic_titles = [t.title for t in topics]
    
    # Mock AI logic: constructs a summary based on topic titles
    summary_start = f"In this chapter on {chapter.title}, we explore {len(topic_titles)} key concepts: "
    if len(topic_titles) > 1:
        summary_body = ", ".join(topic_titles[:-1]) + f", and {topic_titles[-1]}"
    else:
        summary_body = topic_titles[0]
    summary_end = ". Students will gain a foundational understanding of these areas and their practical applications."
    
    generated_summary = f"{summary_start}{summary_body}{summary_end}"
    
    return {"summary": generated_summary}

@router.get("/course/{course_id}", response_model=schemas.AIReport)
def get_course_analytics(course_id: str, db: Session = Depends(get_db)):
    """Generate AI analysis report for a course based on quiz data."""
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return schemas.AIReport(course_title="Unknown", total_students=0, insight="Course not found.")

    # Get enrolled students
    enrolled = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == course_id,
        models.Enrollment.status == "approved"
    ).all()
    enrolled_ids = [e.user_id for e in enrolled]
    
    # Fallback: if no enrollments, use all students
    if not enrolled_ids:
        students = db.query(models.User).filter(models.User.role == "student").all()
        enrolled_ids = [s.id for s in students]

    total_students = len(enrolled_ids)

    # Get all chapters, topics, quizzes
    chapters = db.query(models.Chapter).filter(models.Chapter.course_id == course_id).all()
    chapter_map = {ch.id: ch.title for ch in chapters}
    chapter_ids = list(chapter_map.keys())

    topics = db.query(models.Topic).filter(models.Topic.chapter_id.in_(chapter_ids)).all()
    topic_map = {t.id: (t.title, t.chapter_id) for t in topics}
    topic_ids = list(topic_map.keys())

    # Analyze quiz performance per topic
    struggling = []
    for topic_id, (topic_title, ch_id) in topic_map.items():
        quiz = db.query(models.Quiz).filter(models.Quiz.topic_id == topic_id).first()
        if not quiz:
            continue
        
        attempts = db.query(models.QuizAttempt).filter(
            models.QuizAttempt.quiz_id == quiz.id,
            models.QuizAttempt.is_first_attempt == True
        ).all()
        
        if not attempts:
            continue
        
        total_score = sum(a.score for a in attempts)
        total_possible = sum(a.total for a in attempts)
        
        if total_possible > 0:
            success_rate = total_score / total_possible
            fail_rate = round((1 - success_rate) * 100, 1)
            
            if fail_rate > 20:  # Flag topics with >20% fail rate
                struggling.append(schemas.StrugglingTopic(
                    topic_title=topic_title,
                    chapter_title=chapter_map.get(ch_id, ""),
                    fail_rate=fail_rate,
                    common_mistake=f"{fail_rate}% of students answered incorrectly on questions about {topic_title}."
                ))

    struggling.sort(key=lambda x: x.fail_rate, reverse=True)

    # Student participation analysis
    low_participation = []
    high_performers = []
    
    for uid in enrolled_ids:
        user = db.query(models.User).filter(models.User.id == uid).first()
        if not user:
            continue
        
        topics_done = db.query(models.TopicCompletion).filter(
            models.TopicCompletion.user_id == uid,
            models.TopicCompletion.topic_id.in_(topic_ids)
        ).count()
        
        quizzes_taken = db.query(models.QuizAttempt).filter(
            models.QuizAttempt.user_id == uid
        ).count()
        
        entry = schemas.StudentParticipation(
            student_id=uid,
            student_name=user.name,
            topics_completed=topics_done,
            quizzes_taken=quizzes_taken
        )
        
        if topics_done == 0 and quizzes_taken == 0:
            low_participation.append(entry)
        elif topics_done >= len(topic_ids) * 0.7:
            high_performers.append(entry)

    # Generate insight
    insight_parts = []
    if struggling:
        insight_parts.append(f"Students are struggling most with '{struggling[0].topic_title}' ({struggling[0].fail_rate}% fail rate).")
    if low_participation:
        names = ", ".join(s.student_name for s in low_participation[:3])
        insight_parts.append(f"Students not participating: {names}.")
    if high_performers:
        insight_parts.append(f"{len(high_performers)} students are performing above average.")
    
    insight = " ".join(insight_parts) if insight_parts else "Not enough data to generate insights yet. Students need to complete more quizzes."

    return schemas.AIReport(
        course_title=course.title,
        total_students=total_students,
        struggling_topics=struggling,
        low_participation=low_participation,
        high_performers=high_performers,
        insight=insight
    )

@router.get("/student/{student_id}", response_model=schemas.StudentAnalyticsOut)
def get_student_analytics(student_id: str, db: Session = Depends(get_db)):
    """Fetch analytics for a specific student (quiz history, recommendations, overall progress)."""
    # 1. Quiz History
    attempts = db.query(models.QuizAttempt).filter(models.QuizAttempt.user_id == student_id).all()
    quiz_history = []
    for a in attempts:
        quiz = db.query(models.Quiz).filter(models.Quiz.id == a.quiz_id).first()
        res = schemas.StudentQuizAttempt.model_validate(a)
        res.quiz_title = quiz.title if quiz else "Unknown Quiz"
        quiz_history.append(res)
    
    # 2. Recommended Topics (from CRUD helper)
    recommended = crud.get_next_recommended_topic(db, student_id)
    
    # 3. Overall Progress
    # Get all topics in all courses the student is enrolled in
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == student_id,
        models.Enrollment.status == "approved"
    ).all()
    
    total_topics = 0
    completed_topics = 0
    
    for en in enrollments:
        course = db.query(models.Course).filter(models.Course.id == en.course_id).first()
        if not course: continue
        
        for chapter in course.chapters:
            for topic in chapter.topics:
                total_topics += 1
                done = db.query(models.TopicCompletion).filter(
                    models.TopicCompletion.user_id == student_id,
                    models.TopicCompletion.topic_id == topic.id
                ).first()
                if done:
                    completed_topics += 1
                    
    progress = (completed_topics / total_topics * 100) if total_topics > 0 else 0
    
    return schemas.StudentAnalyticsOut(
        quiz_attempts=quiz_history,
        recommended_topics=recommended,
        overall_progress=round(progress, 1)
    )
