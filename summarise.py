import os
import re
from dotenv import load_dotenv
import requests
from pathlib import Path
import json


# Configuration
load_dotenv()
env = os.getenv("ENV", "development")
INPUT_DIR = "substack_articles/article_content"
OUTPUT_DIR = "substack_articles/article_content_summary"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv(env)  # Ensure your OpenAI API key is set as an environment variable
print(API_KEY)
MODEL = "deepseek/deepseek-r1-0528:free"
SUMMARY_LENGTH = "200 word"


def sanitize_filename(title: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_-]', '_', title)[:100]

def get_summary(api_key: str, content: str) -> str:
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-app-url.com",  # Optional: replace with your app’s URL
            "X-Title": "Article Summarizer"  # Optional: for OpenRouter analytics
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": f"Summarize the provided article as a professional AI researcher, focusing on key insights, technical advancements, and implications for the field. Deliver a concise {SUMMARY_LENGTH} summary, prioritizing critical details like model capabilities, benchmark results, architectural innovations, and governance trends. Exclude filler words, irrelevant details, and any reference to this prompt. Use precise, technical language suitable for an expert audience."},
                {"role": "user", "content": content}
            ],
            "max_tokens": 2000,  # Adjust based on desired summary length
            "temperature": 0.7
        }
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
        
        response.raise_for_status()  # Raise exception for bad status codes (e.g., 4xx, 5xx)

        response_data = response.json()
        print(response_data)
        if "choices" not in response_data or not response_data["choices"]:
            return f"Error generating summary: No choices in API response: {json.dumps(response_data)}"
        
        choice = response_data["choices"][0]
        message = choice["message"]
        
        # Try to get content from 'content' field first, then fall back to 'reasoning'
        summary = message.get("content", "").strip()
        if not summary and message.get("reasoning"):
            summary = message["reasoning"].strip()
        
        if not summary:
            return f"Error generating summary: No content or reasoning found in response: {json.dumps(response_data)}"
        
        return summary
    
    except requests.exceptions.HTTPError as http_err:
        return f"Error generating summary: HTTP error {http_err.response.status_code} - {http_err.response.text}"
    except requests.exceptions.RequestException as req_err:
        return f"Error generating summary: Request failed - {str(req_err)}"
    except KeyError as key_err:
        return f"Error generating summary: Invalid response format - {str(key_err)}: {json.dumps(response_data)}"
    except Exception as e:
        return f"Error generating summary: Unexpected error - {str(e)}"


def summarize_articles():
    print(">>> Starting article summarization process")
    
    # Ensure input directory exists
    if not os.path.exists(INPUT_DIR):
        print(f" Input directory {INPUT_DIR} does not exist")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get OpenRouter API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(" OPENROUTER_API_KEY environment variable not set. Please set it and try again.")
        return

    # Get all .txt files from input directory
    text_files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    print(f">>> Found {len(text_files)} text files to summarize")

    for idx, filename in enumerate(text_files, 1):
        input_path = os.path.join(INPUT_DIR, filename)
        print(f"--- [{idx}/{len(text_files)}] Processing: {filename}")
        
        try:
            # Read the article content
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content or content == "No content extracted":
                print(f"     No content found in {filename}, skipping")
                continue

            # Generate summary
            print(f"    Sending content to OpenRouter for summarization...")
            summary = get_summary(api_key, content)
            
            # Save summary to output directory
            safe_filename = sanitize_filename(Path(filename).stem) + "_summary.txt"
            output_path = os.path.join(OUTPUT_DIR, safe_filename)
            print(f"    Saving summary to: {output_path}")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"     Done with: {filename}")
        
        except Exception as e:
            print(f"     Failed to process {filename}: {e}")

    print(">>> All articles processed.")
    print(f">>> Summaries saved in: {OUTPUT_DIR}")

if __name__ == "__main__":
    summarize_articles()