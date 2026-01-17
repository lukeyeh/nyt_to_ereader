"""Fetch and parse full article content from NYT."""
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import Dict, Optional
from http.cookiejar import MozillaCookieJar


class ArticleFetcher:
    """Fetches and parses full article content from NYT article pages."""

    def __init__(self, cookie_file: Optional[str] = None):
        """Initialize the article fetcher.

        Args:
            cookie_file: Path to cookie file (JSON or Netscape format)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # Load cookies if provided
        if cookie_file:
            self._load_cookies(cookie_file)

    def _load_cookies(self, cookie_file: str):
        """Load cookies from a file.

        Supports both JSON format and Netscape cookie jar format.

        Args:
            cookie_file: Path to the cookie file
        """
        cookie_path = Path(cookie_file)

        if not cookie_path.exists():
            print(f"Warning: Cookie file not found: {cookie_file}")
            return

        try:
            # Try JSON format first
            if cookie_path.suffix == '.json':
                with open(cookie_path, 'r') as f:
                    cookies = json.load(f)

                # Handle different JSON cookie formats
                if isinstance(cookies, list):
                    # Format: [{"name": "...", "value": "...", "domain": "..."}, ...]
                    for cookie in cookies:
                        self.session.cookies.set(
                            name=cookie.get('name'),
                            value=cookie.get('value'),
                            domain=cookie.get('domain', '.nytimes.com'),
                            path=cookie.get('path', '/')
                        )
                elif isinstance(cookies, dict):
                    # Format: {"cookie_name": "cookie_value", ...}
                    for name, value in cookies.items():
                        self.session.cookies.set(name, value, domain='.nytimes.com')

                print(f"Loaded {len(self.session.cookies)} cookies from {cookie_file}")

            # Try Netscape cookie jar format
            else:
                cookie_jar = MozillaCookieJar(cookie_file)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                self.session.cookies.update(cookie_jar)
                print(f"Loaded {len(cookie_jar)} cookies from {cookie_file}")

        except Exception as e:
            print(f"Warning: Could not load cookies from {cookie_file}: {e}")
            print("Continuing without authentication - full articles may not be available.")

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch the full article content from a URL.

        Args:
            url: The article URL

        Returns:
            HTML content of the article, or None if fetch fails
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # NYT articles are typically in a <article> tag or sections with specific classes
            # Try to find the main article content
            article_body = None

            # Try various selectors that NYT uses
            selectors = [
                'article[id="story"]',
                'section[name="articleBody"]',
                'div.story-body',
                'article.story',
                'div.article-body',
            ]

            for selector in selectors:
                article_body = soup.select_one(selector)
                if article_body:
                    break

            if not article_body:
                # Fallback: try to find all paragraph tags
                article_body = soup.find('article')

            if article_body:
                # Remove script, style, and nav elements
                for element in article_body.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                    element.decompose()

                # Get all paragraphs
                paragraphs = article_body.find_all(['p', 'h2', 'h3'])
                content_html = ''.join(str(p) for p in paragraphs)

                return content_html

            return None

        except Exception as e:
            print(f"Error fetching article from {url}: {e}")
            return None

    def create_article_html(self, article_details: Dict, content: Optional[str]) -> str:
        """Create formatted HTML for an article.

        Args:
            article_details: Article metadata
            content: Article content HTML

        Returns:
            Formatted HTML string
        """
        title = article_details.get('title', 'Untitled')
        byline = article_details.get('byline', '')
        abstract = article_details.get('abstract', '')
        published_date = article_details.get('published_date', '')

        html = f"""
        <html>
        <head>
            <title>{title}</title>
        </head>
        <body>
            <h1>{title}</h1>
            <p><em>{byline}</em></p>
            <p><small>{published_date}</small></p>
            <p><strong>{abstract}</strong></p>
            <hr/>
        """

        if content:
            html += f"\n{content}\n"
        else:
            html += f"""
            <p><em>Full article content not available. Please visit:</em></p>
            <p><a href="{article_details.get('url', '')}">{article_details.get('url', '')}</a></p>
            """

        html += """
        </body>
        </html>
        """

        return html
