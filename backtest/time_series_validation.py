"""Compatibility wrapper for time_series_validation module.

Provides top-level access to the utilities located in backtest.core.time_series_validation
so tests importing `time_series_validation` can find the expected functions.
"""
from core.time_series_validation import *  # noqa: F401,F403
