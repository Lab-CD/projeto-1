import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.neighbors import LocalOutlierFactor, NearestNeighbors
from sklearn.preprocessing import StandardScaler

from analytics.descriptive import iqr_details, valid_values
from config import (
    CONTAMINATION,
    DBSCAN_EPS,
    DBSCAN_MIN_SAMPLES,
    GRUBBS_ALPHA,
    IQR_FACTOR,
    KNN_NEIGHBORS,
    LOF_NEIGHBORS,
    ZSCORE_LIMIT,
)

METHODS = {
    "iqr": "IQR / Boxplot",
    "zscore": "Z-score",
    "grubbs": "Grubbs",
    "ecod": "ECOD",
    "knn": "KNN",
    "dbscan": "DBSCAN",
    "lof": "LOF",
}

DENSITY_BASED_METHODS = {"ecod", "knn", "lof", "dbscan"}
KNN_SCORE_PERCENTILE = 0.95
SCALING_DESCRIPTION = "StandardScaler, ddof=0"
SHAPIRO_MAX_SAMPLE_SIZE = 5000
SHAPIRO_SIGNIFICANCE_LEVEL = 0.05


def _empty_detection(values, flag_default=False):
    scores = pd.Series(np.nan, index=values.index, dtype=float)
    flags = pd.Series(flag_default, index=values.index)
    return scores, flags


def _detect_with_iqr(values, parameters):
    factor = parameters.get("factor", IQR_FACTOR)
    details = iqr_details(values, factor)
    scores = (values - values.median()).abs()
    notes = []

    if details["iqr"] == 0:
        notes.append(
            "IQR zero: qualquer valor fora do intervalo central degenerado "
            "é sinalizado pela regra."
        )

    return {
        "scores": scores,
        "flags": details["outlier_mask"],
        "parameters": {"k": factor, "quartis": "interpolação linear"},
        "threshold": (details["lower"], details["upper"]),
        "notes": notes,
    }


def _detect_with_zscore(values, parameters):
    limit = parameters.get("limit", ZSCORE_LIMIT)
    scores = ((values - values.mean()) / values.std(ddof=1)).abs()

    return {
        "scores": scores,
        "flags": scores > limit,
        "parameters": {"ddof": 1, "limiar |z|": limit},
        "threshold": limit,
        "notes": [],
    }


def _grubbs_critical_value(sample_size, alpha):
    t_quantile = stats.t.ppf(1 - alpha / (2 * sample_size), sample_size - 2)
    t_squared = t_quantile * t_quantile
    return (
        (sample_size - 1) / np.sqrt(sample_size)
        * np.sqrt(t_squared / (sample_size - 2 + t_squared))
    )


def _detect_with_grubbs(values, parameters):
    alpha = parameters.get("alpha", GRUBBS_ALPHA)
    sample_size = len(values)

    scores = ((values - values.mean()) / values.std(ddof=1)).abs()
    critical_value = _grubbs_critical_value(sample_size, alpha)

    _, flags = _empty_detection(values)
    most_extreme_row = scores.idxmax()
    if scores.loc[most_extreme_row] > critical_value:
        flags.loc[most_extreme_row] = True

    shapiro_p_value = None
    if sample_size <= SHAPIRO_MAX_SAMPLE_SIZE:
        shapiro_p_value = float(stats.shapiro(values).pvalue)

    notes = [
        "Teste de um único extremo, sem remoção iterativa. Pressupõe normalidade "
        "aproximada e independência; testes entre séries são exploratórios."
    ]
    status = None
    rejects_normality = (
        shapiro_p_value is not None and shapiro_p_value < SHAPIRO_SIGNIFICANCE_LEVEL
    )
    if rejects_normality:
        status = "exploratório"
        notes.append(
            "Shapiro–Wilk rejeita normalidade a 5%; interpretar Grubbs com ressalva, "
            "especialmente para contagens discretas."
        )

    return {
        "scores": scores,
        "flags": flags,
        "parameters": {
            "alpha": alpha,
            "bilateral": True,
            "candidatos": 1,
            "p Shapiro–Wilk": shapiro_p_value,
        },
        "threshold": float(critical_value),
        "notes": notes,
        "status": status,
    }


def _detect_with_ecod(values, parameters):
    contamination = parameters.get("contamination", CONTAMINATION)
    data = values.to_numpy(dtype=float)
    ordered = np.sort(data)
    left = -np.log(np.searchsorted(ordered, data, side="right") / len(data))
    right = -np.log((len(data) - np.searchsorted(ordered, data, side="left")) / len(data))
    skew = np.sign(np.nan_to_num(stats.skew(data)))
    skew_score = left * -np.sign(skew - 1) + right * np.sign(skew + 1)
    scores = pd.Series(np.maximum(np.maximum(left, right), skew_score), index=values.index)
    threshold = float(np.percentile(scores, 100 * (1 - contamination)))

    return {
        "scores": scores,
        "flags": scores > threshold,
        "parameters": {"contamination": contamination},
        "threshold": threshold,
        "notes": [
            "A fração de contaminação define o limiar exploratório; não estima a "
            "proporção verdadeira de erros. Empates podem alterar a quantidade sinalizada."
        ],
    }


def _distance_to_kth_other_neighbor(distances, neighbor_indices, neighbors_wanted):
    kth_distances = []
    for row_position, (row_distances, row_neighbors) in enumerate(
        zip(distances, neighbor_indices)
    ):
        is_other_point = row_neighbors != row_position
        kth_distances.append(row_distances[is_other_point][:neighbors_wanted][-1])
    return kth_distances


def _detect_with_knn(values, scaled_values, parameters):
    neighbors_wanted = min(parameters.get("neighbors", KNN_NEIGHBORS), len(values) - 1)

    nearest_neighbors = NearestNeighbors(n_neighbors=neighbors_wanted + 1)
    distances, neighbor_indices = nearest_neighbors.fit(scaled_values).kneighbors(
        scaled_values
    )

    kth_distances = _distance_to_kth_other_neighbor(
        distances, neighbor_indices, neighbors_wanted
    )
    scores = pd.Series(kth_distances, index=values.index)
    threshold = float(scores.quantile(KNN_SCORE_PERCENTILE, interpolation="linear"))

    return {
        "scores": scores,
        "flags": scores > threshold,
        "parameters": {
            "k": neighbors_wanted,
            "limiar": "percentil 95 linear",
            "escala": SCALING_DESCRIPTION,
        },
        "threshold": threshold,
        "notes": [
            "Distância ao k-ésimo outro vizinho; sinalização estrita acima do "
            "percentil 95, sem forçar quantidade de extremos."
        ],
    }


def _detect_with_dbscan(values, scaled_values, parameters):
    eps = parameters.get("eps", DBSCAN_EPS)
    min_samples = parameters.get("min_samples", DBSCAN_MIN_SAMPLES)

    cluster_labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(scaled_values)
    scores, _ = _empty_detection(values)

    return {
        "scores": scores,
        "flags": pd.Series(cluster_labels == -1, index=values.index),
        "parameters": {
            "eps": eps,
            "min_samples": min_samples,
            "escala": SCALING_DESCRIPTION,
        },
        "threshold": "rótulo −1 (ruído)",
        "notes": [
            "Não há escore contínuo nativo nesta saída; ruído depende da escolha "
            "de eps e min_samples."
        ],
    }


def _detect_with_lof(values, scaled_values, parameters):
    neighbors_used = min(parameters.get("neighbors", LOF_NEIGHBORS), len(values) - 1)

    with warnings.catch_warnings(record=True) as captured_warnings:
        warnings.simplefilter("always", UserWarning)
        model = LocalOutlierFactor(n_neighbors=neighbors_used, contamination="auto")
        predicted_labels = model.fit_predict(scaled_values)

    scores = pd.Series(-model.negative_outlier_factor_, index=values.index)

    return {
        "scores": scores,
        "flags": pd.Series(predicted_labels == -1, index=values.index),
        "parameters": {
            "n_neighbors": neighbors_used,
            "contamination": "auto",
            "escala": SCALING_DESCRIPTION,
        },
        "threshold": float(-model.offset_),
        "notes": [str(warning.message) for warning in captured_warnings],
    }


def _run_method(method, values, parameters):
    column_of_values = values.to_numpy(dtype=float).reshape(-1, 1)
    scaled_values = StandardScaler().fit_transform(column_of_values)

    if method == "iqr":
        return _detect_with_iqr(values, parameters)
    if method == "zscore":
        return _detect_with_zscore(values, parameters)
    if method == "grubbs":
        return _detect_with_grubbs(values, parameters)
    if method == "ecod":
        return _detect_with_ecod(values, parameters)
    if method == "knn":
        return _detect_with_knn(values, scaled_values, parameters)
    if method == "dbscan":
        return _detect_with_dbscan(values, scaled_values, parameters)
    return _detect_with_lof(values, scaled_values, parameters)


def detect_outliers(series, method, parameters=None):
    if method not in METHODS:
        raise ValueError(f"Método desconhecido: {method}")

    parameters = parameters or {}
    values = valid_values(series)
    sample_size = len(values)
    scores, flags = _empty_detection(values)

    result = {
        "method": method,
        "name": METHODS[method],
        "n": sample_size,
        "status": "calculado",
        "notes": [],
        "parameters": {},
        "threshold": None,
    }

    minimum_sample_size = 3 if method == "grubbs" else 2
    is_applicable = sample_size >= minimum_sample_size and values.nunique() >= 2

    if not is_applicable:
        result["status"] = "não aplicável"
        result["notes"].append(
            f"Exige pelo menos {minimum_sample_size} valores válidos e variabilidade."
        )
    else:
        outcome = _run_method(method, values, parameters)
        scores = outcome["scores"]
        flags = outcome["flags"]
        result["parameters"] = outcome["parameters"]
        result["threshold"] = outcome["threshold"]
        result["notes"].extend(outcome["notes"])
        if outcome.get("status"):
            result["status"] = outcome["status"]

        has_few_distinct_values = values.nunique() < min(sample_size, 10)
        if has_few_distinct_values and method in DENSITY_BASED_METHODS:
            result["notes"].append(
                "Poucos valores distintos: empates e discretização podem tornar a "
                "separação por densidade pouco informativa."
            )

    result["rows"] = pd.DataFrame({
        "valor": values,
        "escore": scores,
        "sinalizado": flags,
    })
    result["count"] = int(flags.sum()) if result["status"] != "não aplicável" else None
    return result
