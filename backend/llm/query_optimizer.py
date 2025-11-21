"""Query optimization for PubMed search."""
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

QUERY_OPTIMIZATION_PROMPT = """あなたはPubMed検索クエリを最適化する専門家です。

【指示】
PubMedで最適な検索結果を得るための英語の検索クエリを生成してください。
- 医学用語の正式名称を使用
- 適切な同義語を含める
- 検索演算子は使わない（AND, OR等は不要、スペース区切りで十分）
- 日本語の入力は英語に翻訳

【出力形式】
英語の検索クエリのみを出力してください（説明不要）。"""


async def optimize_query(user_query: str) -> str:
    """Optimize search query for PubMed.

    Args:
        user_query: User's search query in any language

    Returns:
        Optimized English query for PubMed
    """
    llm = get_llm("summarization")  # Use Haiku for fast optimization

    messages = [
        SystemMessage(content=QUERY_OPTIMIZATION_PROMPT),
        HumanMessage(content=f"【ユーザーの検索意図】\n{user_query}")
    ]

    try:
        response = await llm.ainvoke(messages)
        return response.content.strip().strip('"').strip("'")
    except Exception as e:
        # Fallback: return original query
        return user_query
