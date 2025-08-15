"""
Local configuration file for development.
This file can be tracked in Git but should NOT contain real API keys.
For production, use environment variables or a separate config file.
"""

# AI Services - Replace with your actual keys
OPENAI_API_KEY = "your_openai_api_key_here"  # Get from: https://platform.openai.com/api-keys
PERPLEXITY_API_KEY = "your_perplexity_api_key_here"  # Get from: https://www.perplexity.ai/settings/api
ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key_here"  # Optional: for additional market data

# Database Configuration
ACTIVE_DATABASE = "local"  # Options: "local" or "prod"

# Local Database (PostgreSQL)
DATABASE_URL_LOCAL = "postgresql://username:password@localhost:5432/indian_stocks"
DATABASE_HOST_LOCAL = "localhost"
DATABASE_PORT_LOCAL = 5432
DATABASE_NAME_LOCAL = "indian_stocks"
DATABASE_USER_LOCAL = "username"
DATABASE_PASSWORD_LOCAL = "password"

# Production/Cloud Database (if using)
DATABASE_URL_PROD = "postgresql://username:password@host.cloud.com/database?sslmode=require"
DATABASE_HOST_PROD = "host.cloud.com"
DATABASE_PORT_PROD = 5432
DATABASE_NAME_PROD = "database_name"
DATABASE_USER_PROD = "username"
DATABASE_PASSWORD_PROD = "password"

# Redis Configuration (Optional)
REDIS_URL = "redis://localhost:6379"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

# NSE/BSE Configuration
NSE_BASE_URL = "https://www.nseindia.com"
BSE_BASE_URL = "https://www.bseindia.com"

# Application Settings
SECRET_KEY = "your_secret_key_here_change_in_production"
DEBUG = True
ENVIRONMENT = "development"

# Data Collection Settings
DATA_COLLECTION_INTERVAL = 3600  # in seconds
MAX_RETRIES = 3
REQUEST_DELAY = 1.0  # delay between requests in seconds

# LLM Configuration
LLM_MODEL = "gpt-3.5-turbo"
LLM_TEMPERATURE = 0.7
LLM_MAX_TOKENS = 1000

# Logging
LOG_LEVEL = "INFO"

# =============================================================================
# IMPORTANT: SECURITY NOTES
# =============================================================================
"""
⚠️  SECURITY WARNING ⚠️

1. NEVER commit real API keys to Git
2. Replace placeholder values with your actual keys
3. For production, use environment variables
4. This file is tracked in Git for convenience only

To use this file safely:
1. Copy this file to a new file (e.g., local_config_real.py)
2. Add the real file to .gitignore
3. Update the real file with your actual keys
4. Import from the real file in your code

Example:
    # In your main config file
    try:
        from .local_config_real import *
    except ImportError:
        from .local_config import *  # Use defaults
"""
