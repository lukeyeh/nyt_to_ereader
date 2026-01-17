"""Fetch and parse full article content from NYT."""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional


class ArticleFetcher:
    """Fetches and parses full article content from NYT article pages."""

    def __init__(self):
        """Initialize the article fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

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
