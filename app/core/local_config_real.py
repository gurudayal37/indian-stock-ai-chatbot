"""
REAL LOCAL CONFIGURATION
This file contains actual database credentials and API keys.
DO NOT commit this file to Git!
"""

# AI Services - Replace with your actual keys
OPENAI_API_KEY = "your_openai_api_key_here"
PERPLEXITY_API_KEY = "your_perplexity_api_key_here"
ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key_here"

# Database Configuration
ACTIVE_DATABASE = "prod"  # Use production/cloud database

# Local Database - Update these with your actual PostgreSQL credentials
DATABASE_URL_LOCAL = "postgresql://postgres:password@localhost:5432/indian_stocks"
DATABASE_HOST_LOCAL = "localhost"
DATABASE_PORT_LOCAL = 5432
DATABASE_NAME_LOCAL = "indian_stocks"
DATABASE_USER_LOCAL = "postgres"
DATABASE_PASSWORD_LOCAL = "password"

# Production Database (Neon)
DATABASE_URL_PROD = "postgresql://neondb_owner:npg_bwHv7a8SGtVf@ep-super-dawn-a1z3mcff-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
DATABASE_HOST_PROD = "ep-super-dawn-a1z3mcff-pooler.ap-southeast-1.aws.neon.tech"
DATABASE_PORT_PROD = 5432
DATABASE_NAME_PROD = "neondb"
DATABASE_USER_PROD = "neondb_owner"
DATABASE_PASSWORD_PROD = "npg_bwHv7a8SGtVf"

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
