from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import schemas



def _fetch_discussion_row(db: Session, discussion_id: str, user_id: str):
    """Fetch a single discussion row with its vote totals."""
    return db.execute(text("""
        SELECT
            d.id, d.author, d.author_id, d.title, d.content, d.date,
            d.course_id, d.chapter_id, d.topic_id,
            COALESCE(
                (SELECT SUM(vote_type) FROM discussion_votes WHERE discussion_id = d.id),
            0) AS upvotes,
            COALESCE(
                (SELECT vote_type FROM discussion_votes WHERE discussion_id = d.id AND user_id = :uid),
            0) AS user_vote
        FROM discussions d
        WHERE d.id = :did
    """), {"uid": user_id, "did": discussion_id}).fetchone()


def _fetch_all_discussion_rows(db: Session, user_id: str):
    """Fetch all discussion rows with their vote totals."""
    return db.execute(text("""
        SELECT
            d.id, d.author, d.author_id, d.title, d.content, d.date,
            d.course_id, d.chapter_id, d.topic_id,
            COALESCE(
                (SELECT SUM(vote_type) FROM discussion_votes WHERE discussion_id = d.id),
            0) AS upvotes,
            COALESCE(
                (SELECT vote_type FROM discussion_votes WHERE discussion_id = d.id AND user_id = :uid),
            0) AS user_vote
        FROM discussions d
        ORDER BY d.id DESC
    """), {"uid": user_id}).fetchall()


def _fetch_replies(db: Session, discussion_id: str, user_id: str):
    """Fetch all replies for a discussion with their vote totals."""
    return db.execute(text("""
        SELECT
            r.id, r.author, r.author_id, r.text, r.date, r.role,
            COALESCE(
                (SELECT SUM(vote_type) FROM reply_votes WHERE reply_id = r.id),
            0) AS upvotes,
            COALESCE(
                (SELECT vote_type FROM reply_votes WHERE reply_id = r.id AND user_id = :uid),
            0) AS user_vote
        FROM replies r
        WHERE r.discussion_id = :did
        ORDER BY r.date ASC
    """), {"uid": user_id, "did": discussion_id}).fetchall()


def _get_vote_totals(db: Session, table: str, id_col: str, row_id: str, user_id: str):
    """Return (total_votes, user_vote) for a discussion or reply."""
    total = db.execute(
        text(f"SELECT COALESCE(SUM(vote_type), 0) AS s FROM {table} WHERE {id_col} = :rid"),
        {"rid": row_id}
    ).fetchone().s or 0

    uv_row = db.execute(
        text(f"SELECT vote_type FROM {table} WHERE {id_col} = :rid AND user_id = :uid"),
        {"rid": row_id, "uid": user_id}
    ).fetchone()
    user_vote = uv_row.vote_type if uv_row else 0

    return total, user_vote


def _build_discussion(row, replies: list) -> schemas.Discussion:
    """Assemble a Discussion schema object from a row + reply list."""
    reply_list = [schemas.Reply.model_validate(r) for r in replies]
    return schemas.Discussion(
        id=row.id,
        author=row.author,
        authorId=row.author_id,
        title=row.title,
        content=row.content,
        date=row.date,
        courseId=row.course_id,
        chapterId=row.chapter_id,
        topicId=row.topic_id,
        upvotes=row.upvotes,
        userVote=row.user_vote,
        replies=len(reply_list),
        replyList=reply_list,
    )


# ---------------------------------------------------------------------------
# Public CRUD functions
# ---------------------------------------------------------------------------

def get_discussion(db: Session, discussion_id: str, user_id: str = "u1") -> Optional[schemas.Discussion]:
    row = _fetch_discussion_row(db, discussion_id, user_id)
    if not row:
        return None

    reply_rows = _fetch_replies(db, discussion_id, user_id)
    replies = [
        {
            "id": r.id, "author": r.author, "author_id": r.author_id,
            "text": r.text, "date": r.date, "role": r.role,
            "upvotes": r.upvotes, "user_vote": r.user_vote,
        }
        for r in reply_rows
    ]
    return _build_discussion(row, replies)


def get_discussions(db: Session, user_id: str = "u1") -> List[schemas.Discussion]:
    rows = _fetch_all_discussion_rows(db, user_id)
    result = []
    for row in rows:
        reply_rows = _fetch_replies(db, row.id, user_id)
        replies = [
            {
                "id": r.id, "author": r.author, "author_id": r.author_id,
                "text": r.text, "date": r.date, "role": r.role,
                "upvotes": r.upvotes, "user_vote": r.user_vote,
            }
            for r in reply_rows
        ]
        result.append(_build_discussion(row, replies))
    return result


def create_discussion(db: Session, discussion: schemas.DiscussionBase):
    db.execute(text("""
        INSERT INTO discussions (id, author, author_id, title, content, date, course_id, chapter_id, topic_id)
        VALUES (:id, :author, :author_id, :title, :content, :date, :course_id, :chapter_id, :topic_id)
    """), {
        "id": discussion.id,
        "author": discussion.author,
        "author_id": discussion.authorId,
        "title": discussion.title,
        "content": discussion.content,
        "date": discussion.date,
        "course_id": discussion.courseId,
        "chapter_id": discussion.chapterId,
        "topic_id": discussion.topicId,
    })
    db.commit()
    return get_discussion(db, discussion.id, discussion.authorId)


def create_reply(db: Session, discussion_id: str, reply: schemas.ReplyBase):
    db.execute(text("""
        INSERT INTO replies (id, author, author_id, text, date, role, discussion_id)
        VALUES (:id, :author, :author_id, :text, :date, :role, :discussion_id)
    """), {
        "id": reply.id,
        "author": reply.author,
        "author_id": reply.authorId,
        "text": reply.text,
        "date": reply.date,
        "role": reply.role,
        "discussion_id": discussion_id,
    })
    db.commit()
    return reply


def vote_discussion(db: Session, discussion_id: str, user_id: str, vote_type: int):
    existing = db.execute(
        text("SELECT * FROM discussion_votes WHERE discussion_id = :d AND user_id = :u"),
        {"d": discussion_id, "u": user_id}
    ).fetchone()

    if existing:
        db.execute(
            text("UPDATE discussion_votes SET vote_type = :v WHERE discussion_id = :d AND user_id = :u"),
            {"v": vote_type, "d": discussion_id, "u": user_id}
        )
    else:
        db.execute(
            text("INSERT INTO discussion_votes (discussion_id, user_id, vote_type) VALUES (:d, :u, :v)"),
            {"d": discussion_id, "u": user_id, "v": vote_type}
        )
    db.commit()

    total, user_vote = _get_vote_totals(db, "discussion_votes", "discussion_id", discussion_id, user_id)
    return {"upvotes": total, "user_vote": user_vote}


def vote_reply(db: Session, reply_id: str, user_id: str, vote_type: int):
    existing = db.execute(
        text("SELECT * FROM reply_votes WHERE reply_id = :r AND user_id = :u"),
        {"r": reply_id, "u": user_id}
    ).fetchone()

    if existing:
        db.execute(
            text("UPDATE reply_votes SET vote_type = :v WHERE reply_id = :r AND user_id = :u"),
            {"v": vote_type, "r": reply_id, "u": user_id}
        )
    else:
        db.execute(
            text("INSERT INTO reply_votes (reply_id, user_id, vote_type) VALUES (:r, :u, :v)"),
            {"r": reply_id, "u": user_id, "v": vote_type}
        )
    db.commit()

    total, user_vote = _get_vote_totals(db, "reply_votes", "reply_id", reply_id, user_id)
    return {"upvotes": total, "user_vote": user_vote}
