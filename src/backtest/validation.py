"""Validation methodologies: Purged/Embargoed Walk-Forward and Multiple Testing Corrections."""
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class WalkForwardSplit:
    fold: int
    train_indices: List[int]
    test_indices: List[int]
    purged_count: int
    embargoed_count: int


def purged_walk_forward_splits(
    n_samples: int,
    train_size: int,
    test_size: int,
    purge_size: int = 5,
    embargo_size: int = 5,
    step_size: Optional[int] = None,
) -> List[WalkForwardSplit]:
    """Generate purged and embargoed walk-forward cross-validation splits (de Prado methodology).
    
    Purging removes training observations immediately preceding test labels to prevent label overlap.
    Embargoing removes training observations immediately following test sets to prevent autoregressive leakage.
    """
    step = step_size or test_size
    splits: List[WalkForwardSplit] = []
    start = 0
    fold = 1

    while start + train_size + purge_size + test_size <= n_samples:
        train_end = start + train_size
        test_start = train_end + purge_size
        test_end = test_start + test_size

        train_indices = list(range(start, train_end))
        test_indices = list(range(test_start, test_end))

        splits.append(
            WalkForwardSplit(
                fold=fold,
                train_indices=train_indices,
                test_indices=test_indices,
                purged_count=purge_size,
                embargoed_count=embargo_size,
            )
        )
        fold += 1
        start += step

    return splits


def benjamini_hochberg_fdr(p_values: List[float], alpha: float = 0.05) -> Tuple[List[bool], float]:
    """Benjamini-Hochberg False Discovery Rate (FDR) procedure.
    
    Controls expected proportion of false discoveries when testing multiple alpha strategies.
    Returns:
        (is_significant, critical_p_value_threshold)
    """
    m = len(p_values)
    if m == 0:
        return [], 0.0

    # Sort p-values with original indices
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    
    # Find largest k such that P_(k) <= (k / m) * alpha
    max_k = -1
    threshold = 0.0

    for rank, (orig_idx, p_val) in enumerate(indexed, start=1):
        crit = (rank / m) * alpha
        if p_val <= crit:
            max_k = rank
            threshold = p_val

    is_significant = [False] * m
    if max_k > 0:
        for r in range(max_k):
            orig_idx = indexed[r][0]
            is_significant[orig_idx] = True

    return is_significant, threshold


def holm_bonferroni_correction(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """Holm-Bonferroni step-down Family-Wise Error Rate (FWER) correction.
    
    More powerful than standard Bonferroni while guaranteeing strong FWER control.
    """
    m = len(p_values)
    if m == 0:
        return []

    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    is_significant = [False] * m

    for rank, (orig_idx, p_val) in enumerate(indexed, start=1):
        crit = alpha / (m - rank + 1)
        if p_val <= crit:
            is_significant[orig_idx] = True
        else:
            # Step down stops at first failure
            break

    return is_significant
