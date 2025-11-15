import re
from typing import List, Dict, Optional
from scripture.book_mappings import normalize_book_name, get_all_book_patterns, SPOKEN_NUMBERS

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

class ScriptureDetector:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.book_patterns = get_all_book_patterns()
        self._build_patterns()
    
    def _build_patterns(self):
        book_pattern = '|'.join(re.escape(book) for book in self.book_patterns)
        
        self.patterns = [
            # Standard format: "John 3:16" or "John 3:16-18"
            (
                re.compile(
                    rf'\b({book_pattern})\s+(\d+):(\d+)(?:-(\d+))?\b',
                    re.IGNORECASE
                ),
                1.0,
                'standard'
            ),
            # LLM classifier output: "John 1" (chapter only, default to verse 1)
            (
                re.compile(
                    rf'\b({book_pattern})\s+(\d+)\b(?!\s*:)',
                    re.IGNORECASE
                ),
                0.95,
                'chapter_only'
            ),
            # Spoken full: "John chapter 3 verse 16"
            (
                re.compile(
                    rf'\b({book_pattern})\s+chapter\s+(\d+)\s+verse\s+(\d+)(?:\s+(?:through|to|thru)\s+(?:verse\s+)?(\d+))?\b',
                    re.IGNORECASE
                ),
                0.95,
                'spoken_full'
            ),
            # Spoken verses: "John chapter 3 verses 16-18"
            (
                re.compile(
                    rf'\b({book_pattern})\s+chapter\s+(\d+)\s+verses?\s+(\d+)(?:\s+(?:through|to|thru)\s+(\d+))?\b',
                    re.IGNORECASE
                ),
                0.9,
                'spoken_verses'
            ),
            # "in the book of John 3:16"
            (
                re.compile(
                    rf'\b(?:in\s+)?(?:the\s+book\s+of\s+)?({book_pattern})\s+(\d+):(\d+)(?:-(\d+))?\b',
                    re.IGNORECASE
                ),
                0.85,
                'book_of'
            ),
            # "Turn to John 3 verse 16"
            (
                re.compile(
                    rf'\b(?:turn\s+to\s+)?({book_pattern})\s+(\d+)\s+verse\s+(\d+)(?:\s+(?:through|to)\s+(\d+))?\b',
                    re.IGNORECASE
                ),
                0.85,
                'turn_to'
            ),
        ]
    
    def detect(self, text: str) -> List[ScriptureReference]:
        references = []
        
        for pattern, base_confidence, pattern_type in self.patterns:
            matches = pattern.finditer(text)
            
            for match in matches:
                try:
                    book_raw = match.group(1)
                    chapter = int(match.group(2))
                    
                    # Handle chapter_only pattern (no verse specified, default to 1)
                    if pattern_type == 'chapter_only':
                        start_verse = 1
                        end_verse = 1
                    else:
                        start_verse = int(match.group(3))
                        end_verse_str = match.group(4) if len(match.groups()) >= 4 else None
                        end_verse = int(end_verse_str) if end_verse_str else start_verse
                    
                    book_normalized = normalize_book_name(book_raw)
                    
                    if book_normalized:
                        confidence = base_confidence
                        
                        if book_raw.lower() == book_normalized.lower():
                            confidence *= 1.0
                        else:
                            confidence *= 0.95
                        
                        if confidence >= self.confidence_threshold:
                            ref = ScriptureReference(
                                book=book_normalized,
                                chapter=chapter,
                                start_verse=start_verse,
                                end_verse=end_verse,
                                confidence=confidence,
                                original_text=match.group(0)
                            )
                            references.append(ref)
                
                except (ValueError, IndexError) as e:
                    continue
        
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
