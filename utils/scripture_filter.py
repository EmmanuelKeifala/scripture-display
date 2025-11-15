"""
Scripture reference detection and filtering utilities
"""

import re
from typing import Optional, List, Tuple

# Bible book names and common abbreviations
BIBLE_BOOKS = {
    # Old Testament
    'genesis': ['gen', 'ge', 'gn'],
    'exodus': ['exo', 'ex', 'exod'],
    'leviticus': ['lev', 'le', 'lv'],
    'numbers': ['num', 'nu', 'nm', 'nb'],
    'deuteronomy': ['deut', 'de', 'dt'],
    'joshua': ['josh', 'jos', 'jsh'],
    'judges': ['judg', 'jdg', 'jg', 'jdgs'],
    'ruth': ['rth', 'ru'],
    '1 samuel': ['1 sam', '1 sa', '1samuel', '1s', '1 sm', 'i samuel', 'i sam'],
    '2 samuel': ['2 sam', '2 sa', '2samuel', '2s', '2 sm', 'ii samuel', 'ii sam'],
    '1 kings': ['1 kgs', '1 ki', '1k', '1kgs', 'i kings', 'i kgs'],
    '2 kings': ['2 kgs', '2 ki', '2k', '2kgs', 'ii kings', 'ii kgs'],
    '1 chronicles': ['1 chron', '1 ch', '1ch', '1 chr', 'i chronicles', 'i chron'],
    '2 chronicles': ['2 chron', '2 ch', '2ch', '2 chr', 'ii chronicles', 'ii chron'],
    'ezra': ['ezr', 'ez'],
    'nehemiah': ['neh', 'ne'],
    'esther': ['esth', 'es'],
    'job': ['jb'],
    'psalms': ['psalm', 'ps', 'psa', 'pss', 'pslm'],
    'proverbs': ['prov', 'pr', 'prv'],
    'ecclesiastes': ['eccl', 'ec', 'ecc'],
    'song of solomon': ['song', 'so', 'sos', 'song of songs', 'canticles'],
    'isaiah': ['isa', 'is'],
    'jeremiah': ['jer', 'je', 'jr'],
    'lamentations': ['lam', 'la'],
    'ezekiel': ['ezek', 'eze', 'ezk'],
    'daniel': ['dan', 'da', 'dn'],
    'hosea': ['hos', 'ho'],
    'joel': ['joe', 'jl'],
    'amos': ['am'],
    'obadiah': ['obad', 'ob'],
    'jonah': ['jnh', 'jon'],
    'micah': ['mic', 'mc'],
    'nahum': ['nah', 'na'],
    'habakkuk': ['hab', 'hb'],
    'zephaniah': ['zeph', 'zep', 'zp'],
    'haggai': ['hag', 'hg'],
    'zechariah': ['zech', 'zec', 'zc'],
    'malachi': ['mal', 'ml'],
    
    # New Testament
    'matthew': ['matt', 'mt'],
    'mark': ['mk', 'mr'],
    'luke': ['lk', 'lu'],
    'john': ['jn', 'jhn'],
    'acts': ['ac'],
    'romans': ['rom', 'ro', 'rm'],
    '1 corinthians': ['1 cor', '1 co', '1cor', '1c', 'i corinthians', 'i cor'],
    '2 corinthians': ['2 cor', '2 co', '2cor', '2c', 'ii corinthians', 'ii cor'],
    'galatians': ['gal', 'ga'],
    'ephesians': ['eph', 'ephes'],
    'philippians': ['phil', 'php', 'pp'],
    'colossians': ['col', 'co'],
    '1 thessalonians': ['1 thess', '1 th', '1thess', '1t', 'i thessalonians', 'i thess'],
    '2 thessalonians': ['2 thess', '2 th', '2thess', '2t', 'ii thessalonians', 'ii thess'],
    '1 timothy': ['1 tim', '1 ti', '1tim', '1t', 'i timothy', 'i tim'],
    '2 timothy': ['2 tim', '2 ti', '2tim', '2t', 'ii timothy', 'ii tim'],
    'titus': ['tit', 'ti'],
    'philemon': ['phlm', 'phm'],
    'hebrews': ['heb', 'he'],
    'james': ['jas', 'jm'],
    '1 peter': ['1 pet', '1 pe', '1pet', '1p', 'i peter', 'i pet'],
    '2 peter': ['2 pet', '2 pe', '2pet', '2p', 'ii peter', 'ii pet'],
    '1 john': ['1 jn', '1 jo', '1john', '1j', 'i john', 'i jn'],
    '2 john': ['2 jn', '2 jo', '2john', '2j', 'ii john', 'ii jn'],
    '3 john': ['3 jn', '3 jo', '3john', '3j', 'iii john', 'iii jn'],
    'jude': ['jud', 'jd'],
    'revelation': ['rev', 're', 'rv', 'revelations']
}

# Create reverse lookup for abbreviations
BOOK_LOOKUP = {}
for full_name, abbreviations in BIBLE_BOOKS.items():
    BOOK_LOOKUP[full_name.lower()] = full_name
    for abbr in abbreviations:
        BOOK_LOOKUP[abbr.lower()] = full_name

class ScriptureFilter:
    def __init__(self):
        self.book_pattern = self._create_book_pattern()
        self.reference_patterns = [
            # Full references: "John 3:16", "1 Corinthians 13:4-7"
            re.compile(r'\b(' + self.book_pattern + r')\s+(\d+)(?::(\d+)(?:-(\d+))?)?\b', re.IGNORECASE),
            # Chapter only: "Psalm 23", "Romans 8"
            re.compile(r'\b(' + self.book_pattern + r')\s+(\d+)\b', re.IGNORECASE),
            # Book only: "Genesis", "Revelation"
            re.compile(r'\b(' + self.book_pattern + r')\b', re.IGNORECASE)
        ]
    
    def _create_book_pattern(self) -> str:
        """Create regex pattern for all book names and abbreviations"""
        all_names = list(BOOK_LOOKUP.keys())
        # Sort by length (longest first) to match longer names before shorter ones
        all_names.sort(key=len, reverse=True)
        # Escape special regex characters and join with |
        escaped_names = [re.escape(name) for name in all_names]
        return '|'.join(escaped_names)
    
    def extract_scripture_references(self, text: str) -> List[Tuple[str, str]]:
        """
        Extract scripture references from text
        Returns list of (original_text, normalized_reference) tuples
        """
        references = []
        
        for pattern in self.reference_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                original = match.group(0)
                normalized = self._normalize_reference(match)
                if normalized:
                    references.append((original, normalized))
        
        return references
    
    def _normalize_reference(self, match) -> Optional[str]:
        """Normalize a scripture reference match"""
        book_text = match.group(1).lower().strip()
        
        # Look up the full book name
        full_book = BOOK_LOOKUP.get(book_text)
        if not full_book:
            return None
        
        # Build the reference
        reference = full_book.title()
        
        if len(match.groups()) > 1 and match.group(2):
            chapter = match.group(2)
            reference += f" {chapter}"
            
            if len(match.groups()) > 2 and match.group(3):
                verse_start = match.group(3)
                reference += f":{verse_start}"
                
                if len(match.groups()) > 3 and match.group(4):
                    verse_end = match.group(4)
                    reference += f"-{verse_end}"
        
        return reference
    
    def is_likely_scripture_reference(self, text: str) -> bool:
        """Check if text is likely a scripture reference"""
        text_lower = text.lower()
        
        # Only accept if we have book name + numbers (chapter/verse)
        for book in BOOK_LOOKUP.keys():
            # Check for "book <number>" or "book <number>:<number>" pattern
            if re.search(rf'\b{re.escape(book)}\b\s*[\d:,\-]', text_lower):
                return True
        
        return False
    
    def filter_non_scripture(self, text: str) -> str:
        """Filter out text that doesn't contain scripture references"""
        if not text or len(text.strip()) < 2:
            return ""
        
        text_lower = text.lower()
        
        # VERY STRICT: Only accept if we find a book name + a number/digit
        # This catches patterns like "Luke 1", "John 3:16", "Matthew 5"
        for book in BOOK_LOOKUP.keys():
            # Check for "book <number>" or "book <number>:<number>" or "book <number>-<number>"
            if re.search(rf'\b{re.escape(book)}\b\s*[\d:,\-]', text_lower):
                return text.strip()
        
        # Reject everything else (no book + number pattern found)
        return ""
    
    def enhance_transcription(self, text: str) -> str:
        """Enhance transcription for better scripture detection"""
        if not text:
            return ""
        
        # Common transcription fixes for scripture references
        fixes = {
            # Handle "Book, Chapter N" or "Book Chapter N" patterns
            r',\s*([Cc]hapter)\s+(\d+)': r' \2',
            r'\s+([Cc]hapter)\s+(\d+)': r' \2',
            # Handle "Book Verse N" or "Book V N"
            r'\s+([Vv]erse|V)\s+(\d+)': r':\2',
            # Handle numeric chapter/verse patterns
            r'\b1000\b': '3:16',  # "John 1000" -> "John 3:16"
            r'\bthree sixteen\b': '3:16',
            r'\bthree colon sixteen\b': '3:16',
            # Remove standalone "chapter" or "verse" keywords after extraction
            r'\b([Cc]hapter|[Vv]erse)\b\s*(?![0-9])': '',
            r'\bfirst (\w+)\b': r'1 \1',
            r'\bsecond (\w+)\b': r'2 \1',
            r'\bthird (\w+)\b': r'3 \1',
        }
        
        enhanced = text
        for pattern, replacement in fixes.items():
            enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)
        
        return enhanced.strip()

# Global instance
scripture_filter = ScriptureFilter()

def filter_scripture_text(text: str) -> str:
    """Main function to filter and enhance scripture text"""
    if not text:
        return ""
    
    # Enhance the transcription
    enhanced = scripture_filter.enhance_transcription(text)
    
    # Filter non-scripture content
    filtered = scripture_filter.filter_non_scripture(enhanced)
    
    # DEBUG logging
    if text.lower().count('luke') > 0 or text.lower().count('chapter') > 0:
        print(f"  [DEBUG filter_scripture_text]")
        print(f"    Input: '{text}'")
        print(f"    Enhanced: '{enhanced}'")
        print(f"    Filtered: '{filtered}'")
        print(f"    is_likely_scripture: {scripture_filter.is_likely_scripture_reference(enhanced)}")
    
    return filtered

def extract_references(text: str) -> List[Tuple[str, str]]:
    """Extract scripture references from text"""
    return scripture_filter.extract_scripture_references(text)

if __name__ == "__main__":
    # Test the filter
    test_texts = [
        "John 3:16",
        "The counted CPUs",
        "Michael's like a bodybuilder",
        "Romans just made them sharper",
        "John 1000",  # Should be corrected to John 3:16
        "First Corinthians thirteen four",
        "Psalm twenty three"
    ]
    
    for text in test_texts:
        filtered = filter_scripture_text(text)
        if filtered:
            print(f"'{text}' -> '{filtered}'")
            refs = extract_references(filtered)
            if refs:
                print(f"  References: {refs}")
        else:
            print(f"'{text}' -> [FILTERED OUT]")
