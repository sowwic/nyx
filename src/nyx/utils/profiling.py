"""
Drop-in module combining:
  - codetiming.Timer  -> lightweight, always-on per-call timing (cheap, safe for prod)
  - cProfile/pstats   -> deterministic call profiling, gated behind NYX_PROFILING env var

Usage:
    from nyx.utils.profiling import profile

    @profile()   # writes my_function_profile.pstats when NYX_PROFILING=1
    def my_function():
        ...

Env vars:
    NYX_PROFILING       -> "1"/"true"/"yes" to enable profiling (default: off)
"""

import cProfile
import logging
import threading
from functools import wraps

from codetiming import Timer

from ..static.vars import PROFILING
from ..static.paths import PROFILING_DIR

LOGGER = logging.getLogger("NyxProfiler")
_LOCAL_THREAD = threading.local()


def profile(name=None, text="{name}: {seconds:.4f}s"):
    """Always logs timing; additionally dumps a pstats file under PROFILING_DIR."""

    def decorator(func):
        timer_name = name or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            with Timer(name=timer_name, text=text, logger=LOGGER.info):
                if not PROFILING:
                    return func(*args, **kwargs)

                PROFILING_DIR.mkdir(exist_ok=True)
                # Skip if a profiler is already running in this thread (nested call)
                if getattr(_LOCAL_THREAD, "active", False):
                    return func(*args, **kwargs)

                profiler = cProfile.Profile()
                _LOCAL_THREAD.active = True
                try:
                    result = profiler.runcall(func, *args, **kwargs)
                finally:
                    _LOCAL_THREAD.active = False

                path = PROFILING_DIR / f"{func.__name__}_profile.pstats"
                profiler.dump_stats(path)
                LOGGER.info('snakeviz "%s"', path)

                return result

        return wrapper

    return decorator
