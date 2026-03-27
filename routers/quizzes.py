from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

import models
import schemas
import crud
from database import get_db

router = APIRouter(prefix="/api/quizzes", tags=["Quizzes"])

class QuizQuestionOut(BaseModel):
    id: str
    question: str
    options: str  # JSON string
    correct_option: int
    explanation: str

    class Config:
        from_attributes = True

class QuizOut(BaseModel):
    id: str
    title: str
    quiz_type: str
    topic_id: Optional[str] = None
    chapter_id: Optional[str] = None
    questions: List[QuizQuestionOut] = []

    class Config:
        from_attributes = True

class QuizSubmission(BaseModel):
    user_id: str = "u1"
    answers: List[int]  # index of selected option for each question


@router.get("/topic/{topic_id}", response_model=Optional[QuizOut])
def get_topic_quiz(topic_id: str, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(
        models.Quiz.topic_id == topic_id,
        models.Quiz.quiz_type == "topic"
    ).first()
    if not quiz:
        return None
    quiz_out = QuizOut.model_validate(quiz)
    quiz_out.questions = [QuizQuestionOut.model_validate(q) for q in quiz.questions]
    return quiz_out

@router.get("/chapter/{chapter_id}", response_model=Optional[QuizOut])
def get_chapter_quiz(chapter_id: str, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(
        models.Quiz.chapter_id == chapter_id,
        models.Quiz.quiz_type == "chapter"
    ).first()
    if not quiz:
        return None
    quiz_out = QuizOut.model_validate(quiz)
    quiz_out.questions = [QuizQuestionOut.model_validate(q) for q in quiz.questions]
    return quiz_out

@router.get("/course/{course_id}", response_model=List[QuizOut])
def get_course_quizzes(course_id: str, db: Session = Depends(get_db)):
    """Get all quizzes for a course (topic + chapter quizzes)."""
    chapters = db.query(models.Chapter).filter(models.Chapter.course_id == course_id).all()
    chapter_ids = [ch.id for ch in chapters]
    topics = db.query(models.Topic).filter(models.Topic.chapter_id.in_(chapter_ids)).all()
    topic_ids = [t.id for t in topics]

    quizzes = db.query(models.Quiz).filter(
        (models.Quiz.topic_id.in_(topic_ids)) | (models.Quiz.chapter_id.in_(chapter_ids))
    ).all()

    result = []
    for quiz in quizzes:
        q_out = QuizOut.model_validate(quiz)
        q_out.questions = [QuizQuestionOut.model_validate(q) for q in quiz.questions]
        result.append(q_out)
    return result

@router.get("/{quiz_id}", response_model=QuizOut)
def get_quiz(quiz_id: str, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    quiz_out = QuizOut.model_validate(quiz)
    quiz_out.questions = [QuizQuestionOut.model_validate(q) for q in quiz.questions]
    return quiz_out

@router.post("/{quiz_id}/submit", response_model=schemas.QuizAttemptOut)
def submit_quiz(quiz_id: str, submission: QuizSubmission, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = quiz.questions
    score = 0
    for i, question in enumerate(questions):
        if i < len(submission.answers) and submission.answers[i] == question.correct_option:
            score += 1

    # Check if first attempt
    prior = db.query(models.QuizAttempt).filter(
        models.QuizAttempt.user_id == submission.user_id,
        models.QuizAttempt.quiz_id == quiz_id
    ).first()
    is_first = prior is None

    import uuid
    attempt = models.QuizAttempt(
        id=str(uuid.uuid4()),
        user_id=submission.user_id,
        quiz_id=quiz_id,
        score=score,
        total=len(questions),
        date="Just now",
        is_first_attempt=is_first
    )
    db.add(attempt)
    db.commit()

    # Award points only on first attempt: +5 per correct answer
    points_awarded = 0
    if is_first:
        points_awarded = score * 5
        crud.award_points(db, submission.user_id, points_awarded)

    db.refresh(attempt)

    return schemas.QuizAttemptOut(
        id=attempt.id,
        user_id=attempt.user_id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        total=attempt.total,
        date=attempt.date,
        is_first_attempt=is_first,
        points_awarded=points_awarded
    )

@router.get("/course/{course_id}/attempts", response_model=List[schemas.StudentQuizAttempt])
def get_course_quiz_attempts(course_id: str, db: Session = Depends(get_db)):
    """Fetch all quiz attempts for all students in a course."""
    chapters = db.query(models.Chapter).filter(models.Chapter.course_id == course_id).all()
    chapter_ids = [ch.id for ch in chapters]
    topics = db.query(models.Topic).filter(models.Topic.chapter_id.in_(chapter_ids)).all()
    topic_ids = [t.id for t in topics]
    
    quizzes = db.query(models.Quiz).filter(
        (models.Quiz.topic_id.in_(topic_ids)) | (models.Quiz.chapter_id.in_(chapter_ids))
    ).all()
    quiz_ids = [q.id for q in quizzes]
    quiz_map = {q.id: q.title for q in quizzes}
    
    attempts = db.query(models.QuizAttempt).filter(models.QuizAttempt.quiz_id.in_(quiz_ids)).all()
    
    results = []
    for a in attempts:
        user = db.query(models.User).filter(models.User.id == a.user_id).first()
        res = schemas.StudentQuizAttempt.model_validate(a)
        res.quiz_title = quiz_map.get(a.quiz_id, "Unknown Quiz")
        res.user_name = user.name if user else "Unknown Student"
        results.append(res)
    return results

@router.get("/student/{student_id}/attempts", response_model=List[schemas.StudentQuizAttempt])
def get_student_quiz_attempts(student_id: str, db: Session = Depends(get_db)):
    """Fetch all quiz attempts for a specific student."""
    attempts = db.query(models.QuizAttempt).filter(models.QuizAttempt.user_id == student_id).all()
    results = []
    for a in attempts:
        quiz = db.query(models.Quiz).filter(models.Quiz.id == a.quiz_id).first()
        res = schemas.StudentQuizAttempt.model_validate(a)
        res.quiz_title = quiz.title if quiz else "Unknown Quiz"
        results.append(res)
    return results

@router.post("/topic/{topic_id}", response_model=QuizOut)
def create_topic_quiz(topic_id: str, data: schemas.QuizCreate, db: Session = Depends(get_db)):
    quiz = crud.get_quiz_by_topic(db, topic_id)
    if not quiz:
        quiz = crud.create_quiz(db, data)
    return quiz

@router.post("/chapter/{chapter_id}", response_model=QuizOut)
def create_chapter_quiz(chapter_id: str, data: schemas.QuizCreate, db: Session = Depends(get_db)):
    quiz = crud.get_quiz_by_chapter(db, chapter_id)
    if not quiz:
        quiz = crud.create_quiz(db, data)
    return quiz

@router.post("/{quiz_id}/questions", response_model=QuizQuestionOut)
def add_question(quiz_id: str, data: schemas.QuizQuestionCreate, db: Session = Depends(get_db)):
    return crud.add_quiz_question(db, quiz_id, data)

@router.put("/questions/{question_id}", response_model=QuizQuestionOut)
def update_question(question_id: str, data: schemas.QuizQuestionUpdate, db: Session = Depends(get_db)):
    question = crud.update_quiz_question(db, question_id, data)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.delete("/questions/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db)):
    if not crud.delete_quiz_question(db, question_id):
        raise HTTPException(status_code=404, detail="Question not found")
    return {"status": "success"}
