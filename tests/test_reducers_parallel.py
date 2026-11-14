"""Test 2: Deterministic reducers for parallel branch state merging."""

from app.orchestration.reducers import (
    append_error_records,
    append_unique_strings,
    merge_asset_registry,
    merge_generic_dicts,
    merge_retry_counts,
)
from app.state.enums import AssetType, ReviewStatus
from app.state.models import AssetRecord, NodeErrorRecord


def test_append_unique_strings():
    """Verify list reducer preserves order while eliminating duplicate node records."""
    base = ["load_project", "node_a"]
    update = ["node_a", "node_b", "node_c"]
    result = append_unique_strings(base, update)
    assert result == ["load_project", "node_a", "node_b", "node_c"]


def test_merge_asset_registry():
    """Verify parallel asset ingestion merges distinct assets and nested metadata safely."""
    ast1 = AssetRecord(
        asset_id="ast_1",
        path="C:/demo.mp4",
        checksum_sha256="hash1",
        asset_type=AssetType.SCREEN_RECORDING,
        metadata={"res": "1080p"},
    )
    ast2 = AssetRecord(
        asset_id="ast_2",
        path="C:/bgm.mp3",
        checksum_sha256="hash2",
        asset_type=AssetType.AUDIO_BGM,
        metadata={"bitrate": "320k"},
    )
    base = {"ast_1": ast1}
    update = {"ast_2": ast2}

    merged = merge_asset_registry(base, update)
    assert len(merged) == 2
    assert "ast_1" in merged and "ast_2" in merged
    assert merged["ast_1"].metadata["res"] == "1080p"
    assert merged["ast_2"].metadata["bitrate"] == "320k"


def test_append_error_records():
    """Verify errors from parallel branches are combined without losing any error."""
    err1 = NodeErrorRecord(node_name="node_a", error_type="E1", message="Error A")
    err2 = NodeErrorRecord(node_name="node_b", error_type="E2", message="Error B")

    result = append_error_records([err1], [err2])
    assert len(result) == 2
    assert result[0].node_name == "node_a"
    assert result[1].node_name == "node_b"


def test_merge_retry_counts():
    """Verify retry count map updates correctly taking the maximum count."""
    base = {"node_a": 1, "node_b": 0}
    update = {"node_a": 2, "node_c": 1}
    result = merge_retry_counts(base, update)
    assert result == {"node_a": 2, "node_b": 0, "node_c": 1}

