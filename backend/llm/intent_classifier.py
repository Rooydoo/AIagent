"""LLM1: Intent classification."""
import json
from typing import Optional
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

INTENT_CLASSIFICATION_PROMPT = """あなたはユーザーの入力を分類するエージェントです。
以下のいずれかに必ず分類してください。

【分類カテゴリ】
1. paper_search: 論文を検索したい
2. document_creation: 文書を作成・編集したい
3. file_operation: ファイル・フォルダを操作したい
4. paper_recommendation: 特定の内容に合う論文を推薦してほしい
5. consultation: 相談・質問・雑談

【出力形式】
必ずJSON形式で出力してください:
{
  "intent": "分類カテゴリ",
  "sub_intent": "詳細な意図（あれば）",
  "parameters": {},
  "confidence": 0.0-1.0
}

JSONのみを出力し、他のテキストは含めないでください。"""


async def classify_intent(user_input: str, conversation_history: Optional[list] = None) -> dict:
    """Classify user intent.

    Args:
        user_input: User's input text
        conversation_history: Optional conversation history for context

    Returns:
        Dictionary with intent classification result
    """
    llm = get_llm("summarization")  # Use Haiku for fast classification

    messages = [
        SystemMessage(content=INTENT_CLASSIFICATION_PROMPT),
        HumanMessage(content=f"【ユーザー入力】\n{user_input}")
    ]

    try:
        response = await llm.ainvoke(messages)
        result = json.loads(response.content)
        return result
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "intent": "consultation",
            "sub_intent": None,
            "parameters": {},
            "confidence": 0.5
        }
    except Exception as e:
        return {
            "intent": "consultation",
            "sub_intent": None,
            "parameters": {},
            "confidence": 0.0,
            "error": str(e)
        }
