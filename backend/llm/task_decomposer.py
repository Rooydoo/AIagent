"""LLM2: Task decomposition."""
import json
from typing import Optional
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

TASK_DECOMPOSITION_PROMPT = """あなたはタスクを段階的に分解するプランナーです。

【指示】
ユーザーの要求を実行するための段階的なプランを作成してください。

【出力形式】
必ずJSON形式で出力してください:
{
  "plan": [
    {"step": 1, "action": "アクション名", "description": "説明"},
    {"step": 2, "action": "アクション名", "description": "説明"}
  ],
  "estimated_time": "推定時間",
  "required_tools": ["必要なツールリスト"]
}

JSONのみを出力し、他のテキストは含めないでください。"""


async def decompose_task(user_request: str, intent_result: dict) -> dict:
    """Decompose task into steps.

    Args:
        user_request: User's original request
        intent_result: Result from intent classification

    Returns:
        Dictionary with task decomposition plan
    """
    llm = get_llm("summarization")  # Use Haiku for planning

    prompt = f"""【ユーザーの要求】
{user_request}

【意図分類結果】
{json.dumps(intent_result, ensure_ascii=False)}"""

    messages = [
        SystemMessage(content=TASK_DECOMPOSITION_PROMPT),
        HumanMessage(content=prompt)
    ]

    try:
        response = await llm.ainvoke(messages)
        result = json.loads(response.content)
        return result
    except json.JSONDecodeError:
        return {
            "plan": [{"step": 1, "action": "process", "description": "リクエストを処理"}],
            "estimated_time": "不明",
            "required_tools": []
        }
    except Exception as e:
        return {
            "plan": [],
            "error": str(e)
        }
