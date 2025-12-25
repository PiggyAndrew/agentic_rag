from kb.splitters.splitter_headings import HeadingsSplitter, HeadingItem

def test_headings_splitter():
    # Test 1: Basic initialization
    splitter = HeadingsSplitter()
    assert splitter.allowed_headings == []

    # Test 2: Initialization with allowed headings
    items = [
        HeadingItem(number="1", title="Introduction"),
        HeadingItem(number="2", title="Methods")
    ]
    splitter = HeadingsSplitter(allowed_headings=items)
    assert len(splitter.allowed_headings) == 2
    assert splitter.allowed_headings[0].number == "1"
    assert splitter.allowed_headings[0].title == "Introduction"

    # Test 3: Split logic with allowed headings
    text = """
    1 Introduction
    This is the intro.
    2 Methods
    These are the methods.
    3 Results
    These are results.
    """
    
    # Only 1 and 2 are allowed
    chunks = splitter.split(text)
    
    # Should find 1 and 2. 3 might be skipped if logic dictates so, or included if logic allows non-whitelisted items when whitelist is active?
    # Let's check logic:
    # if allowed_pairs and cand_pair not in allowed_pairs and current_appendix is None: continue
    # So "3 Results" should be skipped if not in allowed list.
    
    print(f"Found {len(chunks)} chunks")
    for c in chunks:
        print(f"Chunk: {c['metadata']['number']} {c['metadata']['title']}")
        
    assert len(chunks) == 2
    assert chunks[0]['metadata']['number'] == "1"
    assert chunks[1]['metadata']['number'] == "2"

if __name__ == "__main__":
    test_headings_splitter()
    print("Test passed!")
