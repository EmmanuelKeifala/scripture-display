import requests
import json
from pathlib import Path
from scripture.database import BibleDatabase

BIBLE_BOOKS = [
    # Old Testament
    (1, "Genesis", "OT", 1, 50),
    (2, "Exodus", "OT", 2, 40),
    (3, "Leviticus", "OT", 3, 27),
    (4, "Numbers", "OT", 4, 36),
    (5, "Deuteronomy", "OT", 5, 34),
    (6, "Joshua", "OT", 6, 24),
    (7, "Judges", "OT", 7, 21),
    (8, "Ruth", "OT", 8, 4),
    (9, "1 Samuel", "OT", 9, 31),
    (10, "2 Samuel", "OT", 10, 24),
    (11, "1 Kings", "OT", 11, 22),
    (12, "2 Kings", "OT", 12, 25),
    (13, "1 Chronicles", "OT", 13, 29),
    (14, "2 Chronicles", "OT", 14, 36),
    (15, "Ezra", "OT", 15, 10),
    (16, "Nehemiah", "OT", 16, 13),
    (17, "Esther", "OT", 17, 10),
    (18, "Job", "OT", 18, 42),
    (19, "Psalms", "OT", 19, 150),
    (20, "Proverbs", "OT", 20, 31),
    (21, "Ecclesiastes", "OT", 21, 12),
    (22, "Song of Solomon", "OT", 22, 8),
    (23, "Isaiah", "OT", 23, 66),
    (24, "Jeremiah", "OT", 24, 52),
    (25, "Lamentations", "OT", 25, 5),
    (26, "Ezekiel", "OT", 26, 48),
    (27, "Daniel", "OT", 27, 12),
    (28, "Hosea", "OT", 28, 14),
    (29, "Joel", "OT", 29, 3),
    (30, "Amos", "OT", 30, 9),
    (31, "Obadiah", "OT", 31, 1),
    (32, "Jonah", "OT", 32, 4),
    (33, "Micah", "OT", 33, 7),
    (34, "Nahum", "OT", 34, 3),
    (35, "Habakkuk", "OT", 35, 3),
    (36, "Zephaniah", "OT", 36, 3),
    (37, "Haggai", "OT", 37, 2),
    (38, "Zechariah", "OT", 38, 14),
    (39, "Malachi", "OT", 39, 4),
    # New Testament
    (40, "Matthew", "NT", 40, 28),
    (41, "Mark", "NT", 41, 16),
    (42, "Luke", "NT", 42, 24),
    (43, "John", "NT", 43, 21),
    (44, "Acts", "NT", 44, 28),
    (45, "Romans", "NT", 45, 16),
    (46, "1 Corinthians", "NT", 46, 16),
    (47, "2 Corinthians", "NT", 47, 13),
    (48, "Galatians", "NT", 48, 6),
    (49, "Ephesians", "NT", 49, 6),
    (50, "Philippians", "NT", 50, 4),
    (51, "Colossians", "NT", 51, 4),
    (52, "1 Thessalonians", "NT", 52, 5),
    (53, "2 Thessalonians", "NT", 53, 3),
    (54, "1 Timothy", "NT", 54, 6),
    (55, "2 Timothy", "NT", 55, 4),
    (56, "Titus", "NT", 56, 3),
    (57, "Philemon", "NT", 57, 1),
    (58, "Hebrews", "NT", 58, 13),
    (59, "James", "NT", 59, 5),
    (60, "1 Peter", "NT", 60, 5),
    (61, "2 Peter", "NT", 61, 3),
    (62, "1 John", "NT", 62, 5),
    (63, "2 John", "NT", 63, 1),
    (64, "3 John", "NT", 64, 1),
    (65, "Jude", "NT", 65, 1),
    (66, "Revelation", "NT", 66, 22),
]

def import_books():
    db = BibleDatabase()
    db.create_schema()
    
    print("Importing books into database...")
    for book_id, name, testament, book_number, chapter_count in BIBLE_BOOKS:
        db.insert_book(book_id, name, testament, book_number, chapter_count)
        print(f"  Added: {name}")
    
    print(f"\nSuccessfully imported {len(BIBLE_BOOKS)} books")

def import_kjv_from_api():
    print("\nDownloading KJV Bible from API...")
    url = "https://cdn.jsdelivr.net/gh/thiagobodruk/bible@master/json/en_kjv.json"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8-sig'
        bible_data = response.json()
        
        db = BibleDatabase()
        
        total_verses = 0
        for book_data in bible_data:
            book_name = book_data.get('name')
            book_id = None
            
            for bid, bname, _, _, _ in BIBLE_BOOKS:
                if bname.lower() == book_name.lower():
                    book_id = bid
                    break
            
            if not book_id:
                print(f"  Warning: Book '{book_name}' not found in book list")
                continue
            
            chapters = book_data.get('chapters', [])
            for chapter_num, verses in enumerate(chapters, 1):
                for verse_num, verse_text in enumerate(verses, 1):
                    db.insert_verse(book_id, chapter_num, verse_num, verse_text, "KJV")
                    total_verses += 1
            
            print(f"  Imported: {book_name} ({len(chapters)} chapters)")
        
        print(f"\nSuccessfully imported {total_verses} verses from KJV")
        
    except requests.RequestException as e:
        print(f"Error downloading Bible data: {e}")
        return False
    
    return True

def main():
    print("Bible Database Importer")
    print("=" * 50)
    
    import_books()
    import_kjv_from_api()
    
    print("\n" + "=" * 50)
    print("Database import complete!")

if __name__ == "__main__":
    main()
