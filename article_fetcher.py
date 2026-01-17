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

                cookie_names = [c.name for c in self.session.cookies]
                print(f"✓ Loaded {len(self.session.cookies)} cookies from {cookie_file}")
                print(f"  Cookie names: {', '.join(cookie_names)}")

                # Check for important NYT authentication cookies
                important_cookies = ['nyt-a', 'nyt-s', 'NYT-S', 'nyt-auth-method']
                found_auth = [c for c in important_cookies if c in cookie_names]
                if found_auth:
                    print(f"  ✓ Found authentication cookies: {', '.join(found_auth)}")
                else:
                    print(f"  ⚠ Warning: No standard NYT authentication cookies found")
                    print(f"    Expected one of: {', '.join(important_cookies)}")

            # Try Netscape cookie jar format
            else:
                cookie_jar = MozillaCookieJar(cookie_file)
                cookie_jar.load(ignore_discard=True, ignore_expires=True)
                self.session.cookies.update(cookie_jar)

                cookie_names = [c.name for c in cookie_jar]
                print(f"✓ Loaded {len(cookie_jar)} cookies from {cookie_file}")
                print(f"  Cookie names: {', '.join(cookie_names)}")

                # Check for important NYT authentication cookies
                important_cookies = ['nyt-a', 'nyt-s', 'NYT-S', 'nyt-auth-method']
                found_auth = [c for c in important_cookies if c in cookie_names]
                if found_auth:
                    print(f"  ✓ Found authentication cookies: {', '.join(found_auth)}")
                else:
                    print(f"  ⚠ Warning: No standard NYT authentication cookies found")
                    print(f"    Expected one of: {', '.join(important_cookies)}")

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
            # Add comprehensive browser-like headers for each request
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
                'Referer': 'https://www.nytimes.com/'
            }

            response = self.session.get(url, headers=headers, timeout=30)

            # Debug: Check if we got a paywall response
            if response.status_code == 403:
                print(f"    ⚠ 403 Forbidden - Authentication may have failed")
                print(f"    Cookies in session: {len(self.session.cookies)} cookies")
                # Check if we got a paywall page
                if 'subscribe' in response.text.lower() or 'paywall' in response.text.lower():
                    print(f"    ⚠ Paywall detected - cookies may be invalid or expired")
                return None

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

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"    ⚠ 403 Forbidden: NYT blocked the request")
                print(f"    This usually means:")
                print(f"      - Cookies are missing, invalid, or expired")
                print(f"      - You need to re-export cookies from your browser")
                print(f"      - Make sure you're logged in to nytimes.com before exporting")
            else:
                print(f"    ⚠ HTTP Error {e.response.status_code}: {e}")
            return None
        except Exception as e:
            print(f"    ⚠ Error fetching article: {e}")
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
