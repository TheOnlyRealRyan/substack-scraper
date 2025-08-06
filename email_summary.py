import os
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
import html
import re
from dotenv import load_dotenv

# Configuration
SUMMARY_DIR = "substack_articles/article_content_summary"
OUTPUT_DIR = "substack_articles/combined_summaries"
DATE = datetime.datetime.now().strftime("%Y-%m-%d")
OUTPUT_FILENAME = f"summaries_{DATE}.txt"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SEPARATOR = "\n" + "-" * 50 + "\n"

def combine_summaries():
    print(">>> Starting summary combination process")
    
    # Ensure summary directory exists
    if not os.path.exists(SUMMARY_DIR):
        print(f"!!! Summary directory {SUMMARY_DIR} does not exist")
        return None
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all .txt files from summary directory
    summary_files = sorted([f for f in os.listdir(SUMMARY_DIR) if f.endswith('.txt')])
    if not summary_files:
        print(f"!!! No .txt files found in {SUMMARY_DIR}")
        return None
    
    print(f">>> Found {len(summary_files)} summary files to combine: {', '.join(summary_files)}")
    
    # Define output file path
    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(f"Combined Summaries for {DATE}\n")
            outfile.write("=" * 50 + "\n")
            
            for idx, filename in enumerate(summary_files, 1):
                input_path = os.path.join(SUMMARY_DIR, filename)
                print(f"--- [{idx}/{len(summary_files)}] Processing: {filename}")
                
                try:
                    with open(input_path, 'r', encoding='utf-8') as infile:
                        content = infile.read().strip()
                    
                    if not content or content.startswith("Error generating summary"):
                        print(f"    ! Skipping {filename}: Empty or contains error")
                        outfile.write(SEPARATOR)
                        outfile.write(f"Summary: {filename}\n")
                        outfile.write(f"Status: Skipped - Empty or error\n")
                        continue
                    
                    # Write separator, header, and content
                    outfile.write(SEPARATOR)
                    outfile.write(f"Summary: {filename}\n")
                    outfile.write(content)
                    print(f"      Added: {filename}")
                
                except Exception as e:
                    print(f"    !!! Failed to process {filename}: {e}")
                    outfile.write(SEPARATOR)
                    outfile.write(f"Summary: {filename}\n")
                    outfile.write(f"Status: Error - {str(e)}\n")
        
        print(f">>> Combined summaries saved to: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"!!! Failed to create combined file: {e}")
        return None

def send_email(output_path, sender_email, sender_password, recipient_email):
    print(">>> Preparing to send email")
    
    if not output_path:
        print("!!! No combined file to send")
        return
    
    # Read the combined summaries file
    try:
        with open(output_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
    except Exception as e:
        print(f"!!! Failed to read combined file for email body: {e}")
        content = "Error: Could not read the combined summaries file."
    
    # Split content into sections based on separator
    sections = content.split(SEPARATOR)
    formatted_sections = []
    
    # Process sections, starting from the first valid summary (skip header)
    for section in sections[1:]:  # Skip the initial header section
        if not section.strip():
            continue
        
        lines = section.split("\n", 2)
        
        if len(lines) < 2 or not lines[0].startswith("Summary:"):
            print(f"    ! Skipping invalid section: {section[:50]}...")
            continue
        
        header = lines[0].replace("Summary: ", "").strip()
        text = lines[2].strip() if len(lines) > 2 else lines[1].strip()
        
        if text.startswith("Status:"):
            text = html.escape(text)
        
        def partial_escape(t):
            # Bug fix implementation for regex not being escaped: Escape &, <, >, but not *
            t = t.replace("&", "&amp;")
            t = t.replace("<", "&lt;")
            t = t.replace(">", "&gt;")
            return t
        
        safe_text = partial_escape(text)
        
        # Replace **text** with styled span
        safe_text = re.sub(r'\*\*(.*?)\*\*', r'<span style="color: #2c5282; font-weight: bold;">\1</span>', safe_text)
        
        # Replace *text* with styled span
        safe_text = re.sub(r'\*(.*?)\*', r'<span style="color: #2c827f;">\1</span>', safe_text)
        safe_text = safe_text.replace("\n", "<br>")
        text = safe_text
        
        formatted_sections.append((header, text))
        print(f"      Formatted section for: {header}")
    
    if not formatted_sections:
        print("!!! No valid sections found for email body")
        html_content = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px;">
            <h1 style="color: #333; font-size: 24px; margin-bottom: 20px;">Combined Summaries - {}</h1>
            <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">No valid summaries found.</p>
        </div>
        """.format(DATE)
    else:
        html_content = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 8px;">
            <h1 style="color: #333; font-size: 24px; margin-bottom: 20px;">Combined Summaries - {}</h1>
        """.format(DATE)
        
        for header, text in formatted_sections:
            html_content += """
            <div style="margin-bottom: 20px;">
                <h2 style="color: #2c5282; font-size: 20px; margin: 0 0 10px 0; border-bottom: 2px solid #2c5282; padding-bottom: 5px;">{}</h2>
                <p style="color: #333; font-size: 16px; line-height: 1.6; margin: 0;">{}</p>
            </div>
            """.format(header, text)
        
        html_content += """
        </div>
        """
    
    # Set up email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Combined Summaries - {DATE}"
    
    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html'))
    
    # Connect to SMTP server
    try:
        print("    Connecting to SMTP server...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print(f">>> Email sent successfully to {recipient_email}")
    
    except Exception as e:
        print(f"!!! Failed to send email: {e}")

def main():
    # Get environment variables
    load_dotenv()
    env = os.getenv("ENV", "development")
    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    
    if not all([sender_email, sender_password, recipient_email]):
        print("!!! Missing environment variables: Set EMAIL_ADDRESS, EMAIL_PASSWORD, and RECIPIENT_EMAIL")
        return
    
    # Combine summaries
    output_path = combine_summaries()
    
    # Send email
    if output_path:
        send_email(output_path, sender_email, sender_password, recipient_email)
    else:
        print(">>> Skipping email due to combination failure")

if __name__ == "__main__":
    main()