# NYT to eReader

Convert the New York Times front page (or any section) into an EPUB book format for your e-reader device. Each article becomes a chapter in the book.

## Features

- 📰 Fetch top stories from any NYT section (home, world, business, technology, etc.)
- 📖 Convert articles to EPUB format with each article as a separate chapter
- 🎨 Clean, readable formatting optimized for e-readers
- 🔍 Optional full article content fetching (or just use abstracts)
- ⚙️ Configurable article limits and output options

## Requirements

- Python 3.7+
- New York Times API key (free from [NYT Developer Portal](https://developer.nytimes.com/))

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd nyt_to_ereader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Get your NYT API key:
   - Go to https://developer.nytimes.com/
   - Create an account (free)
   - Create an app and enable the "Top Stories API"
   - Copy your API key

4. Configure your API key:
```bash
cp .env.example .env
# Edit .env and add your API key
```

Your `.env` file should look like:
```
NYT_API_KEY=your_actual_api_key_here
```

## Usage

### Basic Usage

Convert today's NYT front page to an EPUB:
```bash
python nyt_to_ereader.py
```

This will create a file named `nyt_home_YYYYMMDD.epub` in the current directory.

### Advanced Options

Specify a different section:
```bash
python nyt_to_ereader.py --section world
python nyt_to_ereader.py --section technology
python nyt_to_ereader.py --section business
```

Available sections: `home`, `world`, `business`, `technology`, `sports`, `science`, `health`, `arts`, `books`, `movies`, `theater`, `travel`, `food`, `opinion`

Custom output filename:
```bash
python nyt_to_ereader.py --output my_news.epub
```

Limit the number of articles:
```bash
python nyt_to_ereader.py --limit 5
```

Only use abstracts (faster, no full content fetching):
```bash
python nyt_to_ereader.py --no-content
```

Combine options:
```bash
python nyt_to_ereader.py --section technology --limit 15 --output tech_news.epub
```

### Help

```bash
python nyt_to_ereader.py --help
```

## How It Works

1. **Fetch Stories**: Uses the NYT Top Stories API to get the latest articles from the specified section
2. **Parse Content**: Optionally fetches the full article content from each article's URL
3. **Generate EPUB**: Creates an EPUB file with:
   - Table of contents with all articles
   - Each article as a separate chapter
   - Clean formatting with title, byline, date, and content
   - Readable typography optimized for e-readers

## Transferring to Your E-Reader

### Kindle
1. Connect your Kindle via USB
2. Copy the `.epub` file to the `Documents` folder
3. Eject safely
4. The book will appear in your library

Note: Older Kindles may require conversion to MOBI format using Calibre or Amazon's Send to Kindle service.

### Kobo / Nook / Other E-Readers
1. Connect your device via USB
2. Copy the `.epub` file to the appropriate folder (usually Books or Documents)
3. Eject safely
4. The book will appear in your library

### Using Calibre
1. Install [Calibre](https://calibre-ebook.com/)
2. Add the EPUB to your library
3. Convert to any format if needed
4. Send to your device

## Troubleshooting

**"NYT_API_KEY not found" error**
- Make sure you've created a `.env` file (not `.env.example`)
- Verify your API key is set correctly in `.env`
- The `.env` file should be in the same directory as the scripts

**"Could not fetch full content" warnings**
- Some articles may have paywalls or different formatting
- The tool will fall back to using the article abstract
- Use `--no-content` flag to skip content fetching entirely

**API rate limits**
- The free NYT API tier has rate limits (typically 500 requests per day, 5 per minute)
- If you hit limits, wait a few minutes and try again
- Use `--limit` to fetch fewer articles

## Project Structure

```
nyt_to_ereader/
├── nyt_to_ereader.py    # Main CLI tool
├── config.py            # Configuration management
├── nyt_client.py        # NYT API client
├── article_fetcher.py   # Article content fetcher
├── epub_generator.py    # EPUB file generator
├── requirements.txt     # Python dependencies
├── .env.example         # Example environment file
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## License

This is a personal tool for converting publicly available NYT content to e-reader format. Please respect NYT's terms of service and copyright. This tool is intended for personal, non-commercial use only.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Disclaimer

This tool is not affiliated with or endorsed by The New York Times. All content fetched belongs to The New York Times and its contributors.
