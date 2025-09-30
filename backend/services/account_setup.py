"""
Account Setup and Initialization
Populates the account_mappings table with the three test accounts
"""
from sqlalchemy.orm import Session
from database import get_db
from models.user_profile import AccountMapping


def initialize_account_mappings():
    """
    Initialize the account mappings table with the three test accounts
    """
    db: Session = next(get_db())
    
    # Define the three test accounts
    accounts = [
        {
            "account_id": "dfsa",
            "account_name": "DFSA - Goodness to Go",
            "google_ads_id": "7574136388",
            "ga4_property_id": "458016659",
            "meta_ads_id": None,  # To be configured when Meta Ads account is available
            "business_type": "food",
            "sort_order": 1,
            "account_color": "#4CAF50",  # Green
            "default_date_range_days": 30
        },
        {
            "account_id": "cherry_time",
            "account_name": "Cherry Time",
            "google_ads_id": "8705861821",
            "ga4_property_id": "292652926",
            "meta_ads_id": None,  # To be configured when Meta Ads account is available
            "business_type": "food",
            "sort_order": 2,
            "account_color": "#E91E63",  # Pink/Red
            "default_date_range_days": 30
        },
        {
            "account_id": "onvlee",
            "account_name": "Onvlee Engineering",
            "google_ads_id": "7482456286",
            "ga4_property_id": "428236885",
            "meta_ads_id": None,  # To be configured when Meta Ads account is available
            "business_type": "engineering",
            "sort_order": 3,
            "account_color": "#2196F3",  # Blue
            "default_date_range_days": 30
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for account_data in accounts:
        # Check if account already exists
        existing = db.query(AccountMapping).filter(
            AccountMapping.account_id == account_data["account_id"]
        ).first()
        
        if existing:
            # Update existing account
            for key, value in account_data.items():
                setattr(existing, key, value)
            updated_count += 1
            print(f"[ACCOUNT-SETUP] Updated: {account_data['account_name']}")
        else:
            # Create new account
            new_account = AccountMapping(**account_data)
            db.add(new_account)
            created_count += 1
            print(f"[ACCOUNT-SETUP] Created: {account_data['account_name']}")
    
    db.commit()
    
    print(f"[ACCOUNT-SETUP] Complete: {created_count} created, {updated_count} updated")
    return {"created": created_count, "updated": updated_count}


def get_account_selection_data():
    """
    Get formatted account data for frontend account selection
    """
    try:
        db: Session = next(get_db())
        
        accounts = db.query(AccountMapping).filter(
            AccountMapping.is_active == True
        ).order_by(AccountMapping.sort_order).all()
        
        return [
            {
                "id": account.account_id,
                "name": account.account_name,
                "google_ads_id": account.google_ads_id,
                "ga4_property_id": account.ga4_property_id,
                "meta_ads_id": account.meta_ads_id,
                "business_type": account.business_type,
                "color": account.account_color,
                "display_name": f"{account.account_name} • Google Ads: {account.google_ads_id or 'None'} • GA4: {account.ga4_property_id or 'None'}" + (f" • Meta Ads: {account.meta_ads_id}" if account.meta_ads_id else "")
            }
            for account in accounts
        ]
    except Exception as e:
        print(f"[ACCOUNT-SELECTION] Error: {e}")
        return []


if __name__ == "__main__":
    # Run initialization
    initialize_account_mappings()
    
    # Show results
    print("\n🎯 Available Accounts:")
    accounts = get_account_selection_data()
    for account in accounts:
        print(f"  • {account['name']} ({account['id']})")
        print(f"    Google Ads: {account['google_ads_id']}, GA4: {account['ga4_property_id']}")