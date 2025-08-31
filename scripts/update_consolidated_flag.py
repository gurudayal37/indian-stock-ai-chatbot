#!/usr/bin/env python3
"""
Script to update all existing quarterly results to set is_consolidated = False
Since we're currently collecting standalone results from BSE, all existing data should be marked as standalone.
"""

import sys
import os
sys.path.append('.')

from app.core.database import get_db
from app.models.stock import QuarterlyResult
from sqlalchemy import update

def update_consolidated_flag():
    """Update all quarterly results to set is_consolidated = False"""
    try:
        db = next(get_db())
        
        # Count existing records
        total_records = db.query(QuarterlyResult).count()
        print(f"📊 Total quarterly results records: {total_records}")
        
        if total_records == 0:
            print("✅ No quarterly results to update")
            return
        
        # Update all records to set is_consolidated = False
        update_query = update(QuarterlyResult).values(is_consolidated=False)
        result = db.execute(update_query)
        
        # Commit the changes
        db.commit()
        
        print(f"✅ Successfully updated {result.rowcount} quarterly results records")
        print("🔍 All records now have is_consolidated = False (standalone)")
        
        # Verify the update
        updated_records = db.query(QuarterlyResult).filter(QuarterlyResult.is_consolidated == False).count()
        print(f"📋 Verified: {updated_records} records now have is_consolidated = False")
        
    except Exception as e:
        print(f"❌ Error updating consolidated flag: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Updating quarterly results consolidated flag...")
    update_consolidated_flag()
    print("✅ Update completed!")
