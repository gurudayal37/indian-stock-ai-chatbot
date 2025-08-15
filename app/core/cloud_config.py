"""
Cloud Database Configuration for Indian Stock Market Database
Multiple free database service configurations
"""

from typing import Dict, Optional
from app.core.config import settings


class CloudDatabaseConfig:
    """Configuration for various cloud database services."""
    
    # Neon PostgreSQL Configuration
    NEON_CONFIG = {
        "name": "Neon",
        "type": "postgresql",
        "free_tier": "3GB storage, 10GB transfer/month",
        "setup_url": "https://neon.tech",
        "connection_template": "postgresql://{user}:{password}@{host}/{database}?sslmode=require",
        "environment_vars": {
            "DATABASE_URL": "postgresql://username:password@host.neon.tech/database?sslmode=require",
            "DATABASE_HOST": "host.neon.tech",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "your_database_name",
            "DATABASE_USER": "your_username",
            "DATABASE_PASSWORD": "your_password"
        }
    }
    
    # Supabase Configuration
    SUPABASE_CONFIG = {
        "name": "Supabase",
        "type": "postgresql",
        "free_tier": "500MB database, 2GB bandwidth/month",
        "setup_url": "https://supabase.com",
        "connection_template": "postgresql://postgres:{password}@{host}:5432/postgres",
        "environment_vars": {
            "DATABASE_URL": "postgresql://postgres:password@host.supabase.co:5432/postgres",
            "DATABASE_HOST": "host.supabase.co",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "postgres",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "your_password"
        }
    }
    
    # Railway Configuration
    RAILWAY_CONFIG = {
        "name": "Railway",
        "type": "postgresql",
        "free_tier": "$5 credit monthly",
        "setup_url": "https://railway.app",
        "connection_template": "postgresql://{user}:{password}@{host}:{port}/{database}",
        "environment_vars": {
            "DATABASE_URL": "postgresql://username:password@host.railway.app:port/database",
            "DATABASE_HOST": "host.railway.app",
            "DATABASE_PORT": "port_number",
            "DATABASE_NAME": "your_database_name",
            "DATABASE_USER": "your_username",
            "DATABASE_PASSWORD": "your_password"
        }
    }
    
    # PlanetScale Configuration (MySQL)
    PLANETSCALE_CONFIG = {
        "name": "PlanetScale",
        "type": "mysql",
        "free_tier": "1 database, 1GB storage, 1B reads/month",
        "setup_url": "https://planetscale.com",
        "connection_template": "mysql://{user}:{password}@{host}:3306/{database}",
        "environment_vars": {
            "DATABASE_URL": "mysql://username:password@host.aws.connect.psdb.cloud:3306/database?sslaccept=strict",
            "DATABASE_HOST": "host.aws.connect.psdb.cloud",
            "DATABASE_PORT": "3306",
            "DATABASE_NAME": "your_database_name",
            "DATABASE_USER": "your_username",
            "DATABASE_PASSWORD": "your_password"
        }
    }
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, Dict]:
        """Get all available database configurations."""
        return {
            "neon": cls.NEON_CONFIG,
            "supabase": cls.SUPABASE_CONFIG,
            "railway": cls.RAILWAY_CONFIG,
            "planetscale": cls.PLANETSCALE_CONFIG
        }
    
    @classmethod
    def get_config(cls, service_name: str) -> Optional[Dict]:
        """Get configuration for a specific service."""
        configs = cls.get_all_configs()
        return configs.get(service_name.lower())
    
    @classmethod
    def print_setup_guide(cls, service_name: str):
        """Print setup guide for a specific service."""
        config = cls.get_config(service_name)
        if not config:
            print(f"❌ Service '{service_name}' not found")
            return
        
        print(f"\n🚀 Setting up {config['name']} Database")
        print("=" * 50)
        print(f"Service Type: {config['type']}")
        print(f"Free Tier: {config['free_tier']}")
        print(f"Setup URL: {config['setup_url']}")
        print(f"\n📋 Environment Variables:")
        
        for key, value in config['environment_vars'].items():
            print(f"{key}={value}")
        
        print(f"\n🔧 Setup Steps:")
        if service_name.lower() == "neon":
            cls._print_neon_setup()
        elif service_name.lower() == "supabase":
            cls._print_supabase_setup()
        elif service_name.lower() == "railway":
            cls._print_railway_setup()
        elif service_name.lower() == "planetscale":
            cls._print_planetscale_setup()
    
    @classmethod
    def _print_neon_setup(cls):
        """Print Neon setup steps."""
        print("1. Go to https://neon.tech and sign up")
        print("2. Create a new project")
        print("3. Create a new database")
        print("4. Copy the connection string")
        print("5. Update your .env file with the connection details")
        print("6. Run: python scripts/init_database.py")
    
    @classmethod
    def _print_supabase_setup(cls):
        """Print Supabase setup steps."""
        print("1. Go to https://supabase.com and sign up")
        print("2. Create a new project")
        print("3. Go to Settings > Database")
        print("4. Copy the connection string")
        print("5. Update your .env file with the connection details")
        print("6. Run: python scripts/init_database.py")
    
    @classmethod
    def _print_railway_setup(cls):
        """Print Railway setup steps."""
        print("1. Go to https://railway.app and sign up")
        print("2. Create a new project")
        print("3. Add PostgreSQL service")
        print("4. Copy the connection details")
        print("5. Update your .env file with the connection details")
        print("6. Run: python scripts/init_database.py")
    
    @classmethod
    def _print_planetscale_setup(cls):
        """Print PlanetScale setup steps."""
        print("1. Go to https://planetscale.com and sign up")
        print("2. Create a new database")
        print("3. Go to Connect > Connect with Prisma")
        print("4. Copy the connection string")
        print("5. Update your .env file with the connection details")
        print("6. Note: You'll need to modify the app for MySQL compatibility")


def setup_cloud_database():
    """Interactive setup for cloud database."""
    print("🌐 Cloud Database Setup for Indian Stock Market Project")
    print("=" * 60)
    print("Choose your preferred database service:")
    
    configs = CloudDatabaseConfig.get_all_configs()
    
    for i, (key, config) in enumerate(configs.items(), 1):
        print(f"{i}. {config['name']} ({config['type']}) - {config['free_tier']}")
    
    print(f"{len(configs) + 1}. Show all setup guides")
    print(f"{len(configs) + 2}. Exit")
    
    try:
        choice = input(f"\nEnter your choice (1-{len(configs) + 2}): ").strip()
        
        if choice.isdigit():
            choice_num = int(choice)
            if 1 <= choice_num <= len(configs):
                service_name = list(configs.keys())[choice_num - 1]
                CloudDatabaseConfig.print_setup_guide(service_name)
            elif choice_num == len(configs) + 1:
                print("\n📚 All Setup Guides:")
                for service_name in configs.keys():
                    CloudDatabaseConfig.print_setup_guide(service_name)
            elif choice_num == len(configs) + 2:
                print("👋 Goodbye!")
                return
            else:
                print("❌ Invalid choice")
        else:
            print("❌ Please enter a number")
    
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    setup_cloud_database()
