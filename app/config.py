from pydantic import BaseModel
from dotenv import load_dotenv
import os

# Load variables from the .env file into the app.
load_dotenv()


class Settings(BaseModel):
    """
    Application settings loaded from .env.

    Database options:
    - DATABASE_URL is preferred for Supabase or hosted PostgreSQL.
    - Individual POSTGRES_* values are used for local Docker PostgreSQL fallback.
    """

    app_name: str = os.getenv("APP_NAME", "Buddy AI Backend")
    app_env: str = os.getenv("APP_ENV", "local")

    # Preferred for Supabase / hosted PostgreSQL.
    database_url: str = os.getenv("DATABASE_URL", "")

    # Local Docker PostgreSQL fallback.
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "buddy_db")
    postgres_user: str = os.getenv("POSTGRES_USER", "buddy")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "buddy_password")

    # Qdrant vector database.
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "buddy_documents")

    # DeepSeek answer generation.
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # Answer generation provider:
    # - "deepseek" uses DeepSeek
    # - "openai" uses OpenAI
    llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek")

    # OpenAI support. Do not commit the key. Keep it only in .env.
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_embedding_model: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

    # Embedding provider:
    # - "local" uses the deterministic fallback embedding
    # - "openai" uses OpenAI embeddings
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local")


settings = Settings()
