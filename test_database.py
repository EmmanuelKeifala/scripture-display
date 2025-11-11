from scripture.lookup import ScriptureLookup

def test_lookup():
    print("Testing Scripture Lookup")
    print("=" * 60)
    
    lookup = ScriptureLookup()
    
    print("\nTest 1: Single verse lookup (John 3:16)")
    verse = lookup.get_verse("John", 3, 16)
    if verse:
        print(f"  {verse['book']} {verse['chapter']}:{verse['verse']}")
        print(f"  {verse['text']}")
    else:
        print("  Verse not found")
    
    print("\nTest 2: Verse range lookup (Psalm 23:1-3)")
    verses = lookup.get_verse_range("Psalms", 23, 1, 3)
    if verses:
        for v in verses:
            print(f"  {v['verse']}: {v['text']}")
    else:
        print("  Verses not found")
    
    print("\nTest 3: Available translations")
    translations = lookup.get_available_translations()
    print(f"  {translations}")
    
    print("\nTest 4: All books")
    books = lookup.get_all_books()
    print(f"  Total books: {len(books)}")
    print(f"  First 5: {[b['name'] for b in books[:5]]}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")

if __name__ == "__main__":
    test_lookup()
