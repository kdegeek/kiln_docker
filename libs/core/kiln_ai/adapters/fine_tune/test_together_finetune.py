import pytest
from together.types.finetune import FinetuneJobStatus as TogetherFinetuneJobStatus

from kiln_ai.adapters.fine_tune.together_finetune import (
    _completed_statuses,
    _failed_statuses,
    _pending_statuses,
    _running_statuses,
)


def test_together_status_categorization():
    """
    Test that all statuses from TogetherFinetuneJobStatus are included in exactly one
    of the status categorization arrays.
    """
    # Collect all status values from the TogetherFinetuneJobStatus class
    all_statuses = list(TogetherFinetuneJobStatus)

    # Collect all statuses from the categorization arrays
    categorized_statuses = set()
    categorized_statuses.update(_pending_statuses)
    categorized_statuses.update(_running_statuses)
    categorized_statuses.update(_completed_statuses)
    categorized_statuses.update(_failed_statuses)

    # Check if any status is missing from categorization
    missing_statuses = set(all_statuses) - categorized_statuses
    assert not missing_statuses, (
        f"These statuses are not categorized: {missing_statuses}"
    )

    # Check if any status appears in multiple categories
    all_categorization_lists = [
        _pending_statuses,
        _running_statuses,
        _completed_statuses,
        _failed_statuses,
    ]

    for status in all_statuses:
        appearances = sum(status in category for category in all_categorization_lists)
        assert appearances == 1, (
            f"Status '{status}' appears in {appearances} categories (should be exactly 1)"
        )
