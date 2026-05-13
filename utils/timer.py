# utils/timer.py

import time
import logging
import functools

# ── Logger setup ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TIMER] %(message)s",
    handlers=[
        logging.FileHandler("pipeline_timing.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
timer_log = logging.getLogger("timer")

# ── Global registry to collect all timings ───────────────────
_timing_registry = []

def get_all_timings():
    return _timing_registry

def reset_timings():
    _timing_registry.clear()

# ── Decorator ─────────────────────────────────────────────────
def timed(func):
    """
    Decorator — wraps any function and logs how long it took.
    Usage: @timed above any function definition.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start  = time.perf_counter()
        result = func(*args, **kwargs)
        end    = time.perf_counter()
        elapsed = end - start

        entry = {
            "function" : func.__name__,
            "elapsed_s": round(elapsed, 3),
            "elapsed"  : f"{elapsed:.2f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        }

        _timing_registry.append(entry)
        timer_log.info(f"{func.__name__:<40} -> {entry['elapsed']}")

        return result
    return wrapper

# ── Context manager for inline blocks ─────────────────────────
class Timer:
    """
    Use for timing a block of code without a decorator.
    with Timer("fetch_zerodha"):
        data = fetch_zerodha()
    """
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self.start
        entry = {
            "function" : self.label,
            "elapsed_s": round(elapsed, 3),
            "elapsed"  : f"{elapsed:.2f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
        }
        _timing_registry.append(entry)
        timer_log.info(f"{self.label:<40} → {entry['elapsed']}")

# ── Summary printer ───────────────────────────────────────────
def print_timing_summary():
    timings = get_all_timings()
    if not timings:
        print("No timings recorded.")
        return

    total = sum(t["elapsed_s"] for t in timings)
    print("\n" + "="*55)
    print(f"{'FUNCTION':<40} {'TIME':>10}")
    print("="*55)
    for t in timings:
        bar = "█" * min(int(t["elapsed_s"] / max(total,1) * 30), 30)
        print(f"{t['function']:<40} {t['elapsed']:>10}  {bar}")
    print("-"*55)
    print(f"{'TOTAL':<40} {total:>9.2f}s")
    print("="*55 + "\n")