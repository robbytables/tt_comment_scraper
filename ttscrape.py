import pandas as pd
import hashlib
import json
import time
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TikTokCommentScraper:
    def __init__(self, headless=False, delay_range=(2, 5), debug=False):
        """
        Initialize the TikTok comment scraper

        Args:
            headless (bool): Run browser in headless mode
            delay_range (tuple): Range for random delays between actions
            debug (bool): Enable debug logging
        """
        self.delay_range = delay_range
        self.debug = debug
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
        self.setup_driver(headless)

    def setup_driver(self, headless):
        """Set up Chrome WebDriver with appropriate options"""
        chrome_options = Options()

        # Essential options for TikTok
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # User agent to appear more human-like
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        if headless:
            chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def random_delay(self, min_delay=None, max_delay=None):
        """Add random delay to mimic human behavior"""
        if min_delay is None or max_delay is None:
            min_delay, max_delay = self.delay_range
        delay = random.uniform(min_delay, max_delay)
        if self.debug:
            logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)

    def _matches_reply_pattern(self, text):
        """Check if the text matches our specific reply expansion patterns"""
        text = text.strip()

        # Pattern 1: "View 1 reply"
        if text == "View 1 reply":
            return True

        # Pattern 2: "View X replies" (X is any number > 1)
        if re.match(r"^View \d+ replies$", text):
            return True

        # Pattern 3: "View X More" (X is any number)
        if re.match(r"^View \d+ more$", text):
            return True

        return False

    def try_click_load_more(self):
        """Try to click various load more buttons"""
        load_more_patterns = [
            # Original patterns for main comment loading
            # "//div[contains(text(), 'View more comments')]",
            # "//div[contains(text(), 'Load more')]",
            # "//div[contains(text(), 'Show more')]",
            # "//button[contains(text(), 'View more')]",
            # "//button[contains(text(), 'Load more')]",
            # "*[data-e2e='comment-load-more']",
            # "*[class*='load-more']",
            # "*[class*='LoadMore']",
            # Specific patterns for reply expansion
            # "View 1 reply"
            "//span[normalize-space(text())='View 1 reply']",
            "//div[normalize-space(text())='View 1 reply']",
            "//button[normalize-space(text())='View 1 reply']",
            # "View X replies" (where X is any number > 1)
            "//span[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' replies')]",
            "//div[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' replies')]",
            "//button[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' replies')]",
            # "View X More" (where X is any number)
            "//span[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' more')]",
            "//div[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' more')]",
            "//button[starts-with(normalize-space(text()), 'View ') and contains(normalize-space(text()), ' more')]",
        ]

        for pattern in load_more_patterns:
            try:
                if pattern.startswith("//"):
                    buttons = self.driver.find_elements(By.XPATH, pattern)
                else:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, pattern)

                for button in buttons:
                    try:
                        text = button.text.strip()
                        if not self._matches_reply_pattern(text):
                            continue

                        if button.is_displayed() and button.is_enabled():

                            self.driver.execute_script("arguments[0].click();", button)
                            self.random_delay(2, 4)

                    except Exception as e:
                        logger.debug(f"Failed to click button: {e}")

            except Exception as e:
                logger.debug(f"Error finding load more buttons with {pattern}: {e}")

    def count_comments_multiple_methods(self):
        """Count comments using multiple selector strategies"""
        counts = {}

        selectors = [
            "[data-e2e='comment-item']",
            "[data-e2e='comment-level-1']",
            "[data-e2e^='comment-level-']",  # This includes all reply levels
            "div[class*='comment']",
            "li[class*='comment']",
            "*[class*='CommentItem']",
            "*[class*='comment-item']",
        ]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                counts[selector] = len(elements)
                if self.debug and len(elements) > 0:
                    logger.debug(
                        f"Selector '{selector}' found {len(elements)} elements"
                    )
            except:
                counts[selector] = 0

        # Return the highest count
        max_count = max(counts.values()) if counts.values() else 0
        if self.debug:
            logger.debug(f"Comment count methods: {counts}")
            logger.debug(f"Using max count: {max_count}")

        return max_count

    def scroll_to_load_comments(self, max_scrolls=500, scroll_pause=2):
        """
        Scroll down to load all comments with enhanced detection

        Args:
            max_scrolls (int): Maximum number of scroll attempts
            scroll_pause (int): Pause between scrolls

        Returns:
            int: Number of comments loaded
        """
        logger.info("Starting comment loading process...")

        last_comment_count = 0
        scroll_count = 0
        stagnant_scrolls = 0

        while scroll_count < max_scrolls:
            logger.debug(f"Scroll attempt {scroll_count + 1}/{max_scrolls}")

            # Scroll to bottom
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            self.random_delay(scroll_pause, scroll_pause + 2)

            # Try to click load more buttons
            self.try_click_load_more()

            # Count current comments using multiple methods
            current_comment_count = self.count_comments_multiple_methods()

            logger.debug(f"Comments found: {current_comment_count}")

            if current_comment_count == last_comment_count:
                stagnant_scrolls += 1
                logger.debug(f"No new comments loaded (stagnant: {stagnant_scrolls}/5)")
                if stagnant_scrolls >= 5:
                    logger.info(
                        f"No new comments after {stagnant_scrolls} scrolls. Stopping."
                    )
                    break
            else:
                stagnant_scrolls = 0
                logger.info(f"Comments loaded: {current_comment_count}")

            last_comment_count = current_comment_count
            scroll_count += 1

        logger.info(f"Finished loading. Total comments found: {last_comment_count}")
        return last_comment_count

    def extract_comments(self, video_url):
        """
        Extract comments and metadata from a TikTok video

        Args:
            video_url (str): TikTok video URL

        Returns:
            dict: Extracted data including comments and metadata
        """
        logger.info(f"Processing: {video_url}")

        try:
            self.driver.get(video_url)
            self.random_delay(5, 8)  # Wait for page to load

            # Extract video metadata
            video_data = self.extract_video_metadata()

            # Load all comments
            comment_count = self.scroll_to_load_comments()

            # Extract comments using multiple strategies
            comments = self.extract_comment_data()

            logger.info(f"Successfully extracted {len(comments)} comments")

            return {
                "url": video_url,
                "scraped_at": datetime.now().isoformat(),
                "video_metadata": video_data,
                "comments": comments,
                "total_comments_scraped": len(comments),
                "debug_info": {
                    "comments_found_during_scroll": comment_count,
                    "comments_extracted": len(comments),
                },
            }

        except Exception as e:
            logger.error(f"Error processing {video_url}: {e}")
            return {
                "url": video_url,
                "scraped_at": datetime.now().isoformat(),
                "error": str(e),
                "video_metadata": {},
                "comments": [],
                "total_comments_scraped": 0,
            }

    def extract_video_metadata(self):
        """Extract video metadata with enhanced selectors"""
        metadata = {}

        # Enhanced selectors for metadata
        metadata_selectors = {
            "title": [
                "[data-e2e='browse-video-desc']",
                "[data-e2e='video-desc']",
                "h1[data-e2e='browse-video-desc']",
                "*[class*='VideoUserCardTitle']",
                "*[class*='video-desc']",
            ],
            "author": [
                "[data-e2e='browse-username']",
                "[data-e2e='video-author-uniqueid']",
                "*[class*='author']",
                "*[class*='username']",
            ],
            "like_count": [
                "[data-e2e='like-count']",
                "*[class*='like-count']",
                "*[class*='LikeCount']",
            ],
        }

        for field, selectors in metadata_selectors.items():
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    metadata[field] = element.text.strip()
                    if self.debug:
                        logger.debug(
                            f"Found {field}: {metadata[field]} (selector: {selector})"
                        )
                    break
                except:
                    continue

        return metadata

    def extract_comment_data(self):
        """Enhanced comment extraction with multiple fallback strategies"""
        comments = []

        if self.debug:
            logger.debug("=== STARTING COMMENT EXTRACTION ===")

        # Try multiple selector strategies
        # strategies = [
        #     self.strategy_data_attributes,
        #     self.strategy_class_names,
        #     self.strategy_text_content,
        #     self.strategy_generic_divs,
        # ]

        comments = self.strategy_data_attribute()
        if comments:
            logger.info(f"Strategy successful: extracted {len(comments)} comments")
        else:
            logger.debug("Strategy failed")

        if not comments:
            logger.error("ALL EXTRACTION STRATEGIES FAILED")

        return comments

    def strategy_data_attribute(self):
        """Strategy 0: Just use the one data-e2e attribute"""
        comments = []
        selector = "[data-e2e^='comment-level-']"

        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.debug(f"Found {len(elements)} comment elements with {selector}")
                comments = self.extract_comment_data_from_elements(elements)
        except Exception as e:
            logger.debug(f"Data attribute strategy failed for {selector}: {e}")

        return comments

    def extract_comment_data_from_elements(self, elements):
        comments = []

        for i, element in enumerate(elements):
            try:
                comment_data = self.extract_single_comment_data(element, i)
                if comment_data:
                    comments.append(comment_data)
            except Exception as e:
                logger.debug(f"Failed to extract comment {i}: {e}")

        logger.debug(f"Successfully extracted {len(comments)} comments")
        return comments

    def extract_single_comment_data(self, element, index):
        try:
            parent = element.find_element(By.XPATH, "..")
            comment_parts = parent.text.split("\n")
            username = comment_parts[0]
            text = comment_parts[1]
            date = comment_parts[2]
            likes = comment_parts[4]
            identifier = hashlib.md5(parent.text.encode("utf-8")).hexdigest()

            comment_data = {
                "index": index,
                "username": username,
                "text": text,
                "date": date,
                "likes": likes,
                "id": identifier,
            }

            # Is this a reply or top level comment?
            data_e2e = element.get_attribute("data-e2e")
            if data_e2e:
                match = re.match(r"^comment-level-(\d+)$", data_e2e)
                if match and int(match.group(1)) > 1:  # This is a reply

                    # Get the ancestor that houses the OG comment and all replies
                    ancestor = element.find_element(
                        By.XPATH,
                        "./ancestor::div[contains(@class, 'DivCommentObjectWrapper')]",
                    )

                    # Now find the OG comment
                    comment_level_1 = ancestor.find_element(
                        By.XPATH, ".//*[@data-e2e='comment-level-1'][1]"
                    )

                    # Get the ID
                    parent_id = hashlib.md5(
                        comment_level_1.find_element(By.XPATH, "..").text.encode(
                            "utf-8"
                        )
                    ).hexdigest()
                    comment_data["parent_id"] = parent_id

            return comment_data
        except Exception as e:
            logger.error(f"Failure in extracting comment data {e}")
            return {}

    def scrape_urls_from_csv(self, csv_file, url_column="url", output_file=None):
        """
        Scrape comments from URLs in a CSV file

        Args:
            csv_file (str): Path to CSV file containing URLs
            url_column (str): Name of column containing URLs
            output_file (str): Output file path (JSON format)

        Returns:
            list: All scraped data
        """
        # Read URLs from CSV
        try:
            df = pd.read_csv(csv_file)
            urls = df[url_column].tolist()
            logger.info(f"Found {len(urls)} URLs to process")
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []

        # Process each URL
        all_data = []

        for i, url in enumerate(urls, 1):
            logger.info(f"Processing URL {i}/{len(urls)}: {url}")

            try:
                data = self.extract_comments(url)
                all_data.append(data)

                # Print summary for each URL
                print(f"URL {i}: Extracted {len(data.get('comments', []))} comments")
                if data.get("comments"):
                    print(
                        f"  Sample comment: {data['comments'][0].get('text', 'No text')[:100]}..."
                    )

                # Save progress periodically
                if output_file and i % 5 == 0:  # Save every 5 URLs
                    self.save_data(all_data, output_file)
                    logger.info(f"Progress saved: {i}/{len(urls)} URLs processed")

                # Random delay between URLs
                self.random_delay(10, 20)

            except Exception as e:
                logger.error(f"Failed to process URL {url}: {e}")
                all_data.append(
                    {
                        "url": url,
                        "scraped_at": datetime.now().isoformat(),
                        "error": str(e),
                        "comments": [],
                    }
                )

        # Save final results
        if output_file:
            self.save_data(all_data, output_file)

        return all_data

    def save_data(self, data, filename):
        """Save data to JSON file"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def export_to_csv(self, json_file, csv_file):
        """Convert JSON results to CSV format for analysis"""
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Flatten comments into rows
            rows = []

            for video_data in data:
                video_url = video_data.get("url", "")
                video_metadata = video_data.get("video_metadata", {})
                comments = video_data.get("comments", [])

                for comment in comments:
                    row = {
                        "video_url": video_url,
                        "video_author": video_metadata.get("author", ""),
                        "video_title": video_metadata.get("title", ""),
                        "video_like_count": video_metadata.get("like_count", ""),
                        "scraped_at": video_data.get("scraped_at", ""),
                        "comment_username": comment.get("username", ""),
                        "comment_text": comment.get("text", ""),
                        "comment_likes": comment.get("likes", ""),
                        "comment_timestamp": comment.get("timestamp", ""),
                        "comment_reply_count": comment.get("reply_count", ""),
                        "comment_index": comment.get("comment_index", ""),
                        "extraction_strategy": comment.get("extraction_strategy", ""),
                    }
                    rows.append(row)

            # Save to CSV
            df = pd.DataFrame(rows)
            df.to_csv(csv_file, index=False, encoding="utf-8")
            logger.info(f"CSV exported to {csv_file} with {len(rows)} comment rows")

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")

    def close(self):
        """Close the browser driver"""
        if hasattr(self, "driver"):
            self.driver.quit()


# Test single URL function
def test_single_url(url, debug=True):
    """Test scraper on a single URL"""
    scraper = TikTokCommentScraper(headless=False, debug=debug)

    try:
        print(f"Testing URL: {url}")
        result = scraper.extract_comments(url)

        print(f"\n=== RESULTS ===")
        print(f"Comments extracted: {len(result.get('comments', []))}")
        print(f"Video metadata: {result.get('video_metadata', {})}")

        if result.get("comments"):
            print(f"\nFirst few comments:")
            for i, comment in enumerate(result["comments"][:3]):
                print(f"  {i+1}. Username: {comment.get('username', 'N/A')}")
                print(f"     Text: {comment.get('text', 'N/A')[:100]}...")
                print(f"     Strategy: {comment.get('extraction_strategy', 'N/A')}")
        else:
            print("No comments extracted!")

        return result

    finally:
        scraper.close()


# Example usage
if __name__ == "__main__":
    # Test with a single URL first
    # test_url = input("Enter TikTok URL to test (or press Enter to skip): ").strip()
    # if test_url:
    #    test_single_url(test_url)
    # else:
    # Initialize scraper for batch processing
    scraper = TikTokCommentScraper(headless=False, debug=False)

    try:
        # Scrape from CSV file
        results = scraper.scrape_urls_from_csv(
            csv_file="tiktok_urls.csv",  # Your input CSV file
            url_column="url",  # Column name containing URLs
            output_file="tiktok_comments_raw.json",  # Output file
        )

        # Convert to CSV for analysis
        scraper.export_to_csv(
            "tiktok_comments_raw.json", "tiktok_comments_analysis.csv"
        )

        print(f"Scraping completed! Processed {len(results)} URLs")

    finally:
        scraper.close()
