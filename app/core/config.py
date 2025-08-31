import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    active_database: str = Field(default="local", env="ACTIVE_DATABASE")
    
    # Database URL (direct from environment)
    database_url: str = Field(default="", env="DATABASE_URL")
    
    # Local Database (fallback)
    database_url_local: str = Field(default="postgresql://username:password@localhost:5432/indian_stocks", env="DATABASE_URL_LOCAL")
    
    # Production Database (fallback)
    database_url_prod: str = Field(default="", env="DATABASE_URL_PROD")
    
    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL based on configuration."""
        # If DATABASE_URL is set directly, use it
        if self.database_url:
            return self.database_url
        
        # Otherwise, use the active database setting
        if self.active_database.lower() == "prod":
            return self.database_url_prod if self.database_url_prod else self.database_url_local
        return self.database_url_local
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    perplexity_api_key: Optional[str] = Field(None, env="PERPLEXITY_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(None, env="ALPHA_VANTAGE_API_KEY")
    
    # NSE/BSE Configuration
    nse_base_url: str = Field(default="https://www.nseindia.com", env="NSE_BASE_URL")
    bse_base_url: str = Field(default="https://www.bseindia.com", env="BSE_BASE_URL")
    
    # Application
    secret_key: str = Field(default="your_secret_key_here_change_in_production", env="SECRET_KEY")
    debug: bool = Field(default=True, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Data Collection
    data_collection_interval: int = Field(default=3600, env="DATA_COLLECTION_INTERVAL")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    request_delay: float = Field(default=1.0, env="REQUEST_DELAY")
    
    # LLM
    llm_model: str = Field(default="gpt-3.5-turbo", env="LLM_MODEL")
    llm_temperature: float = Field(default=0.7, env="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=1000, env="LLM_MAX_TOKENS")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
