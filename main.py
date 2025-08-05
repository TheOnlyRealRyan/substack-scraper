import asyncio
from playwright.async_api import async_playwright
import csv

SEARCH_URL = "https://substack.com/search/artificial%20intelligence?searching=all_posts"
print('1')
async def scrape_substack_post_links():
    async with async_playwright() as p:
        print('2')
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        print('3')
        await page.goto(SEARCH_URL, wait_until="networkidle")

        # Scroll to load more results (optional)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(3000)
        print('4')
        # Wait for post containers to load
        await page.wait_for_selector('div.linkRow-ddH7S0.reader2-post-container')
        print('5')
        # Select all post containers
        posts = await page.query_selector_all('div.linkRow-ddH7S0.reader2-post-container a[href^="https://"]')
        print('6')
        links = []
        for post in posts:
            href = await post.get_attribute("href")
            if href:
                links.append({"url": href.strip()})
        print('7')
        await browser.close()

        # Save to CSV
        with open("substack_ai_post_links.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["url"])
            writer.writeheader()
            writer.writerows(links)

        print(f"Extracted {len(links)} article links.")

if __name__ == "__main__":
    asyncio.run(scrape_substack_post_links())
