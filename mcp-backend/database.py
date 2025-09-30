import sqlite3
import json
import os
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

DB_PATH = "credentials.db"

class CredentialStorage:
    """Handles persistent storage of user credentials"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    credentials TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, data_source)
                )
            """)
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_credentials(self, user_id: str, data_source: str, credentials: Dict[str, Any]) -> bool:
        """Save or update credentials for a user and data source"""
        try:
            credentials_json = json.dumps(credentials)
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_credentials 
                    (user_id, data_source, credentials, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, data_source, credentials_json))
                conn.commit()
            logger.info(f"Saved credentials for user {user_id}, data source {data_source}")
            return True
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
            return False
    
    def get_credentials(self, user_id: str, data_source: str) -> Optional[Dict[str, Any]]:
        """Retrieve credentials for a user and data source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT credentials FROM user_credentials 
                    WHERE user_id = ? AND data_source = ?
                """, (user_id, data_source))
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row['credentials'])
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {e}")
            return None
    
    def get_user_credentials(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all credentials for a user"""
        try:
            credentials = {}
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT data_source, credentials FROM user_credentials 
                    WHERE user_id = ?
                """, (user_id,))
                
                for row in cursor.fetchall():
                    data_source = row['data_source']
                    creds = json.loads(row['credentials'])
                    credentials[data_source] = creds
                    
            return credentials
        except Exception as e:
            logger.error(f"Failed to retrieve user credentials: {e}")
            return {}
    
    def delete_credentials(self, user_id: str, data_source: str) -> bool:
        """Delete credentials for a user and data source"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM user_credentials 
                    WHERE user_id = ? AND data_source = ?
                """, (user_id, data_source))
                conn.commit()
                deleted = cursor.rowcount > 0
            
            if deleted:
                logger.info(f"Deleted credentials for user {user_id}, data source {data_source}")
            return deleted
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False
    
    def list_users(self) -> List[str]:
        """List all users with stored credentials"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT DISTINCT user_id FROM user_credentials")
                return [row['user_id'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []
    
    def list_user_data_sources(self, user_id: str) -> List[str]:
        """List all data sources for a user"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT data_source FROM user_credentials 
                    WHERE user_id = ?
                """, (user_id,))
                return [row['data_source'] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list user data sources: {e}")
            return []
    
    def get_all_users(self) -> List[str]:
        """Get all user IDs with stored credentials (alias for list_users)"""
        return self.list_users()
    
    def store_credentials(self, user_id: str, credentials: Dict[str, Dict[str, Any]]) -> bool:
        """Store multiple credentials for a user (replaces all existing credentials)"""
        try:
            with self.get_connection() as conn:
                # Start transaction
                conn.execute("BEGIN")
                
                # Store each data source
                for data_source, creds in credentials.items():
                    credentials_json = json.dumps(creds)
                    conn.execute("""
                        INSERT OR REPLACE INTO user_credentials 
                        (user_id, data_source, credentials, updated_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """, (user_id, data_source, credentials_json))
                
                conn.commit()
                logger.info(f"Stored credentials for user {user_id} with {len(credentials)} data sources")
                return True
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")
            return False

# Global instance
credential_storage = CredentialStorage()