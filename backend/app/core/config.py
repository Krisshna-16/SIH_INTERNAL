import json
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "UFDR Analysis Platform"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    DATABASE_URL: str = "sqlite:///./ufdr.db"
    LOG_LEVEL: str = "INFO"
    EXTERNAL_LLM_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or not isinstance(v, str) or not v.strip():
            raise ValueError("DATABASE_URL configuration parameter is missing or empty. Application cannot start.")
        s_val = v.strip()
        valid_schemes = ("sqlite://", "postgresql://", "postgres://", "mysql://")
        if not any(s_val.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(f"DATABASE_URL '{v}' has an invalid or unsupported database scheme. Must start with one of {valid_schemes}.")
        return s_val

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in v_str.split(",") if item.strip()]
        elif isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        raise ValueError("ALLOWED_ORIGINS must be a list of origin strings or a comma-separated/JSON string.")


settings = Settings()
