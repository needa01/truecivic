"""
Configuration management for Parliament Explorer.

Supports multiple environments (local, development, production) with
different database, cache, and message queue configurations.

Responsibility: Centralized configuration and environment management
"""

from enum import Enum
from typing import Optional, List
import json
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment"""
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    
    # Connection settings - prioritize DATABASE_URL env var
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")
    driver: str = Field(default="postgresql+asyncpg")
    host: Optional[str] = Field(default="localhost")
    port: Optional[int] = Field(default=5432)
    database: str = Field(default="parliament_explorer")
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    
    # Connection pool settings
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)
    
    # Query settings
    echo: bool = Field(default=False)
    echo_pool: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True  # Allow alias matching
    )
    
    @property
    def connection_string(self) -> str:
        """
        Build database connection string.
        
        Returns:
            SQLAlchemy connection string
        """
        # Use DATABASE_URL env var if provided (Railway sets this)
        if self.database_url:
            # Convert async driver if needed
            url = self.database_url
            # Ensure async driver for async connections
            if "postgresql" in url and "+asyncpg" not in url and "+psycopg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://")
            return url
        
        if self.driver.startswith("sqlite"):
            raise ValueError(
                "SQLite is no longer supported. Configure a PostgreSQL/pgvector connection instead."
            )
        
        # PostgreSQL: use host/port/credentials
        auth = ""
        if self.username:
            auth = self.username
            if self.password:
                auth = f"{auth}:{self.password}"
            auth = f"{auth}@"
        
        host_port = self.host or "localhost"
        if self.port:
            host_port = f"{host_port}:{self.port}"
        
        return f"{self.driver}://{auth}{host_port}/{self.database}"
    
    @property
    def sync_connection_string(self) -> str:
        """
        Build synchronous database connection string for Alembic migrations.
        
        Returns:
            SQLAlchemy sync connection string (without async drivers)
        """
        # Use DATABASE_URL env var if provided, convert to sync driver
        if self.database_url:
            url = self.database_url
            # Convert async drivers to sync equivalents
            if "+asyncpg" in url:
                url = url.replace("+asyncpg", "+psycopg")
            elif "postgresql://" in url and "+psycopg" not in url:
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        
        # Replace async drivers with sync equivalents
        sync_driver = self.driver.replace("+asyncpg", "+psycopg")
        
        if sync_driver.startswith("sqlite"):
            raise ValueError(
                "SQLite is no longer supported. Configure a PostgreSQL/pgvector connection instead."
            )
        
        # PostgreSQL: use host/port/credentials
        auth = ""
        if self.username:
            auth = self.username
            if self.password:
                auth = f"{auth}:{self.password}"
            auth = f"{auth}@"
        
        host_port = self.host or "localhost"
        if self.port:
            host_port = f"{host_port}:{self.port}"
        
        return f"{sync_driver}://{auth}{host_port}/{self.database}"


class RedisConfig(BaseSettings):
    """Redis cache configuration"""
    
    enabled: bool = Field(default=False)
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    
    # Connection pool
    max_connections: int = Field(default=50)
    socket_timeout: int = Field(default=5)
    socket_connect_timeout: int = Field(default=5)
    
    # Cache TTLs (seconds)
    default_ttl: int = Field(default=3600)  # 1 hour
    bill_ttl: int = Field(default=21600)  # 6 hours
    politician_ttl: int = Field(default=86400)  # 24 hours
    
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def connection_string(self) -> str:
        """Build Redis connection string"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


class KafkaConfig(BaseSettings):
    """Kafka message queue configuration"""
    
    enabled: bool = Field(default=False)
    bootstrap_servers: str = Field(default="localhost:9092")
    
    # Consumer settings
    consumer_group_id: str = Field(default="parliament-explorer")
    auto_offset_reset: str = Field(default="earliest")
    
    # Producer settings
    compression_type: str = Field(default="gzip")
    acks: str = Field(default="all")
    retries: int = Field(default=3)
    
    # Topics
    bills_topic: str = Field(default="parliament.bills")
    politicians_topic: str = Field(default="parliament.politicians")
    votes_topic: str = Field(default="parliament.votes")
    
    model_config = SettingsConfigDict(
        env_prefix="KAFKA_",
        case_sensitive=False,
        extra="ignore"
    )


class AppConfig(BaseSettings):
    """Application configuration"""
    
    # Environment
    environment: Environment = Field(default=Environment.LOCAL)
    debug: bool = Field(default=True)
    require_api_key: bool = Field(
        default=True,
        description="Require X-API-Key authentication for protected routes"
    )
    
    # Application metadata
    app_name: str = Field(default="Parliament Explorer")
    app_version: str = Field(default="1.0.0")
    
    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")
    
    # API settings
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_workers: int = Field(default=1)
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins (JSON list or comma-separated in env)"
    )
    
    # Data refresh intervals (seconds)
    bill_refresh_interval: int = Field(default=3600)  # 1 hour
    politician_refresh_interval: int = Field(default=86400)  # 24 hours
    
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or comma-separated list"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            # Remove outer quotes if present (Railway wraps JSON strings in quotes)
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            # Try parsing as JSON first
            if v.startswith("["):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


class Settings(BaseSettings):
    """
    Global settings container.
    
    Loads configuration from:
    1. Environment variables
    2. .env file
    3. Default values
    
    Example:
        # Local development (PostgreSQL)
        settings = Settings()
        
        # Production (PostgreSQL)
        settings = Settings(
            environment=Environment.PRODUCTION,
            db=DatabaseConfig(
                driver="postgresql+asyncpg",
                host="db.railway.app",
                database="railway"
            )
        )
    """
    
    app: AppConfig = Field(default_factory=AppConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def redis_url(self) -> Optional[str]:
        """Get Redis connection URL for rate limiting"""
        if self.redis.enabled:
            return self.redis.connection_string
        return None
    
    @classmethod
    def for_production(cls) -> "Settings":
        """
        Create settings for production (PostgreSQL, Redis, Kafka).
        
        Requires environment variables:
        - DB_HOST, DB_PORT, DB_DATABASE, DB_USERNAME, DB_PASSWORD
        - REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
        - KAFKA_BOOTSTRAP_SERVERS
        """
        return cls(
            app=AppConfig(
                environment=Environment.PRODUCTION,
                debug=False,
                log_level="INFO"
            ),
            db=DatabaseConfig(
                driver="postgresql+asyncpg",
                # Host/port/credentials from env vars
            ),
            redis=RedisConfig(
                enabled=True,
                # Host/port/password from env vars
            ),
            kafka=KafkaConfig(
                enabled=True,
                # Bootstrap servers from env vars
            )
        )


# Global settings instance
settings = Settings()
