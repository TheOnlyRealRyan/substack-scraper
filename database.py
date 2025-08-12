import sqlite3
import datetime
from typing import List, Dict, Optional
import os

class SubstackDatabase:
    def __init__(self, db_path: str = "substack_articles.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT,
                    content TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Create summaries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER,
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (article_id) REFERENCES articles (id)
                )
            ''')
            
            # Create execution_logs table for tracking runs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_date DATE DEFAULT CURRENT_DATE,
                    articles_scraped INTEGER DEFAULT 0,
                    articles_summarized INTEGER DEFAULT 0,
                    email_sent BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    execution_time_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def insert_article(self, url: str, title: str, content: str) -> int:
        """Insert a new article into the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO articles (url, title, content, scraped_at, processed)
                VALUES (?, ?, ?, ?, ?)
            ''', (url, title, content, datetime.datetime.now(), False))
            conn.commit()
            return cursor.lastrowid
    
    def get_unprocessed_articles(self) -> List[Dict]:
        """Get all articles that haven't been summarized yet"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, url, title, content FROM articles 
                WHERE processed = FALSE
                ORDER BY scraped_at DESC
            ''')
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def insert_summary(self, article_id: int, summary: str):
        """Insert a summary for an article"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO summaries (article_id, summary)
                VALUES (?, ?)
            ''', (article_id, summary))
            
            # Mark article as processed
            cursor.execute('''
                UPDATE articles SET processed = TRUE WHERE id = ?
            ''', (article_id,))
            
            conn.commit()
    
    def get_todays_summaries(self) -> List[Dict]:
        """Get all summaries created today"""
        today = datetime.datetime.now().date()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.title, a.url, s.summary, s.created_at
                FROM summaries s
                JOIN articles a ON s.article_id = a.id
                WHERE DATE(s.created_at) = ?
                ORDER BY s.created_at DESC
            ''', (today,))
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def log_execution(self, articles_scraped: int, articles_summarized: int, 
                     email_sent: bool, execution_time: float, error_message: str = None):
        """Log execution details for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO execution_logs 
                (articles_scraped, articles_summarized, email_sent, execution_time_seconds, error_message)
                VALUES (?, ?, ?, ?, ?)
            ''', (articles_scraped, articles_summarized, email_sent, execution_time, error_message))
            conn.commit()
    
    def get_article_count(self) -> int:
        """Get total number of articles in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM articles')
            return cursor.fetchone()[0]
    
    def get_summary_count(self) -> int:
        """Get total number of summaries in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM summaries')
            return cursor.fetchone()[0]
