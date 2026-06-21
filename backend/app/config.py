"""
Azure Incident Log Pipeline — Application Configuration
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
    app_name: str = "Azure Incident Log Pipeline"
    app_version: str = "2.0.0"
    debug: bool = True
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Database (Azure PostgreSQL) ---
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/incident_pipeline"
    database_sync_url: str = "postgresql://postgres:postgres@localhost:5432/incident_pipeline"

    # --- Azure Subscription & Auth ---
    azure_subscription_id: str = ""
    azure_resource_group: str = ""
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # --- Azure Log Sources ---
    azure_frontdoor_resource_id: str = ""
    azure_appgateway_resource_id: str = ""
    azure_apim_resource_id: str = ""
    azure_appservice_url: str = ""
    azure_apim_gateway_url: str = ""
    azure_appgw_public_ip: str = ""
    azure_appgw_dns: str = ""
    azure_vm_resource_id: str = ""
    azure_log_analytics_workspace_id: str = ""

    # --- GCP / Vertex AI ---
    google_application_credentials: str = "../service-account-key.json"
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"

    # --- Scheduler ---
    scheduler_interval_hours: int = 6
    scheduler_enabled: bool = True

    # --- Pipeline Control ---
    pipeline_enabled: bool = True

    # --- Notification ---
    notification_channel: str = "smtp"  # "smtp" or "azure_communication_service"
    azure_communication_connection_string: str = ""
    azure_communication_sender: str = ""

    # --- SMTP Email ---
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_to_email: str = ""

    # --- Authentication (JWT) ---
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # --- Export ---
    export_dir: str = "./exports"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def scheduler_interval_seconds(self) -> int:
        """Scheduler interval in seconds."""
        return self.scheduler_interval_hours * 3600

    @property
    def azure_log_source_ids(self) -> dict[str, str]:
        """Map of source name to Azure resource ID."""
        sources = {}
        if self.azure_frontdoor_resource_id:
            sources["azure-front-door"] = self.azure_frontdoor_resource_id
        if self.azure_appgateway_resource_id:
            sources["azure-app-gateway"] = self.azure_appgateway_resource_id
        if self.azure_apim_resource_id:
            sources["azure-apim"] = self.azure_apim_resource_id
        if self.azure_vm_resource_id:
            sources["azure-vm"] = self.azure_vm_resource_id
        return sources

    def setup_gcp_credentials(self) -> None:
        """Set the GOOGLE_APPLICATION_CREDENTIALS environment variable."""
        cred_path = Path(self.google_application_credentials)
        if not cred_path.is_absolute():
            cred_path = Path(__file__).parent.parent / cred_path
        cred_path = cred_path.resolve()
        if cred_path.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred_path)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.setup_gcp_credentials()
    return settings
