from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "DraftAdvisor API"
    data_dir: str = "data"  # chemin relatif depuis DraftAPI/

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()