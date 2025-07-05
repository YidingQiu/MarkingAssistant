"""
Analysis module for the marking assistant.

This module contains tools for analyzing and extracting information from
marking pipeline results, including score extraction and data aggregation.
"""

from .score_extractor import ScoreExtractor, extract_scores_for_task, ModuleScore, StudentScoreSummary

__all__ = [
    'ScoreExtractor',
    'extract_scores_for_task', 
    'ModuleScore',
    'StudentScoreSummary'
] 