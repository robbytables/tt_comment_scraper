# TikTok Comment Scraper

This script is used to scrape comments and their replies from a list of TikTok videos. This is purely for research use, not for any business or monetary purposes.

## Getting Started

Create a virtual environment and install dependencies.

```
python3 -m venv ttscrape
pip3 install -r requirements.txt
```

Note that depending on how Python is setup on your machine and which versions are installed, you may need to use `python` instead of `python3`, and `pip` instead of `pip3`.

You may need to download the Chrome webdriver and place it on your machine somewhere that `PATH` has access to. A link to the latest version of Chromedriver can be found [here](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json) by searching for your Chrome version and matching it with your OS. For example, `{"platform":"win64","url":"https://storage.googleapis.com/chrome-for-testing-public/138.0.7152.0/win64/chromedriver-win64.zip"}`.

## Usage

Running the script is easy- just `python3 ttscrape.py`

To test scraping a URL without writing to file, you can provide a single URL when prompted.

Otherwise, use the `tiktok_urls.csv` file to list all URLs of videos you want scraped.
