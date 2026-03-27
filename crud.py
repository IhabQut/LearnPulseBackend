from sqlalchemy.orm import Session
import models
import schemas
from typing import List
import uuid

def get_user(db: Session, user_id: str) -> models.User:
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserBase) -> models.User:
    db_user = models.User(
        id=user.id, name=user.name, role=user.role, points=user.points,
        email=f"{user.name.lower().replace(' ', '.')}@university.edu"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_profile(db: Session, user_id: str, data: schemas.ProfileUpdate) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        user.email = data.email
    if data.bio is not None:
        user.bio = data.bio
    if data.office_hours is not None:
        user.office_hours = data.office_hours
    if data.meeting_link is not None:
        user.meeting_link = data.meeting_link
    if data.zoom_enabled is not None:
        user.zoom_enabled = data.zoom_enabled
    if data.in_person_enabled is not None:
        user.in_person_enabled = data.in_person_enabled
    db.commit()
    db.refresh(user)
    return user

def award_points(db: Session, user_id: str, points: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.points = (user.points or 0) + points
        db.commit()

def search_users(db: Session, query: str, role: str = "student") -> List[models.User]:
    return db.query(models.User).filter(
        models.User.role == role,
        (models.User.name.ilike(f"%{query}%") | models.User.id.ilike(f"%{query}%"))
    ).all()

def get_topic(db: Session, topic_id: str) -> models.Topic:
    return db.query(models.Topic).filter(models.Topic.id == topic_id).first()

# ─── Courses ─────────────────────────────────────────────────

def get_courses(db: Session, user_id: str) -> List[schemas.Course]:
    courses = db.query(models.Course).all()
    result = []
    for course in courses:
        course_schema = schemas.Course.model_validate(course)
        for i, chapter in enumerate(course.chapters):
            for j, topic in enumerate(chapter.topics):
                completion = db.query(models.TopicCompletion).filter(
                    models.TopicCompletion.topic_id == topic.id,
                    models.TopicCompletion.user_id == user_id
                ).first()
                if completion:
                    course_schema.chapters[i].topics[j].completed = True
        result.append(course_schema)
    return result

def get_course(db: Session, course_id: str) -> models.Course:
    return db.query(models.Course).filter(models.Course.id == course_id).first()

def create_course(db: Session, data: schemas.CourseCreate, professor_id: str) -> models.Course:
    course = models.Course(
        id=f"c{uuid.uuid4().hex[:8]}",
        title=data.title,
        description=data.description,
        professor_id=professor_id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

def update_course(db: Session, course_id: str, data: schemas.CourseUpdate) -> models.Course:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return None
    if data.title is not None:
        course.title = data.title
    if data.description is not None:
        course.description = data.description
    db.commit()
    db.refresh(course)
    return course

def delete_course(db: Session, course_id: str):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if course:
        db.delete(course)
        db.commit()
    return course

# ─── Materials ───────────────────────────────────────────────

def create_material(db: Session, course_id: str, data: schemas.MaterialCreate) -> models.Material:
    db_material = models.Material(
        id=f"mat{uuid.uuid4().hex[:8]}",
        name=data.name,
        type=data.type,
        url=data.url,
        course_id=course_id
    )
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material

def delete_material(db: Session, material_id: str):
    db_material = db.query(models.Material).filter(models.Material.id == material_id).first()
    if db_material:
        db.delete(db_material)
        db.commit()
    return db_material

# ─── Chapters ────────────────────────────────────────────────

def create_chapter(db: Session, course_id: str, data: schemas.ChapterCreate) -> models.Chapter:
    chapter = models.Chapter(
        id=f"ch{uuid.uuid4().hex[:8]}",
        title=data.title,
        summary=data.summary,
        course_id=course_id
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter

def update_chapter(db: Session, chapter_id: str, data: schemas.ChapterUpdate) -> models.Chapter:
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if not chapter:
        return None
    if data.title is not None:
        chapter.title = data.title
    if data.summary is not None:
        chapter.summary = data.summary
    db.commit()
    db.refresh(chapter)
    return chapter

def delete_chapter(db: Session, chapter_id: str):
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()
    if chapter:
        db.delete(chapter)
        db.commit()
    return chapter

# ─── Topics ──────────────────────────────────────────────────

def create_topic(db: Session, chapter_id: str, data: schemas.TopicCreate) -> models.Topic:
    max_order = db.query(models.Topic).filter(models.Topic.chapter_id == chapter_id).count()
    topic = models.Topic(
        id=f"t{uuid.uuid4().hex[:8]}",
        title=data.title,
        description=data.description,
        chapter_id=chapter_id,
        order=max_order
    )
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic

def update_topic(db: Session, topic_id: str, data: schemas.TopicUpdate) -> models.Topic:
    topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()
    if not topic:
        return None
    if data.title is not None:
        topic.title = data.title
    if data.description is not None:
        topic.description = data.description
    db.commit()
    db.refresh(topic)
    return topic

def mark_topic_completed(db: Session, user_id: str, topic_id: str):
    completion = db.query(models.TopicCompletion).filter(
        models.TopicCompletion.topic_id == topic_id,
        models.TopicCompletion.user_id == user_id
    ).first()
    if not completion:
        completion = models.TopicCompletion(user_id=user_id, topic_id=topic_id)
        db.add(completion)
        # Award 10 points for topic completion
        award_points(db, user_id, 10)
        db.commit()

# ─── Discussions ─────────────────────────────────────────────

def get_discussion(db: Session, discussion_id: str) -> models.Discussion:
    return db.query(models.Discussion).filter(models.Discussion.id == discussion_id).first()

def get_discussions(db: Session) -> List[schemas.Discussion]:
    discussions = db.query(models.Discussion).order_by(models.Discussion.id.desc()).all()
    result = []
    for d in discussions:
        # Build schema manually: ORM has replies as relationship (list), schema has replies as int
        d_schema = schemas.Discussion(
            id=d.id,
            author=d.author,
            authorId=d.author_id,
            title=d.title,
            content=d.content,
            date=d.date,
            courseId=d.course_id,
            chapterId=d.chapter_id,
            topicId=d.topic_id,
            replies=len(d.replies),
            replyList=[schemas.Reply.model_validate(r) for r in d.replies],
        )
        result.append(d_schema)
    return result

def create_discussion(db: Session, discussion: schemas.DiscussionBase) -> models.Discussion:
    db_discussion = models.Discussion(
        id=discussion.id,
        author=discussion.author,
        author_id=discussion.authorId,
        title=discussion.title,
        content=discussion.content,
        date=discussion.date,
        course_id=discussion.courseId,
        chapter_id=discussion.chapterId,
        topic_id=discussion.topicId
    )
    db.add(db_discussion)
    db.commit()
    db.refresh(db_discussion)
    return db_discussion

def create_reply(db: Session, discussion_id: str, reply: schemas.ReplyBase) -> models.Reply:
    db_reply = models.Reply(
        id=reply.id,
        author=reply.author,
        author_id=reply.authorId,
        text=reply.text,
        date=reply.date,
        role=reply.role,
        discussion_id=discussion_id
    )
    db.add(db_reply)
    db.commit()
    db.refresh(db_reply)
    return db_reply

# ─── Enrollment ──────────────────────────────────────────────

def request_enrollment(db: Session, user_id: str, course_id: str) -> models.Enrollment:
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == user_id,
        models.Enrollment.course_id == course_id
    ).first()
    if existing:
        return existing
    enrollment = models.Enrollment(
        id=f"e{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        course_id=course_id,
        status="pending",
        date="Just now"
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment

def approve_enrollment(db: Session, enrollment_id: str) -> models.Enrollment:
    enrollment = db.query(models.Enrollment).filter(models.Enrollment.id == enrollment_id).first()
    if enrollment:
        enrollment.status = "approved"
        db.commit()
        db.refresh(enrollment)
    return enrollment

def enroll_student_directly(db: Session, user_id: str, course_id: str) -> models.Enrollment:
    existing = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == user_id,
        models.Enrollment.course_id == course_id
    ).first()
    if existing:
        existing.status = "approved"
        db.commit()
        db.refresh(existing)
        return existing
    enrollment = models.Enrollment(
        id=f"e{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        course_id=course_id,
        status="approved",
        date="Just now"
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment

def get_course_enrollments(db: Session, course_id: str, status: str = None):
    q = db.query(models.Enrollment).filter(models.Enrollment.course_id == course_id)
    if status:
        q = q.filter(models.Enrollment.status == status)
    return q.all()

def get_user_enrollments(db: Session, user_id: str):
    """Return all enrollments for a user (for student 'my requests' / status per course)."""
    return db.query(models.Enrollment).filter(models.Enrollment.user_id == user_id).all()

# ─── Meetings ────────────────────────────────────────────────

def create_meeting_request(db: Session, user_id: str, data: schemas.MeetingRequestCreate) -> models.MeetingRequest:
    import datetime
    db_meeting = models.MeetingRequest(
        id=f"m{uuid.uuid4().hex[:8]}",
        user_id=user_id,
        professor_id=data.professor_id,
        note=data.note,
        slot=data.slot,
        meeting_type=data.meeting_type,
        status="pending",
        date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_meeting)
    db.commit()
    db.refresh(db_meeting)
    return db_meeting

def get_meeting_requests(db: Session, user_id: str):
    # Get requests where user is either the student or the professor
    return db.query(models.MeetingRequest).filter(
        (models.MeetingRequest.user_id == user_id) | (models.MeetingRequest.professor_id == user_id)
    ).all()

def update_meeting_status(db: Session, meeting_id: str, status: str) -> models.MeetingRequest:
    meeting = db.query(models.MeetingRequest).filter(models.MeetingRequest.id == meeting_id).first()
    if meeting:
        meeting.status = status
        db.commit()
        db.refresh(meeting)
    return meeting

# ─── Quizzes ──────────────────────────────────────────────────

def get_quiz_by_topic(db: Session, topic_id: str):
    return db.query(models.Quiz).filter(models.Quiz.topic_id == topic_id, models.Quiz.quiz_type == "topic").first()

def get_quiz_by_chapter(db: Session, chapter_id: str):
    return db.query(models.Quiz).filter(models.Quiz.chapter_id == chapter_id, models.Quiz.quiz_type == "chapter").first()

def create_quiz(db: Session, data: schemas.QuizCreate) -> models.Quiz:
    db_quiz = models.Quiz(
        id=f"qz{uuid.uuid4().hex[:8]}",
        title=data.title,
        quiz_type=data.quiz_type,
        topic_id=data.topic_id,
        chapter_id=data.chapter_id
    )
    db.add(db_quiz)
    db.commit()
    db.refresh(db_quiz)
    return db_quiz

def add_quiz_question(db: Session, quiz_id: str, data: schemas.QuizQuestionCreate) -> models.QuizQuestion:
    db_question = models.QuizQuestion(
        id=f"qq{uuid.uuid4().hex[:8]}",
        quiz_id=quiz_id,
        question=data.question,
        options=data.options,
        correct_option=data.correct_option,
        explanation=data.explanation
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def update_quiz_question(db: Session, question_id: str, data: schemas.QuizQuestionUpdate) -> models.QuizQuestion:
    db_question = db.query(models.QuizQuestion).filter(models.QuizQuestion.id == question_id).first()
    if not db_question:
        return None
    if data.question is not None:
        db_question.question = data.question
    if data.options is not None:
        db_question.options = data.options
    if data.correct_option is not None:
        db_question.correct_option = data.correct_option
    if data.explanation is not None:
        db_question.explanation = data.explanation
    db.commit()
    db.refresh(db_question)
    return db_question

def delete_quiz_question(db: Session, question_id: str):
    db_question = db.query(models.QuizQuestion).filter(models.QuizQuestion.id == question_id).first()
    if db_question:
        db.delete(db_question)
        db.commit()
    return db_question

def award_points(db: Session, user_id: str, points: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.points += points
        db.commit()
    return user

# ─── Notifications ───────────────────────────────────────────

def create_notification(db: Session, notification: schemas.NotificationCreate) -> models.Notification:
    db_notification = models.Notification(
        id=f"n_{uuid.uuid4().hex[:8]}",
        **notification.model_dump()
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_notifications(db: Session, user_id: str) -> List[models.Notification]:
    return db.query(models.Notification).filter(models.Notification.user_id == user_id).order_by(models.Notification.date.desc()).all()

def mark_notification_read(db: Session, notification_id: str):
    db_notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if db_notification:
        db_notification.is_read = True
        db.commit()
        db.refresh(db_notification)
    return db_notification

def delete_notification(db: Session, notification_id: str):
    db_notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if db_notification:
        db.delete(db_notification)
        db.commit()
    return db_notification

def get_next_recommended_topic(db: Session, user_id: str):
    # Find all approved enrollments
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == user_id, 
        models.Enrollment.status == "approved"
    ).all()
    
    recommended = []
    for en in enrollments:
        course = db.query(models.Course).filter(models.Course.id == en.course_id).first()
        if not course: continue
        
        found_for_course = False
        for chapter in course.chapters:
            for topic in chapter.topics:
                # Check if this topic is completed
                done = db.query(models.TopicCompletion).filter(
                    models.TopicCompletion.user_id == user_id,
                    models.TopicCompletion.topic_id == topic.id
                ).first()
                
                if not done:
                    recommended.append({
                        "course_id": course.id,
                        "course_title": course.title,
                        "chapter_id": chapter.id,
                        "topic_id": topic.id,
                        "topic_title": topic.title
                    })
                    found_for_course = True
                    break # Next course
            if found_for_course: break
            
    return recommended
