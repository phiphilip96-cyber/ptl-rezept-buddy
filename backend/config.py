from pydantic_settings import BaseSettings, SettingsConfigDict


class Einstellungen(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB: str = "ptl_buddy"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    JWT_SECRET: str = "dev-secret"
    JWT_GUELTIG_STUNDEN: int = 24 * 30
    APP_URL: str = "http://localhost:5173"
    MAIL_HOST: str = ""
    MAIL_PORT: int = 587
    MAIL_USER: str = ""
    MAIL_PASS: str = ""
    MAIL_FROM: str = "coach@ptl-pforzheim.de"
    COACH_EMAIL: str = ""
    COACH_PASSWORT: str = ""
    PROMPT_DATEI: str = "../prompts/rezept_buddy.md"
    MAX_TOOL_AUFRUFE: int = 6


einstellungen = Einstellungen()
