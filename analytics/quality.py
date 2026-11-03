import numpy as np
import pandas as pd

from analytics.descriptive import iqr_details
from analytics.schema import MEASUREMENTS, NUMERIC, SCHEMA

ISSUE_COLUMNS = ["Linha CSV", "Time", "Partida", "Coluna", "Valor original", "Regra"]
RATIO_TOLERANCE = 0.00050001
REQUIRED_COLUMNS = {"time_id", "partida_id", "time", "data_partida"}

SHOT_RATIO_COLUMNS = [
    ("arremessos_quadra_convertidos", "arremessos_quadra_tentados", "aproveitamento_quadra"),
    ("cestas_tres_convertidas", "cestas_tres_tentadas", "aproveitamento_tres"),
    ("lances_livres_convertidos", "lances_livres_tentados", "aproveitamento_lance_livre"),
]

MADE_NOT_GREATER_THAN_ATTEMPTED = [
    ("arremessos_quadra_convertidos", "arremessos_quadra_tentados"),
    ("cestas_tres_convertidas", "cestas_tres_tentadas"),
    ("lances_livres_convertidos", "lances_livres_tentados"),
    ("cestas_tres_convertidas", "arremessos_quadra_convertidos"),
    ("cestas_tres_tentadas", "arremessos_quadra_tentados"),
]


class IssueLog:
    def __init__(self, dataframe, raw_dataset, teams):
        self.dataframe = dataframe
        self.raw_dataset = raw_dataset
        self.teams = teams
        self.issues = []
        self.invalid_cells = pd.DataFrame(
            False, index=dataframe.index, columns=dataframe.columns
        )

    def _team_name(self, row_id):
        team_id = str(self.dataframe.at[row_id, "time_id"])
        return self.teams.get(team_id, {}).get("name", "Desconhecido")

    def flag(self, condition, columns, rule, exclude_from_analysis=True):
        affected_rows = pd.Series(condition, index=self.dataframe.index)
        affected_rows = affected_rows.fillna(False).astype(bool)

        for row_id in self.dataframe.index[affected_rows]:
            for column in columns:
                self.issues.append({
                    "Linha CSV": int(row_id),
                    "Time": self._team_name(row_id),
                    "Partida": self.dataframe.at[row_id, "partida_id"],
                    "Coluna": column,
                    "Valor original": self.raw_dataset.at[row_id, column],
                    "Regra": rule,
                })
                if exclude_from_analysis:
                    self.invalid_cells.at[row_id, column] = True

    def as_dataframe(self):
        return pd.DataFrame(self.issues, columns=ISSUE_COLUMNS)


def _check_each_column(log):
    dataframe = log.dataframe
    raw_dataset = log.raw_dataset

    for column, metadata in SCHEMA.items():
        values = dataframe[column]
        kind = metadata["kind"]

        log.flag(
            raw_dataset[column].notna() & values.isna(),
            [column],
            "Falha de conversão",
        )

        if column in NUMERIC:
            numeric_values = pd.to_numeric(values, errors="coerce").astype(float)
            is_finite = np.isfinite(numeric_values)

            log.flag(values.notna() & ~is_finite, [column], "Valor não finito")
            log.flag(numeric_values < 0, [column], "Valor negativo fora do domínio")

            if "contagem" in kind:
                is_fractional = (
                    numeric_values.notna() & is_finite & (numeric_values % 1 != 0)
                )
                log.flag(is_fractional, [column], "Contagem fracionária")

            if "proporção" in kind:
                is_outside_unit_interval = (numeric_values < 0) | (numeric_values > 1)
                log.flag(is_outside_unit_interval, [column], "Proporção fora de [0, 1]")

            if kind == "binária":
                log.flag(
                    values.notna() & ~values.isin([0, 1]),
                    [column],
                    "Resultado fora de {0, 1}",
                )

        if column in REQUIRED_COLUMNS:
            log.flag(raw_dataset[column].isna(), [column], "Campo obrigatório ausente")


def _check_minutes_and_team_names(log, teams):
    dataframe = log.dataframe

    log.flag(
        dataframe["minutos_equipe"].le(0),
        ["minutos_equipe"],
        "Minutos devem ser positivos",
    )

    for team_id, team in teams.items():
        name_differs_from_expected = (
            dataframe["time"].astype("string").ne(team["name"])
        )
        log.flag(
            dataframe["time_id"].eq(team_id) & name_differs_from_expected,
            ["time"],
            "Nome incompatível com ID da equipe",
            exclude_from_analysis=False,
        )


def _check_arithmetic_relationships(log):
    dataframe = log.dataframe

    rebounds_do_not_add_up = (
        dataframe["rebotes"]
        != dataframe["rebotes_ofensivos"] + dataframe["rebotes_defensivos"]
    )
    expected_points = (
        2 * dataframe["arremessos_quadra_convertidos"]
        + dataframe["cestas_tres_convertidas"]
        + dataframe["lances_livres_convertidos"]
    )
    points_do_not_add_up = dataframe["pontos"] != expected_points

    relationships = [
        (
            ["rebotes", "rebotes_ofensivos", "rebotes_defensivos"],
            rebounds_do_not_add_up,
            "REB ≠ OREB + DREB",
        ),
        (
            [
                "pontos",
                "arremessos_quadra_convertidos",
                "cestas_tres_convertidas",
                "lances_livres_convertidos",
            ],
            points_do_not_add_up,
            "PTS ≠ 2 × FGM + FG3M + FTM",
        ),
    ]
    for made, attempted in MADE_NOT_GREATER_THAN_ATTEMPTED:
        relationships.append((
            [made, attempted],
            dataframe[made] > dataframe[attempted],
            "Convertidos/tentados incompatíveis",
        ))

    for columns, violates_relationship, rule in relationships:
        all_columns_present = dataframe[columns].notna().all(axis=1)
        log.flag(all_columns_present & violates_relationship, columns, rule)


def _check_percentage_columns(log):
    dataframe = log.dataframe

    for made, attempted, ratio_column in SHOT_RATIO_COLUMNS:
        expected_ratio = dataframe[made] / dataframe[attempted].where(dataframe[attempted] > 0)
        ratio_differs = (dataframe[ratio_column] - expected_ratio).abs().gt(RATIO_TOLERANCE)
        log.flag(
            dataframe[ratio_column].notna() & expected_ratio.notna() & ratio_differs,
            [ratio_column],
            "Aproveitamento incompatível com razão (tolerância 0,0005)",
        )

    games_played = dataframe["vitorias_acumuladas"] + dataframe["derrotas_acumuladas"]
    expected_win_ratio = dataframe["vitorias_acumuladas"] / games_played.where(games_played > 0)
    win_ratio_differs = (
        (dataframe["proporcao_vitorias"] - expected_win_ratio).abs().gt(RATIO_TOLERANCE)
    )
    log.flag(
        expected_win_ratio.notna() & dataframe["proporcao_vitorias"].notna() & win_ratio_differs,
        ["proporcao_vitorias"],
        "Aproveitamento acumulado incompatível",
    )


def _check_duplicate_keys(log):
    is_duplicate_key = log.dataframe.duplicated(["time_id", "partida_id"], keep=False)
    log.flag(
        is_duplicate_key,
        ["partida_id"],
        "Chave time + partida duplicada",
        exclude_from_analysis=False,
    )
    return int(is_duplicate_key.sum())


def _check_cumulative_record_progression(log, teams):
    dataframe = log.dataframe

    for team_id in teams:
        team_games = dataframe.loc[dataframe["time_id"].eq(team_id)]
        team_games = team_games.sort_values("data_partida")

        games_played = team_games["vitorias_acumuladas"] + team_games["derrotas_acumuladas"]
        follows_previous_game = games_played.diff().eq(1)

        wins_change_mismatch = team_games["vitorias_acumuladas"].diff() != team_games["venceu"]
        losses_change_mismatch = team_games["derrotas_acumuladas"].diff() != 1 - team_games["venceu"]
        progression_is_wrong = follows_previous_game & (
            wins_change_mismatch | losses_change_mismatch
        )

        log.flag(
            progression_is_wrong.reindex(dataframe.index, fill_value=False),
            ["vitorias_acumuladas", "derrotas_acumuladas"],
            "Evolução acumulada incompatível com resultado",
            exclude_from_analysis=False,
        )


def _check_against_opponent_rows(log, original_dataset):
    dataframe = log.dataframe
    rows_by_game = {
        str(game_id): rows for game_id, rows in original_dataset.groupby("Game_ID")
    }

    for row_id, row in dataframe.iterrows():
        this_row_only = dataframe.index == row_id
        game_rows = rows_by_game.get(str(row["partida_id"]))

        game_is_incomplete = (
            game_rows is None
            or len(game_rows) != 2
            or game_rows["Team_ID"].nunique() != 2
        )
        if game_is_incomplete:
            log.flag(
                this_row_only,
                ["partida_id"],
                "Estrutura da partida na origem incompleta",
                exclude_from_analysis=False,
            )
            continue

        opponent = game_rows.loc[game_rows["Team_ID"] != row["time_id"]].iloc[0]
        opponent_points = pd.to_numeric(opponent["PTS"], errors="coerce")

        result_is_checkable = (
            pd.notna(row["pontos"]) and pd.notna(row["venceu"]) and pd.notna(opponent_points)
        )
        if result_is_checkable:
            tied_score = row["pontos"] == opponent_points
            result_contradicts_score = int(row["venceu"]) != int(row["pontos"] > opponent_points)
            if tied_score or result_contradicts_score:
                log.flag(
                    this_row_only,
                    ["venceu", "pontos"],
                    "Resultado incompatível com placar do adversário",
                )

        for original_column, internal_column in [
            ("GAME_DATE", "data_partida"),
            ("MIN", "minutos_equipe"),
        ]:
            if game_rows[original_column].nunique() != 1:
                log.flag(
                    this_row_only,
                    [internal_column],
                    "Divergência entre as duas equipes na origem",
                    exclude_from_analysis=False,
                )


def _build_cleaned_dataframe(dataframe, invalid_cells):
    cleaned = dataframe.copy()
    for column in NUMERIC:
        cleaned.loc[invalid_cells[column], column] = pd.NA
    cleaned.loc[invalid_cells["data_partida"], "data_partida"] = pd.NaT
    return cleaned


def _count_iqr_outliers_per_team(cleaned, column):
    total = 0
    for _, team_rows in cleaned.groupby("time_id", observed=True):
        total += int(iqr_details(team_rows[column])["outlier_mask"].sum())
    return total


def _summarize_columns(dataframe, raw_dataset, cleaned, issues):
    summary_rows = []

    for column, metadata in SCHEMA.items():
        is_measurement = column in MEASUREMENTS
        rows_with_issues = (
            issues.loc[issues["Coluna"] == column, "Linha CSV"].nunique()
            if len(issues)
            else 0
        )
        missing_after_conversion = int(dataframe[column].isna().sum())
        missing_percentage = (
            100 * float(missing_after_conversion) / len(dataframe) if len(dataframe) else np.nan
        )

        summary_rows.append({
            "Coluna": metadata["original"],
            "Nome": column,
            "Ausentes na leitura": int(raw_dataset[column].isna().sum()),
            "Ausentes após conversão": missing_after_conversion,
            "Ausentes (%)": missing_percentage,
            "Zeros": int(dataframe[column].eq(0).sum()) if column in NUMERIC else "Não aplicável",
            "Inconsistentes": int(rows_with_issues),
            "Outliers IQR por equipe": (
                _count_iqr_outliers_per_team(cleaned, column) if is_measurement else "Não aplicável"
            ),
        })

    return pd.DataFrame(summary_rows)


def audit_quality(dataframe, raw_dataset, teams, original_dataset=None):
    log = IssueLog(dataframe, raw_dataset, teams)

    _check_each_column(log)
    _check_minutes_and_team_names(log, teams)
    _check_arithmetic_relationships(log)
    _check_percentage_columns(log)
    duplicate_key_rows = _check_duplicate_keys(log)
    exact_duplicates = int(raw_dataset.duplicated().sum())
    _check_cumulative_record_progression(log, teams)
    if original_dataset is not None:
        _check_against_opponent_rows(log, original_dataset)

    cleaned = _build_cleaned_dataframe(dataframe, log.invalid_cells)
    issues = log.as_dataframe()

    return {
        "summary": _summarize_columns(dataframe, raw_dataset, cleaned, issues),
        "issues": issues,
        "cleaned": cleaned,
        "invalid": log.invalid_cells,
        "exact_duplicates": exact_duplicates,
        "duplicate_key_rows": duplicate_key_rows,
    }
