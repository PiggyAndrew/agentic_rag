
from kb.splitters.splitter_headings import HeadingsSplitter, HeadingItem

def test_heading_missed_by_regex():
    # Case 1: "Chapter 1" style which generic regex might miss (it expects digit start)
    text = """
    Chapter 1 Introduction
    Content of chapter 1.
    
    Chapter 2 Methods
    Content of chapter 2.
    """
    
    allowed = [
        HeadingItem(number="Chapter 1", title="Introduction"),
        HeadingItem(number="Chapter 2", title="Methods"),
    ]
    
    splitter = HeadingsSplitter(allowed_headings=allowed)
    chunks = splitter.split(text)
    
    print(f"Text:\n{text}")
    print(f"Allowed: {allowed}")
    print(f"Chunks found: {len(chunks)}")
    for c in chunks:
        print(f" - {c['metadata']['number']} {c['metadata']['title']}")

    # If the current logic relies on `heading_re` starting with \d+, this will fail (return 1 chunk of whole text).
    if len(chunks) == 2:
        print("SUCCESS: Found chapters despite non-standard format.")
    else:
        print("FAILURE: Missed chapters.")

def test_heading_exact_match():
    # Case 2: Standard format but maybe skipped due to strict filtering or logic
    text = """
    1. Introduction
    Text
    2. Methods
    Text
    """
    allowed = [
        HeadingItem(number="1", title="Introduction"),
        HeadingItem(number="2", title="Methods"),
    ]
    splitter = HeadingsSplitter(allowed_headings=allowed)
    chunks = splitter.split(text)
    print(f"\nChunks found (Standard): {len(chunks)}")
    assert len(chunks) == 2

if __name__ == "__main__":
    test_heading_missed_by_regex()
    test_heading_exact_match()
