"""Chat API endpoints."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_session, ConversationHistory, Project
from ..llm.intent_classifier import classify_intent
from ..llm.task_decomposer import decompose_task
from ..config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    project_id: str
    content: str


class ChatResponse(BaseModel):
    role: str
    content: str
    intent: Optional[dict] = None
    plan: Optional[dict] = None


@router.post("/", response_model=ChatResponse)
async def send_message(message: ChatMessage):
    """Send a chat message and get AI response."""
    session = get_session()
    try:
        # Verify project exists
        project = session.query(Project).filter(
            Project.project_id == message.project_id,
            Project.is_active == True
        ).first()
        if not project:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        # Get current sequence number
        max_seq = session.query(ConversationHistory).filter(
            ConversationHistory.project_id == message.project_id
        ).count()

        # Apply FIFO if over limit
        if max_seq >= settings.max_conversation_history:
            oldest = session.query(ConversationHistory).filter(
                ConversationHistory.project_id == message.project_id
            ).order_by(ConversationHistory.sequence_number).first()
            if oldest:
                session.delete(oldest)
                # Resequence remaining
                remaining = session.query(ConversationHistory).filter(
                    ConversationHistory.project_id == message.project_id
                ).order_by(ConversationHistory.sequence_number).all()
                for i, conv in enumerate(remaining):
                    conv.sequence_number = i + 1
            max_seq -= 1

        # Save user message
        user_msg = ConversationHistory(
            project_id=message.project_id,
            role="user",
            content=message.content,
            sequence_number=max_seq + 1
        )
        session.add(user_msg)

        # Classify intent
        intent_result = await classify_intent(message.content)

        # Decompose task
        plan_result = await decompose_task(message.content, intent_result)

        # Generate response based on intent
        response_content = generate_response(intent_result, plan_result, message.content)

        # Save assistant message
        assistant_msg = ConversationHistory(
            project_id=message.project_id,
            role="assistant",
            content=response_content,
            sequence_number=max_seq + 2
        )
        session.add(assistant_msg)
        session.commit()

        return ChatResponse(
            role="assistant",
            content=response_content,
            intent=intent_result,
            plan=plan_result
        )
    finally:
        session.close()


def generate_response(intent: dict, plan: dict, user_input: str) -> str:
    """Generate response based on intent and plan."""
    intent_type = intent.get("intent", "consultation")

    if intent_type == "paper_search":
        return f"論文検索を開始します。\n\n検索計画:\n" + \
               "\n".join([f"{s['step']}. {s['description']}" for s in plan.get("plan", [])])

    elif intent_type == "document_creation":
        return f"文書作成を開始します。\n\n作成計画:\n" + \
               "\n".join([f"{s['step']}. {s['description']}" for s in plan.get("plan", [])])

    elif intent_type == "file_operation":
        return f"ファイル操作を実行します。\n\n実行計画:\n" + \
               "\n".join([f"{s['step']}. {s['description']}" for s in plan.get("plan", [])])

    elif intent_type == "paper_recommendation":
        return "関連論文を検索して推薦します。"

    else:
        return f"ご質問を承りました。どのようにお手伝いしましょうか？\n\n意図: {intent_type}"


@router.get("/{project_id}/history")
async def get_history(project_id: str, limit: int = 50):
    """Get conversation history for a project."""
    session = get_session()
    try:
        history = session.query(ConversationHistory).filter(
            ConversationHistory.project_id == project_id
        ).order_by(ConversationHistory.sequence_number.desc()).limit(limit).all()

        return [
            {
                "role": h.role,
                "content": h.content,
                "timestamp": h.timestamp,
                "sequence_number": h.sequence_number
            }
            for h in reversed(history)
        ]
    finally:
        session.close()
