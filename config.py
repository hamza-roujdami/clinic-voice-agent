"""Configuration management for Clinic Voice Agent."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration from environment variables."""
    
    # Azure AI Foundry
    project_endpoint: str = os.environ.get("PROJECT_ENDPOINT", "")
    model_primary: str = os.environ.get("FOUNDRY_MODEL_PRIMARY", "gpt-4o-mini")
    embedding_model: str = os.environ.get("FOUNDRY_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Azure AI Search (for RAG)
    search_endpoint: str = os.environ.get("AZURE_SEARCH_ENDPOINT", "")
    
    # Cosmos DB (session storage)
    cosmos_endpoint: str = os.environ.get("COSMOS_ENDPOINT", "")
    cosmos_database: str = os.environ.get("COSMOS_DATABASE", "enterprise_memory")
    cosmos_container: str = os.environ.get("COSMOS_CONTAINER", "sessions")
    
    # Foundry Memory (long-term cross-session)
    memory_store_id: str = os.environ.get("FOUNDRY_MEMORY_STORE_ID", "")
    
    # Azure Speech (for Voice Gateway)
    speech_endpoint: str = os.environ.get("SPEECH_ENDPOINT", "")
    speech_region: str = os.environ.get("SPEECH_REGION", "swedencentral")
    
    # Memory (long-term cross-session)
    enable_memory: bool = os.environ.get("ENABLE_MEMORY", "true").lower() == "true"
    
    # Server
    host: str = os.environ.get("HOST", "0.0.0.0")
    port: int = int(os.environ.get("PORT", "8000"))
    
    def validate(self) -> list[str]:
        """Check required config is set. Returns list of missing vars."""
        missing = []
        
        if not self.project_endpoint:
            missing.append("PROJECT_ENDPOINT")
        
        return missing


# Global config instance
config = Config()
