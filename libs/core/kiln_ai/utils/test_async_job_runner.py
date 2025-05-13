from unittest.mock import AsyncMock

import pytest

from kiln_ai.utils.async_job_runner import AsyncJobRunner


# Test with and without concurrency
@pytest.mark.parametrize("concurrency", [1, 25])
@pytest.mark.asyncio
async def test_async_job_runner_status_updates(concurrency):
    job_count = 50
    jobs = [{"id": i} for i in range(job_count)]

    runner = AsyncJobRunner(concurrency=concurrency)

    # fake run_job that succeeds
    mock_run_job_success = AsyncMock(return_value=True)

    # Expect the status updates in order, and 1 for each job
    expected_completed_count = 0
    async for progress in runner.run(jobs, mock_run_job_success):
        assert progress.complete == expected_completed_count
        expected_completed_count += 1
        assert progress.errors == 0
        assert progress.total == job_count

    # Verify last status update was complete
    assert expected_completed_count == job_count + 1

    # Verify run_job was called for each job
    assert mock_run_job_success.call_count == job_count

    # Verify run_job was called with the correct arguments
    for i in range(job_count):
        mock_run_job_success.assert_any_await(jobs[i])
