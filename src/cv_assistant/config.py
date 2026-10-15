from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", str_strip_whitespace=True)

    groq_api_key: SecretStr
    database_url: SecretStr
    data_encryption_key: SecretStr
    checkpoint_encryption_key: SecretStr
    auth_jwks_url: str
    auth_issuer: str
    auth_audience: str
    deployment_jurisdictions: str = ""
    legal_review_reference: str = ""
    bias_audit_reference: str = ""
    privacy_review_reference: str = ""
    review_workflow_reference: str = ""
    groq_zero_data_retention: bool = False
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = 30.0
    max_retry_attempts: int = 3
    retry_base_delay_seconds: float = 1.0
    max_resume_chars: int = 100_000
    similarity_threshold: float = 0.85
    app_env: str = "development"

    @field_validator("max_retry_attempts")
    @classmethod
    def validate_attempts(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("max_retry_attempts must be between 1 and 5")
        return value

    @field_validator("groq_timeout_seconds", "retry_base_delay_seconds")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("timeout and retry delay must be positive")
        return value

    @field_validator("max_resume_chars")
    @classmethod
    def validate_resume_limit(cls, value: int) -> int:
        if not 20 <= value <= 100_000:
            raise ValueError("max_resume_chars must be between 20 and 100000")
        return value

    @field_validator("similarity_threshold")
    @classmethod
    def validate_similarity_threshold(cls, value: float) -> float:
        if not 0 < value <= 1:
            raise ValueError("similarity_threshold must be in (0, 1]")
        return value

    @field_validator("auth_jwks_url")
    @classmethod
    def validate_jwks_url(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("AUTH_JWKS_URL must use HTTPS")
        return value

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, value: str) -> str:
        normalized = value.casefold()
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV must be development, test, staging, or production")
        return normalized

    @field_validator("data_encryption_key", "checkpoint_encryption_key")
    @classmethod
    def validate_fernet_key(cls, value: SecretStr) -> SecretStr:
        try:
            Fernet(value.get_secret_value().encode("ascii"))
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("encryption keys must be valid urlsafe Fernet keys") from exc
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_production_readiness(settings: Settings) -> None:
    if settings.app_env in {"development", "test"}:
        return
    missing: list[str] = []
    required = {
        "AUTH_ISSUER": settings.auth_issuer,
        "AUTH_AUDIENCE": settings.auth_audience,
        "DEPLOYMENT_JURISDICTIONS": settings.deployment_jurisdictions,
        "LEGAL_REVIEW_REFERENCE": settings.legal_review_reference,
        "BIAS_AUDIT_REFERENCE": settings.bias_audit_reference,
        "PRIVACY_REVIEW_REFERENCE": settings.privacy_review_reference,
        "REVIEW_WORKFLOW_REFERENCE": settings.review_workflow_reference,
    }
    if not settings.groq_zero_data_retention:
        missing.append("GROQ_ZERO_DATA_RETENTION=true")
    database_url = settings.database_url.get_secret_value().casefold()
    if "sslmode=verify-full" not in database_url:
        missing.append("DATABASE_URL with sslmode=verify-full")
    missing.extend(name for name, value in required.items() if not value.strip())
    if missing:
        raise ValueError("Production startup blocked; configure approved references for: " + ", ".join(missing))
