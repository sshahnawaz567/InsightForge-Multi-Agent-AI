"""
Configuration management for InsightForge
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class Settings:
    """Application settings"""
    
    # API Keys
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    # ANTHROPIC_API_KEY: str = os.getenv('ANTHROPIC_API_KEY', '')
    
    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    
    # Redis
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv('PINECONE_API_KEY', '')
    PINECONE_ENVIRONMENT: str = os.getenv('PINECONE_ENVIRONMENT', 'us-west1-gcp')
    PINECONE_INDEX_NAME: str = os.getenv('PINECONE_INDEX_NAME', 'insightforge-context')

    # LangSmith (tracing, token usage, cost per agent call)
    # LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT are read
    # directly from the environment by the langsmith/langchain SDKs - these
    # attributes just mirror them here so we can warn if they're missing.
    LANGSMITH_TRACING: bool = os.getenv('LANGSMITH_TRACING', 'false').lower() == 'true'
    LANGSMITH_API_KEY: str = os.getenv('LANGSMITH_API_KEY', '')
    LANGSMITH_PROJECT: str = os.getenv('LANGSMITH_PROJECT', 'insightforge')


    # Agent Configuration
    AGENT_MAX_RETRIES: int = 3
    AGENT_TIMEOUT: int = 30  # seconds
    
    # LLM Configuration
    DEFAULT_MODEL: str = "gpt-4o-mini"
    DEFAULT_TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 2000
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate required settings"""
        errors = []
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set in .env")
        
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL not set in .env")

        # Pinecone is optional for now
        if not cls.PINECONE_API_KEY:
            print("⚠️  Warning: PINECONE_API_KEY not set (Context Agent will use in-memory fallback)")

        # LangSmith is optional - app works fine without tracing
        if cls.LANGSMITH_TRACING and not cls.LANGSMITH_API_KEY:
            print("⚠️  Warning: LANGSMITH_TRACING is true but LANGSMITH_API_KEY not set (tracing disabled)")
        elif not cls.LANGSMITH_TRACING:
            print("ℹ️  LangSmith tracing disabled (set LANGSMITH_TRACING=true in .env to enable)")

        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True

# Singleton instance
settings = Settings()