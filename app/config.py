from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_base_url: str
    parser_model: str
    buhgalter_model: str
    docling_base_url: str

    input_dir: str
    review_pending_dir: str
    approved_dir: str
    rejected_dir: str
    contragents_file: str
    client_name: str
    client_edrpou: str
    client_ipn: str
    non_business_operations_file: str

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    langfuse_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()