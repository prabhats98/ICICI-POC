"""
Banking Cloud Log Analyser - Application Configuration
Loads all settings from .env file using Pydantic Settings.
"""

import os
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "Banking Cloud Log Analyser"
    app_version: str = "1.0.0"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/banking_log_analyser"
    database_sync_url: str = "postgresql://postgres:postgres@localhost:5432/banking_log_analyser"

    # --- GCP / Vertex AI ---
    google_application_credentials: str = "../service-account-key.json"
    gcp_project_id: str = "gen-ai-poc-onboarding"
    gcp_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"

    # --- SMTP Email ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = "demo-alerts@example.com"
    smtp_password: str = "demo-password-replace-me"
    smtp_from_email: str = "demo-alerts@example.com"
    smtp_to_email: str = "production-manager@example.com"

    # --- Scheduler ---
    scheduler_interval_minutes: int = 5

    # --- Export ---
    export_dir: str = "./exports"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def setup_gcp_credentials(self) -> None:
        """Set the GOOGLE_APPLICATION_CREDENTIALS environment variable."""
        cred_path = Path(self.google_application_credentials)
        if not cred_path.is_absolute():
            # Resolve relative to the backend directory
            cred_path = Path(__file__).parent.parent / cred_path
        cred_path = cred_path.resolve()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.setup_gcp_credentials()
    return settings
