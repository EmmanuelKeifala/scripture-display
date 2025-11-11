import sqlite3
import json
import os
from pathlib import Path

class BibleDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "bible.db"
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        if self.conn:
            self.conn.close()
    
    def create_schema(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                testament TEXT NOT NULL,
                book_number INTEGER NOT NULL,
                chapter_count INTEGER NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                chapter INTEGER NOT NULL,
                verse INTEGER NOT NULL,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                FOREIGN KEY (book_id) REFERENCES books(id),
                UNIQUE(book_id, chapter, verse, translation)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_verses_lookup 
            ON verses(book_id, chapter, verse, translation)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_books_name 
            ON books(name)
        ''')
        
        conn.commit()
        self.close()
        
    def insert_book(self, book_id, name, testament, book_number, chapter_count):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO books (id, name, testament, book_number, chapter_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (book_id, name, testament, book_number, chapter_count))
        
        conn.commit()
        self.close()
        
    def insert_verse(self, book_id, chapter, verse, text, translation):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO verses (book_id, chapter, verse, text, translation)
            VALUES (?, ?, ?, ?, ?)
        ''', (book_id, chapter, verse, text, translation))
        
        conn.commit()
        self.close()
        
    def get_book_id(self, book_name):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM books WHERE LOWER(name) = LOWER(?)', (book_name,))
        result = cursor.fetchone()
        self.close()
        
        return result['id'] if result else None
    
    def get_all_books(self):
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM books ORDER BY book_number')
        results = cursor.fetchall()
        self.close()
        
        return [dict(row) for row in results]
