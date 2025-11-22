"""Project archiving utilities."""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict

from ..database import get_session, Project, ConversationHistory, ProjectPaper, Citation, Document
from ..config import settings


def archive_project(project_id: str) -> Dict:
    """Archive a project to external storage.

    Args:
        project_id: Project ID to archive

    Returns:
        Archive result dictionary
    """
    session = get_session()
    try:
        project = session.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            return {"success": False, "error": "プロジェクトが見つかりません"}

        # Create archive directory
        archive_dir = Path("archived_projects")
        archive_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"proj_{timestamp}_{project.project_name}"
        archive_path = archive_dir / archive_name
        archive_path.mkdir(parents=True, exist_ok=True)

        # Export project metadata
        project_data = {
            "project_id": project.project_id,
            "project_name": project.project_name,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "settings": project.settings,
            "archived_at": datetime.now().isoformat()
        }

        # Export conversation history
        conversations = session.query(ConversationHistory).filter(
            ConversationHistory.project_id == project_id
        ).order_by(ConversationHistory.sequence_number).all()

        conversations_data = [
            {
                "role": c.role,
                "content": c.content,
                "timestamp": c.timestamp.isoformat(),
                "sequence_number": c.sequence_number
            }
            for c in conversations
        ]

        # Export project papers
        project_papers = session.query(ProjectPaper).filter(
            ProjectPaper.project_id == project_id
        ).all()

        papers_data = [
            {
                "pmid": pp.pmid,
                "added_at": pp.added_at.isoformat()
            }
            for pp in project_papers
        ]

        # Export citations
        citations = session.query(Citation).filter(
            Citation.project_id == project_id
        ).all()

        citations_data = [
            {
                "document_id": c.document_id,
                "pmid": c.pmid,
                "citation_number": c.citation_number,
                "citation_text": c.citation_text,
                "source_text": c.source_text,
                "confidence": c.confidence,
                "created_at": c.created_at.isoformat()
            }
            for c in citations
        ]

        # Export documents
        documents = session.query(Document).filter(
            Document.project_id == project_id
        ).all()

        documents_data = []
        for doc in documents:
            doc_info = {
                "document_id": doc.document_id,
                "file_type": doc.file_type,
                "citation_style": doc.citation_style,
                "language": doc.language,
                "created_at": doc.created_at.isoformat()
            }

            # Copy document file if it exists
            if doc.file_path:
                src_path = Path(doc.file_path)
                if src_path.exists():
                    dst_path = archive_path / src_path.name
                    shutil.copy2(src_path, dst_path)
                    doc_info["archived_file"] = src_path.name

            documents_data.append(doc_info)

        # Save all data to JSON
        archive_data = {
            "project": project_data,
            "conversations": conversations_data,
            "papers": papers_data,
            "citations": citations_data,
            "documents": documents_data
        }

        metadata_file = archive_path / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(archive_data, f, ensure_ascii=False, indent=2)

        # Mark project as inactive (don't delete from DB)
        project.is_active = False
        session.commit()

        return {
            "success": True,
            "archive_path": str(archive_path),
            "project_name": project.project_name,
            "items_archived": {
                "conversations": len(conversations_data),
                "papers": len(papers_data),
                "citations": len(citations_data),
                "documents": len(documents_data)
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        session.close()


def get_oldest_project() -> str:
    """Get the oldest active project ID.

    Returns:
        Project ID of the oldest project
    """
    session = get_session()
    try:
        oldest = session.query(Project).filter(
            Project.is_active == True
        ).order_by(Project.created_at).first()

        return oldest.project_id if oldest else None
    finally:
        session.close()
