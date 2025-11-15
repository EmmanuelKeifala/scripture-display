from scripture.detector import ScriptureDetector

def test_detector():
    print("Scripture Detector Tests")
    print("=" * 70)
    
    detector = ScriptureDetector(confidence_threshold=0.7)
    
    test_cases = [
        "Today we will look at John 3:16 which tells us about God's love.",
        "Turn to Matthew 5:1-10 for the Beatitudes.",
        "In the book of Genesis chapter 1 verse 1, we read about creation.",
        "First Corinthians chapter 13 verses 4 through 7 describes love.",
        "Let's read Psalm 23:1-3 together.",
        "As it says in Romans 8:28, all things work together for good.",
        "The passage in 1 John 4:8 says God is love.",
        "In Second Timothy chapter 3 verse 16 we learn about Scripture.",
        "Look at Rev 21:4 where it talks about no more tears.",
        "The prophet Isaiah in chapter 40 verse 31 gives us hope.",
        "Multiple references: John 3:16 and also Romans 5:8 show God's love.",
        "Consider what James chapter 1 verses 2 to 4 says about trials.",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {text}")
        print("-" * 70)
        
        references = detector.detect(text)
        
        if references:
            print(f"Found {len(references)} reference(s):")
            for ref in references:
                if ref.start_verse == ref.end_verse:
                    verse_str = f"{ref.start_verse}"
                else:
                    verse_str = f"{ref.start_verse}-{ref.end_verse}"
                
                print(f"  - {ref.book} {ref.chapter}:{verse_str}")
                print(f"    Confidence: {ref.confidence:.2%}")
                print(f"    Original: '{ref.original_text}'")
        else:
            print("  No references found")
    
    print("\n" + "=" * 70)
    print("\nConfidence Threshold Test")
    print("-" * 70)
    
    text = "Turn to John 3:16 and also look at the book of Romans 8:28"
    print(f"Text: {text}\n")
    
    for threshold in [0.5, 0.7, 0.9]:
        detector.set_confidence_threshold(threshold)
        refs = detector.detect(text)
        print(f"Threshold {threshold:.1f}: Found {len(refs)} reference(s)")
        for ref in refs:
            print(f"  - {ref}")
    
    print("\n" + "=" * 70)
    print("Tests complete!")

if __name__ == "__main__":
    test_detector()
