import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

# Import configuration values
try:
    from .local_config_real import *
except ImportError:
    try:
        from .local_config import *
    except ImportError:
        pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database Configuration
    active_database: str = Field(default=ACTIVE_DATABASE if 'ACTIVE_DATABASE' in globals() else "local", env="ACTIVE_DATABASE")
    
    # Local Database
    database_url_local: str = Field(default=DATABASE_URL_LOCAL if 'DATABASE_URL_LOCAL' in globals() else "postgresql://username:password@localhost:5432/indian_stocks", env="DATABASE_URL_LOCAL")
    database_host_local: str = Field(default=DATABASE_HOST_LOCAL if 'DATABASE_HOST_LOCAL' in globals() else "localhost", env="DATABASE_HOST_LOCAL")
    database_port_local: int = Field(default=DATABASE_PORT_LOCAL if 'DATABASE_PORT_LOCAL' in globals() else 5432, env="DATABASE_PORT_LOCAL")
    database_name_local: str = Field(default=DATABASE_NAME_LOCAL if 'DATABASE_NAME_LOCAL' in globals() else "indian_stocks", env="DATABASE_NAME_LOCAL")
    database_user_local: str = Field(default=DATABASE_USER_LOCAL if 'DATABASE_USER_LOCAL' in globals() else "username", env="DATABASE_USER_LOCAL")
    database_password_local: str = Field(default=DATABASE_PASSWORD_LOCAL if 'DATABASE_PASSWORD_LOCAL' in globals() else "password", env="DATABASE_PASSWORD_LOCAL")
    
    # Production/Cloud Database
    database_url_prod: str = Field(default=DATABASE_URL_PROD if 'DATABASE_URL_PROD' in globals() else "postgresql://username:password@host.cloud.com/database?sslmode=require", env="DATABASE_URL_PROD")
    database_host_prod: str = Field(default=DATABASE_HOST_PROD if 'DATABASE_HOST_PROD' in globals() else "host.cloud.com", env="DATABASE_HOST_PROD")
    database_port_prod: int = Field(default=DATABASE_PORT_PROD if 'DATABASE_PORT_PROD' in globals() else 5432, env="DATABASE_PORT_PROD")
    database_name_prod: str = Field(default=DATABASE_NAME_PROD if 'DATABASE_NAME_PROD' in globals() else "database_name", env="DATABASE_NAME_PROD")
    database_user_prod: str = Field(default=DATABASE_USER_PROD if 'DATABASE_USER_PROD' in globals() else "username", env="DATABASE_USER_PROD")
    database_password_prod: str = Field(default=DATABASE_PASSWORD_PROD if 'DATABASE_PASSWORD_PROD' in globals() else "password", env="DATABASE_PASSWORD_PROD")
    
    @property
    def database_url(self) -> str:
        """Get the active database URL based on configuration."""
        if self.active_database.lower() == "prod":
            return self.database_url_prod
        return self.database_url_local
    
    @property
    def database_host(self) -> str:
        """Get the active database host."""
        if self.active_database.lower() == "prod":
            return self.database_host_prod
        return self.database_host_local
    
    @property
    def database_port(self) -> int:
        """Get the active database port."""
        if self.active_database.lower() == "prod":
            return self.database_port_prod
        return self.database_port_local
    
    @property
    def database_name(self) -> str:
        """Get the active database name."""
        if self.active_database.lower() == "prod":
            return self.database_name_prod
        return self.database_name_local
    
    @property
    def database_user(self) -> str:
        """Get the active database user."""
        if self.active_database.lower() == "prod":
            return self.database_user_prod
        return self.database_user_local
    
    @property
    def database_password(self) -> str:
        """Get the active database password."""
        if self.active_database.lower() == "prod":
            return self.database_password_prod
        return self.database_password_local
    
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
