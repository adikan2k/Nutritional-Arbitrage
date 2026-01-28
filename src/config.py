"""
Configuration Module - Centralized Settings Management

Why this matters:
- Single source of truth for all configuration
- Type-safe (Pydantic validates everything)
- Fails fast if required env vars are missing
- Easy to test (can override values)

Industry Practice: Never hardcode secrets or config in your code.
Always use environment variables for portability and security.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from .env file
    
    Pydantic automatically:
    1. Loads from .env file
    2. Validates types (str, int, etc.)
    3. Raises clear errors if required fields missing
    """
    
    kroger_client_id: str = Field(..., description="Kroger API Client ID")
    kroger_client_secret: str = Field(..., description="Kroger API Client Secret")
    kroger_location_id: str = Field(default="01400943", description="Kroger store location ID")
    
    usda_api_key: str = Field(..., description="USDA FoodData Central API Key")
    
    database_path: str = Field(
        default="data/cache.db",
        description="SQLite database path for caching"
    )
    
    log_level: str = Field(default="INFO", description="Logging level")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Why @lru_cache?
    - Settings are loaded once and reused (performance)
    - Prevents reading .env file multiple times
    - Thread-safe singleton pattern
    
    Industry Pattern: This is how FastAPI does configuration
    """
    return Settings()
