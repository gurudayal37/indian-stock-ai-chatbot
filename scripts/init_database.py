#!/usr/bin/env python3
"""
Initialize database with updated schema including last_updated field
"""

import sys
import os
import logging

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import create_tables, engine
from app.models.stock import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Initialize database and create tables."""
    try:
        logger.info("Initializing database...")
        
        # Test database connection
        try:
            with engine.connect() as conn:
                logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
        
        # Create tables
        logger.info("Creating database tables...")
        create_tables()
        logger.info("✅ Database tables created successfully")
        
        # Verify tables
        try:
            with engine.connect() as conn:
                result = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row[0] for row in result.fetchall()]
                logger.info(f"✅ Tables created: {tables}")
                
                # Check if last_updated column exists
                result = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'stocks' AND column_name = 'last_updated'")
                if result.fetchone():
                    logger.info("✅ last_updated column exists in stocks table")
                else:
                    logger.warning("⚠️  last_updated column not found in stocks table")
        except Exception as e:
            logger.error(f"Error checking tables/columns: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
