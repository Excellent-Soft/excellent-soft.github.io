from baggage_monitor.aggregator import Aggregator
from baggage_monitor.models import Observation


def obs(t, unloading, people=2, num="AKE02105BG", ok=True, slot=1, conf="high"):
    return Observation(
        frame_index=int(t), time_s=t, captured_at=f"T{int(t):03d}", slot=slot, container_raw=num,
        container_norm=num, check_ok=ok, door_open=True, unloading=unloading, people=people,
        confidence=conf, notes="",
    )


def feed_all(agg, seq):
    out = []
    for o in seq:
        out += agg.feed(o, b"jpg")
    return out + agg.flush()


def test_single_session_start_end_and_people():
    seq = [obs(0, False, 0), obs(3, True, 2), obs(6, True, 4), obs(9, True, 3), obs(12, True, 3),
           obs(15, False, 0), obs(18, False, 0), obs(21, False, 0), obs(24, False, 0)]
    (r,) = feed_all(Aggregator(), seq)
    assert (r.started_at, r.ended_at) == ("T003", "T012")
    assert r.duration_s == 9.0
    assert (r.people_peak, r.people_median) == (4, 3)
    assert r.container_number == "AKE02105BG" and r.container_valid
    assert not r.needs_review and r.evidence_jpeg == b"jpg"


def test_single_active_frame_is_noise():
    assert feed_all(Aggregator(), [obs(0, True), obs(3, False), obs(6, False)]) == []


def test_flush_closes_running_session():
    (r,) = feed_all(Aggregator(), [obs(0, True), obs(3, True), obs(6, True)])
    assert r.ended_at == "T006"


def test_invalid_number_needs_review():
    seq = [obs(t, True, num="AKE0210", ok=False) for t in (0, 3, 6)]
    (r,) = feed_all(Aggregator(), seq)
    assert r.needs_review and not r.container_valid
    assert any("ফরম্যাট" in x for x in r.review_reasons)


def test_valid_read_beats_misreads():
    seq = [obs(0, True), obs(3, True, num="AKE0210", ok=False), obs(6, True), obs(9, True)]
    (r,) = feed_all(Aggregator(), seq)
    assert r.container_number == "AKE02105BG" and r.container_valid


def test_slots_are_independent():
    seq = []
    for t in (0, 3, 6, 9):
        seq.append(obs(t, True, slot=1))
        seq.append(obs(t, t >= 6, slot=2, num="AKH10234BG"))
    reports = feed_all(Aggregator(), seq)
    assert {r.slot for r in reports} == {1, 2}
