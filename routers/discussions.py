from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

import crud
import schemas
import models
from database import get_db

router = APIRouter(prefix="/api/discussions", tags=["Discussions"])

@router.get("", response_model=List[schemas.Discussion])
def read_discussions(user_id: Optional[str] = "u1", db: Session = Depends(get_db)):
    return crud.get_discussions(db, user_id)

@router.get("/{discussion_id}", response_model=schemas.Discussion)
def read_discussion(discussion_id: str, user_id: Optional[str] = "u1", db: Session = Depends(get_db)):
    d = crud.get_discussion(db, discussion_id, user_id)
    if not d:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return d

@router.post("", response_model=schemas.Discussion)
def create_discussion(discussion: schemas.DiscussionBase, db: Session = Depends(get_db)):
    return crud.create_discussion(db, discussion)

@router.post("/{discussion_id}/replies", response_model=schemas.Reply)
def create_reply(discussion_id: str, reply: schemas.ReplyBase, db: Session = Depends(get_db)):
    created_reply = crud.create_reply(db, discussion_id, reply)
    # Notify discussion author
    discussion = crud.get_discussion(db, discussion_id, reply.authorId)
    if discussion and discussion.authorId != reply.authorId:
        import crud as _crud
        _crud.create_notification(db, schemas.NotificationCreate(
            user_id=discussion.authorId, title="New Reply on your Discussion",
            message=f"Someone has replied to your discussion: '{discussion.title}'",
            type="info", date=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    return created_reply

@router.post("/{discussion_id}/vote")
def set_discussion_vote(discussion_id: str, vote: schemas.VoteRequest, db: Session = Depends(get_db)):
    return crud.vote_discussion(db, discussion_id, vote.user_id, vote.vote_type)

@router.post("/replies/{reply_id}/vote")
def set_reply_vote(reply_id: str, vote: schemas.VoteRequest, db: Session = Depends(get_db)):
    return crud.vote_reply(db, reply_id, vote.user_id, vote.vote_type)

@router.post("/{discussion_id}/award-points")
def award_discussion_points(discussion_id: str, data: schemas.PointAward, db: Session = Depends(get_db)):
    d = db.execute(text("SELECT course_id FROM discussions WHERE id=:id"), {"id": discussion_id}).fetchone()
    if d and d.course_id:
        import crud.users as _users
        import crud as _crud
        _users.award_course_points(db, data.user_id, d.course_id, data.points)
        _crud.create_notification(db, schemas.NotificationCreate(
            user_id=data.user_id, title="Points Awarded!",
            message=f"A professor has awarded you {data.points} points for your contribution to the discussion.",
            type="success", date=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    return {"message": f"Awarded {data.points} points to user {data.user_id}"}
