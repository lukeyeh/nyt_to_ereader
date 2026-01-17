"""Client for interacting with the NYT Top Stories API."""
import requests
from typing import List, Dict, Optional
from config import Config


class NYTClient:
    """Client for fetching top stories from the New York Times API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the NYT client.

        Args:
            api_key: NYT API key. If not provided, will use Config.NYT_API_KEY
        """
        self.api_key = api_key or Config.NYT_API_KEY
        if not self.api_key:
            raise ValueError("API key is required")
        self.base_url = Config.NYT_API_BASE_URL

    def get_top_stories(self, section: str = 'home') -> List[Dict]:
        """Fetch top stories from a specific section.

        Args:
            section: The section to fetch (e.g., 'home', 'world', 'business')

        Returns:
            List of article dictionaries

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/{section}.json"
        params = {'api-key': self.api_key}

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('results', [])

    def get_article_details(self, article: Dict) -> Dict:
        """Extract relevant details from an article.

        Args:
            article: Raw article data from API

        Returns:
            Dictionary with cleaned article details
        """
        return {
            'title': article.get('title', 'Untitled'),
            'abstract': article.get('abstract', ''),
            'byline': article.get('byline', 'By NYT Staff'),
            'published_date': article.get('published_date', ''),
            'url': article.get('url', ''),
            'section': article.get('section', ''),
            'subsection': article.get('subsection', ''),
            'multimedia': article.get('multimedia', []),
        }
