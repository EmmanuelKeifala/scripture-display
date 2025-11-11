import sqlite3
from pathlib import Path
from typing import Optional, List, Dict

class ScriptureLookup:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "bible.db"
        self.db_path = db_path
        
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_book_id(self, book_name: str) -> Optional[int]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM books 
            WHERE LOWER(name) = LOWER(?)
        ''', (book_name,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result['id'] if result else None
    
    def get_verse(self, book: str, chapter: int, verse: int, translation: str = "KJV") -> Optional[Dict]:
        book_id = self.get_book_id(book)
        if not book_id:
            return None
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.name as book_name, v.chapter, v.verse, v.text, v.translation
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.book_id = ? AND v.chapter = ? AND v.verse = ? AND v.translation = ?
        ''', (book_id, chapter, verse, translation))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'book': result['book_name'],
                'chapter': result['chapter'],
                'verse': result['verse'],
                'text': result['text'],
                'translation': result['translation']
            }
        return None
    
    def get_verse_range(self, book: str, chapter: int, start_verse: int, 
                       end_verse: int, translation: str = "KJV") -> List[Dict]:
        book_id = self.get_book_id(book)
        if not book_id:
            return []
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.name as book_name, v.chapter, v.verse, v.text, v.translation
            FROM verses v
            JOIN books b ON v.book_id = b.id
            WHERE v.book_id = ? AND v.chapter = ? 
            AND v.verse BETWEEN ? AND ?
            AND v.translation = ?
            ORDER BY v.verse
        ''', (book_id, chapter, start_verse, end_verse, translation))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'book': row['book_name'],
            'chapter': row['chapter'],
            'verse': row['verse'],
            'text': row['text'],
            'translation': row['translation']
        } for row in results]
    
    def get_available_translations(self) -> List[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT translation FROM verses ORDER BY translation')
        results = cursor.fetchall()
        conn.close()
        
        return [row['translation'] for row in results]
    
    def get_all_books(self) -> List[Dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM books ORDER BY book_number')
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
