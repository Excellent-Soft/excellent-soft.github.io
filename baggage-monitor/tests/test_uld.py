from baggage_monitor import uld


def test_valid_formats():
    assert uld.is_valid("AKE02105BG")
    assert uld.is_valid("ake 02105 bg")
    assert uld.is_valid("PMC4501BG")  # ৪ অঙ্কের সিরিয়াল
    assert uld.normalize("AKE-02105-BG") == "AKE02105BG"


def test_bad_formats():
    assert uld.normalize("AKE0210") is None
    assert uld.normalize("CSQU3054383") is None  # সমুদ্রপথের কনটেইনার ULD নয়
    assert uld.normalize(None) is None


def test_owner_filter():
    assert uld.is_valid("AKE02105BG", {"BG"})
    assert not uld.is_valid("AKE02105EK", {"BG"})
    assert uld.is_valid("AKE02105EK")  # owners না দিলে যেকোনো মালিক
