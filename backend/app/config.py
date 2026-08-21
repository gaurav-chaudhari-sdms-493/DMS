from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from typing import Literal, List
import json

class Settings(BaseSettings):
    # App
    app_env: Literal['development', 'production', 'test'] = 'development'
    cors_origins: List[str] = ['*']
    
    # File Upload limits
    max_upload_size_mb: int = 50
    allowed_upload_extensions: List[str] = [
        "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
        "csv", "txt", "md", "rtf", "json", "jpg", "jpeg", "png", "webp", "bmp",
        # Code / config / plain-text formats — all handled by the same
        # plain-text extraction fallback as .txt/.md, so no new parser needed.
        "py", "js", "jsx", "ts", "tsx", "java", "c", "cpp", "h", "hpp", "cs",
        "go", "rb", "php", "sh", "bash", "sql", "yaml", "yml", "xml",
        "html", "css", "scss", "log", "ini", "toml", "conf",
    ]
    
    # Database
    postgres_url: str
    
    # Redis
    redis_url: str
    
    # JWT
    jwt_secret_key: str = 'secret'
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 43200  # 30 days
    jwt_refresh_token_expire_days: int = 60  # 60 days
    
    # AWS S3 / MinIO
    aws_access_key_id: str = 'minioadmin'
    aws_secret_access_key: str = 'minioadmin'
    aws_region: str = 'us-east-1'
    s3_bucket_name: str = 'docsearch-documents'
    s3_endpoint_url: str = 'http://localhost:9000'
    s3_public_endpoint_url: str = 'http://localhost:9000'
    s3_presigned_url_expiry_seconds: int = 900
    
    # AI Providers
    ai_llm_provider: Literal['openai', 'anthropic', 'groq'] = 'openai'
    ai_embed_provider: Literal['openai', 'bgem3', 'gemini', 'cohere'] = 'bgem3'
    ai_embed_fallback_provider: Literal['cohere', 'openai', 'none'] = 'none'
    ai_rerank_provider: Literal['cohere', 'bgem3', 'none'] = 'cohere'
    ai_ocr_provider: Literal['pdfplumber', 'llamaparse'] = 'pdfplumber'
    
    openai_api_key: str = ''
    openai_llm_model: str = 'gpt-4o-mini'
    openai_embed_model: str = 'text-embedding-3-small'
    openai_embed_dimensions: int = 1024
    
    anthropic_api_key: str = ''
    anthropic_llm_model: str = 'claude-3-5-haiku-20241022'
    
    groq_api_key: str = ''
    groq_api_key1: str = ''
    groq_api_key2: str = ''
    groq_api_key3: str = ''
    groq_api_keys: str = ''
    groq_llm_model: str = 'openai/gpt-oss-120b'
    
    def get_groq_api_keys(self) -> List[str]:
        keys = []
        for k in [self.groq_api_key, self.groq_api_key1, self.groq_api_key2, self.groq_api_key3]:
            if k and k.strip() and k.strip() not in keys:
                keys.append(k.strip())
        if self.groq_api_keys:
            for k in self.groq_api_keys.split(','):
                k_clean = k.strip()
                if k_clean and k_clean not in keys:
                    keys.append(k_clean)
        return keys

    
    google_api_key: str = ''
    gemini_embed_model: str = 'text-embedding-004'
    
    cohere_api_key: str = ''
    cohere_rerank_model: str = 'rerank-english-v3.0'
    bgem3_rerank_model: str = 'BAAI/bge-reranker-v2-m3'
    
    llamaparse_api_key: str = ''
    
    # Rate limiting
    rate_limit_per_user: str = '60/minute'
    rate_limit_per_tenant: str = '1000/minute'

    # SFTP connector (demo scope: single fixed server/credentials/remote dir)
    sftp_enabled: bool = False
    sftp_host: str = 'sftp'
    sftp_port: int = 22
    sftp_username: str = 'connector'
    sftp_password: str = ''
    sftp_remote_dir: str = '/upload'

    # The host/port an OUTSIDE machine should actually dial in to reach the SFTP
    # server (sftp_host/sftp_port above are the Docker-internal address the
    # backend uses to poll it, not reachable from another laptop on the LAN).
    sftp_external_host: str = 'localhost'
    sftp_external_port: int = 2222

    # Email-in connector (demo scope: single fixed local mailbox, not real
    # internet email — see docker-compose 'mailserver' service)
    email_enabled: bool = False
    email_imap_host: str = 'mailserver'
    email_imap_port: int = 3143
    email_username: str = 'connector'
    email_password: str = ''
    email_address: str = 'connector@dms.local'

    # The host/port an OUTSIDE machine should use to SEND mail into the demo
    # mailbox over SMTP (not the IMAP host/port above, which the backend uses
    # to poll it).
    email_external_smtp_host: str = 'localhost'
    email_external_smtp_port: int = 3025
    
    @field_validator('cors_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    @model_validator(mode='after')
    def validate_production_jwt_secret(self):
        WEAK_SECRETS = {"secret", "change_me", "changeme", "secretkey", "jwtsecret", "password", "123456"}
        if self.app_env == "production":
            if self.jwt_secret_key.lower() in WEAK_SECRETS or len(self.jwt_secret_key) < 32:
                raise ValueError("In production, JWT_SECRET_KEY must be a strong secret of at least 32 characters")
        return self
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False
        extra = 'ignore'

settings = Settings()