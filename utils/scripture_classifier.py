"""
Scripture reference classifier using a lightweight LLM/zero-shot classifier.
Instead of regex patterns, use a small ML model to decide if text is a scripture reference.
"""

import torch
from transformers import pipeline
import logging

logging.getLogger("transformers").setLevel(logging.CRITICAL)

class ScriptureClassifier:
    """
    Uses a zero-shot classification model to detect scripture references.
    This is more robust than regex and handles diverse phrasings.
    """
    
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = 0 if self.use_gpu else -1  # -1 = CPU, 0 = GPU
        
        try:
            # Use a lightweight zero-shot classifier
            # This model can classify text into arbitrary categories without fine-tuning
            print("Loading zero-shot classification model...")
            self.classifier = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=self.device,
                framework="pt"
            )
            print(f"Classifier loaded on {'GPU' if self.use_gpu else 'CPU'}")
        except Exception as e:
            print(f"Failed to load classifier: {e}")
            self.classifier = None
    
    def is_scripture_reference(self, text: str, threshold: float = 0.5) -> tuple:
        """
        Intelligently determine if text is scripture-related using context and intent.
        Detects:
        1. Explicit scripture references ("John 3:16", "Matthew chapter 5")
        2. Scripture being read/quoted ("Blessed is the man who walks not...")
        3. Contextual cues ("This is a reading of Psalms", "Turn to Romans")
        
        Args:
            text: The transcribed text to classify
            threshold: Confidence threshold (0.0-1.0), default lowered to 0.5 for flexibility
        
        Returns:
            (is_scripture: bool, confidence: float, explanation: str)
        """
        import re
        
        if not text or not self.classifier:
            return False, 0.0, "No text or classifier unavailable"
        
        text = text.strip()
        if len(text) < 3:
            return False, 0.0, "Text too short"
        
        text_lower = text.lower()
        
        # Quick rejection filters for obvious non-scripture
        rejection_phrases = [
            'what is', 'alright but', 'welcome to', 'hello', 'hi everyone',
            'good morning', 'good evening', 'thank you for', 'let me tell you',
            'you know what', 'i hope you', 'don\'t you just', 'all right',
            'the holy spirit is', 'holy spirit is', 'the spirit is'
        ]
        
        # Check if text starts with obvious conversational phrases
        for phrase in rejection_phrases:
            if text_lower.startswith(phrase):
                return False, 0.0, f"Starts with conversational phrase: '{phrase}'"
        
        # Bible book names including common misspellings and abbreviations
        bible_books = [
            'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy', 'joshua', 'judges', 'ruth',
            'samuel', 'kings', 'chronicles', 'ezra', 'nehemiah', 'esther', 'job', 'psalms', 'psalm',
            'proverbs', 'ecclesiastes', 'ecclesiastes', 'isaiah', 'jeremiah', 'lamentations', 'ezekiel', 'daniel',
            'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah', 'nahum', 'habakkuk', 'zephaniah',
            'haggai', 'zechariah', 'malachi', 'matthew', 'mark', 'luke', 'john', 'acts', 'romans',
            'corinthians', 'galatians', 'ephesians', 'philippians', 'colossians', 'thessalonians',
            'timothy', 'titus', 'philemon', 'hebrews', 'james', 'peter', 'jude', 'revelation',
            'gen', 'ex', 'lev', 'num', 'deut', 'josh', 'judg', 'sam', 'kgs', 'chr', 'ezr',
            'neh', 'est', 'ps', 'psa', 'prov', 'eccl', 'isa', 'jer', 'lam', 'ezek', 'dan',
            'hos', 'amos', 'obad', 'jon', 'mic', 'nah', 'hab', 'zeph', 'hag', 'zech', 'mal',
            'matt', 'mat', 'mk', 'lk', 'jn', 'rom', 'cor', 'gal', 'eph', 'phil', 'col', 'thess',
            'tim', 'phlm', 'heb', 'jas', 'pet', 'rev',
            # Common misspellings
            'mathew', 'matthw', 'look', 'joan', 'chaps', 'chapsdos', 'chap'
        ]
        
        # Contextual indicators that strongly suggest scripture
        strong_indicators = [
            r'\b(?:this is a|here is a|the)\s+(?:reading|passage)\s+(?:of|from)',
            r'\bturn to\b',
            r'\bopen your bible to\b',
            r'\blet\'s read\b',
            r'\bblessed (?:is|are)\b',
            r'\bin the beginning\b',
            r'\bfor god so loved\b',
            r'\bthe lord is\b',
            r'\bthus (?:saith|says) the lord\b',
            r'\bverily\b',
            r'\bbook of\b.*(?:' + '|'.join(bible_books[:20]) + ')',
            r'\bchapter\s+\d+\s+verse',
        ]
        
        has_strong_indicator = any(re.search(pattern, text_lower) for pattern in strong_indicators)
        
        # Build pattern for book + number reference
        book_pattern = '|'.join(re.escape(book) for book in bible_books)
        number_words = 'one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred'
        reference_pattern = rf'\b({book_pattern})\b\s*(?:chapter\s+)?(?:{number_words}|\d)'
        
        has_reference_pattern = bool(re.search(reference_pattern, text_lower))
        
        # If has strong indicator OR reference pattern, proceed to LLM
        if not (has_strong_indicator or has_reference_pattern):
            # Last chance: use LLM for content that might be scripture text
            # Check for biblical language patterns
            biblical_words = [
                'blessed', 'lord', 'god', 'jesus', 'christ', 'holy', 'spirit',
                'father', 'kingdom', 'heaven', 'righteousness', 'mercy', 'grace',
                'faith', 'salvation', 'covenant', 'testament', 'gospel', 'disciples',
                'apostle', 'prophet', 'pharisee', 'jerusalem', 'israel', 'zion'
            ]
            
            biblical_word_count = sum(1 for word in biblical_words if word in text_lower)
            
            if biblical_word_count < 2:  # Need at least 2 biblical words
                return False, 0.0, "No scripture indicators found"
        
        # Use LLM for intelligent classification
        try:
            # Improved prompt with multiple classification categories
            candidate_labels = [
                "This is a Bible scripture reference or verse being quoted",
                "This is sermon commentary or casual conversation",
                "This is an introduction or transition in a sermon"
            ]
            
            result = self.classifier(text, candidate_labels, multi_class=False)
            top_label = result['labels'][0]
            top_score = result['scores'][0]
            
            # Scripture is the top category
            is_scripture = top_label == "This is a Bible scripture reference or verse being quoted"
            
            # Boost confidence if we found strong indicators
            adjusted_score = top_score
            if has_strong_indicator:
                adjusted_score = min(1.0, top_score * 1.2)  # 20% boost
            
            if adjusted_score < threshold:
                return False, adjusted_score, f"Below threshold ({adjusted_score:.2f} < {threshold})"
            
            explanation_parts = []
            if has_strong_indicator:
                explanation_parts.append("Strong contextual cues")
            if has_reference_pattern:
                explanation_parts.append("Reference pattern found")
            explanation_parts.append(f"LLM confidence: {adjusted_score:.2f}")
            
            explanation = " + ".join(explanation_parts)
            return is_scripture, adjusted_score, explanation
        
        except Exception as e:
            print(f"Classification error: {e}")
            return False, 0.0, f"Error: {e}"
    
    def correct_transcription(self, text: str) -> str:
        """
        Correct common transcription errors to match Bible book names.
        Uses the LLM to suggest the correct book name.
        
        Examples:
            "Mat You Chapter" -> "Matthew Chapter"
            "look chapet 1" -> "Luke Chapter 1"
            "mark 5" -> "Mark 5"
        
        Args:
            text: The transcribed text with potential errors
        
        Returns:
            Corrected text with proper book names
        """
        if not text or not self.classifier:
            return text
        
        text = text.strip()
        text_lower = text.lower()
        
        # Define all possible Bible book names and common abbreviations
        bible_books = {
            # OT books with common variations/misspellings
            'genesis': ['genesis', 'gen', 'genisis'],
            'exodus': ['exodus', 'ex', 'exod'],
            'leviticus': ['leviticus', 'lev'],
            'numbers': ['numbers', 'num', 'numb'],
            'deuteronomy': ['deuteronomy', 'deut'],
            'joshua': ['joshua', 'josh'],
            'judges': ['judges', 'judg'],
            'ruth': ['ruth'],
            '1 samuel': ['1 samuel', '1st samuel', 'first samuel', '1 sam', '1sam'],
            '2 samuel': ['2 samuel', '2nd samuel', 'second samuel', '2 sam', '2sam'],
            '1 kings': ['1 kings', '1st kings', 'first kings', '1 king', '1kgs'],
            '2 kings': ['2 kings', '2nd kings', 'second kings', '2 king', '2kgs'],
            '1 chronicles': ['1 chronicles', '1st chronicles', '1 chr'],
            '2 chronicles': ['2 chronicles', '2nd chronicles', '2 chr'],
            'ezra': ['ezra', 'ezr'],
            'nehemiah': ['nehemiah', 'neh'],
            'esther': ['esther', 'est'],
            'job': ['job'],
            'psalms': ['psalms', 'psalm', 'psa', 'ps'],
            'proverbs': ['proverbs', 'prov'],
            'ecclesiastes': ['ecclesiastes', 'eccl'],
            'isaiah': ['isaiah', 'isa'],
            'jeremiah': ['jeremiah', 'jer'],
            'lamentations': ['lamentations', 'lam'],
            'ezekiel': ['ezekiel', 'ezek'],
            'daniel': ['daniel', 'dan'],
            'hosea': ['hosea', 'hos'],
            'joel': ['joel'],
            'amos': ['amos'],
            'obadiah': ['obadiah', 'obad'],
            'jonah': ['jonah', 'jon'],
            'micah': ['micah', 'mic'],
            'nahum': ['nahum', 'nah'],
            'habakkuk': ['habakkuk', 'hab'],
            'zephaniah': ['zephaniah', 'zeph'],
            'haggai': ['haggai', 'hag'],
            'zechariah': ['zechariah', 'zech'],
            'malachi': ['malachi', 'mal'],
            # NT books
            'matthew': ['matthew', 'matt', 'mat', 'mathew', 'matt.', 'matte', 'matthw'],
            'mark': ['mark', 'mk', 'marc'],
            'luke': ['luke', 'lk', 'look', 'lute'],
            'john': ['john', 'jn', 'jon', 'joan'],
            'acts': ['acts', 'act'],
            'romans': ['romans', 'rom', 'roman', "roman's", "romans'"],
            '1 corinthians': ['1 corinthians', '1st corinthians', '1 cor', '1cor'],
            '2 corinthians': ['2 corinthians', '2nd corinthians', '2 cor', '2cor'],
            'galatians': ['galatians', 'gal'],
            'ephesians': ['ephesians', 'eph'],
            'philippians': ['philippians', 'phil'],
            'colossians': ['colossians', 'col'],
            '1 thessalonians': ['1 thessalonians', '1st thessalonians', '1 thess'],
            '2 thessalonians': ['2 thessalonians', '2nd thessalonians', '2 thess'],
            '1 timothy': ['1 timothy', '1st timothy', '1 tim'],
            '2 timothy': ['2 timothy', '2nd timothy', '2 tim'],
            'titus': ['titus', 'tit'],
            'philemon': ['philemon', 'phlm'],
            'hebrews': ['hebrews', 'heb'],
            'james': ['james', 'jas'],
            '1 peter': ['1 peter', '1st peter', '1 pet'],
            '2 peter': ['2 peter', '2nd peter', '2 pet'],
            '1 john': ['1 john', '1st john', '1 jn'],
            '2 john': ['2 john', '2nd john', '2 jn'],
            '3 john': ['3 john', '3rd john', '3 jn'],
            'jude': ['jude'],
            'revelation': ['revelation', 'rev'],
        }
        
        # Create inverse mapping: misspelling -> correct name
        corrections = {}
        for correct_name, variations in bible_books.items():
            for var in variations:
                corrections[var] = correct_name
        
        # Try to find and correct book names in the text
        corrected_text = text
        import re
        
        # Look for words that might be book names
        # Sort by length (longest first) to match longer names before abbreviations
        sorted_corrections = sorted(corrections.items(), key=lambda x: len(x[0]), reverse=True)
        
        for misspelled, correct in sorted_corrections:
            # Use word boundaries to avoid partial matches
            pattern = rf'\b{re.escape(misspelled)}\b'
            if re.search(pattern, corrected_text, re.IGNORECASE):
                # Only replace if it looks like it's in a scripture context
                # (check if nearby words suggest a chapter/verse number)
                replacement = correct.capitalize()  # Capitalize properly
                corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
                break  # Only correct the first/most relevant book name
        
        return corrected_text.strip()
    
    def extract_reference(self, text: str) -> str:
        """
        Extract and clean a potential scripture reference.
        Remove common transcription artifacts and normalize format.
        Converts number words (one, two, etc.) to digits (1, 2, etc.)
        """
        if not text:
            return ""
        
        text = text.strip()
        
        # Remove common transcription artifacts
        artifacts = [
            r'\.\.\.$',  # trailing ellipsis
            r',$',        # trailing comma
            r'^\s*and\s+',  # leading "and"
            r'^\s*the\s+',  # leading "the"
        ]
        
        import re
        for pattern in artifacts:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Normalize common patterns: "Book Chapter N" -> "Book N"
        text = re.sub(r'\b([Cc]hapter)\s+', '', text)
        text = re.sub(r'\b([Vv]erse)\s+', ':', text)
        
        # Convert number words to digits (one->1, two->2, etc.)
        number_map = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
            'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
            'eighteen': '18', 'nineteen': '19', 'twenty': '20', 'thirty': '30',
            'forty': '40', 'fifty': '50', 'sixty': '60', 'seventy': '70',
            'eighty': '80', 'ninety': '90'
        }
        
        text_lower = text.lower()
        for word, digit in number_map.items():
            # Replace whole-word matches only (word boundaries)
            text = re.sub(rf'\b{word}\b', digit, text, flags=re.IGNORECASE)
        
        return text.strip()


# Global instance
classifier = ScriptureClassifier(use_gpu=True)

def is_scripture(text: str, threshold: float = 0.5) -> bool:
    """Check if text is a scripture reference"""
    is_ref, _, _ = classifier.is_scripture_reference(text, threshold)
    return is_ref

def classify_text(text: str, threshold: float = 0.5) -> dict:
    """
    Classify text and return detailed results.
    Includes transcription correction for common book name errors.
    
    Returns:
        {
            'text': original text,
            'is_scripture': bool,
            'confidence': float,
            'explanation': str,
            'cleaned': cleaned and corrected text for display
        }
    """
    # First, try to correct any transcription errors in book names
    corrected_text = classifier.correct_transcription(text)
    
    # Then classify the corrected text
    is_ref, confidence, explanation = classifier.is_scripture_reference(corrected_text, threshold)
    cleaned = classifier.extract_reference(corrected_text)
    
    return {
        'text': text,
        'is_scripture': is_ref,
        'confidence': confidence,
        'explanation': explanation,
        'cleaned': cleaned
    }


if __name__ == "__main__":
    # Comprehensive test cases covering references and actual scripture
    test_cases = [
        # Explicit references
        "Luke 1",
        "John 3:16",
        "Matthew chapter 5",
        "Psalm 23",
        "Genesis 1:1 in the beginning",
        "This is a reading of the Chaps do's 1-4-1",
        "Turn to Romans 8:28",
        
        # Actual scripture being read
        "Blessed is the man who doesn't walk in the council",
        "Blessed is the man who doesn't walk in the council left the wicked",
        "In the beginning God created the heavens and the earth",
        "For God so loved the world that he gave his only begotten son",
        "The Lord is my shepherd I shall not want",
        
        # Non-scripture (should be rejected)
        "Alright, but what is electricity?",
        "Welcome to the Hard Guy Playcast",
        "I hope you know you're everybody",
        "Don't you just love it don't you",
        "I'm gonna go to the next one",
        "Many have undertaken to draw up an account",  # Could be borderline
    ]
    
    print("SCRIPTURE CLASSIFICATION TEST")
    print("=" * 80)
    for text in test_cases:
        result = classify_text(text)
        status = "SCRIPTURE" if result['is_scripture'] else "NON-SCRIPTURE"
        print(f"\n[{status}] {text[:60]}..." if len(text) > 60 else f"\n[{status}] {text}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Explanation: {result['explanation']}")
        if result['is_scripture']:
            print(f"  Cleaned: {result['cleaned']}")
    print("\n" + "=" * 80)
