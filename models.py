from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    role = Column(String)
    points = Column(Integer, default=0)
    email = Column(String, default="")
    bio = Column(Text, default="")
    office_hours = Column(Text, default="[]")   # JSON string for professors
    meeting_link = Column(String, default="")
    zoom_enabled = Column(Boolean, default=True)
    in_person_enabled = Column(Boolean, default=True)

    topic_completions = relationship("TopicCompletion", back_populates="user")
    enrollments = relationship("Enrollment", back_populates="user")

class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    professor_id = Column(String, ForeignKey("users.id"), nullable=True)

    chapters = relationship("Chapter", back_populates="course", cascade="all, delete-orphan")
    materials = relationship("Material", back_populates="course", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
    professor = relationship("User", foreign_keys=[professor_id])

class Material(Base):
    __tablename__ = "materials"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    url = Column(String)
    course_id = Column(String, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="materials")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    summary = Column(Text)
    course_id = Column(String, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="chapter")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    chapter_id = Column(String, ForeignKey("chapters.id"))
    order = Column(Integer, default=0)

    chapter = relationship("Chapter", back_populates="topics")
    completions = relationship("TopicCompletion", back_populates="topic")

class TopicCompletion(Base):
    __tablename__ = "topic_completions"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    topic_id = Column(String, ForeignKey("topics.id"), primary_key=True)

    user = relationship("User", back_populates="topic_completions")
    topic = relationship("Topic", back_populates="completions")

class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(String, primary_key=True, index=True)
    author = Column(String)
    author_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    content = Column(Text)
    date = Column(String)
    course_id = Column(String, ForeignKey("courses.id"), nullable=True)
    chapter_id = Column(String, ForeignKey("chapters.id"), nullable=True)
    topic_id = Column(String, ForeignKey("topics.id"), nullable=True)

    course = relationship("Course", back_populates="discussions")
    chapter = relationship("Chapter", back_populates="discussions")
    topic = relationship("Topic")
    replies = relationship("Reply", back_populates="discussion", cascade="all, delete-orphan")
    user = relationship("User")

class Reply(Base):
    __tablename__ = "replies"

    id = Column(String, primary_key=True, index=True)
    author = Column(String)
    author_id = Column(String, ForeignKey("users.id"))
    text = Column(Text)
    date = Column(String)
    role = Column(String)
    discussion_id = Column(String, ForeignKey("discussions.id"))

    discussion = relationship("Discussion", back_populates="replies")
    user = relationship("User")

# ─── Quiz System ────────────────────────────────────────────────

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    quiz_type = Column(String)  # 'topic' or 'chapter'
    topic_id = Column(String, ForeignKey("topics.id"), nullable=True)
    chapter_id = Column(String, ForeignKey("chapters.id"), nullable=True)

    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz")

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(String, primary_key=True, index=True)
    quiz_id = Column(String, ForeignKey("quizzes.id"))
    question = Column(Text)
    options = Column(Text)  # JSON string of options list
    correct_option = Column(Integer)
    explanation = Column(Text)

    quiz = relationship("Quiz", back_populates="questions")

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    quiz_id = Column(String, ForeignKey("quizzes.id"))
    score = Column(Integer)
    total = Column(Integer)
    date = Column(String)
    is_first_attempt = Column(Boolean, default=True)

    user = relationship("User")
    quiz = relationship("Quiz", back_populates="attempts")

# ─── Enrollment System ──────────────────────────────────────────

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    course_id = Column(String, ForeignKey("courses.id"))
    status = Column(String, default="pending")  # 'pending' or 'approved'
    date = Column(String)

    user = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")

# ─── Meeting System ─────────────────────────────────────────────

class MeetingRequest(Base):
    __tablename__ = "meeting_requests"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    professor_id = Column(String, ForeignKey("users.id"))
    note = Column(Text)
    slot = Column(String)
    meeting_type = Column(String)  # 'Zoom' or 'In-person'
    status = Column(String, default="pending")  # 'pending', 'approved', 'rejected'
    date = Column(String)

    user = relationship("User", foreign_keys=[user_id])
    professor = relationship("User", foreign_keys=[professor_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    title = Column(String)
    message = Column(Text)
    type = Column(String) # 'info', 'success', 'warning', 'error'
    is_read = Column(Boolean, default=False)
    date = Column(String)

    user = relationship("User")
