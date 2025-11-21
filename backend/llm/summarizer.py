"""LLM3: Paper summarization."""
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

SUMMARIZATION_PROMPT = """以下の論文Abstractを2-3文で簡潔に要約してください。

【要約の指針】
- 研究の目的
- 主な手法
- 重要な結果
を含めてください。

要約のみを出力してください（説明不要）。"""


async def summarize_abstract(abstract: str) -> str:
    """Summarize a paper abstract.

    Args:
        abstract: Paper abstract text

    Returns:
        Summarized text (2-3 sentences)
    """
    llm = get_llm("summarization")  # Use Haiku for summaries

    messages = [
        SystemMessage(content=SUMMARIZATION_PROMPT),
        HumanMessage(content=f"【Abstract】\n{abstract}")
    ]

    try:
        response = await llm.ainvoke(messages)
        return response.content.strip()
    except Exception as e:
        return f"要約生成エラー: {str(e)}"


async def summarize_abstracts_batch(abstracts: list[dict]) -> list[dict]:
    """Summarize multiple abstracts.

    Args:
        abstracts: List of dicts with 'pmid' and 'abstract' keys

    Returns:
        List of dicts with 'pmid' and 'summary' keys
    """
    results = []
    for item in abstracts:
        summary = await summarize_abstract(item["abstract"])
        results.append({
            "pmid": item["pmid"],
            "summary": summary
        })
    return results
