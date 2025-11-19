#!/usr/bin/env python3
"""
Test the improved scripture classifier with real-world examples.
"""

from utils.scripture_classifier import classify_text

def test_classifier():
    print("\n" + "=" * 80)
    print("IMPROVED SCRIPTURE CLASSIFIER TEST")
    print("=" * 80)
    
    # Test cases from actual user log
    test_cases = [
        # Cases from user's log that should be detected
        ("This is a reading of the Chaps do's 1-4-1", True, "Reference with misspelling"),
        ("Blessed is the man who doesn't walk in the council", True, "Psalms 1:1 text"),
        ("Blessed is the man who doesn't walk in the council left the wicked", True, "Psalms 1:1 extended"),
        ("the Lord is my shepherd", True, "Psalms 23 text"),
        ("For God so loved the world", True, "John 3:16 text"),
        ("In the beginning God created", True, "Genesis 1:1 text"),
        
        # References that should be detected
        ("John 3:16", True, "Standard reference"),
        ("Turn to Matthew 5", True, "Spoken reference"),
        ("Psalm 23", True, "Simple reference"),
        ("Romans chapter 8 verse 28", True, "Full spoken reference"),
        
        # Non-scripture from user's log that should be rejected
        ("Alright, but what is electricity?", False, "Question"),
        ("Welcome to the Hard Guy Playcast", False, "Introduction"),
        ("I hope you know you're everybody", False, "Conversation"),
        ("Don't you just love it don't you", False, "Casual speech"),
        ("you know what I'm trying to say", False, "Filler phrase"),
        ("Thank you", False, "Politeness"),
        ("Good night", False, "Greeting"),
        
        # Edge cases
        ("the Holy Spirit is empty", False, "Contains 'Holy Spirit' but not scripture"),
        ("movement it has It's been limited just to certain", False, "Sermon commentary"),
        ("charismatic movement in Southern Poland", False, "Historical reference"),
    ]
    
    correct = 0
    total = len(test_cases)
    
    for text, expected_scripture, description in test_cases:
        result = classify_text(text)
        is_correct = result['is_scripture'] == expected_scripture
        correct += is_correct
        
        status_symbol = "PASS" if is_correct else "FAIL"
        detection = "SCRIPTURE" if result['is_scripture'] else "NON-SCRIPTURE"
        expected = "SCRIPTURE" if expected_scripture else "NON-SCRIPTURE"
        
        print(f"\n[{status_symbol}] {description}")
        print(f"  Text: {text[:70]}..." if len(text) > 70 else f"  Text: {text}")
        print(f"  Expected: {expected} | Got: {detection}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Explanation: {result['explanation']}")
        if result['is_scripture']:
            print(f"  Cleaned: {result['cleaned']}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {correct}/{total} tests passed ({100*correct/total:.1f}%)")
    print("=" * 80 + "\n")
    
    return correct == total

if __name__ == "__main__":
    success = test_classifier()
    exit(0 if success else 1)
