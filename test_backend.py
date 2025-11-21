#!/usr/bin/env python3
"""Simple test script for the backend."""
import asyncio
import sys
sys.path.insert(0, '/home/user/AIagent')

from backend.database import init_database, get_session, Project
from backend.config import settings


def test_database():
    """Test database initialization."""
    print("Testing database initialization...")
    engine = init_database()
    print(f"  Database URL: {engine.url}")

    session = get_session()
    count = session.query(Project).count()
    print(f"  Projects count: {count}")
    session.close()
    print("  Database test passed!")


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    print(f"  Database path: {settings.database_path}")
    print(f"  Papers directory: {settings.papers_directory}")
    print(f"  Default citation style: {settings.default_citation_style}")
    print(f"  Generation model: {settings.generation_model}")
    print(f"  Summarization model: {settings.summarization_model}")
    print("  Configuration test passed!")


async def test_intent_classifier():
    """Test intent classification (requires API key)."""
    if not settings.anthropic_api_key:
        print("\nSkipping intent classifier test (no API key)")
        return

    print("\nTesting intent classifier...")
    from backend.llm.intent_classifier import classify_intent

    result = await classify_intent("脳卒中のtDCS研究を探して")
    print(f"  Intent: {result.get('intent')}")
    print(f"  Confidence: {result.get('confidence')}")
    print("  Intent classifier test passed!")


def main():
    print("=" * 50)
    print("Paper Agent - Backend Tests")
    print("=" * 50)

    test_database()
    test_config()

    # Run async tests
    asyncio.run(test_intent_classifier())

    print("\n" + "=" * 50)
    print("All tests passed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
