import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from decorators.throttle import throttle


class TestThrottleDecorator:
    """Test cases for the throttle decorator."""

    def test_sync_function_immediate_call(self):
        """Test that synchronous function is called immediately on first invocation."""
        mock_func = MagicMock(return_value="result")

        @throttle(1.0)
        def test_func():
            return mock_func()

        result = test_func()

        assert result == "result"
        mock_func.assert_called_once()

    def test_sync_function_throttling(self):
        """Test that synchronous function is throttled within interval."""
        mock_func = MagicMock()

        @throttle(0.5)
        def test_func():
            mock_func()

        # First call should execute immediately
        test_func()
        assert mock_func.call_count == 1

        # Second call within interval should not execute immediately
        test_func()
        assert mock_func.call_count == 1

        # Wait for trailing call
        time.sleep(0.6)
        assert mock_func.call_count == 2

    def test_sync_function_multiple_calls_within_interval(self):
        """Test multiple calls within throttle interval only trigger one trailing call."""
        mock_func = MagicMock()

        @throttle(0.3)
        def test_func():
            mock_func()

        # First call executes immediately
        test_func()
        assert mock_func.call_count == 1

        # Multiple calls within interval
        test_func()
        test_func()
        test_func()
        assert mock_func.call_count == 1  # Still only one call

        # Wait for trailing call
        time.sleep(0.4)
        assert mock_func.call_count == 2  # Only one trailing call

    def test_sync_function_calls_after_interval(self):
        """Test that calls after interval execute immediately."""
        mock_func = MagicMock()

        @throttle(0.2)
        def test_func():
            mock_func()

        # First call
        test_func()
        assert mock_func.call_count == 1

        # Wait for interval to pass
        time.sleep(0.25)

        # Second call should execute immediately
        test_func()
        assert mock_func.call_count == 2

    def test_sync_function_with_arguments(self):
        """Test that throttled function preserves arguments and return values."""
        mock_func = MagicMock()

        @throttle(0.1)
        def test_func(a, b, c=None):
            mock_func(a, b, c=c)
            return f"{a}-{b}-{c}"

        result = test_func("arg1", "arg2", c="kwarg")

        assert result == "arg1-arg2-kwarg"
        mock_func.assert_called_once_with("arg1", "arg2", c="kwarg")

    @pytest.mark.asyncio
    async def test_async_function_immediate_call(self):
        """Test that async function is called immediately on first invocation."""
        mock_func = MagicMock()

        @throttle(1.0)
        async def async_test_func():
            mock_func()
            return "async_result"

        result = await async_test_func()

        assert result == "async_result"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_function_throttling(self):
        """Test that async function is throttled within interval."""
        mock_func = MagicMock()

        @throttle(0.3)
        async def async_test_func():
            mock_func()

        # First call should execute immediately
        await async_test_func()
        assert mock_func.call_count == 1

        # Second call within interval should not execute immediately
        await async_test_func()
        assert mock_func.call_count == 1

        # Wait for trailing call
        await asyncio.sleep(0.4)
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_multiple_calls_within_interval(self):
        """Test multiple async calls within throttle interval only trigger one trailing call."""
        mock_func = MagicMock()

        @throttle(0.2)
        async def async_test_func():
            mock_func()

        # First call executes immediately
        await async_test_func()
        assert mock_func.call_count == 1

        # Multiple calls within interval
        await async_test_func()
        await async_test_func()
        await async_test_func()
        assert mock_func.call_count == 1  # Still only one call

        # Wait for trailing call
        await asyncio.sleep(0.3)
        assert mock_func.call_count == 2  # Only one trailing call

    @pytest.mark.asyncio
    async def test_async_function_calls_after_interval(self):
        """Test that async calls after interval execute immediately."""
        mock_func = MagicMock()

        @throttle(0.15)
        async def async_test_func():
            mock_func()

        # First call
        await async_test_func()
        assert mock_func.call_count == 1

        # Wait for interval to pass
        await asyncio.sleep(0.2)

        # Second call should execute immediately
        await async_test_func()
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_with_arguments(self):
        """Test that throttled async function preserves arguments and return values."""
        mock_func = MagicMock()

        @throttle(0.1)
        async def async_test_func(x, y, z=None):
            mock_func(x, y, z=z)
            return f"async-{x}-{y}-{z}"

        result = await async_test_func("a", "b", z="c")

        assert result == "async-a-b-c"
        mock_func.assert_called_once_with("a", "b", z="c")

    def test_function_detection(self):
        """Test that decorator correctly identifies sync vs async functions."""
        sync_func = MagicMock()
        async_func = MagicMock()

        @throttle(0.1)
        def sync_test():
            sync_func()

        @throttle(0.1)
        async def async_test():
            async_func()

        # Check that the wrapper types are correct
        assert not asyncio.iscoroutinefunction(sync_test)
        assert asyncio.iscoroutinefunction(async_test)

    def test_zero_interval(self):
        """Test throttle with zero interval."""
        mock_func = MagicMock()

        @throttle(0.0)
        def test_func():
            mock_func()

        # With zero interval, every call should execute
        test_func()
        test_func()
        test_func()

        # All calls should execute immediately
        assert mock_func.call_count == 3

    def test_very_short_interval(self):
        """Test throttle with very short interval."""
        mock_func = MagicMock()

        @throttle(0.01)  # 10ms
        def test_func():
            mock_func()

        test_func()
        assert mock_func.call_count == 1

        # Call again immediately
        test_func()
        assert mock_func.call_count == 1

        # Wait for short interval
        time.sleep(0.02)
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(self):
        """Test concurrent async calls to throttled function."""
        mock_func = MagicMock()
        call_times = []

        @throttle(0.2)
        async def async_test_func():
            call_times.append(time.time())
            mock_func()

        # Start multiple concurrent calls
        tasks = [async_test_func() for _ in range(5)]
        await asyncio.gather(*tasks)

        # Only first call should execute immediately
        assert mock_func.call_count == 1

        # Wait for trailing call
        await asyncio.sleep(0.3)
        assert mock_func.call_count == 2

        # Should have exactly 2 call times recorded
        assert len(call_times) == 2

    def test_threading_safety_sync(self):
        """Test that sync throttle is thread-safe."""
        mock_func = MagicMock()

        @throttle(0.2)
        def test_func():
            mock_func()

        def call_function():
            test_func()

        # Start multiple threads
        threads = [threading.Thread(target=call_function) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Only first call should execute immediately
        assert mock_func.call_count == 1

        # Wait for trailing call
        time.sleep(0.3)
        assert mock_func.call_count == 2

    def test_function_metadata_preservation(self):
        """Test that function metadata is preserved by the decorator."""

        @throttle(0.1)
        def test_func():
            """Test function docstring."""
            pass

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."

    @pytest.mark.asyncio
    async def test_async_function_metadata_preservation(self):
        """Test that async function metadata is preserved by the decorator."""

        @throttle(0.1)
        async def async_test_func():
            """Async test function docstring."""
            pass

        assert async_test_func.__name__ == "async_test_func"
        assert async_test_func.__doc__ == "Async test function docstring."

    def test_exception_handling_sync(self):
        """Test that exceptions in sync functions are properly propagated."""

        @throttle(0.1)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_func()

    @pytest.mark.asyncio
    async def test_exception_handling_async(self):
        """Test that exceptions in async functions are properly propagated."""

        @throttle(0.1)
        async def failing_async_func():
            raise ValueError("Async test error")

        with pytest.raises(ValueError, match="Async test error"):
            await failing_async_func()

    def test_large_interval(self):
        """Test throttle with large interval."""
        mock_func = MagicMock()

        @throttle(10.0)  # 10 seconds
        def test_func():
            mock_func()

        # First call executes immediately
        test_func()
        assert mock_func.call_count == 1

        # Second call should be throttled
        test_func()
        assert mock_func.call_count == 1

        # Trailing call would happen after 10 seconds (we won't wait for it in test)

    @pytest.mark.asyncio
    async def test_async_exception_in_trailing_call(self):
        """Test that exceptions in async trailing calls are handled gracefully."""
        call_count = 0

        @throttle(0.1)
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on trailing call
                raise ValueError("Trailing call error")

        # First call should succeed
        await test_func()
        assert call_count == 1

        # Second call triggers trailing call
        await test_func()
        assert call_count == 1

        # Wait for trailing call (it will fail but shouldn't crash the test)
        await asyncio.sleep(0.15)
        assert call_count == 2  # Trailing call was attempted

    def test_sync_exception_in_trailing_call(self):
        """Test that exceptions in sync trailing calls are handled gracefully."""
        call_count = 0

        @throttle(0.1)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on trailing call
                raise ValueError("Sync trailing call error")

        # First call should succeed
        test_func()
        assert call_count == 1

        # Second call triggers trailing call
        test_func()
        assert call_count == 1

        # Wait for trailing call (it will fail but shouldn't crash the test)
        time.sleep(0.15)
        assert call_count == 2  # Trailing call was attempted
