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


@pytest.mark.parametrize("concurrency", [1, 25])
@pytest.mark.asyncio
async def test_async_job_runner_all_failures(concurrency):
    job_count = 50
    jobs = [{"id": i} for i in range(job_count)]

    runner = AsyncJobRunner(concurrency=concurrency)

    # fake run_job that fails
    mock_run_job_failure = AsyncMock(return_value=False)

    # Expect the status updates in order, and 1 for each job
    expected_error_count = 0
    async for progress in runner.run(jobs, mock_run_job_failure):
        assert progress.complete == 0
        assert progress.errors == expected_error_count
        expected_error_count += 1
        assert progress.total == job_count

    # Verify last status update was complete
    assert expected_error_count == job_count + 1

    # Verify run_job was called for each job
    assert mock_run_job_failure.call_count == job_count

    # Verify run_job was called with the correct arguments
    for i in range(job_count):
        mock_run_job_failure.assert_any_await(jobs[i])


@pytest.mark.parametrize("concurrency", [1, 25])
@pytest.mark.asyncio
async def test_async_job_runner_partial_failures(concurrency):
    job_count = 50
    jobs = [{"id": i} for i in range(job_count)]

    # we want to fail on some jobs and succeed on others
    jobs_to_fail = (0, 2, 4, 6, 8, 20, 25)

    runner = AsyncJobRunner(concurrency=concurrency)

    # fake run_job that fails
    mock_run_job_partial_success = AsyncMock(
        # return True for jobs that should succeed
        side_effect=lambda job: job["id"] not in jobs_to_fail
    )

    # Expect the status updates in order, and 1 for each job
    async for progress in runner.run(jobs, mock_run_job_partial_success):
        assert progress.total == job_count

    # Verify last status update was complete
    expected_error_count = len([job for job in jobs if job["id"] in jobs_to_fail])
    expected_success_count = len(jobs) - expected_error_count
    assert progress.errors == expected_error_count
    assert progress.complete == expected_success_count

    # Verify run_job was called for each job
    assert mock_run_job_partial_success.call_count == job_count

    # Verify run_job was called with the correct arguments
    for i in range(job_count):
        mock_run_job_partial_success.assert_any_await(jobs[i])


@pytest.mark.asyncio
async def test_async_job_runner_partial_raises():
    job_count = 50
    jobs = [{"id": i} for i in range(job_count)]

    # we use concurrency=1 to avoid having the other workers complete jobs
    # concurrently as that would make it hard to verify when the runner exits
    runner = AsyncJobRunner(concurrency=1)

    id_to_fail = 10

    def failure_fn(job):
        if job["id"] == id_to_fail:
            raise Exception("job failed unexpectedly")
        return True

    # fake run_job that fails
    mock_run_job_partial_success = AsyncMock(side_effect=failure_fn)

    # Expect the status updates in order, and 1 for each job
    # until we hit the job that raises an exception
    with pytest.raises(Exception, match="job failed unexpectedly"):
        expected_complete = 0
        async for progress in runner.run(jobs, mock_run_job_partial_success):
            assert progress.complete == expected_complete
            assert progress.errors == 0
            assert progress.total == job_count
            expected_complete += 1

    # verify that we yielded progress for jobs all the way up to the job that raised an exception
    assert expected_complete == id_to_fail + 1
