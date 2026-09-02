from app.services.data_loss_audit import audit_pages_vs_chunks, tokenize_words


def test_tokenize_words_lowercases_and_splits_on_punctuation():
    assert tokenize_words("Hello, World! 123.") == ["hello", "world", "123"]


def test_tokenize_words_handles_devanagari():
    words = tokenize_words("वाशिम गाव सर्वं नंबर")
    assert words == ["वाशिम", "गाव", "सर्वं", "नंबर"]


def test_tokenize_words_empty_string():
    assert tokenize_words("") == []
    assert tokenize_words(None) == []


def test_audit_passes_when_all_words_survive():
    pages = [{"page_number": 1, "text": "Priya Sharma owns 4.5 hectares near the river"}]
    chunk_contents = ["Priya Sharma owns 4.5 hectares", "near the river in Washim"]
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.passed is True
    assert result.missing_count == 0
    assert result.loss_ratio == 0.0


def test_audit_tolerates_a_couple_of_missing_words():
    pages = [{"page_number": 1, "text": " ".join(f"word{i}" for i in range(500)) + " strayartifact"}]
    chunk_contents = [" ".join(f"word{i}" for i in range(500))]  # "strayartifact" genuinely missing, 1 word
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.missing_count == 1
    assert result.passed is True  # within DEFAULT_MIN_ABSOLUTE_TOLERANCE


def test_audit_fails_when_loss_exceeds_tolerance():
    pages = [{"page_number": 1, "text": " ".join(f"word{i}" for i in range(20)) + " lost1 lost2 lost3 lost4"}]
    chunk_contents = [" ".join(f"word{i}" for i in range(20))]  # 4 words missing, above tolerance for this size
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.missing_count == 4
    assert result.passed is False


def test_audit_fails_on_real_data_loss():
    pages = [{"page_number": 1, "text": "The quick brown fox jumps over the lazy dog"}]
    chunk_contents = ["The quick brown fox"]  # "jumps over the lazy dog" entirely dropped
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.passed is False
    assert result.missing_count >= 4
    assert any(item["word"] in ("jumps", "lazy", "dog") for item in result.missing_sample)


def test_audit_skips_extraction_failed_pages():
    pages = [
        {"page_number": 1, "text": "Real OCR content here", "extraction_failed": False},
        {"page_number": 2, "text": "Scanned PDF document: placeholder.pdf", "extraction_failed": True},
    ]
    chunk_contents = ["Real OCR content here"]
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.passed is True
    assert result.total_words == 4  # only page 1's real words counted


def test_audit_handles_no_pages_without_division_by_zero():
    result = audit_pages_vs_chunks([], [])
    assert result.total_words == 0
    assert result.loss_ratio == 0.0
    assert result.passed is True


def test_audit_passes_when_word_repeats_fewer_times_downstream():
    """Word presence, not word count: a register repeating its column
    titles on every OCR'd page but stated once downstream (T26/TS1
    stitching collapsing duplicates) is correct restructuring, not loss —
    the audit checks each OCR'd word appears at least once downstream,
    not that occurrence counts match."""
    pages = [{"page_number": 1, "text": "owner owner owner valuation"}]
    chunk_contents = ["owner valuation"]  # "owner" appears once here, three times in OCR
    result = audit_pages_vs_chunks(pages, chunk_contents)
    assert result.passed is True
    assert result.missing_count == 0


def test_audit_missing_sample_capped():
    pages = [{"page_number": 1, "text": " ".join(f"lostword{i}" for i in range(50))}]
    result = audit_pages_vs_chunks(pages, [], sample_cap=10)
    assert result.missing_count == 50
    assert len(result.missing_sample) == 10
