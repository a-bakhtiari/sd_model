"""Simple test to verify rate limit retry logic works."""
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent to path
sys.path.insert(0, '.')

from src.sd_model.external import semantic_scholar


def test_basic_retry():
    """Basic test that retry logic is invoked."""
    # Create client
    client = semantic_scholar.SemanticScholarClient()

    # Track calls
    call_count = [0]
    sleep_calls = []

    original_get = semantic_scholar.requests.get

    def mock_get(*args, **kwargs):
        call_count[0] += 1
        print(f"  Mock GET called (call #{call_count[0]})")

        # First call: return 429
        if call_count[0] == 1:
            response = Mock()
            response.status_code = 429
            print("  → Returning 429 error")
            return response

        # Second call: return success
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": []}
        print("  → Returning 200 success")
        return response

    def mock_sleep(seconds):
        sleep_calls.append(seconds)
        print(f"  Sleep called: {seconds}s")

    # Patch at the module level
    with patch.object(semantic_scholar.requests, 'get', side_effect=mock_get):
        with patch.object(semantic_scholar.time, 'sleep', side_effect=mock_sleep):
            print("\nCalling search_papers...")
            results = client.search_papers("test", limit=1)

            print(f"\nResults:")
            print(f"  API calls made: {call_count[0]}")
            print(f"  Sleep calls: {sleep_calls}")
            print(f"  Results returned: {len(results)} papers")

            if call_count[0] == 2:
                print("\n✅ SUCCESS: Retry logic worked! Made 2 API calls (1 fail + 1 retry)")
            else:
                print(f"\n❌ FAIL: Expected 2 calls, got {call_count[0]}")


if __name__ == "__main__":
    test_basic_retry()
