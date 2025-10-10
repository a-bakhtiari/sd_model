"""Test rate limit handling with exponential backoff in SemanticScholarClient."""
from unittest.mock import Mock, patch
import sys

sys.path.insert(0, '.')

from src.sd_model.external import semantic_scholar
from src.sd_model.external.semantic_scholar import SemanticScholarClient


def test_retry_on_429_error():
    """Test that 429 errors trigger exponential backoff retries."""
    client = SemanticScholarClient()

    call_count = [0]
    sleep_calls = []

    def mock_get(*args, **kwargs):
        call_count[0] += 1
        # First call returns 429, second call succeeds
        if call_count[0] == 1:
            response = Mock()
            response.status_code = 429
            return response
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "data": [
                {
                    "paperId": "test123",
                    "title": "Test Paper",
                    "authors": [{"name": "Test Author"}],
                    "year": 2024,
                    "citationCount": 10,
                }
            ]
        }
        return response

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch.object(semantic_scholar.requests, 'get', side_effect=mock_get), \
         patch.object(semantic_scholar.time, 'sleep', side_effect=mock_sleep), \
         patch.object(client, '_read_cache', return_value=None), \
         patch.object(client, '_write_cache'):
        results = client.search_papers("test query", limit=1)

        # Should have made 2 calls (1 fail + 1 success)
        assert call_count[0] == 2, f"Expected 2 API calls, got {call_count[0]}"

        # Should have slept for 2 seconds on first retry (exponential backoff: 2^1 = 2)
        assert 2 in sleep_calls, f"Expected 2s backoff sleep, got {sleep_calls}"

        # Should still return results after retry
        assert len(results) == 1
        assert results[0].title == "Test Paper"

    print("✓ Test passed: 429 errors trigger retry with exponential backoff")


def test_max_retries_exceeded():
    """Test that max retries is respected."""
    client = SemanticScholarClient()

    call_count = [0]
    sleep_calls = []

    def mock_get(*args, **kwargs):
        call_count[0] += 1
        # Always return 429
        response = Mock()
        response.status_code = 429
        return response

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch.object(semantic_scholar.requests, 'get', side_effect=mock_get), \
         patch.object(semantic_scholar.time, 'sleep', side_effect=mock_sleep), \
         patch.object(client, '_read_cache', return_value=None), \
         patch.object(client, '_write_cache'):
        # Should fail after max retries and return empty list
        results = client.search_papers("test query", limit=1)

        # Should have made 4 calls (initial + 3 retries)
        assert call_count[0] == 4, f"Expected 4 API calls (1 initial + 3 retries), got {call_count[0]}"

        # Should have exponential backoff sleeps: 2, 4, 8 seconds
        assert sleep_calls == [2, 4, 8], f"Expected backoff [2, 4, 8], got {sleep_calls}"

        # Should return empty list when all retries fail (caught by exception handler)
        assert results == [], "Expected empty list when all retries fail"

    print("✓ Test passed: Max retries limit is respected")


def test_immediate_success_no_retry():
    """Test that successful responses don't trigger retries."""
    client = SemanticScholarClient()

    call_count = [0]
    sleep_calls = []

    def mock_get(*args, **kwargs):
        call_count[0] += 1
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        return response

    def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch.object(semantic_scholar.requests, 'get', side_effect=mock_get), \
         patch.object(semantic_scholar.time, 'sleep', side_effect=mock_sleep), \
         patch.object(client, '_read_cache', return_value=None), \
         patch.object(client, '_write_cache'):
        results = client.search_papers("test query", limit=1)

        # Should only make 1 call
        assert call_count[0] == 1, f"Expected 1 API call, got {call_count[0]}"

        # Should not have any retry backoff sleeps (may have rate limit sleep)
        backoff_sleeps = [s for s in sleep_calls if s >= 2]
        assert backoff_sleeps == [], f"Expected no backoff sleeps for success, got {backoff_sleeps}"

    print("✓ Test passed: Successful responses don't trigger unnecessary retries")


if __name__ == "__main__":
    print("Testing Semantic Scholar rate limit retry logic...\n")

    test_retry_on_429_error()
    test_max_retries_exceeded()
    test_immediate_success_no_retry()

    print("\n✅ All tests passed!")
