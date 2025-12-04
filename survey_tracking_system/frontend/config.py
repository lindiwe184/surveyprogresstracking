import os


def get_api_base_url() -> str:
    """
    Base URL for backend API, configurable via env var FRONTEND_API_BASE_URL.
    """
    return os.getenv("FRONTEND_API_BASE_URL", "http://localhost:5001")


