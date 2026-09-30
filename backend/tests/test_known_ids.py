import json
from pathlib import Path

from app.shared.known_ids import load_known_ids, vendor_for_id_name

SAMPLE_TABLE = {
    "id5id": ["ID5"],
    "__tamLIResolveResult": ["Live Intent", "Open X"],
}


def test_vendor_for_id_name_single_vendor() -> None:
    assert vendor_for_id_name("id5id", SAMPLE_TABLE) == ["ID5"]


def test_vendor_for_id_name_multiple_vendors_for_one_shared_name() -> None:
    assert vendor_for_id_name("__tamLIResolveResult", SAMPLE_TABLE) == ["Live Intent", "Open X"]


def test_vendor_for_id_name_is_case_sensitive() -> None:
    assert vendor_for_id_name("ID5ID", SAMPLE_TABLE) == []


def test_vendor_for_id_name_unknown_returns_empty_list() -> None:
    assert vendor_for_id_name("not_a_real_id", SAMPLE_TABLE) == []


def test_vendor_for_id_name_returns_a_copy_not_the_shared_list() -> None:
    # Mutating what's returned must never corrupt the table for later callers.
    result = vendor_for_id_name("id5id", SAMPLE_TABLE)
    result.append("Not Actually ID5")
    assert vendor_for_id_name("id5id", SAMPLE_TABLE) == ["ID5"]


def test_load_known_ids_returns_empty_dict_for_missing_directory() -> None:
    assert load_known_ids(Path("/does/not/exist")) == {}


def test_load_known_ids_skips_unfilled_placeholder(tmp_path: Path) -> None:
    (tmp_path / "unresearched.json").write_text(
        json.dumps({"research": {"Service": "Unresearched Co", "IDs": [{"ID": "<ID>"}]}}),
        encoding="utf-8",
    )
    assert load_known_ids(tmp_path) == {}


def test_load_known_ids_merges_a_name_documented_by_two_vendors(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(
        json.dumps({"research": {"Service": "Vendor A", "IDs": [{"ID": "shared_id"}]}}),
        encoding="utf-8",
    )
    (tmp_path / "b.json").write_text(
        json.dumps({"research": {"Service": "Vendor B", "IDs": [{"ID": "shared_id"}]}}),
        encoding="utf-8",
    )
    table = load_known_ids(tmp_path)
    assert table["shared_id"] == ["Vendor A", "Vendor B"]


def test_real_generated_known_ids_load_and_match_id5() -> None:
    """Smoke test against the actual committed backend/app/data/known_ids/
    -- catches the generated files themselves being broken/missing."""
    from app.shared.known_ids import DEFAULT_KNOWN_IDS_DIR

    table = load_known_ids(DEFAULT_KNOWN_IDS_DIR)
    assert vendor_for_id_name("id5id", table) == ["ID5"]
    assert vendor_for_id_name("__tamLIResolveResult", table) == ["Live Intent", "Open X"]
