from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

class UserBase(BaseModel):
    id: str
    name: str
    role: str
    email: Optional[str] = ""
    phone_number: Optional[str] = ""
    bio: Optional[str] = ""

class StudentProfile(BaseModel):
    points: int = 0
    major: str = ""
    level: str = "Undergraduate"
    gpa: float = 0.0
    graduation_year: Optional[int] = None

    class Config:
        from_attributes = True

class ProfessorProfile(BaseModel):
    department: str = ""
    expertise: str = ""
    academic_rank: str = ""
    office_location: str = ""
    meeting_link: str = ""
    zoom_enabled: bool = True
    in_person_enabled: bool = True
    office_hours: str = "[]" # Serialized JSON

    class Config:
        from_attributes = True

class RecentActivity(BaseModel):
    id: str
    type: str  # 'topic_completion' or 'quiz_attempt'
    title: str
    date: str
    detail: str = ""

class UserStats(BaseModel):
    completed_topics_count: int = 0
    quizzes_taken_count: int = 0
    average_quiz_score: float = 0.0
    courses_enrolled_count: int = 0
    managed_students_count: int = 0
    total_courses_count: int = 0
    recent_activity: List[RecentActivity] = []

class User(UserBase):
    student: Optional[StudentProfile] = None
    professor: Optional[ProfessorProfile] = None
    stats: Optional[UserStats] = None

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    
    # Student fields
    major: Optional[str] = None
    level: Optional[str] = None
    graduation_year: Optional[int] = None
    
    # Professor fields
    department: Optional[str] = None
    expertise: Optional[str] = None
    academic_rank: Optional[str] = None
    office_location: Optional[str] = None
    office_hours: Optional[str] = None # JSON string
    meeting_link: Optional[str] = None
    zoom_enabled: Optional[bool] = None
    in_person_enabled: Optional[bool] = None

class MaterialBase(BaseModel):
    id: str
    name: str
    type: str
    url: str

class MaterialCreate(BaseModel):
    name: str
    type: str
    url: str

class Material(MaterialBase):
    course_id: str

    class Config:
        from_attributes = True

# ─── Notifications ───────────────────────────────────────────

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    date: str

class NotificationCreate(NotificationBase):
    user_id: str

class Notification(NotificationBase):
    id: str
    user_id: str
    is_read: bool

    class Config:
        from_attributes = True

class TopicBase(BaseModel):
    id: str
    title: str
    description: str

class Topic(TopicBase):
    completed: bool = False
    order: int = 0

    class Config:
        from_attributes = True

class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)

class TopicUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class ChapterBase(BaseModel):
    id: str
    title: str
    summary: str

class Chapter(ChapterBase):
    topics: List[Topic] = []

    class Config:
        from_attributes = True

class ChapterCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(default="", max_length=5000)

class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None

class CourseBase(BaseModel):
    id: str
    title: str
    description: str
    is_open: bool = True

class CourseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_open: Optional[bool] = None

class Course(CourseBase):
    materials: List[Material] = []
    chapters: List[Chapter] = []
    professor_id: Optional[str] = None
    professor_name: Optional[str] = ""
    student_count: int = 0
    category: Optional[str] = ""
    image: Optional[str] = ""
    user_role: Optional[str] = None

    class Config:
        from_attributes = True

class ReplyBase(BaseModel):
    id: str
    author: str
    authorId: str = Field(alias="author_id")
    text: str
    date: str
    role: str
    upvotes: int = 0
    userVote: int = Field(default=0, alias="user_vote")

    class Config:
        populate_by_name = True  # accept authorId or author_id in request body

class Reply(ReplyBase):
    class Config:
        from_attributes = True
        populate_by_name = True

class DiscussionBase(BaseModel):
    id: str
    author: str
    authorId: str = Field(alias="author_id")
    title: str
    content: str
    date: str
    courseId: Optional[str] = Field(default=None, alias="course_id")
    chapterId: Optional[str] = Field(default=None, alias="chapter_id")
    topicId: Optional[str] = Field(default=None, alias="topic_id")
    upvotes: int = 0
    userVote: int = Field(default=0, alias="user_vote")

    class Config:
        populate_by_name = True

class VoteRequest(BaseModel):
    user_id: str
    vote_type: int

class Discussion(DiscussionBase):
    replies: int = 0
    replyList: List[Reply] = []

    class Config:
        from_attributes = True
        populate_by_name = True

# ─── Enrollment ──────────────────────────────────────────────

class EnrollmentOut(BaseModel):
    id: str
    user_id: str
    course_id: str
    status: str
    role: str
    date: str
    user_name: str = ""

    class Config:
        from_attributes = True

class EnrollRequest(BaseModel):
    course_id: str
    role: Optional[str] = "student" # 'student' or 'viewer'

class EnrollStudentRequest(BaseModel):
    user_id: str
    role: Optional[str] = "student"

class PointAward(BaseModel):
    user_id: str
    points: int

# ─── AI Analytics ────────────────────────────────────────────

class StrugglingTopic(BaseModel):
    topic_title: str
    chapter_title: str
    fail_rate: float
    common_mistake: str = ""

class StudentParticipation(BaseModel):
    student_id: str
    student_name: str
    topics_completed: int
    quizzes_taken: int

class AIReport(BaseModel):
    course_title: str
    total_students: int
    struggling_topics: List[StrugglingTopic] = []
    low_participation: List[StudentParticipation] = []
    high_performers: List[StudentParticipation] = []
    insight: str = ""

# ─── Meetings ────────────────────────────────────────────────

class MeetingRequestBase(BaseModel):
    id: str
    user_id: str
    professor_id: str
    note: str
    slot: str
    meeting_type: str
    status: str
    date: str

class MeetingRequestCreate(BaseModel):
    professor_id: str
    note: str
    slot: str
    meeting_type: str

class MeetingRequestOut(MeetingRequestBase):
    user_name: str = ""
    professor_name: str = ""

    class Config:
        from_attributes = True

# ─── Quizzes ──────────────────────────────────────────────────

class QuizQuestionBase(BaseModel):
    id: str
    question: str
    options: str  # JSON string
    correct_option: int
    explanation: str

class QuizQuestionCreate(BaseModel):
    question: str
    options: str  # JSON string
    correct_option: int
    explanation: str

class QuizQuestionUpdate(BaseModel):
    question: Optional[str] = None
    options: Optional[str] = None
    correct_option: Optional[int] = None
    explanation: Optional[str] = None

class QuizBase(BaseModel):
    id: str
    title: str
    quiz_type: str
    topic_id: Optional[str] = None
    chapter_id: Optional[str] = None

class QuizCreate(BaseModel):
    title: str
    quiz_type: str
    topic_id: Optional[str] = None
    chapter_id: Optional[str] = None

class QuizAttemptOut(BaseModel):
    id: str
    user_id: str
    quiz_id: str
    score: int
    total: int
    date: str
    is_first_attempt: bool = True
    points_awarded: int = 0
    
    class Config:
        from_attributes = True

class StudentQuizAttempt(QuizAttemptOut):
    quiz_title: str = ""
    user_name: str = ""

# ─── Student Analytics ───────────────────────────────────────

class RecommendedTopic(BaseModel):
    course_id: str
    course_title: str
    chapter_id: str
    topic_id: str
    topic_title: str

class StudentAnalyticsOut(BaseModel):
    quiz_attempts: List[StudentQuizAttempt] = []
    recommended_topics: List[RecommendedTopic] = []
    overall_progress: float = 0.0
