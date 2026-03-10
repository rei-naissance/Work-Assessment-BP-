import os
import warnings
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongo_uri: str = Field(
        default="mongodb://localhost:27017/home_binder",
        validation_alias=AliasChoices("MONGO_URI", "MONGODB_URI", "mongo_uri"),
    )
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    data_dir: str = "./data/binders"
    port: int = 7691
    resend_api_key: str = ""
    from_email: str = "noreply@mybinderpro.com"
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "homebinder:8b"
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    frontend_url: str = "http://localhost:7680"
    encryption_key: str = ""  # Fernet key for field-level encryption (required in production)
    ai_enhancement_enabled: bool = True
    ai_enhancement_provider: str = "auto"  # "claude", "ollama", "auto", "none"
    environment: str = "development"  # development, staging, production
    # Comma-separated origins for CORS; empty = use frontend_url in production, * in dev
    cors_origins: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    def get_cors_origins(self) -> list[str]:
        """Return list of allowed CORS origins. Production defaults to frontend_url only."""
        if self.cors_origins.strip():
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.environment == "production":
            return [self.frontend_url.rstrip("/")]
        return ["*"]  # development: allow all

    def validate_for_production(self) -> list[str]:
        """Check if all required production settings are configured.

        Returns list of missing/invalid settings.
        """
        issues = []

        if self.jwt_secret == "change-me-in-production":
            issues.append("JWT_SECRET must be changed for production")

        if self.environment == "production":
            if not self.encryption_key:
                issues.append("ENCRYPTION_KEY is required for production (generate with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')")
            if not self.stripe_secret_key:
                issues.append("STRIPE_SECRET_KEY is required for production")
            if not self.stripe_webhook_secret:
                issues.append("STRIPE_WEBHOOK_SECRET is required for production")
            if not self.resend_api_key:
                issues.append("RESEND_API_KEY is required for production emails")
            if "localhost" in self.frontend_url:
                issues.append("FRONTEND_URL should not be localhost in production")
            if self.ai_enhancement_enabled and self.ai_enhancement_provider in ("ollama", "auto") and "localhost" in self.ollama_base_url:
                warnings.warn("OLLAMA_BASE_URL is localhost — Ollama will be unavailable in production unless configured")
            if "localhost" in self.mongo_uri:
                warnings.warn("Using localhost MongoDB in production - consider using Atlas")
            elif "tls=true" not in self.mongo_uri and "ssl=true" not in self.mongo_uri and "+srv" not in self.mongo_uri:
                issues.append("MONGO_URI should use TLS in production (add tls=true or use mongodb+srv://)")

        return issues


settings = Settings()

# Validate config on startup
if settings.environment == "production":
    issues = settings.validate_for_production()
    if issues:
        error_msg = "Production config validation failed:\n" + "\n".join(f"  - {i}" for i in issues)
        raise RuntimeError(error_msg)
elif settings.environment != "development":
    # For staging, warn but don't fail
    issues = settings.validate_for_production()
    for issue in issues:
        warnings.warn(f"Config warning: {issue}")
