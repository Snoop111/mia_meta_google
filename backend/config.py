import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Server
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/mia.db")

    # Anthropic API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    # MCP Server (NGROK for Meta OAuth compatibility)
    MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://c0b45cdfaa6f.ngrok.app/llm/mcp")
    # MCP_API_KEY removed - MCP uses OAuth authentication, not API keys

    # Frontend
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

    # CORS - Dynamic origins for development flexibility
    CORS_ORIGINS = ["*"]  # Allow all origins for development


settings = Settings()