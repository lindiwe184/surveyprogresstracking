import os


class BaseConfig:
    """Base configuration shared across environments."""

    APP_NAME = "Namibia Survey Tracking System"
    
    # PostgreSQL database connection
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://survey_user:Timer%402001@localhost:5432/survey_tracking",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Connection pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
    }
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = ENV == "development"


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "production")
    return config_by_name.get(env, ProductionConfig)


