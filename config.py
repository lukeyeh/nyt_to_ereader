"""Configuration management for NYT to eReader converter."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the application."""

    NYT_API_KEY = os.getenv('NYT_API_KEY')
    NYT_API_BASE_URL = 'https://api.nytimes.com/svc/topstories/v2'

    # Default section to fetch (home is the front page)
    DEFAULT_SECTION = 'home'

    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.NYT_API_KEY:
            raise ValueError(
                "NYT_API_KEY not found. Please set it in your .env file.\n"
                "Get your API key from https://developer.nytimes.com/"
            )
        return True
