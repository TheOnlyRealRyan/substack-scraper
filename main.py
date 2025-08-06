import asyncio
from playwright.async_api import async_playwright
import os
import re
import csv
from bs4 import BeautifulSoup

#TODO: write articles into date subfolder

SEARCH_URL = "https://substack.com/search/artificial%20intelligence?searching=all_posts"
OUTPUT_DIR = "substack_articles"
CONTENT_SUBFOLDER = "article_content"
CSV_FILE = "substack_ai_post_links.csv"

def sanitize_filename(title: str) -> str:
    # Remove special characters and limit filename to 100 characters
    return re.sub(r'[^a-zA-Z0-9_-]', '', title)[:100]

async def scrape_and_extract_content():
    """
    Scrape substack using a specific search filter: SEARCH_URL using playwright library
    Saves all article links to a csv
    Visits each artcle and saves content to a txt file
    Filter out irrelavant segments from the html
    """
    print(">>> Starting Substack scraping process")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, CONTENT_SUBFOLDER), exist_ok=True)

    async with async_playwright() as p:
        print(">>> Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f">>> Navigating to search page: {SEARCH_URL}")
        await page.goto(SEARCH_URL, wait_until="networkidle")

        print(">>> Waiting for search results to load...")
        await page.wait_for_selector('div.linkRow-ddH7S0.reader2-post-container', timeout=30000) # website specific container

        print(">>> Extracting article links from the search results...")
        posts = await page.query_selector_all('div.linkRow-ddH7S0.reader2-post-container a[href^="https://"]')

        article_data = []
        count, max_count = 0, 80 # limit articles pulled to 80
        for post in posts:
            count += 1
            if count > max_count:
                break
            href = await post.get_attribute("href")
            if href:
                article_data.append({"url": href.strip()})
                    
        print(f">>> Found {len(article_data)} article links.")
        print(f">>> Saving links to CSV: {CSV_FILE}")
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url"])
            writer.writeheader()
            writer.writerows(article_data)

        print(">>> Beginning to visit each article for content extraction...")

        for i, entry in enumerate(article_data, 1):
            url = entry["url"]
            print(f"--- [{i}/{len(article_data)}] Visiting: {url}")
            try:
                article_page = await context.new_page()
                await article_page.goto(url, wait_until="networkidle", timeout=60000)
                await article_page.wait_for_timeout(2000)  # Extra wait for dynamic content

                title = await article_page.title()
                safe_name = sanitize_filename(title or f"article_{i}")

                # Get the page content
                html_content = await article_page.content()
                soup = BeautifulSoup(html_content, 'html.parser')

                # Extract main article content from div.body.markup or fallback to main
                article_content = []
                content_container = soup.find('div', class_='body markup') or soup.find('main')
                if content_container:
                    print(f"    Found content container for {url}")
                    # Target headings, paragraphs, and other relevant tags
                    for element in content_container.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li']):
                        # Skip elements in unwanted sections
                        if element.find_parent(class_=[
                            'share', 'subscribe', 'comments', 'post-meta', 'social', 
                            'subscription', 'signup', 'caption', 'likes', 'ufi']):
                            continue
                        # Skip script tags and their parents
                        if element.name == 'script' or element.find_parent('script'):
                            continue
                        # Skip elements with specific classes or roles
                        if element.get('class') and any(cls in element.get('class') for cls in [
                            'button', 'image', 'graphic', 'newsletter', 'footer']):
                            continue
                        text = element.get_text(separator=' ', strip=True)
                        if text:
                            article_content.append(text)
                else:
                    print(f"!!! No content container found for {url}")

                # Join content and clean up excessive whitespace
                article_text = '\n\n'.join(article_content).strip()
                article_text = re.sub(r'\s+', ' ', article_text)

                # Save to text file in subfolder
                content_path = os.path.join(OUTPUT_DIR, CONTENT_SUBFOLDER, f"{safe_name}.txt")
                print(f"    Saving article content to: {content_path}")
                with open(content_path, "w", encoding="utf-8") as f:
                    f.write(article_text if article_text else "No content extracted")

                print(f"    Done with: {safe_name}")
                await article_page.close()

            except Exception as e:
                print(f"!!! Failed to scrape {url}: {e}")

        await browser.close()
        print(">>> All articles processed. Browser closed.")
        print(f">>> Output folder: {OUTPUT_DIR}/{CONTENT_SUBFOLDER}")
        print(f">>> CSV file: {CSV_FILE}")

if __name__ == "__main__":
    asyncio.run(scrape_and_extract_content())