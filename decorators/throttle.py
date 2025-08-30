import time
import asyncio
from functools import wraps


def throttle(interval: float):
    """
    Throttle decorator: ensures the function executes immediately on the first call (leading)
    and is called one last time (trailing) after the `interval`.
    Supports both synchronous and asynchronous functions.
    """

    def decorator(func):
        last_called = {"time": 0.0}
        trailing_call = {"scheduled": False}
        lock = asyncio.Lock()

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with lock:
                now = time.time()
                if now - last_called["time"] >= interval:
                    # Call immediately if interval has passed
                    last_called["time"] = now
                    return await func(*args, **kwargs)
                elif not trailing_call["scheduled"]:
                    # Schedule the trailing call if not already scheduled
                    trailing_call["scheduled"] = True

                    async def call_later():
                        await asyncio.sleep(interval - (now - last_called["time"]))
                        async with lock:
                            last_called["time"] = time.time()
                            trailing_call["scheduled"] = False
                            await func(*args, **kwargs)

                    asyncio.create_task(call_later())

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            now = time.time()
            if now - last_called["time"] >= interval:
                # Call immediately if interval has passed
                last_called["time"] = now
                return func(*args, **kwargs)
            elif not trailing_call["scheduled"]:
                # Schedule the trailing call if not already scheduled
                trailing_call["scheduled"] = True

                def call_later():
                    time.sleep(interval - (now - last_called["time"]))
                    last_called["time"] = time.time()
                    trailing_call["scheduled"] = False
                    func(*args, **kwargs)

                import threading

                threading.Thread(target=call_later).start()

        # Return the appropriate wrapper based on whether func is async or sync
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
