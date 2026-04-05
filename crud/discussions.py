from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import schemas

def get_discussion(db: Session, discussion_id: str, user_id: str = "u1"):
    res = db.execute(text("""
        SELECT 
            d.id, d.author, d.author_id, d.title, d.content, d.date, 
            d.course_id, d.chapter_id, d.topic_id,
            COALESCE((SELECT SUM(vote_type) FROM discussion_votes WHERE discussion_id = d.id), 0) as upvotes,
            COALESCE((SELECT vote_type FROM discussion_votes WHERE discussion_id = d.id AND user_id = :uid), 0) as user_vote,
            r.id AS r_id, r.author AS r_author, r.author_id AS r_author_id, 
            r.text AS r_text, r.date AS r_date, r.role AS r_role,
            COALESCE((SELECT SUM(vote_type) FROM reply_votes WHERE reply_id = r.id), 0) as r_upvotes,
            COALESCE((SELECT vote_type FROM reply_votes WHERE reply_id = r.id AND user_id = :uid), 0) as r_user_vote
        FROM discussions d
        LEFT JOIN replies r ON r.discussion_id = d.id
        WHERE d.id = :did
        ORDER BY d.id DESC, r.date ASC
    """), {"uid": user_id, "did": discussion_id}).fetchall()
    
    if not res: return None
    
    did = res[0].id
    d_dict = {
        "id": did, "author": res[0].author, "author_id": res[0].author_id,
        "title": res[0].title, "content": res[0].content, "date": res[0].date,
        "course_id": res[0].course_id, "chapter_id": res[0].chapter_id, "topic_id": res[0].topic_id,
        "upvotes": res[0].upvotes, "user_vote": res[0].user_vote,
        "replyList": []
    }
    
    for row in res:
        if row.r_id:
            d_dict["replyList"].append({
                "id": row.r_id, "author": row.r_author, "author_id": row.r_author_id,
                "text": row.r_text, "date": row.r_date, "role": row.r_role,
                "upvotes": row.r_upvotes, "user_vote": row.r_user_vote
            })
            
    return schemas.Discussion(
        id=d_dict["id"], author=d_dict["author"], authorId=d_dict["author_id"],
        title=d_dict["title"], content=d_dict["content"], date=d_dict["date"],
        courseId=d_dict["course_id"], chapterId=d_dict["chapter_id"], topicId=d_dict["topic_id"],
        upvotes=d_dict["upvotes"], userVote=d_dict["user_vote"],
        replies=len(d_dict["replyList"]), replyList=[schemas.Reply.model_validate(r) for r in d_dict["replyList"]]
    )

def get_discussions(db: Session, user_id: str = "u1") -> List[schemas.Discussion]:
    discussions = db.execute(text("""
        SELECT 
            d.id, d.author, d.author_id, d.title, d.content, d.date, 
            d.course_id, d.chapter_id, d.topic_id,
            COALESCE((SELECT SUM(vote_type) FROM discussion_votes WHERE discussion_id = d.id), 0) as upvotes,
            COALESCE((SELECT vote_type FROM discussion_votes WHERE discussion_id = d.id AND user_id = :uid), 0) as user_vote,
            r.id AS r_id, r.author AS r_author, r.author_id AS r_author_id, 
            r.text AS r_text, r.date AS r_date, r.role AS r_role,
            COALESCE((SELECT SUM(vote_type) FROM reply_votes WHERE reply_id = r.id), 0) as r_upvotes,
            COALESCE((SELECT vote_type FROM reply_votes WHERE reply_id = r.id AND user_id = :uid), 0) as r_user_vote
        FROM discussions d
        LEFT JOIN replies r ON r.discussion_id = d.id
        ORDER BY d.id DESC, r.date ASC
    """), {"uid": user_id}).fetchall()

    d_dict = {}
    for row in discussions:
        did = row.id
        if did not in d_dict:
            d_dict[did] = {
                "id": did, "author": row.author, "author_id": row.author_id,
                "title": row.title, "content": row.content, "date": row.date,
                "course_id": row.course_id, "chapter_id": row.chapter_id, "topic_id": row.topic_id,
                "upvotes": row.upvotes, "user_vote": row.user_vote,
                "replyList": []
            }
        
        if row.r_id:
            d_dict[did]["replyList"].append({
                "id": row.r_id, "author": row.r_author, "author_id": row.r_author_id,
                "text": row.r_text, "date": row.r_date, "role": row.r_role,
                "upvotes": row.r_upvotes, "user_vote": row.r_user_vote
            })

    result = []
    for did, data in d_dict.items():
        result.append(schemas.Discussion(
            id=data["id"], author=data["author"], authorId=data["author_id"],
            title=data["title"], content=data["content"], date=data["date"],
            courseId=data["course_id"], chapterId=data["chapter_id"], topicId=data["topic_id"],
            upvotes=data["upvotes"], userVote=data["user_vote"],
            replies=len(data["replyList"]), replyList=[schemas.Reply.model_validate(r) for r in data["replyList"]]
        ))
    return result

def create_discussion(db: Session, discussion: schemas.DiscussionBase):
    db.execute(text("""
        INSERT INTO discussions (id, author, author_id, title, content, date, course_id, chapter_id, topic_id)
        VALUES (:id, :author, :author_id, :title, :content, :date, :course_id, :chapter_id, :topic_id)
    """), {
        "id": discussion.id, "author": discussion.author, "author_id": discussion.authorId,
        "title": discussion.title, "content": discussion.content, "date": discussion.date,
        "course_id": discussion.courseId, "chapter_id": discussion.chapterId, "topic_id": discussion.topicId
    })
    db.commit()
    return get_discussion(db, discussion.id, discussion.authorId)

def create_reply(db: Session, discussion_id: str, reply: schemas.ReplyBase):
    db.execute(text("""
        INSERT INTO replies (id, author, author_id, text, date, role, discussion_id)
        VALUES (:id, :author, :author_id, :text, :date, :role, :discussion_id)
    """), {
        "id": reply.id, "author": reply.author, "author_id": reply.authorId,
        "text": reply.text, "date": reply.date, "role": reply.role, "discussion_id": discussion_id
    })
    db.commit()
    return reply

def vote_discussion(db: Session, discussion_id: str, user_id: str, vote_type: int):
    # Upsert logic
    prior = db.execute(text("SELECT * FROM discussion_votes WHERE discussion_id=:d AND user_id=:u"), {"d": discussion_id, "u": user_id}).fetchone()
    if prior:
        db.execute(text("UPDATE discussion_votes SET vote_type=:v WHERE discussion_id=:d AND user_id=:u"), {"v": vote_type, "d": discussion_id, "u": user_id})
    else:
        db.execute(text("INSERT INTO discussion_votes (discussion_id, user_id, vote_type) VALUES (:d, :u, :v)"), {"d": discussion_id, "u": user_id, "v": vote_type})
    db.commit()
    ups = db.execute(text("SELECT SUM(vote_type) as s FROM discussion_votes WHERE discussion_id=:d"), {"d": discussion_id}).fetchone().s or 0
    uv = db.execute(text("SELECT vote_type FROM discussion_votes WHERE discussion_id=:d AND user_id=:u"), {"d": discussion_id, "u": user_id}).fetchone().vote_type or 0
    return {"upvotes": ups, "user_vote": uv}

def vote_reply(db: Session, reply_id: str, user_id: str, vote_type: int):
    prior = db.execute(text("SELECT * FROM reply_votes WHERE reply_id=:r AND user_id=:u"), {"r": reply_id, "u": user_id}).fetchone()
    if prior:
        db.execute(text("UPDATE reply_votes SET vote_type=:v WHERE reply_id=:r AND user_id=:u"), {"v": vote_type, "r": reply_id, "u": user_id})
    else:
        db.execute(text("INSERT INTO reply_votes (reply_id, user_id, vote_type) VALUES (:r, :u, :v)"), {"r": reply_id, "u": user_id, "v": vote_type})
    db.commit()
    ups = db.execute(text("SELECT SUM(vote_type) as s FROM reply_votes WHERE reply_id=:r"), {"r": reply_id}).fetchone().s or 0
    uv = db.execute(text("SELECT vote_type FROM reply_votes WHERE reply_id=:r AND user_id=:u"), {"r": reply_id, "u": user_id}).fetchone().vote_type or 0
    return {"upvotes": ups, "user_vote": uv}
