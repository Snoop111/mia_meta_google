"""
Dynamic Endpoint Service
Provides account-aware data access for all endpoints
Replaces hardcoded account logic throughout the system
"""
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from services.session_service import session_service
from services.adk_mcp_integration import get_adk_marketing_agent
from models.user_profile import UserProfile


class DynamicEndpointService:
    """
    Service that provides dynamic account context for all endpoints
    Eliminates hardcoded accounts and enables seamless account switching
    """
    
    @staticmethod
    async def get_request_context(session_id: str) -> Dict[str, Any]:
        """
        Get complete request context based on current session
        Returns user info, selected account, and MCP context
        """
        # Get active session
        session = session_service.get_active_session(session_id)
        
        if not session or not session.selected_account_id:
            raise ValueError("No active session or account selected")
        
        # Get account mapping
        account_mapping = session_service.get_account_mapping(session.selected_account_id)
        if not account_mapping:
            raise ValueError(f"Account mapping not found: {session.selected_account_id}")
        
        # Get user profile
        profile = session_service.db.query(UserProfile).filter(
            UserProfile.google_user_id == session.google_user_id
        ).first()
        
        # Build context
        context = {
            # User context
            "google_user_id": session.google_user_id,
            "user_name": profile.name if profile else "Unknown",
            "user_email": profile.email if profile else "unknown@example.com",
            
            # Session context
            "session_id": session_id,
            "authenticated": True,
            
            # Account context
            "selected_account": {
                "id": account_mapping.account_id,
                "name": account_mapping.account_name,
                "google_ads_id": account_mapping.google_ads_id,
                "ga4_property_id": account_mapping.ga4_property_id,
                "business_type": account_mapping.business_type
            },
            
            # MCP context (for backwards compatibility)
            "focus_account": account_mapping.account_id,  # "dfsa", "cherry_time", "onvlee"
            "user_id": session.google_user_id,
            "google_ads_id": account_mapping.google_ads_id,
            "ga4_property_id": account_mapping.ga4_property_id,
            
            # Default date range (can be overridden)
            "start_date": (datetime.now() - timedelta(days=account_mapping.default_date_range_days)).strftime('%Y-%m-%d'),
            "end_date": datetime.now().strftime('%Y-%m-%d')
        }
        
        return context
    
    @staticmethod
    async def call_mcp_with_context(session_id: str, 
                                   override_start_date: Optional[str] = None,
                                   override_end_date: Optional[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Call MCP with proper account context from session
        Returns (mcp_agent, context)
        """
        # Get request context
        context = await DynamicEndpointService.get_request_context(session_id)
        
        # Override dates if provided
        if override_start_date:
            context["start_date"] = override_start_date
        if override_end_date:
            context["end_date"] = override_end_date
        
        # Get MCP agent
        agent = await get_adk_marketing_agent()
        
        # Build MCP context
        mcp_context = {
            "user_id": context["user_id"],
            "focus_account": context["focus_account"],
            "start_date": context["start_date"],
            "end_date": context["end_date"]
        }
        
        print(f"[DYNAMIC-MCP] Context: Account={context['focus_account']} ({context['selected_account']['name']})")
        print(f"[DYNAMIC-MCP] Date range: {context['start_date']} to {context['end_date']}")
        
        return agent, mcp_context
    
    @staticmethod
    def track_endpoint_activity(session_id: str, endpoint: str, 
                               activity_data: Dict[str, Any] = None,
                               duration_seconds: int = None):
        """
        Track activity for any endpoint
        """
        try:
            session = session_service.get_active_session(session_id)
            if session:
                session_service.track_activity(
                    session.google_user_id,
                    session_id,
                    f"endpoint_{endpoint}",
                    activity_data or {},
                    endpoint,
                    duration_seconds
                )
        except Exception as e:
            print(f"[TRACK-ENDPOINT] Error tracking {endpoint}: {e}")
    
    @staticmethod
    def validate_session_and_account(session_id: str) -> Tuple[bool, str]:
        """
        Validate that session exists and has account selected
        Returns (is_valid, error_message)
        """
        if not session_id:
            return False, "Session ID required"
        
        session = session_service.get_active_session(session_id)
        if not session:
            return False, "No active session found"
        
        if not session.selected_account_id:
            return False, "No account selected for session"
        
        account_mapping = session_service.get_account_mapping(session.selected_account_id)
        if not account_mapping:
            return False, f"Invalid account mapping: {session.selected_account_id}"
        
        return True, ""
    
    @staticmethod
    def get_account_display_info(session_id: str) -> Dict[str, Any]:
        """
        Get account info for display purposes
        """
        try:
            session = session_service.get_active_session(session_id)
            if not session or not session.selected_account_id:
                return {"error": "No account selected"}
            
            account_mapping = session_service.get_account_mapping(session.selected_account_id)
            if not account_mapping:
                return {"error": "Invalid account"}
            
            return {
                "account_name": account_mapping.account_name,
                "account_id": account_mapping.account_id,
                "business_type": account_mapping.business_type,
                "google_ads_id": account_mapping.google_ads_id,
                "ga4_property_id": account_mapping.ga4_property_id,
                "color": account_mapping.account_color
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
dynamic_service = DynamicEndpointService()