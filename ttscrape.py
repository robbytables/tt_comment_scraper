import pandas as pd
import json
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # User agent to appear more human-like
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        if headless:
            chrome_options.add_argument("--headless")
            
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def random_delay(self, min_delay=None, max_delay=None):
        """Add random delay to mimic human behavior"""
        if min_delay is None or max_delay is None:
            min_delay, max_delay = self.delay_range
        delay = random.uniform(min_delay, max_delay)
        if self.debug:
            logger.debug(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)
        
    def try_click_load_more(self):
        """Try to click various load more buttons"""

        load_more_patterns = [
            "//div[contains(text(), 'View more comments')]",
            "//div[contains(text(), 'Load more')]", 
            "//div[contains(text(), 'Show more')]",
            "//button[contains(text(), 'View more')]",
            "//button[contains(text(), 'Load more')]",
            "*[data-e2e='comment-load-more']",
            "*[class*='load-more']",
            "*[class*='LoadMore']",
            "div[class*='ViewRepliesContainer'] span"
        ]
        
        clicked = False
        for pattern in load_more_patterns:
            try:
                if pattern.startswith("//"):
                    buttons = self.driver.find_elements(By.XPATH, pattern)
                else:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    
                for button in buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            self.driver.execute_script("arguments[0].click();", button)
                            logger.debug(f"Clicked load more button: {pattern}")
                            clicked = True
                            self.random_delay(2, 4)
                            break
                    except Exception as e:
                        logger.debug(f"Failed to click button: {e}")
                        
                if clicked:
                    break
                    
            except Exception as e:
                logger.debug(f"Error finding load more buttons with {pattern}: {e}")
                
        return clicked
        
    def count_comments_multiple_methods(self):
        """Count comments using multiple selector strategies"""
        counts = {}
        
        selectors = [
            "[data-e2e='comment-item']",
            "[data-e2e^='comment-level-]", 
            "div[class*='comment']",
            "li[class*='comment']",
            "*[class*='CommentItem']",
            "*[class*='comment-item']",
            "*[class*='Comment']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                counts[selector] = len(elements)
                if self.debug and len(elements) > 0:
                    logger.debug(f"Selector '{selector}' found {len(elements)} elements")
            except:
                counts[selector] = 0
                
        # Return the highest count
        max_count = max(counts.values()) if counts.values() else 0
        if self.debug:
            logger.debug(f"Comment count methods: {counts}")
            logger.debug(f"Using max count: {max_count}")
        
        return max_count
        
    def scroll_to_load_comments(self, max_scrolls=50, scroll_pause=3):
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
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
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
                    logger.info(f"No new comments after {stagnant_scrolls} scrolls. Stopping.")
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
                'url': video_url,
                'scraped_at': datetime.now().isoformat(),
                'video_metadata': video_data,
                'comments': comments,
                'total_comments_scraped': len(comments),
                'debug_info': {
                    'comments_found_during_scroll': comment_count,
                    'comments_extracted': len(comments)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing {video_url}: {e}")
            return {
                'url': video_url,
                'scraped_at': datetime.now().isoformat(),
                'error': str(e),
                'video_metadata': {},
                'comments': [],
                'total_comments_scraped': 0
            }
            
    def extract_video_metadata(self):
        """Extract video metadata with enhanced selectors"""
        metadata = {}
        
        # Enhanced selectors for metadata
        metadata_selectors = {
            'title': [
                "[data-e2e='browse-video-desc'] span",
                "[data-e2e='video-desc']", 
                "h1[data-e2e='browse-video-desc']",
                "*[class*='VideoUserCardTitle']",
                "*[class*='video-desc']"
            ],
            'author': [
                "[data-e2e='browse-username']",
                "[data-e2e='video-author-uniqueid']",
                "*[class*='author']",
                "*[class*='username']"
            ],
            'like_count': [
                "[data-e2e='like-count']",
                "*[class*='like-count']",
                "*[class*='LikeCount']"
            ]
        }
        
        for field, selectors in metadata_selectors.items():
            for selector in selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    metadata[field] = element.text.strip()
                    if self.debug:
                        logger.debug(f"Found {field}: {metadata[field]} (selector: {selector})")
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
        strategies = [
            self.strategy_data_attributes,
            self.strategy_class_names,
            self.strategy_text_content,
            self.strategy_generic_divs
        ]
        
        for i, strategy in enumerate(strategies):
            logger.debug(f"Trying extraction strategy {i+1}")
            comments = strategy()
            if comments:
                logger.info(f"Strategy {i+1} successful: extracted {len(comments)} comments")
                break
            else:
                logger.debug(f"Strategy {i+1} failed")
                
        if not comments:
            logger.error("ALL EXTRACTION STRATEGIES FAILED")
            
        return comments
        
    def strategy_data_attributes(self):
        """Strategy 1: Use data-e2e attributes"""
        comments = []
        selectors = [
            "[data-e2e='comment-item']",
            "[data-e2e^='comment-level-']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} comment elements with {selector}")
                    comments = self.extract_from_elements(elements, "data-attributes")
                    break
            except Exception as e:
                logger.debug(f"Data attribute strategy failed for {selector}: {e}")
                
        return comments
     
    def strategy_class_names(self):
        """Strategy 2: Use class name patterns"""
        comments = []
        selectors = [
            "*[class*='CommentItem']",
            "*[class*='comment-item']", 
            "div[class*='comment']",
            "li[class*='comment']"
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"Found {len(elements)} comment elements with {selector}")
                    comments = self.extract_from_elements(elements, "class-names")
                    break
            except Exception as e:
                logger.debug(f"Class name strategy failed for {selector}: {e}")
                
        return comments
        
    def strategy_text_content(self):
        """Strategy 3: Look for text content patterns"""
        comments = []
        try:
            # Find all divs/spans that might contain comment text
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, span, p")
            potential_comments = []
            
            for elem in all_elements:
                text = elem.text.strip()
                # Heuristic: looks like a comment if it's 3-500 chars and contains common words
                if 3 <= len(text) <= 500 and any(word in text.lower() for word in ['the', 'is', 'and', 'this', 'that', 'for', 'you', 'love', 'great', 'wow']):
                    potential_comments.append(elem)
                    
            logger.debug(f"Found {len(potential_comments)} potential comment elements by text content")
            
            # Try to extract from these
            if potential_comments:
                comments = self.extract_from_elements(potential_comments[:50], "text-content")  # Limit to first 50
                
        except Exception as e:
            logger.debug(f"Text content strategy failed: {e}")
            
        return comments
        
    def strategy_generic_divs(self):
        """Strategy 4: Generic div scanning"""
        comments = []
        
        try:
            # Look for structural patterns
            container_selectors = [
                "div[role='button']",
                "div[tabindex]",
                "article",
                "section[class*='comment']"
            ]
            
            for selector in container_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.debug(f"Trying generic strategy with {len(elements)} {selector} elements")
                    comments = self.extract_from_elements(elements, "generic")
                    if comments:
                        break
                        
        except Exception as e:
            logger.debug(f"Generic strategy failed: {e}")
            
        return comments
        
    def extract_from_elements(self, elements, strategy_name):
        """Extract comment data from a list of elements"""
        comments = []
        
        logger.debug(f"Extracting from {len(elements)} elements using {strategy_name} strategy")
        
        for i, element in enumerate(elements[:100]):  # Limit to first 100
            try:
                comment_data = self.extract_single_comment(element, i, strategy_name)
                if comment_data:
                    comments.append(comment_data)
                    
            except Exception as e:
                logger.debug(f"Failed to extract comment {i}: {e}")
                
        logger.debug(f"Successfully extracted {len(comments)} comments using {strategy_name}")
        return comments
        
    def extract_single_comment(self, element, index, strategy):
        """Extract data from a single comment element"""
        comment_data = {'comment_index': index, 'extraction_strategy': strategy}
        
        # Try multiple approaches for each field
        field_selectors = {
            'username': [
                "[data-e2e^='comment-username'] a p",
                "*[class*='username']", 
                "*[class*='Username']",
                "*[class*='author']"
            ],
            'text': [
                "[data-e2e^=comment-level-] span",
                "[data-e2e='comment-text']",
                "*[class*='comment-text']",
                "*[class*='CommentText']", 
                "*[class*='text']",
                "span",
                "p"
            ],
            'likes': [
                "[class=*='LikeContainer] span",
                "[data-e2e='comment-like-count']",
                "*[class*='like']",
                "*[class*='Like']"
            ],
            'timestamp': [
                "div[class*='commentSubContentWrapper] span:nth-of-type(1)",
                "*[class*='time']",
                "*[class*='Time']",
                "*[class*='date']"
            ]
        }
        
        # Extract each field
        for field, selectors in field_selectors.items():
            for selector in selectors:
                try:
                    child_elem = element.find_element(By.CSS_SELECTOR, selector)
                    value = child_elem.text.strip()
                    if value:
                        comment_data[field] = value
                        if self.debug and field in ['username', 'text']:
                            logger.debug(f"  Found {field}: {value[:50]}...")
                        break
                except:
                    continue
                    
        # Fallback: if no text found, use element's direct text
        if 'text' not in comment_data:
            direct_text = element.text.strip()
            if direct_text and len(direct_text) > 3:
                comment_data['text'] = direct_text
                
        # Only return if we found at least username or text
        if comment_data.get('username') or comment_data.get('text'):
            return comment_data
        else:
            return None
        
    def scrape_urls_from_csv(self, csv_file, url_column='url', output_file=None):
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
                if data.get('comments'):
                    print(f"  Sample comment: {data['comments'][0].get('text', 'No text')[:100]}...")
                
                # Save progress periodically
                if output_file and i % 5 == 0:  # Save every 5 URLs
                    self.save_data(all_data, output_file)
                    logger.info(f"Progress saved: {i}/{len(urls)} URLs processed")
                    
                # Random delay between URLs
                self.random_delay(10, 20)
                
            except Exception as e:
                logger.error(f"Failed to process URL {url}: {e}")
                all_data.append({
                    'url': url,
                    'scraped_at': datetime.now().isoformat(),
                    'error': str(e),
                    'comments': []
                })
                
        # Save final results
        if output_file:
            self.save_data(all_data, output_file)
            
        return all_data
        
    def save_data(self, data, filename):
        """Save data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            
    def export_to_csv(self, json_file, csv_file):
        """Convert JSON results to CSV format for analysis"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Flatten comments into rows
            rows = []
            
            for video_data in data:
                video_url = video_data.get('url', '')
                video_metadata = video_data.get('video_metadata', {})
                comments = video_data.get('comments', [])
                
                for comment in comments:
                    row = {
                        'video_url': video_url,
                        'video_author': video_metadata.get('author', ''),
                        'video_title': video_metadata.get('title', ''),
                        'video_like_count': video_metadata.get('like_count', ''),
                        'scraped_at': video_data.get('scraped_at', ''),
                        'comment_username': comment.get('username', ''),
                        'comment_text': comment.get('text', ''),
                        'comment_likes': comment.get('likes', ''),
                        'comment_timestamp': comment.get('timestamp', ''),
                        'comment_reply_count': comment.get('reply_count', ''),
                        'comment_index': comment.get('comment_index', ''),
                        'extraction_strategy': comment.get('extraction_strategy', '')
                    }
                    rows.append(row)
                    
            # Save to CSV
            df = pd.DataFrame(rows)
            df.to_csv(csv_file, index=False, encoding='utf-8')
            logger.info(f"CSV exported to {csv_file} with {len(rows)} comment rows")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            
    def close(self):
        """Close the browser driver"""
        if hasattr(self, 'driver'):
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
        
        if result.get('comments'):
            print(f"\nFirst few comments:")
            for i, comment in enumerate(result['comments'][:3]):
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
    #test_url = input("Enter TikTok URL to test (or press Enter to skip): ").strip()
    #if test_url:
    #    test_single_url(test_url)
    #else:
    # Initialize scraper for batch processing
    scraper = TikTokCommentScraper(headless=False, debug=False)
    
    try:
        # Scrape from CSV file
        results = scraper.scrape_urls_from_csv(
            csv_file='tiktok_urls.csv',  # Your input CSV file
            url_column='url',  # Column name containing URLs
            output_file='tiktok_comments_raw.json'  # Output file
        )
       
        # Convert to CSV for analysis
        scraper.export_to_csv('tiktok_comments_raw.json', 'tiktok_comments_analysis.csv')
        
        print(f"Scraping completed! Processed {len(results)} URLs")
        
    finally:
        scraper.close()
