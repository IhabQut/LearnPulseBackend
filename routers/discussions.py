from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

import crud
import schemas
import models
from database import get_db

router = APIRouter(prefix="/api/discussions", tags=["Discussions"])

@router.get("", response_model=List[schemas.Discussion])
def read_discussions(db: Session = Depends(get_db)):
    return crud.get_discussions(db)

@router.post("", response_model=schemas.Discussion)
def create_discussion(discussion: schemas.DiscussionBase, db: Session = Depends(get_db)):
    created = crud.create_discussion(db, discussion)
    all_disc = crud.get_discussions(db)
    for d in all_disc:
        if d.id == created.id:
            return d
    return all_disc[0] if all_disc else schemas.Discussion.model_validate(created)

@router.post("/{discussion_id}/replies", response_model=schemas.Reply)
def create_reply(discussion_id: str, reply: schemas.ReplyBase, db: Session = Depends(get_db)):
    created_reply = crud.create_reply(db, discussion_id, reply)
    
    # Notify discussion author (unless they are the one replying)
    discussion = crud.get_discussion(db, discussion_id)
    if discussion and discussion.user_id != reply.user_id:
        crud.create_notification(db, schemas.NotificationCreate(
            user_id=discussion.user_id,
            title="New Reply on your Discussion",
            message=f"Someone has replied to your discussion: '{discussion.title}'",
            type="info",
            date=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
    
    return created_reply

@router.post("/{discussion_id}/award-points")
def award_discussion_points(discussion_id: str, data: schemas.PointAward, db: Session = Depends(get_db)):
    """Professor manually awards points to a student for discussion participation."""
    crud.award_points(db, data.user_id, data.points)
    
    # Notify student
    crud.create_notification(db, schemas.NotificationCreate(
        user_id=data.user_id,
        title="Points Awarded!",
        message=f"A professor has awarded you {data.points} points for your contribution to the discussion.",
        type="success",
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    
    return {"message": f"Awarded {data.points} points to user {data.user_id}"}
