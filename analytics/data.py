import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from analytics.schema import NUMERIC, RENAME, SCHEMA

MISSING_VALUE_TOKENS = ["", "NA", "N/A", "NaN", "nan", "null", "NULL", "None"]
WHOLE_NUMBER_KINDS = {"contagem", "contagem acumulada", "binária"}
DATE_FORMAT = "%Y-%m-%d"
FIRST_DATA_ROW_IN_CSV = 2


def load_dataset(csv_path):
    csv_path = Path(csv_path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Base não encontrada: {csv_path}. Consulte o README.")

    dataset = pd.read_csv(
        csv_path,
        dtype="string",
        encoding="utf-8-sig",
        keep_default_na=False,
    )

    missing_columns = set(RENAME) - set(dataset.columns)
    if missing_columns:
        raise ValueError(
            f"Colunas obrigatórias ausentes: {', '.join(sorted(missing_columns))}"
        )

    dataset.index = pd.Index(
        np.arange(FIRST_DATA_ROW_IN_CSV, len(dataset) + FIRST_DATA_ROW_IN_CSV),
        name="linha_csv",
    )
    return dataset


def _convert_to_numeric(raw_column, kind):
    converted = pd.to_numeric(raw_column, errors="coerce").astype("Float64")

    if kind not in WHOLE_NUMBER_KINDS:
        return converted

    present_values = converted.dropna()
    all_values_are_whole = (
        np.isfinite(present_values.to_numpy(dtype=float)).all()
        and present_values.mod(1).eq(0).all()
    )
    if all_values_are_whole:
        return converted.astype("Int64")
    return converted


def _convert_column(raw_column, name, kind):
    if name in NUMERIC:
        return _convert_to_numeric(raw_column, kind)
    if kind == "data":
        return pd.to_datetime(raw_column, format=DATE_FORMAT, errors="coerce")
    if kind == "categórica":
        return raw_column.astype("category")
    return raw_column


def prepare_dataset(original_dataset, teams):
    is_selected_team = original_dataset["Team_ID"].str.strip().isin(teams)
    selected_rows = original_dataset.loc[is_selected_team].copy()
    if selected_rows.empty:
        raise ValueError("A base não contém registros das equipes configuradas.")

    raw_dataset = selected_rows.rename(columns=RENAME).loc[:, list(SCHEMA)].copy()
    raw_dataset = raw_dataset.apply(lambda column: column.str.strip())
    raw_dataset = raw_dataset.replace(MISSING_VALUE_TOKENS, pd.NA)

    prepared_dataset = raw_dataset.copy()
    conversion_log = []

    for name, metadata in SCHEMA.items():
        raw_column = raw_dataset[name]
        prepared_dataset[name] = _convert_column(raw_column, name, metadata["kind"])

        conversion_failures = int(
            (raw_column.notna() & prepared_dataset[name].isna()).sum()
        )
        conversion_log.append({
            "Original": metadata["original"],
            "Nome interno": name,
            "Tipo inicial": "texto (leitura preservada)",
            "Tipo final": str(prepared_dataset[name].dtype),
            "Valores presentes": int(raw_column.notna().sum()),
            "Falhas de conversão": conversion_failures,
        })

    return raw_dataset, prepared_dataset, pd.DataFrame(conversion_log)


def source_metadata(csv_path, original_dataset, prepared_dataset):
    csv_path = Path(csv_path)
    game_dates = prepared_dataset["data_partida"].dropna()

    return {
        "filename": csv_path.name,
        "sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "bytes": csv_path.stat().st_size,
        "original_rows": len(original_dataset),
        "original_columns": len(original_dataset.columns),
        "original_teams": original_dataset["Team_ID"].nunique(),
        "rows": len(prepared_dataset),
        "columns": len(prepared_dataset.columns),
        "games": prepared_dataset["partida_id"].nunique(),
        "teams": prepared_dataset["time_id"].nunique(),
        "date_min": game_dates.min() if not game_dates.empty else None,
        "date_max": game_dates.max() if not game_dates.empty else None,
        "memory_bytes": int(prepared_dataset.memory_usage(deep=True).sum()),
    }
