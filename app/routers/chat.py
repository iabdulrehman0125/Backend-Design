from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, ChatLog
from app.ai.agent import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Save user message
    db.add(ChatLog(user_id=current_user.id, role="user", message=payload.message))
    db.commit()

    # Run the AI agent (role-aware)
    reply = run_agent(db, current_user, payload.message)

    # Save bot reply
    db.add(ChatLog(user_id=current_user.id, role="bot", message=reply))
    db.commit()

    return ChatResponse(reply=reply)


@router.get("/history")
def chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.user_id == current_user.id)
        .order_by(ChatLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {"role": l.role, "message": l.message, "created_at": l.created_at.isoformat()}
        for l in reversed(logs)
    ]