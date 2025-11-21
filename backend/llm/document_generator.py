"""LLM5: Document section generator."""
import json
from typing import List, Dict, Optional
from langchain.schema import HumanMessage, SystemMessage

from ..utils.langchain_setup import get_llm

SECTION_GENERATION_PROMPT = """あなたは学術論文のレビュー論文を執筆する研究者です。

【タスク】
指定されたセクションを執筆してください。

【指示】
- 複数の論文を適切に引用しながら執筆
- 引用は[1], [2]の形式で挿入
- 引用する際は必ず元論文の内容に基づくこと
- 学術的で客観的な文体を使用
- 指定された言語で執筆

【出力形式】
必ずJSON形式で出力:
{
  "section_content": "セクション本文（引用番号付き）",
  "citations_used": [
    {
      "number": 1,
      "pmid": "論文のPMID",
      "citation_text": "引用した内容の要約",
      "source_text": "元論文の該当テキスト",
      "confidence": 0.95
    }
  ]
}

JSONのみを出力してください。"""

DOCUMENT_STRUCTURE_PROMPT = """あなたは学術論文の構成を提案する専門家です。

【タスク】
与えられた論文リストに基づいて、レビュー論文の構成を提案してください。

【出力形式】
必ずJSON形式で出力:
{
  "title": "提案するタイトル",
  "sections": [
    {"name": "Introduction", "description": "導入部の概要"},
    {"name": "Methods", "description": "方法論の概要"},
    {"name": "Results", "description": "結果の概要"},
    {"name": "Discussion", "description": "考察の概要"},
    {"name": "Conclusion", "description": "結論の概要"}
  ],
  "estimated_citations": 10
}

JSONのみを出力してください。"""


async def propose_document_structure(papers: List[Dict], topic: str, language: str = "ja") -> Dict:
    """Propose document structure based on papers.

    Args:
        papers: List of paper metadata
        topic: Document topic/theme
        language: Output language

    Returns:
        Proposed structure
    """
    llm = get_llm("generation")

    papers_summary = "\n".join([
        f"- {p.get('title', 'Unknown')} ({p.get('year', 'N/A')}): {p.get('summary', p.get('abstract', '')[:200])}"
        for p in papers[:10]
    ])

    prompt = f"""【トピック】
{topic}

【参考論文リスト】
{papers_summary}

【言語】
{language}

上記の論文を使用したレビュー論文の構成を提案してください。"""

    messages = [
        SystemMessage(content=DOCUMENT_STRUCTURE_PROMPT),
        HumanMessage(content=prompt)
    ]

    try:
        response = await llm.ainvoke(messages)
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "title": topic,
            "sections": [
                {"name": "Introduction", "description": "背景と目的"},
                {"name": "Methods", "description": "方法"},
                {"name": "Results", "description": "結果"},
                {"name": "Discussion", "description": "考察"},
                {"name": "Conclusion", "description": "結論"}
            ]
        }
    except Exception as e:
        return {"error": str(e)}


async def generate_section(
    section_name: str,
    papers: List[Dict],
    previous_sections: str,
    language: str = "ja",
    citation_start: int = 1
) -> Dict:
    """Generate a document section.

    Args:
        section_name: Name of section to generate
        papers: List of paper metadata with abstracts
        previous_sections: Previously generated sections for context
        language: Output language
        citation_start: Starting citation number

    Returns:
        Generated section with citations
    """
    llm = get_llm("generation")

    papers_context = "\n\n".join([
        f"【論文{i+citation_start}】PMID: {p.get('pmid', 'N/A')}\n"
        f"タイトル: {p.get('title', 'Unknown')}\n"
        f"著者: {', '.join(p.get('authors', [])[:3])} et al.\n"
        f"年: {p.get('year', 'N/A')}\n"
        f"要約: {p.get('abstract', 'N/A')[:500]}"
        for i, p in enumerate(papers)
    ])

    prompt = f"""【セクション名】
{section_name}

【参考論文】
{papers_context}

【これまでのセクション】
{previous_sections if previous_sections else "（なし - 最初のセクションです）"}

【言語】
{language}

【引用番号の開始】
{citation_start}

上記の論文を引用しながら、{section_name}セクションを執筆してください。"""

    messages = [
        SystemMessage(content=SECTION_GENERATION_PROMPT),
        HumanMessage(content=prompt)
    ]

    try:
        response = await llm.ainvoke(messages)
        result = json.loads(response.content)
        return result
    except json.JSONDecodeError as e:
        # Try to extract content even if JSON is malformed
        content = response.content if 'response' in dir() else ""
        return {
            "section_content": content,
            "citations_used": [],
            "parse_error": str(e)
        }
    except Exception as e:
        return {
            "section_content": "",
            "citations_used": [],
            "error": str(e)
        }
