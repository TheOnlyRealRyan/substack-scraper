import asyncio
import time
import os
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SubstackDatabase
import logging

# Load environment variables
load_dotenv()

# Configuration
SEARCH_URL = "https://substack.com/search/artificial%20intelligence?searching=all_posts"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "deepseek/deepseek-r1-0528:free"
SUMMARY_LENGTH = "200 word"
MAX_ARTICLES = 80

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('substack_scraper.log'),
        logging.StreamHandler()
    ]
)

class SubstackScraper:
    def __init__(self):
        self.db = SubstackDatabase()
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.sender_email = os.getenv("EMAIL_ADDRESS")
        self.sender_password = os.getenv("EMAIL_PASSWORD")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")
        
        self.start_time = time.time()
        self.articles_scraped = 0
        self.articles_summarized = 0
        self.email_sent = False
        self.error_message = None
    
    def sanitize_filename(self, title: str) -> str:
        """Remove special characters and limit filename length"""
        return re.sub(r'[^a-zA-Z0-9_-]', '', title)[:100]
    
    async def scrape_articles(self):
        """Scrape articles from Substack search results"""
        logging.info("Starting Substack scraping process")
        
        try:
            async with async_playwright() as p:
                logging.info("Launching browser...")
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                logging.info(f"Navigating to search page: {SEARCH_URL}")
                await page.goto(SEARCH_URL, wait_until="networkidle")

                logging.info("Waiting for search results to load...")
                await page.wait_for_selector('div.linkRow-ddH7S0.reader2-post-container', timeout=30000)

                logging.info("Extracting article links from the search results...")
                posts = await page.query_selector_all('div.linkRow-ddH7S0.reader2-post-container a[href^="https://"]')

                article_urls = []
                count = 0
                for post in posts:
                    count += 1
                    if count > MAX_ARTICLES:
                        break
                    href = await post.get_attribute("href")
                    if href:
                        article_urls.append(href.strip())
                        
                logging.info(f"Found {len(article_urls)} article links.")

                logging.info("Beginning to visit each article for content extraction...")
                for i, url in enumerate(article_urls, 1):
                    logging.info(f"--- [{i}/{len(article_urls)}] Visiting: {url}")
                    try:
                        article_page = await context.new_page()
                        await article_page.goto(url, wait_until="networkidle", timeout=60000)
                        await article_page.wait_for_timeout(2000)

                        title = await article_page.title()
                        safe_name = self.sanitize_filename(title or f"article_{i}")

                        # Get the page content
                        html_content = await article_page.content()
                        soup = BeautifulSoup(html_content, 'html.parser')

                        # Extract main article content
                        article_content = []
                        content_container = soup.find('div', class_='body markup') or soup.find('main')
                        if content_container:
                            logging.info(f"    Found content container for {url}")
                            for element in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
                                # Skip elements in unwanted sections
                                if element.find_parent(class_=[
                                    'share', 'subscribe', 'comments', 'post-meta', 'social', 
                                    'subscription', 'signup', 'caption', 'likes', 'ufi']):
                                    continue
                                if element.name == 'script' or element.find_parent('script'):
                                    continue
                                if element.get('class') and any(cls in element.get('class') for cls in [
                                    'button', 'image', 'graphic', 'newsletter', 'footer']):
                                    continue
                                text = element.get_text(separator=' ', strip=True)
                                if text:
                                    article_content.append(text)
                        else:
                            logging.warning(f"!!! No content container found for {url}")

                        # Join content and clean up excessive whitespace
                        article_text = '\n\n'.join(article_content).strip()
                        article_text = re.sub(r'\s+', ' ', article_text)

                        if article_text and article_text != "No content extracted":
                            # Save to database
                            self.db.insert_article(url, title, article_text)
                            self.articles_scraped += 1
                            logging.info(f"    Saved article: {safe_name}")

                        await article_page.close()

                    except Exception as e:
                        logging.error(f"!!! Failed to scrape {url}: {e}")

                await browser.close()
                logging.info("Browser closed. Scraping completed.")
                
        except Exception as e:
            logging.error(f"Error during scraping: {e}")
            self.error_message = f"Scraping error: {str(e)}"
    
    def get_summary(self, content: str) -> str:
        """Generate AI summary using OpenRouter API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": f"Summarize the provided article as a professional AI researcher, focusing on key insights, technical advancements, and implications for the field. Deliver a concise {SUMMARY_LENGTH} summary, prioritizing critical details like model capabilities, benchmark results, architectural innovations, and governance trends. Exclude filler words, irrelevant details, and any reference to this prompt. Use precise, technical language suitable for an expert audience."},
                    {"role": "user", "content": content}
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            response_data = response.json()
            if "choices" not in response_data or not response_data["choices"]:
                return f"!!! Error generating summary: No choices in API response"
            
            choice = response_data["choices"][0]
            message = choice["message"]
            
            summary = message.get("content", "").strip()
            if not summary and message.get("reasoning"):
                summary = message["reasoning"].strip()
            
            if not summary:
                return f"!!! Error generating summary: No content found in response"
            
            return summary

        except Exception as e:
            logging.error(f"Error generating summary: {e}")
            return f"!!! Error generating summary: {str(e)}"
    
    def summarize_articles(self):
        """Summarize all unprocessed articles"""
        logging.info("Starting article summarization process")
        
        unprocessed_articles = self.db.get_unprocessed_articles()
        logging.info(f"Found {len(unprocessed_articles)} unprocessed articles")

        for article in unprocessed_articles:
            try:
                logging.info(f"Summarizing: {article['title']}")
                summary = self.get_summary(article['content'])
                
                if not summary.startswith("!!! Error"):
                    self.db.insert_summary(article['id'], summary)
                    self.articles_summarized += 1
                    logging.info(f"    Summary generated successfully")
                else:
                    logging.warning(f"    Summary generation failed: {summary}")
                    
            except Exception as e:
                logging.error(f"Error processing article {article['id']}: {e}")
    
    def send_email(self):
        """Send email with today's summaries"""
        if not all([self.sender_email, self.sender_password, self.recipient_email]):
            logging.warning("Missing email credentials, skipping email")
            return
        
        logging.info("Preparing to send email")
        
        summaries = self.db.get_todays_summaries()
        if not summaries:
            logging.warning("No summaries found for today")
            return
        
        # Create HTML email content
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px;">
            <h1 style="color: #333; font-size: 24px; margin-bottom: 20px;">AI Article Summaries - {summaries[0]['created_at'][:10]}</h1>
        """
        
        for summary_data in summaries:
            title = summary_data['title'] or "Untitled Article"
            summary = summary_data['summary']
            url = summary_data['url']
            
            # Clean up the summary text for HTML
            safe_summary = summary.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            safe_summary = safe_summary.replace("\n", "<br>")
            
            html_content += f"""
            <div style="margin-bottom: 20px;">
                <h2 style="color: #2c5282; font-size: 20px; margin: 0 0 10px 0; border-bottom: 2px solid #2c5282; padding-bottom: 5px;">
                    <a href="{url}" style="color: #2c5282; text-decoration: none;">{title}</a>
                </h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">{safe_summary}</p>
            </div>
            """
        
        html_content += "</div>"
        
        # Set up email
        msg = MIMEMultipart()
        msg['From'] = self.sender_email
        msg['To'] = self.recipient_email
        msg['Subject'] = f"AI Article Summaries - {summaries[0]['created_at'][:10]}"
        msg.attach(MIMEText(html_content, 'html'))
        
        try:
            logging.info("Connecting to SMTP server...")
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.email_sent = True
            logging.info(f"Email sent successfully to {self.recipient_email}")
            
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            self.error_message = f"Email error: {str(e)}"
    
    async def run_full_pipeline(self):
        """Run the complete scraping and summarization pipeline"""
        try:
            # Step 1: Scrape articles
            await self.scrape_articles()
            
            # Step 2: Summarize articles
            self.summarize_articles()
            
            # Step 3: Send email
            self.send_email()
            
            # Step 4: Log execution
            execution_time = time.time() - self.start_time
            self.db.log_execution(
                self.articles_scraped,
                self.articles_summarized,
                self.email_sent,
                execution_time,
                self.error_message
            )
            
            logging.info(f"Pipeline completed successfully!")
            logging.info(f"Articles scraped: {self.articles_scraped}")
            logging.info(f"Articles summarized: {self.articles_summarized}")
            logging.info(f"Email sent: {self.email_sent}")
            logging.info(f"Execution time: {execution_time:.2f} seconds")
            
        except Exception as e:
            logging.error(f"Pipeline failed: {e}")
            execution_time = time.time() - self.start_time
            self.db.log_execution(
                self.articles_scraped,
                self.articles_summarized,
                self.email_sent,
                execution_time,
                str(e)
            )

async def main():
    """Main entry point"""
    scraper = SubstackScraper()
    await scraper.run_full_pipeline()

if __name__ == "__main__":
    asyncio.run(main())
