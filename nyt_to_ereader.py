#!/usr/bin/env python3
"""
NYT to eReader - Convert New York Times front page to EPUB format.

This tool fetches the top stories from the New York Times and converts them
into an EPUB book format, with each article as a separate chapter.
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from config import Config
from nyt_client import NYTClient
from article_fetcher import ArticleFetcher
from epub_generator import EPUBGenerator


def main():
    """Main entry point for the NYT to eReader converter."""
    parser = argparse.ArgumentParser(
        description='Convert NYT front page articles to an EPUB book'
    )
    parser.add_argument(
        '--section',
        default='home',
        help='NYT section to fetch (default: home for front page). '
             'Options: home, world, business, technology, sports, etc.'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output EPUB filename (default: nyt_YYYYMMDD.epub)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of articles to include (default: 10)'
    )
    parser.add_argument(
        '--no-content',
        action='store_true',
        help='Only include abstracts, skip fetching full article content'
    )
    parser.add_argument(
        '--cookies',
        '-c',
        help='Path to cookie file for NYT authentication (JSON or Netscape format). '
             'Required to access full article content if you have a subscription.'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run browser in non-headless mode for debugging (shows browser window)'
    )
    parser.add_argument(
        '--login',
        action='store_true',
        help='Interactive login mode - opens browser for you to log in manually to NYT. '
             'Much easier than exporting cookies! The browser session is used for all articles.'
    )

    args = parser.parse_args()

    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = f"nyt_{args.section}_{date_str}.epub"

    print(f"NYT to eReader Converter")
    print(f"========================")
    print(f"Section: {args.section}")
    print(f"Output: {output_file}")
    print(f"Max articles: {args.limit}")
    print()

    # Fetch top stories
    print("Fetching top stories from NYT...")
    try:
        client = NYTClient()
        articles = client.get_top_stories(section=args.section)
        print(f"Found {len(articles)} articles")
    except Exception as e:
        print(f"Error fetching articles: {e}", file=sys.stderr)
        return 1

    if not articles:
        print("No articles found!", file=sys.stderr)
        return 1

    # Limit number of articles
    articles = articles[:args.limit]

    # Process articles
    article_data = []
    fetcher = ArticleFetcher(
        cookie_file=args.cookies,
        headless=not args.debug,
        login_mode=args.login
    )

    # Handle interactive login if requested
    if args.login:
        if not fetcher.interactive_login():
            print("❌ Login failed. Exiting.", file=sys.stderr)
            return 1
        print()

    if args.debug:
        print("🐛 DEBUG MODE: Browser will be visible. Watch the automation in action!")
        print()

    for idx, article in enumerate(articles, 1):
        details = client.get_article_details(article)
        title = details['title']
        print(f"[{idx}/{len(articles)}] Processing: {title}")

        # Fetch full content if requested
        content = None
        if not args.no_content:
            url = details['url']
            if url:
                print(f"    Fetching full article content...")
                content = fetcher.fetch_article_content(url)
                if content:
                    print(f"    ✓ Content fetched")
                else:
                    print(f"    ⚠ Could not fetch full content, using abstract only")

        # Create article HTML
        article_html = fetcher.create_article_html(details, content)
        article_data.append((details, article_html))

    # Generate EPUB
    print()
    print("Generating EPUB...")
    try:
        generator = EPUBGenerator(
            title=f"The New York Times - {args.section.title()} - {datetime.now().strftime('%B %d, %Y')}"
        )
        output_path = generator.create_epub(article_data, output_file)
        print(f"✓ EPUB created successfully: {output_path}")
        print()
        print(f"Your eBook is ready! Transfer {output_path} to your e-reader device.")

        # Cleanup browser if in login mode
        if args.login:
            print("\n🧹 Cleaning up browser session...")
            fetcher.cleanup()

        return 0
    except Exception as e:
        print(f"Error generating EPUB: {e}", file=sys.stderr)

        # Cleanup browser if in login mode
        if args.login:
            fetcher.cleanup()

        return 1


if __name__ == '__main__':
    sys.exit(main())
