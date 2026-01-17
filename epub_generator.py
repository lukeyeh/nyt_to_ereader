"""Generate EPUB files from NYT articles."""
from ebooklib import epub
from typing import List, Dict
from datetime import datetime
import re


class EPUBGenerator:
    """Generates EPUB files from article data."""

    def __init__(self, title: str = "New York Times Front Page"):
        """Initialize the EPUB generator.

        Args:
            title: Title of the EPUB book
        """
        self.title = title
        self.book = epub.EpubBook()

    def create_epub(self, articles: List[tuple], output_file: str) -> str:
        """Create an EPUB file from articles.

        Args:
            articles: List of tuples (article_details, article_html)
            output_file: Path to save the EPUB file

        Returns:
            Path to the created EPUB file
        """
        # Set metadata
        self.book.set_identifier(f'nyt-{datetime.now().strftime("%Y%m%d-%H%M%S")}')
        self.book.set_title(self.title)
        self.book.set_language('en')
        self.book.add_author('The New York Times')

        # Create chapters
        chapters = []
        spine = ['nav']

        for idx, (article_details, article_html) in enumerate(articles, 1):
            title = article_details.get('title', f'Article {idx}')
            # Create a safe filename from title
            filename = self._sanitize_filename(title)

            chapter = epub.EpubHtml(
                title=title,
                file_name=f'chapter_{idx}_{filename}.xhtml',
                lang='en'
            )
            chapter.content = article_html

            self.book.add_item(chapter)
            chapters.append(chapter)
            spine.append(chapter)

        # Add table of contents
        self.book.toc = chapters

        # Add navigation files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Add CSS style
        style = '''
        body {
            font-family: Georgia, serif;
            line-height: 1.6;
            margin: 2em;
        }
        h1 {
            font-size: 1.8em;
            margin-bottom: 0.5em;
            color: #000;
        }
        h2 {
            font-size: 1.4em;
            margin-top: 1em;
        }
        h3 {
            font-size: 1.2em;
            margin-top: 0.8em;
        }
        p {
            margin: 1em 0;
            text-align: justify;
        }
        em {
            font-style: italic;
        }
        strong {
            font-weight: bold;
        }
        hr {
            margin: 2em 0;
            border: none;
            border-top: 1px solid #ccc;
        }
        '''

        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style
        )
        self.book.add_item(nav_css)

        # Set spine
        self.book.spine = spine

        # Write the EPUB file
        epub.write_epub(output_file, self.book)

        return output_file

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize a string for use in a filename.

        Args:
            title: The string to sanitize

        Returns:
            Sanitized string safe for filenames
        """
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
        # Replace spaces with underscores
        sanitized = re.sub(r'\s+', '_', sanitized)
        # Limit length
        sanitized = sanitized[:50]
        return sanitized.lower()
