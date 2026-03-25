"""
AI Dev Starter — main entry point.

This is intentionally minimal. Replace this with your project's actual logic.

Usage:
  python src/main.py                    → prints project info
  python src/main.py --scrape           → test-run the Medium scraper
"""

import argparse

from dotenv import load_dotenv

from utils.logger_config import setup_logging


def main():
    load_dotenv()
    setup_logging("INFO")

    parser = argparse.ArgumentParser(description="AI Dev Starter")
    parser.add_argument("--scrape", action="store_true", help="Test Medium scraper")
    args = parser.parse_args()

    if args.scrape:
        import os

        from knowledge.medium_scraper import MediumScraper

        cookie_string = os.environ.get("MEDIUM_COOKIES", "")
        scraper = MediumScraper(cookie_string=cookie_string)
        scraper.fetch_reading_list(cookie_string, max_articles=10)
    else:
        print("AI Dev Starter is ready.")
        print()
        print("  python src/main.py --scrape              # fetch your Medium bookmarks")
        print("  python -m knowledge.medium_scraper --help # full scraper CLI")
        print("  claude                                    # start Claude Code (terminal)")
        print("  .\\scripts\\start_all.ps1                  # launch all tools at once")


if __name__ == "__main__":
    main()
