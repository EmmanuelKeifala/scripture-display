import difflib
import re
from typing import List, Dict, Optional
from scripture.book_mappings import BOOK_NAMES, normalize_book_name, get_all_book_patterns

class ScriptureReference:
    def __init__(self, book: str, chapter: int, start_verse: int, end_verse: Optional[int] = None, 
                 confidence: float = 1.0, original_text: str = ""):
        self.book = book
        self.chapter = chapter
        self.start_verse = start_verse
        self.end_verse = end_verse or start_verse
        self.confidence = confidence
        self.original_text = original_text
    
    def __repr__(self):
        if self.start_verse == self.end_verse:
            return f"{self.book} {self.chapter}:{self.start_verse} ({self.confidence:.2f})"
        else:
            return f"{self.book} {self.chapter}:{self.start_verse}-{self.end_verse} ({self.confidence:.2f})"
    
    def to_dict(self):
        return {
            'book': self.book,
            'chapter': self.chapter,
            'start_verse': self.start_verse,
            'end_verse': self.end_verse,
            'confidence': self.confidence,
            'original_text': self.original_text
        }

_UNITS = 'one two three four five six seven eight nine'.split()
_TEENS = 'ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
_TENS = 'twenty thirty forty fifty sixty seventy eighty ninety'.split()
_SMALL = rf"(?:(?:{'|'.join(_TENS)})(?:[\s-]+(?:{'|'.join(_UNITS)}))?|{'|'.join(_TEENS)}|{'|'.join(_UNITS)})"
_NUMBER_WORDS = re.compile(
    rf"\b(?:({'|'.join(_UNITS)})\s+hundred(?:\s+(?:and\s+)?({_SMALL}))?|({_SMALL}))\b",
    re.IGNORECASE
)

def _small_value(words: str) -> int:
    total = 0
    for word in re.split(r'[\s-]+', words.lower()):
        if word in _UNITS:
            total += _UNITS.index(word) + 1
        elif word in _TEENS:
            total += _TEENS.index(word) + 10
        else:
            total += (_TENS.index(word) + 2) * 10
    return total

def words_to_digits(text: str) -> str:
    """'John three sixteen' -> 'John 3 16', 'Psalm one hundred nineteen' -> 'Psalm 119'."""
    def replace(match):
        hundreds, rest, small = match.groups()
        if hundreds:
            return str(_small_value(hundreds) * 100 + (_small_value(rest) if rest else 0))
        return str(_small_value(small))
    return _NUMBER_WORDS.sub(replace, text)

class ScriptureDetector:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.book_patterns = get_all_book_patterns()
        self._build_patterns()
    
    def _build_patterns(self):
        book_pattern = '|'.join(re.escape(book) for book in self.book_patterns)
        
        # One pattern for written and spoken forms:
        #   "John 3:16-18", "John 3.16", "John 3, 16", "John 3 16",
        #   "John chapter 3 verse 16", "John 3 verses 16 through 18", "Psalm 23"
        self.pattern = re.compile(
            rf'\b({book_pattern})\b\.?[\s,]*(?:in\s+)?(chapter\s+)?(\d{{1,3}})\b'
            rf'(?:\s*([:.,-])?\s*(verses?\s+)?(\d{{1,3}})\b'
            rf'(?:\s*(?:-|–|to|through|thru)\s*(?:verse\s+)?(\d{{1,3}})\b)?)?',
            re.IGNORECASE
        )
        # Misheard book name in front of an unmistakable reference:
        # "Collisions chapter 3 verse 2", "Habacuc 2:4"
        self.misheard_pattern = re.compile(
            r'\b([a-z]{4,})[\s,]+(?:(chapter)\s+(\d{1,3})[\s,]+(verses?)\s+(\d{1,3})|(\d{1,3})(:)(\d{1,3}))\b'
            r'(?:\s*(?:-|–|to|through|thru)\s*(?:verse\s+)?(\d{1,3})\b)?',
            re.IGNORECASE
        )
        # "verse 17", "verses 4 through 7": only meaningful with a current chapter
        self.followup_pattern = re.compile(
            r'\bverses?\s+(\d{1,3})\b(?:\s*(?:-|–|to|through|thru|and)\s*(?:verse\s+)?(\d{1,3})\b)?',
            re.IGNORECASE
        )
        self._single_word_books = [name.lower() for name in BOOK_NAMES if ' ' not in name]
    
    def detect_followup(self, text: str, book: str, chapter: int) -> List[ScriptureReference]:
        """References like "verse 17" that continue in the chapter already on screen."""
        references = []
        for match in self.followup_pattern.finditer(words_to_digits(text)):
            start_verse = int(match.group(1))
            end_verse = int(match.group(2)) if match.group(2) and int(match.group(2)) > start_verse else start_verse
            if 0.75 >= self.confidence_threshold:
                references.append(ScriptureReference(book, chapter, start_verse, end_verse, 0.75, match.group(0)))
        return references
    
    def _detect_misheard(self, text: str) -> List[ScriptureReference]:
        references = []
        for match in self.misheard_pattern.finditer(text):
            word = match.group(1).lower()
            if normalize_book_name(word):
                continue  # a real book name; the main pattern handles it
            close = difflib.get_close_matches(word, self._single_word_books, n=1, cutoff=0.65)
            if not close or 0.8 < self.confidence_threshold:
                continue
            chapter = int(match.group(3) or match.group(6))
            start_verse = int(match.group(5) or match.group(8))
            end_str = match.group(9)
            end_verse = int(end_str) if end_str and int(end_str) > start_verse else start_verse
            references.append(ScriptureReference(
                normalize_book_name(close[0]), chapter, start_verse, end_verse, 0.8, match.group(0)
            ))
        return references
    
    def detect(self, text: str, allow_trailing: bool = True) -> List[ScriptureReference]:
        """allow_trailing=False ignores a reference at the very end of the text: in a
        live partial transcript its numbers may not be finished ("John 3:1" ... "6")."""
        text = words_to_digits(text)
        complete_until = len(text) if allow_trailing else len(text.rstrip(' .,?!'))
        references = self._detect_misheard(text) if allow_trailing else []
        
        for match in self.pattern.finditer(text):
            if not allow_trailing and match.end() >= complete_until:
                continue
            
            book_raw, chapter_word, chapter_str, separator, verse_word, verse_str, end_str = match.groups()
            
            book = normalize_book_name(book_raw)
            if not book:
                continue
            
            # Short abbreviations ("Is", "Am", "Rev") are ordinary words in speech,
            # so only trust them in the explicit written form "Rev 21:4"
            is_abbreviation = book_raw.lower() != book.lower() and len(book_raw.replace(' ', '')) <= 4
            if is_abbreviation and separator != ':':
                continue
            
            chapter = int(chapter_str)
            
            if verse_str:
                start_verse = int(verse_str)
                end_verse = int(end_str) if end_str and int(end_str) > start_verse else start_verse
                if separator == ':' or (chapter_word and verse_word):
                    confidence = 1.0
                elif chapter_word or verse_word:
                    confidence = 0.95
                else:
                    confidence = 0.85
            elif len(chapter_str) == 3 and book != 'Psalms':
                # Whisper writes "John three sixteen" as "John 316"
                chapter, start_verse = int(chapter_str[0]), int(chapter_str[1:])
                end_verse = start_verse
                confidence = 0.8
            else:
                # Chapter only: show verse 1. Without the word "chapter" this is
                # usually a false alarm ("Mark 1 day..."), except for Psalms.
                start_verse = end_verse = 1
                confidence = 0.9 if chapter_word else 0.85 if book == 'Psalms' else 0.65
            
            if confidence >= self.confidence_threshold:
                references.append(ScriptureReference(
                    book=book,
                    chapter=chapter,
                    start_verse=start_verse,
                    end_verse=end_verse,
                    confidence=confidence,
                    original_text=match.group(0)
                ))
        
        references = self._deduplicate_references(references)
        
        return sorted(references, key=lambda x: x.confidence, reverse=True)
    
    def _deduplicate_references(self, references: List[ScriptureReference]) -> List[ScriptureReference]:
        if not references:
            return []
        
        unique_refs = []
        seen = set()
        
        for ref in references:
            key = (ref.book, ref.chapter, ref.start_verse, ref.end_verse)
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        return unique_refs
    
    def detect_and_filter(self, text: str, min_confidence: Optional[float] = None) -> List[ScriptureReference]:
        threshold = min_confidence if min_confidence is not None else self.confidence_threshold
        all_refs = self.detect(text)
        return [ref for ref in all_refs if ref.confidence >= threshold]
    
    def set_confidence_threshold(self, threshold: float):
        self.confidence_threshold = max(0.0, min(1.0, threshold))
