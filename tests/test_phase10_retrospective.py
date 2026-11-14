"""Test Phase 10: Retrospective metrics compilation and controlled scaling governance."""

from app.services.retrospective_service import RetrospectiveService


def test_retrospective_metrics_and_governance():
    """Verify production metrics calculation, 0 unrecovered failures, and unattended batching prohibition."""
    metrics, policy = RetrospectiveService.compile_short_13_retrospective()

    assert metrics.short_id == "short_13_whatsapp_pg_rent"
    assert metrics.total_mcp_operations == 15
    assert metrics.unrecovered_failures == 0
    assert metrics.synthetic_media_placed == 0
    assert metrics.guardrail_violations_prevented == 4
    assert metrics.overall_quality_score >= 9.0

    # Strict controlled scaling assertions
    assert policy.approved_for_unattended_batching is False
    assert policy.max_concurrent_projects == 1
    assert len(policy.governance_rules) >= 5
    assert "Short #14" in policy.scaling_recommendation

