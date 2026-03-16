import time
from reporting.models import AnalysisReport


def analyze_optimization(report: AnalysisReport, slow_func, optimized_func):
    slow_time = None
    optimized_time = None

    try:
        start = time.perf_counter()
        slow_func()
        slow_time = time.perf_counter() - start
    except Exception:
        return report

    try:
        start = time.perf_counter()
        optimized_func()
        optimized_time = time.perf_counter() - start
    except Exception:
        return report

    if optimized_time < slow_time:
        improvement = slow_time - optimized_time
        percent = (improvement / slow_time) * 100

        report.optimization_status = "performance improvement detected"
        report.optimization_notes = [
            f"Original runtime: {slow_time:.6f} seconds",
            f"Optimized runtime: {optimized_time:.6f} seconds",
            f"Estimated improvement: {percent:.2f}% faster",
        ]
    else:
        report.optimization_status = "no performance improvement detected"
        report.optimization_notes = [
            f"Original runtime: {slow_time:.6f} seconds",
            f"Optimized runtime: {optimized_time:.6f} seconds",
        ]

    return report