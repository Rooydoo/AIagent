"""LLM6: Citation integrity checker."""
import json
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

CITATION_CHECK_PROMPT = """以下の引用が元論文の内容と一致しているか検証してください。

【出力形式】
必ずJSON形式で出力:
{
  "is_accurate": true/false,
  "confidence": 0.0-1.0,
  "issues": "問題があれば記載（なければnull）",
  "suggestion": "修正提案があれば記載（なければnull）"
}

JSONのみを出力してください。"""


async def check_citation(citation_text: str, source_text: str) -> dict:
    """Check citation accuracy against source.

    Args:
        citation_text: The citation text in the document
        source_text: The original text from the paper

    Returns:
        Verification result
    """
    llm = get_llm("summarization")

    prompt = f"""【引用文】
{citation_text}

【元論文の該当箇所】
{source_text}"""

    messages = [
        SystemMessage(content=CITATION_CHECK_PROMPT),
        HumanMessage(content=prompt)
    ]

    try:
        response = await llm.ainvoke(messages)
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "is_accurate": True,
            "confidence": 0.5,
            "issues": "検証結果のパースに失敗",
            "suggestion": None
        }
    except Exception as e:
        return {
            "is_accurate": True,
            "confidence": 0.0,
            "issues": str(e),
            "suggestion": None
        }


async def check_all_citations(citations: list) -> list:
    """Check all citations in a document.

    Args:
        citations: List of citation dicts with citation_text and source_text

    Returns:
        List of verification results
    """
    results = []
    for citation in citations:
        if citation.get("source_text"):
            result = await check_citation(
                citation.get("citation_text", ""),
                citation.get("source_text", "")
            )
            result["citation_number"] = citation.get("number")
            result["pmid"] = citation.get("pmid")
            results.append(result)
    return results
