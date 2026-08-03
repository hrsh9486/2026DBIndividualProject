"""
calculate_etf_correlations.py

Correlation analysis for Indian ETFs against global ETFs.

Inputs
------
returns : pd.DataFrame
    DataFrame of daily (or log) returns with columns corresponding to ETFs.

Example Columns
---------------
NIFTY
SENSEX
BANKNIFTY
SP500
NASDAQ100
FTSE100
HSI
BVSP

Outputs
-------
All functions return either a pandas DataFrame, pandas Series,
or a nested dictionary of pandas Series suitable for further processing.
"""

from __future__ import annotations

import pandas as pd


# ============================================================================
# Correlation Matrices
# ============================================================================

def pearson_correlation(
    returns: pd.DataFrame,
    indian_markets: list[str],
    global_markets: list[str],
) -> pd.DataFrame:
    """
    Pearson correlation between Indian and global markets.
    """

    corr = returns.corr(method="pearson")

    return corr.loc[indian_markets, global_markets]


def spearman_correlation(
    returns: pd.DataFrame,
    indian_markets: list[str],
    global_markets: list[str],
) -> pd.DataFrame:
    """
    Spearman rank correlation between Indian and global markets.
    """

    corr = returns.corr(method="spearman")

    return corr.loc[indian_markets, global_markets]


def kendall_correlation(
    returns: pd.DataFrame,
    indian_markets: list[str],
    global_markets: list[str],
) -> pd.DataFrame:
    """
    Kendall Tau correlation between Indian and global markets.
    """

    corr = returns.corr(method="kendall")

    return corr.loc[indian_markets, global_markets]


# ============================================================================
# Rolling Correlations
# ============================================================================

def rolling_pearson(
    returns: pd.DataFrame,
    indian_markets: list[str],
    global_markets: list[str],
    window: int = 90,
) -> dict[str, dict[str, pd.Series]]:
    """
    Rolling Pearson correlation.
    """

    output = {}

    for indian in indian_markets:

        output[indian] = {}

        for global_market in global_markets:

            output[indian][global_market] = (
                returns[indian]
                .rolling(window)
                .corr(
                    returns[global_market]
                )
                .dropna()
            )

    return output


# ============================================================================
# Correlation Stability
# ============================================================================

def correlation_stability(
    rolling_correlations: dict[str, dict[str, pd.Series]]
) -> pd.DataFrame:
    """
    Statistics describing the stability of rolling correlations.
    """

    rows = []

    for indian in rolling_correlations:

        for global_market in rolling_correlations[indian]:

            series = rolling_correlations[indian][global_market]

            rows.append({

                "Indian Market": indian,

                "Global Market": global_market,

                "Mean Correlation": series.mean(),

                "Std Correlation": series.std(),

                "Min Correlation": series.min(),

                "Max Correlation": series.max(),

            })

    return pd.DataFrame(rows).dropna()


# ============================================================================
# Average Correlations
# ============================================================================

def average_correlations(
    correlation_matrix: pd.DataFrame,
) -> pd.Series:
    """
    Average correlation for each Indian market across all global markets.
    """

    return correlation_matrix.mean(axis=1)


def average_global_correlations(
    correlation_matrix: pd.DataFrame,
) -> pd.Series:
    """
    Average correlation for each global market across all Indian markets.
    """

    return correlation_matrix.mean(axis=0).dropna()


# ============================================================================
# Maximum / Minimum Correlations
# ============================================================================

def strongest_global_market(
    correlation_matrix: pd.DataFrame,
) -> pd.DataFrame:
    """
    Strongest correlated global market for each Indian market.
    """

    rows = []

    for indian in correlation_matrix.index:

        market = correlation_matrix.loc[indian].idxmax()

        value = correlation_matrix.loc[indian].max()

        rows.append({

            "Indian Market": indian,

            "Global Market": market,

            "Correlation": value,

        })

    return pd.DataFrame(rows).dropna()


def weakest_global_market(
    correlation_matrix: pd.DataFrame,
) -> pd.DataFrame:
    """
    Weakest correlated global market for each Indian market.
    """

    rows = []

    for indian in correlation_matrix.index:

        market = correlation_matrix.loc[indian].idxmin()

        value = correlation_matrix.loc[indian].min()

        rows.append({

            "Indian Market": indian,

            "Global Market": market,

            "Correlation": value,

        })

    return pd.DataFrame(rows).dropna()


# ============================================================================
# Correlation Rankings
# ============================================================================

def ranked_global_markets(
    correlation_matrix: pd.DataFrame,
) -> dict[str, pd.Series]:
    """
    Rank global markets by correlation for each Indian market.
    """

    rankings = {}

    for indian in correlation_matrix.index:

        rankings[indian] = (
            correlation_matrix
            .loc[indian]
            .sort_values(
                ascending=False
            )
        )

    return rankings


def ranked_indian_markets(
    correlation_matrix: pd.DataFrame,
) -> dict[str, pd.Series]:
    """
    Rank Indian markets by correlation for each global market.
    """

    rankings = {}

    for global_market in correlation_matrix.columns:

        rankings[global_market] = (
            correlation_matrix
            .loc[:, global_market]
            .sort_values(
                ascending=False
            )
        )

    return rankings


# ============================================================================
# Correlation Difference
# ============================================================================

def correlation_spread(
    correlation_matrix: pd.DataFrame,
) -> pd.Series:
    """
    Difference between strongest and weakest correlation
    for each Indian market.
    """

    return (
        correlation_matrix.max(axis=1)
        - correlation_matrix.min(axis=1)
    )


# ============================================================================
# Volatility of Rolling Correlations
# ============================================================================

def rolling_correlation_volatility(
    rolling_correlations: dict[str, dict[str, pd.Series]]
) -> pd.DataFrame:
    """
    Standard deviation of rolling correlations.
    """

    rows = []

    for indian in rolling_correlations:

        for global_market in rolling_correlations[indian]:

            series = rolling_correlations[indian][global_market]

            rows.append({

                "Indian Market": indian,

                "Global Market": global_market,

                "Rolling Correlation Volatility": series.std()

            })

    return pd.DataFrame(rows).dropna()


# ============================================================================
# Correlation Trend
# ============================================================================

def latest_rolling_correlations(
    rolling_correlations: dict[str, dict[str, pd.Series]]
) -> pd.DataFrame:
    """
    Latest available rolling correlation.
    """

    rows = []

    for indian in rolling_correlations:

        for global_market in rolling_correlations[indian]:

            series = rolling_correlations[indian][global_market]

            rows.append({

                "Indian Market": indian,

                "Global Market": global_market,

                "Latest Correlation": series.iloc[-1]

            })

    return pd.DataFrame(rows).dropna()