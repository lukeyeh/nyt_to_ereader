"""Fetch and parse full article content from NYT."""
import json
from pathlib import Path
from typing import Dict, Optional
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


class ArticleFetcher:
    """Fetches and parses full article content from NYT article pages using a real browser."""

    def __init__(self, cookie_file: Optional[str] = None, use_browser: bool = True):
        """Initialize the article fetcher.

        Args:
            cookie_file: Path to cookie file (JSON format for Playwright)
            use_browser: Use real browser via Playwright (recommended, bypasses bot detection)
        """
        self.cookie_file = cookie_file
        self.cookies = []
        self.use_browser = use_browser and PLAYWRIGHT_AVAILABLE

        if not PLAYWRIGHT_AVAILABLE and use_browser:
            print("⚠ Playwright not installed. Install with: pip install playwright && playwright install chromium")
            print("  Continuing without browser automation - articles may be blocked by paywall")
            self.use_browser = False

        # Load cookies if provided
        if cookie_file:
            self._load_cookies(cookie_file)

    def _load_cookies(self, cookie_file: str):
        """Load cookies from a JSON file.

        Args:
            cookie_file: Path to the cookie file (JSON format)
        """
        cookie_path = Path(cookie_file)

        if not cookie_path.exists():
            print(f"⚠ Warning: Cookie file not found: {cookie_file}")
            return

        try:
            with open(cookie_path, 'r') as f:
                cookies_data = json.load(f)

            # Convert to Playwright cookie format
            if isinstance(cookies_data, list):
                for cookie in cookies_data:
                    # Playwright expects specific format
                    playwright_cookie = {
                        'name': cookie.get('name'),
                        'value': cookie.get('value'),
                        'domain': cookie.get('domain', '.nytimes.com'),
                        'path': cookie.get('path', '/'),
                    }
                    # Add optional fields if present
                    if 'expires' in cookie:
                        playwright_cookie['expires'] = cookie['expires']
                    if 'httpOnly' in cookie:
                        playwright_cookie['httpOnly'] = cookie['httpOnly']
                    if 'secure' in cookie:
                        playwright_cookie['secure'] = cookie['secure']

                    # Handle sameSite - Playwright is strict about valid values
                    if 'sameSite' in cookie:
                        same_site = cookie['sameSite']
                        # Normalize to capitalized format
                        if isinstance(same_site, str):
                            same_site_normalized = same_site.capitalize()
                            # Only include if it's a valid value
                            if same_site_normalized in ['Strict', 'Lax', 'None']:
                                playwright_cookie['sameSite'] = same_site_normalized
                            # Handle special case for "no_restriction" -> "None"
                            elif same_site.lower() == 'no_restriction':
                                playwright_cookie['sameSite'] = 'None'

                    self.cookies.append(playwright_cookie)

            elif isinstance(cookies_data, dict):
                # Simple format: {"cookie_name": "cookie_value"}
                for name, value in cookies_data.items():
                    self.cookies.append({
                        'name': name,
                        'value': value,
                        'domain': '.nytimes.com',
                        'path': '/'
                    })

            cookie_names = [c['name'] for c in self.cookies]
            print(f"✓ Loaded {len(self.cookies)} cookies from {cookie_file}")
            print(f"  Cookie names: {', '.join(cookie_names[:10])}")
            if len(cookie_names) > 10:
                print(f"  ... and {len(cookie_names) - 10} more")

            # Check for important NYT authentication cookies
            important_cookies = ['nyt-a', 'nyt-s', 'NYT-S', 'nyt-auth-method']
            found_auth = [c for c in important_cookies if c in cookie_names]
            if found_auth:
                print(f"  ✓ Found authentication cookies: {', '.join(found_auth)}")
            else:
                print(f"  ⚠ Warning: No standard NYT authentication cookies found")
                print(f"    Expected one of: {', '.join(important_cookies)}")

        except Exception as e:
            print(f"⚠ Warning: Could not load cookies from {cookie_file}: {e}")
            print("  Continuing without authentication - full articles may not be available.")

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch the full article content from a URL.

        Args:
            url: The article URL

        Returns:
            HTML content of the article, or None if fetch fails
        """
        if self.use_browser:
            return self._fetch_with_browser(url)
        else:
            print(f"    ⚠ Browser automation not available - article may be blocked")
            return None

    def _fetch_with_browser(self, url: str) -> Optional[str]:
        """Fetch article using a real browser with anti-detection measures.

        Args:
            url: The article URL

        Returns:
            HTML content of the article, or None if fetch fails
        """
        try:
            with sync_playwright() as p:
                # Launch browser with anti-detection flags
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process'
                    ]
                )

                # Create context with realistic device emulation
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    permissions=['geolocation'],
                    color_scheme='light',
                    extra_http_headers={
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
                    }
                )

                # Add cookies if available (BEFORE creating the page)
                if self.cookies:
                    context.add_cookies(self.cookies)

                # Create new page
                page = context.new_page()

                # Add JavaScript to hide automation indicators
                page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    window.chrome = {
                        runtime: {}
                    };

                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });

                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                """)

                # Navigate to article with realistic behavior
                try:
                    # FIRST: Visit NYT homepage to establish session (looks more human)
                    print(f"    Establishing session at nytimes.com...")
                    page.goto('https://www.nytimes.com/', wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(1000 + (hash(url) % 1000))  # Random delay 1-2s

                    # NOW: Navigate to the actual article
                    print(f"    Fetching article...")
                    response = page.goto(url, wait_until='networkidle', timeout=45000)

                    # Check if we got blocked
                    if response and response.status == 403:
                        print(f"    ⚠ 403 Forbidden - NYT blocked the request")
                        browser.close()
                        return None

                    # Wait for content to fully load (random human-like delay)
                    import time
                    page.wait_for_timeout(2000 + (hash(url) % 1500))

                    # Scroll down a bit (human behavior)
                    page.evaluate('window.scrollBy(0, 500)')
                    page.wait_for_timeout(500)

                    # Get the page content
                    html_content = page.content()

                    # Close browser
                    browser.close()

                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')

                    # Check for paywall indicators
                    if soup.find(string=lambda text: text and 'subscribe' in text.lower()):
                        paywall_divs = soup.find_all(['div', 'section'], class_=lambda x: x and ('paywall' in str(x).lower() or 'gateway' in str(x).lower()))
                        if paywall_divs:
                            print(f"    ⚠ Paywall detected - cookies may be invalid or expired")
                            return None

                    # Try to find the main article content
                    article_body = None

                    # Try various selectors that NYT uses
                    selectors = [
                        'article[id="story"]',
                        'section[name="articleBody"]',
                        'div.story-body',
                        'article.story',
                        'div.article-body',
                        'article',
                    ]

                    for selector in selectors:
                        article_body = soup.select_one(selector)
                        if article_body:
                            break

                    if article_body:
                        # Remove unwanted elements
                        for element in article_body.find_all(['script', 'style', 'nav', 'aside', 'footer', 'button']):
                            element.decompose()

                        # Get all content paragraphs and headers
                        paragraphs = article_body.find_all(['p', 'h2', 'h3', 'h4', 'blockquote'])
                        content_html = ''.join(str(p) for p in paragraphs)

                        if content_html.strip():
                            return content_html

                    print(f"    ⚠ Could not find article content on page")
                    return None

                except Exception as e:
                    print(f"    ⚠ Error loading page: {e}")
                    browser.close()
                    return None

        except Exception as e:
            print(f"    ⚠ Browser error: {e}")
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
