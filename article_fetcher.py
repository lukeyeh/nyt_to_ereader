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

    def __init__(self, cookie_file: Optional[str] = None, use_browser: bool = True, headless: bool = True, login_mode: bool = False):
        """Initialize the article fetcher.

        Args:
            cookie_file: Path to cookie file (JSON format for Playwright)
            use_browser: Use real browser via Playwright (recommended, bypasses bot detection)
            headless: Run browser in headless mode (set False for debugging)
            login_mode: Interactive login mode - opens browser for manual login
        """
        self.cookie_file = cookie_file
        self.cookies = []
        self.use_browser = use_browser and PLAYWRIGHT_AVAILABLE
        self.headless = headless if not login_mode else False  # Login mode always non-headless
        self.login_mode = login_mode
        self.browser = None
        self.context = None
        self.logged_in = False

        if not PLAYWRIGHT_AVAILABLE and use_browser:
            print("⚠ Playwright not installed. Install with: pip install playwright && playwright install chromium")
            print("  Continuing without browser automation - articles may be blocked by paywall")
            self.use_browser = False

        # Load cookies if provided (not in login mode)
        if cookie_file and not login_mode:
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

    def interactive_login(self):
        """Open browser for interactive login to NYT.

        This method opens a browser window where you can manually log in to NYT.
        After you log in, the session is preserved for fetching articles.
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("⚠ Playwright not available. Cannot use interactive login.")
            return False

        try:
            from playwright.sync_api import sync_playwright

            print("\n" + "="*60)
            print("INTERACTIVE LOGIN MODE")
            print("="*60)
            print("\nA browser window will open. Please:")
            print("  1. Log in to your NYT account")
            print("  2. Wait until you see your personalized homepage")
            print("  3. Come back here and press ENTER to continue")
            print("\nOpening browser in 3 seconds...")
            print("="*60 + "\n")

            import time
            time.sleep(3)

            # Start playwright
            self.playwright = sync_playwright().start()

            # Launch browser (NON-headless for login) with maximum stealth
            self.browser = self.playwright.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--disable-dev-shm-usage',
                    '--disable-browser-side-navigation',
                    '--disable-gpu',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-web-security',
                ]
            )

            # Create context
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
            )

            # Create page
            page = self.context.new_page()

            # Add stealth JavaScript (same as main fetcher)
            page.add_init_script("""
                // Override webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Add chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                        {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                        {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                    ]
                });

                // Override other detection points
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
            """)

            # Navigate to NYT login page
            print("📱 Opening NYT login page...")
            page.goto('https://myaccount.nytimes.com/auth/login', wait_until='domcontentloaded', timeout=30000)

            # Wait for user to log in
            print("\n✋ Waiting for you to log in...")
            print("   If you see a CAPTCHA (puzzle piece), solve it first!")
            print("   After logging in successfully, press ENTER here to continue...\n")
            input(">>> Press ENTER when you're logged in and see the NYT homepage >>> ")

            # Verify login by checking for user-specific elements
            print("\n🔍 Verifying login status...")
            page.goto('https://www.nytimes.com/', wait_until='domcontentloaded', timeout=15000)
            time.sleep(2)

            # Check for CAPTCHA on homepage
            self._detect_and_handle_captcha(page)

            # Check if logged in (look for account indicators)
            html = page.content()
            if 'myaccount' in html.lower() or 'account' in html.lower():
                print("✅ Successfully logged in!")
                self.logged_in = True

                # Save cookies for future use (optional)
                cookies = self.context.cookies()
                print(f"📦 Session active with {len(cookies)} cookies")

                return True
            else:
                print("⚠️  Could not verify login. Proceeding anyway...")
                self.logged_in = True  # Assume success
                return True

        except Exception as e:
            print(f"❌ Error during interactive login: {e}")
            if self.browser:
                self.browser.close()
            self.browser = None
            self.context = None
            return False

    def cleanup(self):
        """Clean up browser resources."""
        if self.browser:
            try:
                self.browser.close()
                self.playwright.stop()
            except:
                pass
            self.browser = None
            self.context = None

    def fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch the full article content from a URL.

        Args:
            url: The article URL

        Returns:
            HTML content of the article, or None if fetch fails
        """
        if self.use_browser:
            # In login mode, use existing browser session
            if self.login_mode and self.logged_in and self.context:
                return self._fetch_with_existing_session(url)
            else:
                return self._fetch_with_browser(url)
        else:
            print(f"    ⚠ Browser automation not available - article may be blocked")
            return None

    def _detect_and_handle_captcha(self, page) -> bool:
        """Detect if CAPTCHA appeared and handle it.

        Args:
            page: Playwright page object

        Returns:
            True if CAPTCHA was handled, False otherwise
        """
        try:
            # More sophisticated CAPTCHA detection
            # Check for visible CAPTCHA elements with specific selectors
            captcha_selectors = [
                '[class*="captcha"]',
                '[id*="captcha"]',
                '[class*="challenge"]',
                '[id*="px-captcha"]',
                'iframe[src*="captcha"]',
                'iframe[src*="recaptcha"]',
                '[class*="arkose"]',
            ]

            # Check if any CAPTCHA element is visible
            captcha_visible = False
            for selector in captcha_selectors:
                try:
                    element = page.query_selector(selector)
                    if element and element.is_visible():
                        captcha_visible = True
                        break
                except:
                    continue

            # Also check page title for CAPTCHA indicators
            title = page.title().lower()
            if 'captcha' in title or 'challenge' in title or 'verification' in title:
                captcha_visible = True

            # If we think there's a CAPTCHA, ask user to confirm
            if captcha_visible:
                print(f"\n" + "="*60)
                print("⚠️  POSSIBLE CAPTCHA DETECTED")
                print("="*60)
                print("\nDo you see a CAPTCHA (puzzle piece slider) on the page?")
                response = input(">>> Type 'yes' if you see a CAPTCHA, or just press ENTER to continue: ").strip().lower()

                if response in ['yes', 'y']:
                    print("\n🧩 PLEASE SOLVE THE CAPTCHA IN THE BROWSER WINDOW:")
                    print("   1. Drag the puzzle piece to complete the image")
                    print("   2. Wait for the page to load normally")
                    print("   3. Press ENTER here when you're done")
                    print("\n" + "="*60 + "\n")

                    # Wait for user to solve CAPTCHA
                    input(">>> Press ENTER after solving the CAPTCHA >>> ")

                    # Wait a bit for page to settle
                    page.wait_for_timeout(2000)
                    print("✅ Continuing...")
                    return True
                else:
                    print("✅ No CAPTCHA, continuing...")
                    return False

            return False

        except Exception as e:
            print(f"    ⚠ Error checking for CAPTCHA: {e}")
            return False

    def _fetch_with_existing_session(self, url: str) -> Optional[str]:
        """Fetch article using the existing logged-in browser session.

        Args:
            url: The article URL

        Returns:
            HTML content of the article, or None if fetch fails
        """
        try:
            # Create new page in existing context
            page = self.context.new_page()

            # Add some random delay to seem more human (avoid triggering CAPTCHA)
            import time
            import random
            delay = random.uniform(2.0, 5.0)
            print(f"    Waiting {delay:.1f}s before fetching (human-like behavior)...")
            time.sleep(delay)

            print(f"    Fetching article with logged-in session...")
            response = page.goto(url, wait_until='networkidle', timeout=60000)

            if response:
                if response.status == 403:
                    print(f"    ⚠ 403 Forbidden (even with login)")
                    page.close()
                    return None
                elif response.status >= 400:
                    print(f"    ⚠ HTTP {response.status}")
                    page.close()
                    return None

            # Check for CAPTCHA
            self._detect_and_handle_captcha(page)

            # Wait for content
            page.wait_for_timeout(2000)

            # Scroll a bit (human behavior)
            page.evaluate('window.scrollBy(0, 300)')
            page.wait_for_timeout(500)

            # Get content
            html_content = page.content()
            page.close()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Check for paywall
            if soup.find(string=lambda text: text and 'subscribe' in text.lower()):
                paywall_divs = soup.find_all(['div', 'section'], class_=lambda x: x and ('paywall' in str(x).lower() or 'gateway' in str(x).lower()))
                if paywall_divs:
                    print(f"    ⚠ Paywall detected - login may not have worked")
                    return None

            # Extract article content
            article_body = None
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

            print(f"    ⚠ Could not find article content")
            return None

        except Exception as e:
            print(f"    ⚠ Error: {e}")
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
                # Launch browser with MAXIMUM anti-detection flags
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                        '--disable-infobars',
                        '--window-position=0,0',
                        '--ignore-certifcate-errors',
                        '--ignore-certifcate-errors-spki-list',
                        '--disable-gpu',
                        '--disable-software-rasterizer',
                        '--disable-dev-shm-usage',
                        '--no-zygote',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-hang-monitor',
                        '--disable-ipc-flooding-protection',
                        '--disable-popup-blocking',
                        '--disable-prompt-on-repost',
                        '--metrics-recording-only',
                        '--safebrowsing-disable-auto-update',
                        '--password-store=basic',
                        '--use-mock-keychain',
                        '--enable-features=NetworkService,NetworkServiceInProcess'
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

                # Add COMPREHENSIVE JavaScript to hide ALL automation indicators
                page.add_init_script("""
                    // Override webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });

                    // Add chrome object
                    window.chrome = {
                        runtime: {},
                        loadTimes: function() {},
                        csi: function() {},
                        app: {}
                    };

                    // Override plugins
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [
                            {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                            {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                            {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                        ]
                    });

                    // Override languages
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Override permissions
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({state: Notification.permission}) :
                            originalQuery(parameters)
                    );

                    // Override platform
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32'
                    });

                    // Override hardwareConcurrency
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => 8
                    });

                    // Override deviceMemory
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8
                    });

                    // Canvas fingerprinting protection
                    const getImageData = CanvasRenderingContext2D.prototype.getImageData;
                    CanvasRenderingContext2D.prototype.getImageData = function() {
                        const imageData = getImageData.apply(this, arguments);
                        // Add tiny noise to prevent fingerprinting
                        for (let i = 0; i < imageData.data.length; i++) {
                            imageData.data[i] = imageData.data[i] + Math.floor(Math.random() * 2);
                        }
                        return imageData;
                    };

                    // WebGL fingerprinting protection
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter.apply(this, arguments);
                    };

                    // Override maxTouchPoints
                    Object.defineProperty(navigator, 'maxTouchPoints', {
                        get: () => 0
                    });

                    // Override vendor
                    Object.defineProperty(navigator, 'vendor', {
                        get: () => 'Google Inc.'
                    });

                    // Add missing window.chrome properties
                    if (!window.chrome) {
                        window.chrome = {};
                    }
                    window.chrome.runtime = {
                        onMessage: {},
                        sendMessage: () => {}
                    };

                    // Spoof timezone
                    Date.prototype.getTimezoneOffset = function() {
                        return 300; // EST timezone offset
                    };
                """)

                # Navigate to article with MAXIMUM realistic behavior
                try:
                    # FIRST: Visit NYT homepage to establish session (looks more human)
                    print(f"    [1/6] Establishing session at nytimes.com...")
                    home_response = page.goto('https://www.nytimes.com/', wait_until='domcontentloaded', timeout=30000)
                    if home_response:
                        print(f"    [✓] Homepage loaded (status: {home_response.status})")

                    # Human-like delay
                    page.wait_for_timeout(1500 + (hash(url) % 1500))  # 1.5-3s

                    # Move mouse around a bit (very human!)
                    print(f"    [2/6] Simulating human interaction...")
                    page.mouse.move(100, 200)
                    page.wait_for_timeout(200)
                    page.mouse.move(400, 500)

                    # Scroll on homepage
                    page.evaluate('window.scrollBy(0, 300)')
                    page.wait_for_timeout(800)

                    # NOW: Navigate to the actual article
                    print(f"    [3/6] Navigating to article...")
                    response = page.goto(url, wait_until='networkidle', timeout=60000)

                    # DIAGNOSTIC: Check response
                    if response:
                        print(f"    [✓] Article page loaded (status: {response.status})")
                        if response.status == 403:
                            print(f"    [✗] 403 FORBIDDEN - NYT blocked the request")
                            print(f"    Debugging info:")
                            print(f"      - Cookies loaded: {len(self.cookies)}")
                            print(f"      - URL: {url}")
                            # Save screenshot for debugging
                            if not self.headless:
                                page.screenshot(path='debug_403.png')
                                print(f"      - Screenshot saved to debug_403.png")
                            browser.close()
                            return None
                        elif response.status >= 400:
                            print(f"    [✗] HTTP {response.status} - Error loading article")
                            browser.close()
                            return None

                    # Wait for content to fully load (random human-like delay)
                    print(f"    [4/6] Waiting for content to load...")
                    page.wait_for_timeout(2000 + (hash(url) % 2000))  # 2-4s

                    # Human-like reading behavior
                    print(f"    [5/6] Simulating reading behavior...")
                    # Scroll down slowly (like reading)
                    for i in range(3):
                        page.evaluate(f'window.scrollBy(0, {300 + (i * 100)})')
                        page.wait_for_timeout(600 + (hash(url) % 400))

                    # Scroll back up a bit (humans do this!)
                    page.evaluate('window.scrollBy(0, -200)')
                    page.wait_for_timeout(400)

                    # Get the page content
                    print(f"    [6/6] Extracting content...")
                    html_content = page.content()

                    # Close browser
                    browser.close()

                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    print(f"    [✓] Content extracted successfully")

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
