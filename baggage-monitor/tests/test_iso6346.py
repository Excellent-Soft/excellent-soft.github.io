from baggage_monitor import iso6346


def test_known_valid_numbers():
    assert iso6346.is_valid("CSQU3054383")
    assert iso6346.is_valid("csqu 305438 3")
    assert iso6346.is_valid("MSKU9070323")


def test_wrong_check_digit():
    assert not iso6346.is_valid("CSQU3054384")


def test_bad_shapes():
    assert iso6346.normalize("ABC123") is None
    assert iso6346.normalize("CSQX3054383") is None  # ৪র্থ অক্ষর U/J/Z নয়
    assert iso6346.normalize(None) is None


def test_ocr_fix_in_digit_part():
    assert iso6346.normalize("CSQU3O54383") == "CSQU3054383"
