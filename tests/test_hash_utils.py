from datetime import UTC, datetime, timedelta

from src.models.bill import Bill
from src.utils.hash_utils import compute_bill_hash, deduplicate_by_hash


def _make_bill(number: str, title: str) -> Bill:
    """Helper to create a minimal Bill instance for hashing tests."""
    return Bill(
        jurisdiction="ca-federal",
        parliament=44,
        session=1,
        number=number,
        title_en=title,
        last_fetched_at=datetime.now(UTC),
    )


def test_compute_bill_hash_ignores_timestamps() -> None:
    base_bill = _make_bill("C-1", "An Act respecting example data")
    later_fetched = base_bill.model_copy(update={"last_fetched_at": base_bill.last_fetched_at + timedelta(days=1)})

    assert compute_bill_hash(base_bill) == compute_bill_hash(later_fetched)


def test_compute_bill_hash_detects_content_changes() -> None:
    bill_a = _make_bill("C-2", "Original Title")
    bill_b = _make_bill("C-2", "Updated Title")

    assert compute_bill_hash(bill_a) != compute_bill_hash(bill_b)


def test_deduplicate_by_hash_removes_duplicates() -> None:
    bill_a = _make_bill("C-3", "Act A")
    bill_b = bill_a.model_copy(update={"last_fetched_at": bill_a.last_fetched_at + timedelta(hours=1)})
    bill_c = _make_bill("C-4", "Act B")

    unique, duplicates = deduplicate_by_hash([bill_a, bill_b, bill_c], compute_bill_hash)

    assert duplicates == 1
    assert unique == [bill_a, bill_c]
