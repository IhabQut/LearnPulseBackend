CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT,
    role TEXT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    phone_number TEXT DEFAULT '',
    bio TEXT DEFAULT ''
);
CREATE TABLE professors (
    id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    department TEXT DEFAULT '',
    expertise TEXT DEFAULT '',
    academic_rank TEXT DEFAULT '',
    office_location TEXT DEFAULT '',
    meeting_link TEXT DEFAULT '',
    zoom_enabled BOOLEAN DEFAULT 1,
    in_person_enabled BOOLEAN DEFAULT 1
);
CREATE TABLE students (
    id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    major TEXT DEFAULT '',
    level TEXT DEFAULT 'Undergraduate',
    gpa REAL DEFAULT 0.0,
    graduation_year INTEGER
);
CREATE TABLE user_office_hours (
    id TEXT PRIMARY KEY,
    professor_id TEXT REFERENCES professors(id) ON DELETE CASCADE,
    day TEXT,
    time TEXT
);
CREATE TABLE courses (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    category TEXT DEFAULT 'General',
    image TEXT DEFAULT '',
    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    is_open BOOLEAN DEFAULT 1
);
CREATE TABLE materials (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    url TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE
);
CREATE TABLE chapters (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE
);
CREATE TABLE topics (
    id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE,
    "order" INTEGER DEFAULT 0
);
CREATE TABLE topic_completions (
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, topic_id)
);
CREATE TABLE discussions (
    id TEXT PRIMARY KEY,
    author TEXT,
    author_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    content TEXT,
    date TEXT,
    course_id TEXT REFERENCES courses(id) ON DELETE SET NULL,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE SET NULL,
    topic_id TEXT REFERENCES topics(id) ON DELETE SET NULL
);
CREATE TABLE replies (
    id TEXT PRIMARY KEY,
    author TEXT,
    author_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    text TEXT,
    date TEXT,
    role TEXT,
    discussion_id TEXT REFERENCES discussions(id) ON DELETE CASCADE
);
CREATE TABLE discussion_votes (
    discussion_id TEXT REFERENCES discussions(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    vote_type INTEGER DEFAULT 0,
    PRIMARY KEY (discussion_id, user_id)
);
CREATE TABLE reply_votes (
    reply_id TEXT REFERENCES replies(id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    vote_type INTEGER DEFAULT 0,
    PRIMARY KEY (reply_id, user_id)
);
CREATE TABLE quizzes (
    id TEXT PRIMARY KEY,
    title TEXT,
    quiz_type TEXT,
    topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
    chapter_id TEXT REFERENCES chapters(id) ON DELETE CASCADE
);
CREATE TABLE quiz_questions (
    id TEXT PRIMARY KEY,
    quiz_id TEXT REFERENCES quizzes(id) ON DELETE CASCADE,
    question TEXT,
    explanation TEXT
);
CREATE TABLE quiz_options (
    id TEXT PRIMARY KEY,
    question_id TEXT REFERENCES quiz_questions(id) ON DELETE CASCADE,
    text TEXT,
    is_correct BOOLEAN DEFAULT 0
);
CREATE TABLE quiz_attempts (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    quiz_id TEXT REFERENCES quizzes(id) ON DELETE CASCADE,
    score INTEGER,
    total INTEGER,
    date TEXT,
    is_first_attempt BOOLEAN DEFAULT 1
);
CREATE TABLE enrollments (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending',
    role TEXT DEFAULT 'student',
    date TEXT,
    points INTEGER DEFAULT 0
);
CREATE TABLE meeting_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    professor_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    note TEXT,
    slot TEXT,
    meeting_type TEXT,
    status TEXT DEFAULT 'pending',
    date TEXT
);
CREATE TABLE notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    message TEXT,
    type TEXT,
    is_read BOOLEAN DEFAULT 0,
    date TEXT
);
CREATE TABLE course_textbooks (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    filename TEXT,
    file_type TEXT,
    status TEXT DEFAULT 'done'
);
CREATE TABLE grading_components (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    name TEXT,
    weight REAL,
    component_type TEXT DEFAULT 'assessment'
);
CREATE TABLE semester_weeks (
    id TEXT PRIMARY KEY,
    course_id TEXT REFERENCES courses(id) ON DELETE CASCADE,
    week_num INTEGER,
    chapter_title TEXT DEFAULT '',
    topics_json TEXT DEFAULT '[]',
    notes TEXT DEFAULT ''
);