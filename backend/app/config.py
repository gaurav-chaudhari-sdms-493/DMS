from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import Literal, List
import json

class Settings(BaseSettings):
    # App
    app_env: Literal['development', 'production', 'test'] = 'development'
    cors_origins: List[str] = ['http://localhost:3000']
    
    # Database
    postgres_url: str = 'postgresql+asyncpg://user:pass@localhost:5432/db'
    
    # Redis
    redis_url: str = 'redis://localhost:6379/0'
    
    # JWT
    jwt_secret_key: str = 'secret'
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    
    # AWS S3
    aws_access_key_id: str = 'key'
    aws_secret_access_key: str = 'secret'
    aws_region: str = 'us-east-1'
    s3_bucket_name: str = 'bucket'
    s3_presigned_url_expiry_seconds: int = 900
    
    # AI Providers
    ai_llm_provider: Literal['openai', 'anthropic', 'groq'] = 'groq'
    ai_embed_provider: Literal['openai', 'bgem3', 'gemini'] = 'bgem3'
    ai_embed_fallback_provider: Literal['cohere', 'none'] = 'cohere'
    ai_rerank_provider: Literal['cohere', 'none'] = 'cohere'
    ai_ocr_provider: Literal['pdfplumber', 'llamaparse', 'gcv'] = 'pdfplumber'
    
    # Groq
    groq_api_key: str = ''
    groq_llm_model: str = 'llama-3.3-70b-versatile'

    # Gemini
    google_api_key: str = ''
    gemini_embed_model: str = 'text-embedding-004'

    # OpenAI
    openai_api_key: str = ''
    openai_llm_model: str = 'gpt-4o-mini'
    openai_embed_model: str = 'text-embedding-3-small'
    openai_embed_dimensions: int = 1536
    
    # Anthropic (alternative LLM)
    anthropic_api_key: str = ''
    anthropic_llm_model: str = 'claude-3-5-haiku-20241022'
    
    # Cohere (reranker + fallback embed)
    cohere_api_key: str = ''
    cohere_rerank_model: str = 'rerank-english-v3.0'
    
    # LlamaParse
    llamaparse_api_key: str = ''
    
    # Google Cloud Vision Credentials
    google_application_credentials_json: str = ''
    google_application_credentials_path: str = ''

    # Rate limiting
    rate_limit_per_user: str = '60/minute'
    rate_limit_per_tenant: str = '1000/minute'
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'

settings = Settings()
