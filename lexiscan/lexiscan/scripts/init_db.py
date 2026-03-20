"""
LexiScan — Database Initialization Script
Creates tables and runs initial setup.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from backend.utils.database import create_tables, engine
from backend.utils.config import settings


def main():
    logger.info(f"Connecting to: {settings.DATABASE_URL}")
    try:
        create_tables()
        logger.success("✅ Database tables created successfully!")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        logger.info("Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
        sys.exit(1)


if __name__ == "__main__":
    main()
