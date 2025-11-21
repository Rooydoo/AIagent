"""Projects API endpoints."""
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_session, Project

router = APIRouter()


class ProjectCreate(BaseModel):
    project_name: str
    citation_style: Optional[str] = "Vancouver"
    language: Optional[str] = "ja"


class ProjectUpdate(BaseModel):
    project_name: Optional[str] = None
    citation_style: Optional[str] = None
    language: Optional[str] = None


class ProjectResponse(BaseModel):
    project_id: str
    project_name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    settings: Optional[dict] = None

    class Config:
        from_attributes = True


@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    """Create a new project."""
    session = get_session()
    try:
        # Check project limit
        active_count = session.query(Project).filter(Project.is_active == True).count()
        if active_count >= 5:
            raise HTTPException(
                status_code=400,
                detail="最大プロジェクト数（5）に達しています。古いプロジェクトを削除してください。"
            )

        new_project = Project(
            project_id=str(uuid.uuid4()),
            project_name=project.project_name,
            settings={
                "citation_style": project.citation_style,
                "language": project.language
            }
        )
        session.add(new_project)
        session.commit()
        session.refresh(new_project)
        return new_project
    finally:
        session.close()


@router.get("/")
async def list_projects():
    """List all active projects."""
    session = get_session()
    try:
        projects = session.query(Project).filter(Project.is_active == True).all()
        return [ProjectResponse.model_validate(p) for p in projects]
    finally:
        session.close()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details."""
    session = get_session()
    try:
        project = session.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        return project
    finally:
        session.close()


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate):
    """Update project."""
    session = get_session()
    try:
        project = session.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        if update.project_name:
            project.project_name = update.project_name
        if update.citation_style or update.language:
            settings = project.settings or {}
            if update.citation_style:
                settings["citation_style"] = update.citation_style
            if update.language:
                settings["language"] = update.language
            project.settings = settings

        project.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(project)
        return project
    finally:
        session.close()


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete (archive) project."""
    session = get_session()
    try:
        project = session.query(Project).filter(Project.project_id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")

        project.is_active = False
        session.commit()
        return {"message": "プロジェクトを削除しました", "project_id": project_id}
    finally:
        session.close()
