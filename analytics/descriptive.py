import numpy as np
import pandas as pd
from scipy import stats

from config import IQR_FACTOR

QUARTILE_POSITIONS = [0.25, 0.5, 0.75]
SYMMETRIC_SKEW_LIMIT = 0.5
MODERATE_SKEW_LIMIT = 1


def valid_values(series):
    numeric_values = pd.to_numeric(series, errors="coerce").astype(float)
    return numeric_values.loc[np.isfinite(numeric_values)]


def iqr_details(series, factor=IQR_FACTOR):
    values = valid_values(series)

    if len(values):
        q1, median, q3 = values.quantile(
            QUARTILE_POSITIONS, interpolation="linear"
        ).tolist()
    else:
        q1 = median = q3 = np.nan

    interquartile_range = q3 - q1
    lower_limit = q1 - factor * interquartile_range
    upper_limit = q3 + factor * interquartile_range

    is_outlier = (values < lower_limit) | (values > upper_limit)
    values_inside_limits = values.loc[~is_outlier]

    return {
        "q1": q1,
        "median": median,
        "q3": q3,
        "iqr": interquartile_range,
        "lower": lower_limit,
        "upper": upper_limit,
        "whisker_low": values_inside_limits.min(),
        "whisker_high": values_inside_limits.max(),
        "outlier_mask": is_outlier,
        "outliers": values.loc[is_outlier],
    }


def classify_skew_direction(skew):
    if not np.isfinite(skew):
        return "indefinida"
    if skew > 0:
        return "positiva (direita)"
    if skew < 0:
        return "negativa (esquerda)"
    return "simétrica"


def classify_skew_intensity(skew):
    if not np.isfinite(skew):
        return "indefinida"
    if abs(skew) < SYMMETRIC_SKEW_LIMIT:
        return "aproximadamente simétrica"
    if abs(skew) < MODERATE_SKEW_LIMIT:
        return "moderada"
    return "forte"


def compute_skew(values):
    has_enough_values = len(values) >= 3
    has_variation = values.nunique() > 1
    if has_enough_values and has_variation:
        return float(stats.skew(values, bias=False))
    return np.nan


def informative_modes(values):
    modes = values.mode().tolist()
    every_value_is_a_mode = len(modes) == len(values)
    return [] if every_value_is_a_mode else modes


def describe_series(series, factor=IQR_FACTOR):
    values = valid_values(series)
    count = len(values)
    iqr_summary = iqr_details(values, factor)

    mean = values.mean()
    sample_std = values.std(ddof=1)
    median = iqr_summary["median"]
    skew = compute_skew(values)

    coefficient_of_variation = (
        100 * sample_std / mean if count > 1 and mean > 0 else np.nan
    )
    iqr_to_median_ratio = (
        iqr_summary["iqr"] / median if median > 0 else np.nan
    )

    return {
        **iqr_summary,
        "n": count,
        "missing": len(series) - count,
        "mean": mean,
        "modes": informative_modes(values),
        "min": values.min(),
        "max": values.max(),
        "range": values.max() - values.min(),
        "std": sample_std,
        "variance": values.var(ddof=1),
        "cv": coefficient_of_variation,
        "robust_ratio": iqr_to_median_ratio,
        "skew": skew,
        "direction": classify_skew_direction(skew),
        "intensity": classify_skew_intensity(skew),
        "outlier_count": int(iqr_summary["outlier_mask"].sum()),
    }


def describe_by_team(dataframe, variables, teams, factor=IQR_FACTOR):
    summaries = {}
    for team_id in teams:
        team_rows = dataframe.loc[dataframe["time_id"] == team_id]
        for variable in variables:
            summaries[(team_id, variable)] = describe_series(
                team_rows[variable], factor
            )
    return summaries


def standardized_team_means(dataframe, variable, team_ids):
    joint_values = valid_values(dataframe[variable])
    joint_mean = joint_values.mean()
    joint_std = joint_values.std(ddof=1)

    means_by_team = {}
    for team_id in team_ids:
        team_values = valid_values(
            dataframe.loc[dataframe["time_id"] == team_id, variable]
        )
        if joint_std > 0:
            z_scores = (team_values - joint_mean) / joint_std
            means_by_team[team_id] = float(z_scores.mean())
        else:
            means_by_team[team_id] = np.nan

    reference = {"mean": joint_mean, "std": joint_std, "n": len(joint_values)}
    return means_by_team, reference
