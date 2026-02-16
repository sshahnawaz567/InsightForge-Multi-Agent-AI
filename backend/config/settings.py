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
        
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(errors))
        
        return True

# Singleton instance
settings = Settings()