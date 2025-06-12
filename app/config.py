"""
Configuration settings for FastAPI Azure Backend.

This module loads environment variables and provides configuration settings
for the application.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application settings
    APP_TITLE: str = "Avenir FastAPI Backend"
    APP_DESCRIPTION: str = "Production-ready FastAPI backend for Azure Web App"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production")
    PORT: int = Field(default=8000)
    ENABLE_DOCS: bool = Field(default=True)
    
    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"])
    
    # JWT settings
    USER_NAME: str = Field(default="testuser")
    USER_PASSWORD: str = Field(default="testpassword")
    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)
    REFRESH_TOKEN_CONTAINER_NAME: str = Field(...)
    # Azure Cosmos DB settings
    COSMOS_ENDPOINT: str = Field(...)
    COSMOS_KEY: str = Field(...)
    COSMOS_DATABASE: str =Field(...)
    USERS_CONTAINER_NAME: str = Field(...)
    CHAT_CONTAINER_NAME: str = Field(...)
    FILES_CONTAINER_NAME: str = Field(...)
    TASKS_CONTAINER_NAME: str = Field(...)
    TASK_RESULTS_CONTAINER_NAME: str = Field(...)
    EMBEDDINGS_CONTAINER_NAME: str = Field(...)
    ROLES_CONTAINER_NAME: str = Field(...)
    CHAT_MESSAGES_CONTAINER_NAME: str = Field(...)
    PROMPT_CONTAINER_NAME: str = Field(...)
    
    
    # Azure Blob Storage settings
    BLOB_CONNECTION_STRING: str = Field(...)
    BLOB_CONTAINER_USER_FILES: str = Field(...)
    BLOB_CONTAINER_SHARED_FILES: str = Field(...)
    BLOB_CONTAINER_EMBEDDINGS: str = Field(...)
    AZURE_STORAGE_CONNECTION_STRING: str = Field(...)

    
    # Azure OpenAI settings
    OPENAI_API_TYPE: str = Field(default="azure")
    OPENAI_API_VERSION: str = Field(default="2023-05-15")
    OPENAI_API_BASE: str = Field(...)
    OPENAI_API_KEY: str = Field(...)
    OPENAI_EMBEDDING_DEPLOYMENT: str = Field(...)
    OPENAI_COMPLETION_DEPLOYMENT: str = Field(...)
    OPENAI_CHAT_DEPLOYMENT: str = Field(...)
    
    # Azure Translator settings
    TRANSLATOR_ENDPOINT: str = Field(...)
    TRANSLATOR_KEY: str = Field(...)
    TRANSLATOR_REGION: str = Field(...)
    # Admin User credentials (for development/testing only)

    ADMIN_PASSWORD_HASH: Optional[str] = Field(default=None)
    ADMIN_USERNAME: Optional[str] = Field(default="admin")
    
    # GraphRAG Microservice settings
    GRAPHRAG_ENDPOINT: Optional[str] = Field(default=None)
    GRAPHRAG_API_KEY: Optional[str] = Field(default=None)
    
    SESSION_CONTAINER_NAME: Optional[str]= Field(default="session")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# Create settings instance
settings = Settings()
