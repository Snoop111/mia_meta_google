import data_integrator
from database import credential_storage
from shared_integrator import data_integrator_instance
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CredentialManager:
    """Manages loading and configuring data source connectors from stored credentials"""
    
    def __init__(self):
        self.storage = credential_storage
        self.integrator = data_integrator_instance
    
    def load_user_connectors(self, user_id: str) -> Dict[str, bool]:
        """Load all connectors for a user from stored credentials"""
        credentials = self.storage.get_user_credentials(user_id)
        results = {}
        
        for data_source, creds in credentials.items():
            success = self._create_connector(data_source, creds)
            results[data_source] = success
            
        return results
    
    def _create_connector(self, data_source: str, credentials: Dict[str, Any]) -> bool:
        """Create and add a connector based on data source type and credentials"""
        try:
            if data_source == "meta_ads":
                connector = data_integrator.MetaAdsConnector(
                    access_token=credentials.get("access_token"),
                    app_id=credentials.get("app_id"),
                    app_secret=credentials.get("app_secret")
                )
            elif data_source == "google_ads":
                connector = data_integrator.GoogleAdsConnector(
                    developer_token=credentials.get("developer_token"),
                    client_id=credentials.get("client_id"),
                    client_secret=credentials.get("client_secret"),
                    refresh_token=credentials.get("refresh_token")
                )
            elif data_source == "ga4":
                # Check if we have OAuth credentials, otherwise use service account
                oauth_creds = credentials.get("oauth_credentials")
                if oauth_creds:
                    connector = data_integrator.GA4Connector(
                        property_id=credentials.get("property_id", ""),  # Empty string as placeholder
                        oauth_credentials=oauth_creds
                    )
                else:
                    # Fallback to service account
                    connector = data_integrator.GA4Connector(
                        credentials_path=credentials.get("credentials_path"),
                        property_id=credentials.get("property_id", "")  # Empty string as placeholder
                    )
            else:
                logger.error(f"Unknown data source: {data_source}")
                return False
            
            self.integrator.add_connector(data_source, connector)
            logger.info(f"Successfully loaded connector for {data_source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create connector for {data_source}: {e}")
            return False
    
    def save_and_configure_credentials(self, user_id: str, data_source: str, 
                                     credentials: Dict[str, Any]) -> bool:
        """Save credentials to database and configure the connector"""
        # Save to database
        if not self.storage.save_credentials(user_id, data_source, credentials):
            return False
        
        # Create and configure connector
        return self._create_connector(data_source, credentials)
    
    def remove_user_connector(self, user_id: str, data_source: str) -> bool:
        """Remove connector and delete stored credentials"""
        # Remove from integrator
        self.integrator.remove_connector(data_source)
        
        # Remove from database
        return self.storage.delete_credentials(user_id, data_source)
    
    def get_user_data_sources(self, user_id: str) -> Dict[str, Any]:
        """Get information about user's configured data sources"""
        data_sources = self.storage.list_user_data_sources(user_id)
        connector_status = self.integrator.get_connector_status()
        
        return {
            "user_id": user_id,
            "configured_data_sources": data_sources,
            "active_connectors": list(connector_status.keys()),
            "connector_status": connector_status
        }

    def build_integrator_for_user(self, user_id: str) -> data_integrator.DataIntegrator:
        """Build and return a new DataIntegrator instance configured with the user's connectors.

        This creates an isolated DataIntegrator (not the shared global one) so connectors
        configured for one user do not overwrite connectors for other users.
        """
        integrator = data_integrator.DataIntegrator()
        credentials = self.storage.get_user_credentials(user_id)

        for data_source, creds in credentials.items():
            try:
                if data_source == "meta_ads":
                    connector = data_integrator.MetaAdsConnector(
                        access_token=creds.get("access_token"),
                        app_id=creds.get("app_id"),
                        app_secret=creds.get("app_secret")
                    )
                elif data_source == "google_ads":
                    connector = data_integrator.GoogleAdsConnector(
                        developer_token=creds.get("developer_token"),
                        client_id=creds.get("client_id"),
                        client_secret=creds.get("client_secret"),
                        refresh_token=creds.get("refresh_token")
                    )
                elif data_source == "ga4":
                    oauth_creds = creds.get("oauth_credentials")
                    if oauth_creds:
                        # OAuth credentials without property_id (will be set at request time)
                        connector = data_integrator.GA4Connector(
                            property_id=creds.get("property_id", ""),  # Empty string as placeholder
                            oauth_credentials=oauth_creds
                        )
                    else:
                        # Service account fallback
                        connector = data_integrator.GA4Connector(
                            credentials_path=creds.get("credentials_path"),
                            property_id=creds.get("property_id", "")  # Empty string as placeholder
                        )
                else:
                    logger.warning(f"Skipping unknown data source when building integrator: {data_source}")
                    continue

                # Only add connector if credentials validate
                if connector.validate_credentials():
                    integrator.add_connector(data_source, connector)
                    logger.info(f"Built connector for user {user_id}: {data_source}")
                else:
                    logger.warning(f"Invalid credentials for user {user_id}, data source {data_source}")

            except Exception as e:
                logger.error(f"Failed to build connector for user {user_id}, data source {data_source}: {e}")

        return integrator

# Global instance
credential_manager = CredentialManager()