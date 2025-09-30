#!/usr/bin/env python3
"""
Quick script to add Meta ads ID to DFSA account for testing Meta integration
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database import SessionLocal
from models.user_profile import AccountMapping

def update_dfsa_meta_id():
    """Add test Meta ads ID to DFSA account"""
    db = SessionLocal()
    try:
        # Get DFSA account
        dfsa_account = db.query(AccountMapping).filter(
            AccountMapping.account_id == "dfsa"
        ).first()

        if not dfsa_account:
            print("❌ DFSA account not found!")
            return

        # Update with test Meta ads ID
        # Using act_123456789 as a test Meta ads account ID
        dfsa_account.meta_ads_id = "act_123456789"
        db.commit()

        print(f"✅ Updated DFSA account:")
        print(f"   Account: {dfsa_account.account_name}")
        print(f"   Google Ads: {dfsa_account.google_ads_id}")
        print(f"   GA4: {dfsa_account.ga4_property_id}")
        print(f"   Meta Ads: {dfsa_account.meta_ads_id}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_dfsa_meta_id()