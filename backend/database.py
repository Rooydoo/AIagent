"""Database setup and models."""
import json
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, Float, ForeignKey, JSON, TIMESTAMP, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from .config import settings

Base = declarative_base()


class Project(Base):
    """Projects table."""
    __tablename__ = "projects"

    project_id = Column(String, primary_key=True)
    project_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    settings = Column(JSON)  # {citation_style, language}

    conversations = relationship("ConversationHistory", back_populates="project")
    papers = relationship("ProjectPaper", back_populates="project")
    documents = relationship("Document", back_populates="project")


class ConversationHistory(Base):
    """Conversation history table."""
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)
    sequence_number = Column(Integer, nullable=False)

    project = relationship("Project", back_populates="conversations")

    __table_args__ = (
        CheckConstraint('sequence_number <= 300', name='check_sequence_limit'),
    )


class Paper(Base):
    """Papers table."""
    __tablename__ = "papers"

    pmid = Column(String, primary_key=True)
    pmc_id = Column(String)
    title = Column(String, nullable=False)
    authors = Column(JSON)
    journal = Column(String)
    year = Column(Integer)
    abstract = Column(Text)
    summary = Column(Text)  # LLM-generated summary
    keywords = Column(JSON)
    pdf_path = Column(String)
    metadata_path = Column(String)
    page_count = Column(Integer)
    sections = Column(JSON)  # {introduction: {text, pages}, ...}
    indexed_at = Column(TIMESTAMP, default=datetime.utcnow)
    is_favorite = Column(Boolean, default=False)
    tags = Column(JSON)  # Custom tags

    project_papers = relationship("ProjectPaper", back_populates="paper")
    citations = relationship("Citation", back_populates="paper")


class ProjectPaper(Base):
    """Project-Paper many-to-many relationship."""
    __tablename__ = "project_papers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False)
    pmid = Column(String, ForeignKey("papers.pmid"), nullable=False)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)

    project = relationship("Project", back_populates="papers")
    paper = relationship("Paper", back_populates="project_papers")


class Citation(Base):
    """Citations table."""
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False)
    document_id = Column(String, nullable=False)
    pmid = Column(String, ForeignKey("papers.pmid"), nullable=False)
    citation_number = Column(Integer, nullable=False)
    citation_text = Column(Text, nullable=False)
    source_text = Column(Text)  # Original text from paper
    pdf_page = Column(Integer)
    confidence = Column(Float)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    paper = relationship("Paper", back_populates="citations")


class Document(Base):
    """Documents table."""
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.project_id"), nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'docx', 'pdf', 'xlsx'
    citation_style = Column(String, nullable=False)
    language = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="documents")


class TokenUsage(Base):
    """Token usage tracking table."""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    year_month = Column(String, nullable=False)  # 'YYYY-MM'
    model = Column(String, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database initialization
def get_database_url() -> str:
    """Get database URL."""
    db_path = Path(__file__).parent.parent / settings.database_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def init_database():
    """Initialize the database."""
    engine = create_engine(get_database_url(), echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get database session."""
    engine = init_database()
    Session = sessionmaker(bind=engine)
    return Session()
