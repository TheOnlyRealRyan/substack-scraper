#!/usr/bin/env python3
"""
Database Viewer for Substack Scraper
A simple utility to view and query the SQLite database
"""

import sqlite3
import argparse
from datetime import datetime
from tabulate import tabulate
import sys

def connect_db(db_path="substack_articles.db"):
    """Connect to the SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def show_tables(conn):
    """Show all tables in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("📊 Database Tables:")
    for table in tables:
        print(f"  - {table[0]}")
    print()

def show_table_info(conn, table_name):
    """Show table structure and sample data"""
    cursor = conn.cursor()
    
    # Get table schema
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    
    print(f"📋 Table: {table_name}")
    print("Columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    print()
    
    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cursor.fetchone()[0]
    print(f"Total rows: {count}")
    
    # Show sample data
    if count > 0:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
        rows = cursor.fetchall()
        
        if rows:
            print("\nSample data:")
            headers = [description[0] for description in cursor.description]
            print(tabulate(rows, headers=headers, tablefmt="grid"))
    print()

def show_recent_executions(conn, limit=10):
    """Show recent execution logs"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            run_date,
            articles_scraped,
            articles_summarized,
            email_sent,
            execution_time_seconds,
            error_message,
            created_at
        FROM execution_logs 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"📈 Recent Executions (Last {len(rows)}):")
        headers = ["Date", "Scraped", "Summarized", "Email", "Time(s)", "Error", "Created"]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("No execution logs found.")
    print()

def show_todays_summaries(conn):
    """Show summaries created today"""
    cursor = conn.cursor()
    today = datetime.now().date()
    
    cursor.execute("""
        SELECT 
            a.title,
            a.url,
            s.summary,
            s.created_at
        FROM summaries s
        JOIN articles a ON s.article_id = a.id
        WHERE DATE(s.created_at) = ?
        ORDER BY s.created_at DESC
    """, (today,))
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"📧 Today's Summaries ({len(rows)}):")
        for i, row in enumerate(rows, 1):
            print(f"\n{i}. {row['title']}")
            print(f"   URL: {row['url']}")
            print(f"   Summary: {row['summary'][:200]}...")
            print(f"   Created: {row['created_at']}")
    else:
        print("No summaries found for today.")
    print()

def show_stats(conn):
    """Show database statistics"""
    cursor = conn.cursor()
    
    # Article count
    cursor.execute("SELECT COUNT(*) FROM articles;")
    article_count = cursor.fetchone()[0]
    
    # Summary count
    cursor.execute("SELECT COUNT(*) FROM summaries;")
    summary_count = cursor.fetchone()[0]
    
    # Unprocessed articles
    cursor.execute("SELECT COUNT(*) FROM articles WHERE processed = FALSE;")
    unprocessed_count = cursor.fetchone()[0]
    
    # Execution count
    cursor.execute("SELECT COUNT(*) FROM execution_logs;")
    execution_count = cursor.fetchone()[0]
    
    # Last execution
    cursor.execute("SELECT created_at FROM execution_logs ORDER BY created_at DESC LIMIT 1;")
    last_execution = cursor.fetchone()
    last_exec = last_execution[0] if last_execution else "Never"
    
    print("📊 Database Statistics:")
    print(f"  Total Articles: {article_count}")
    print(f"  Total Summaries: {summary_count}")
    print(f"  Unprocessed Articles: {unprocessed_count}")
    print(f"  Total Executions: {execution_count}")
    print(f"  Last Execution: {last_exec}")
    print()

def search_articles(conn, query, limit=10):
    """Search articles by title or content"""
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT title, url, scraped_at, processed
        FROM articles 
        WHERE title LIKE ? OR content LIKE ?
        ORDER BY scraped_at DESC 
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", limit))
    
    rows = cursor.fetchall()
    
    if rows:
        print(f"🔍 Search Results for '{query}' ({len(rows)}):")
        headers = ["Title", "URL", "Scraped", "Processed"]
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print(f"No articles found matching '{query}'.")
    print()

def main():
    parser = argparse.ArgumentParser(description="Database Viewer for Substack Scraper")
    parser.add_argument("--db", default="substack_articles.db", help="Database file path")
    parser.add_argument("--tables", action="store_true", help="Show all tables")
    parser.add_argument("--table", help="Show specific table info")
    parser.add_argument("--executions", type=int, default=10, help="Show recent executions")
    parser.add_argument("--today", action="store_true", help="Show today's summaries")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument("--search", help="Search articles by title or content")
    
    args = parser.parse_args()
    
    # Connect to database
    conn = connect_db(args.db)
    
    try:
        if args.tables:
            show_tables(conn)
        elif args.table:
            show_table_info(conn, args.table)
        elif args.executions:
            show_recent_executions(conn, args.executions)
        elif args.today:
            show_todays_summaries(conn)
        elif args.stats:
            show_stats(conn)
        elif args.search:
            search_articles(conn, args.search)
        else:
            # Default: show overview
            show_tables(conn)
            show_stats(conn)
            show_recent_executions(conn, 5)
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()
