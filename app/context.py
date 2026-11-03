import numpy as np
import pandas as pd

from analytics.charts import (
    build_bars,
    build_boxplot,
    build_detection_heatmap,
    build_histogram,
    build_timeline,
)
from analytics.data import load_dataset, prepare_dataset, source_metadata
from analytics.descriptive import describe_by_team, describe_series, standardized_team_means
from analytics.outliers import METHODS, detect_outliers
from analytics.quality import audit_quality
from analytics.schema import SCHEMA, dictionary_rows
from app.formatting import chart_html, table_html
from config import IQR_FACTOR, TEAMS, VARIABLES

BOTH_TEAMS = "ambos"
BOTH_TEAMS_LABEL = "Chicago Bulls e Minnesota Timberwolves"

MEASURES = {
    "mean": "Média",
    "median": "Mediana",
    "std": "Desvio padrão",
    "variance": "Variância",
    "cv": "CV",
    "iqr": "IQR",
    "zscore": "Média em z-score",
}

DESCRIPTIVE_STATISTICS = [
    ("Valores válidos (jogos)", "n"),
    ("Ausentes/inválidos (jogos)", "missing"),
    ("Média", "mean"),
    ("Mediana", "median"),
    ("Moda(s)", "modes"),
    ("Mínimo", "min"),
    ("Máximo", "max"),
    ("Amplitude", "range"),
    ("Desvio padrão amostral", "std"),
    ("Variância amostral", "variance"),
    ("Q1", "q1"),
    ("Q3", "q3"),
    ("IQR", "iqr"),
    ("CV", "cv"),
    ("Assimetria ajustada G1", "skew"),
    ("IQR / mediana", "robust_ratio"),
    ("Limite inferior teórico", "lower"),
    ("Limite superior teórico", "upper"),
    ("Bigode inferior observado", "whisker_low"),
    ("Bigode superior observado", "whisker_high"),
    ("Outliers IQR (jogos)", "outlier_count"),
]

COUNT_STATISTICS = {"n", "missing", "outlier_count"}
DIMENSIONLESS_STATISTICS = {"skew", "robust_ratio"}


def load_project(csv_path):
    original = load_dataset(csv_path)
    raw, prepared, transformations = prepare_dataset(original, TEAMS)
    quality = audit_quality(prepared, raw, TEAMS, original)
    cleaned = quality["cleaned"]

    summaries = describe_by_team(cleaned, VARIABLES, TEAMS, IQR_FACTOR)

    detectors = {}
    for team_id in TEAMS:
        team_rows = cleaned.loc[cleaned["time_id"] == team_id]
        for variable in VARIABLES:
            for method in METHODS:
                detectors[(team_id, variable, method)] = detect_outliers(
                    team_rows[variable], method
                )

    return {
        "original": original,
        "raw": raw,
        "prepared": prepared,
        "df": cleaned,
        "transformations": transformations,
        "quality": quality,
        "summaries": summaries,
        "detectors": detectors,
        "source": source_metadata(csv_path, original, prepared),
    }


def base_context(project, team_id, variable, method, measure):
    if team_id == BOTH_TEAMS:
        visible_teams = TEAMS
        scope_label = BOTH_TEAMS_LABEL
    else:
        visible_teams = {team_id: TEAMS[team_id]}
        scope_label = TEAMS[team_id]["name"]

    active_rows = int(project["df"]["time_id"].isin(visible_teams).sum())

    return {
        "teams": TEAMS,
        "visible_teams": visible_teams,
        "variables": VARIABLES,
        "schema": SCHEMA,
        "methods": METHODS,
        "measures": MEASURES,
        "selected_team": team_id,
        "variable": variable,
        "method": method,
        "measure": measure,
        "source": project["source"],
        "scope_label": scope_label,
        "active_rows": active_rows,
    }


def overview_context(project, context):
    visible_teams = context["visible_teams"]
    dataframe = project["df"]

    team_cards = []
    for team_id, team in visible_teams.items():
        team_games = dataframe.loc[dataframe["time_id"] == team_id]
        team_cards.append({
            **team,
            "id": team_id,
            "games": len(team_games),
            "wins": int(team_games["venceu"].sum()),
            "summary": project["summaries"][(team_id, "pontos")],
        })

    boxplot = build_boxplot(
        dataframe, context["variable"], project["summaries"], visible_teams
    )
    return {
        "cards": team_cards,
        "timeline": chart_html(build_timeline(dataframe, visible_teams)),
        "overview_box": chart_html(boxplot),
    }


def preparation_context(project):
    return {"transformations_table": table_html(project["transformations"])}


def dictionary_context(project):
    return {"dictionary_table": table_html(pd.DataFrame(dictionary_rows(project["prepared"])))}


def _unit_for_statistic(statistic_key, variable_unit):
    if statistic_key in COUNT_STATISTICS:
        return "jogos"
    if statistic_key == "cv":
        return "%"
    if statistic_key in DIMENSIONLESS_STATISTICS:
        return "adimensional"
    if statistic_key == "variance":
        return f"({variable_unit})²"
    return variable_unit


def _statistics_rows(summaries_by_team, variable_unit):
    rows = []
    for label, statistic_key in DESCRIPTIVE_STATISTICS:
        row = {
            "Medida": label,
            "Unidade": _unit_for_statistic(statistic_key, variable_unit),
        }
        for team_name, summary in summaries_by_team.items():
            row[team_name] = summary[statistic_key]
        rows.append(row)
    return rows


def _extreme_rows(team, summary, dataframe, value_column):
    rows = []
    for row_id, value in summary["outliers"].items():
        game = dataframe.loc[row_id]
        rows.append({
            "Equipe": team["name"],
            "Data": game["data_partida"],
            "Confronto": game["confronto"],
            "Partida": game["partida_id"],
            "Linha CSV": int(row_id),
            value_column: value,
            "Extremo": "Inferior" if value < summary["lower"] else "Superior",
        })
    return rows


def _sensitivity_rows(team, summary, series, unit):
    series_without_outliers = series.drop(index=summary["outliers"].index)
    summary_without_outliers = describe_series(series_without_outliers)

    def scenario_row(scenario, scenario_summary):
        return {
            "Equipe": team["name"],
            "Cenário": scenario,
            "n": scenario_summary["n"],
            f"Desvio ({unit})": scenario_summary["std"],
            f"IQR ({unit})": scenario_summary["iqr"],
            f"Média ({unit})": scenario_summary["mean"],
        }

    return [
        scenario_row("Todos os valores válidos", summary),
        scenario_row("Sem sinalizados IQR (sensibilidade)", summary_without_outliers),
    ]


def descriptive_context(project, context):
    variable = context["variable"]
    dataframe = project["df"]
    visible_teams = context["visible_teams"]
    unit = SCHEMA[variable]["unit"]

    summaries_by_team = {}
    distribution_cards = []
    extreme_rows = []
    sensitivity_rows = []

    for team_id, team in visible_teams.items():
        summary = project["summaries"][(team_id, variable)]
        series = dataframe.loc[dataframe["time_id"] == team_id, variable]
        summaries_by_team[team["name"]] = summary

        distribution_cards.append({
            "team": team,
            "summary": summary,
            "histogram": chart_html(build_histogram(series, variable, team)),
        })
        extreme_rows += _extreme_rows(team, summary, dataframe, f"Valor ({unit})")
        sensitivity_rows += _sensitivity_rows(team, summary, series, unit)

    boxplot = build_boxplot(dataframe, variable, project["summaries"], visible_teams)
    return {
        "statistics_table": table_html(pd.DataFrame(_statistics_rows(summaries_by_team, unit))),
        "distributions": distribution_cards,
        "boxplot": chart_html(boxplot),
        "extremes_table": table_html(pd.DataFrame(extreme_rows)),
        "sensitivity_table": table_html(pd.DataFrame(sensitivity_rows)),
    }


def _unit_for_comparison_matrix(statistic_key, variable):
    if statistic_key == "cv":
        return "%"
    if statistic_key == "skew":
        return "adimensional"
    return SCHEMA[variable]["unit"]


def matrix_table(project, statistic_key, visible_teams):
    rows = []
    for variable in VARIABLES:
        row = {
            "Variável": SCHEMA[variable]["label"],
            "Unidade": _unit_for_comparison_matrix(statistic_key, variable),
        }
        for team_id, team in visible_teams.items():
            row[team["name"]] = project["summaries"][(team_id, variable)][statistic_key]
        rows.append(row)
    return table_html(pd.DataFrame(rows))


def _unit_for_measure(measure, variable):
    unit = SCHEMA[variable]["unit"]
    if measure == "cv":
        return "%"
    if measure == "variance":
        return f"({unit})²"
    return unit


def _team_detail_rows(project, variable, visible_teams):
    rows = []
    for team_id, team in visible_teams.items():
        summary = project["summaries"][(team_id, variable)]
        rows.append({
            "Variável": SCHEMA[variable]["label"],
            "Equipe": team["short"],
            "Unidade": SCHEMA[variable]["unit"],
            "n válido": summary["n"],
            "Média": summary["mean"],
            "Desvio": summary["std"],
            "Amplitude": summary["range"],
            "Q1": summary["q1"],
            "Q3": summary["q3"],
            "IQR": summary["iqr"],
            "CV (%)": summary["cv"],
            "G1 (adimensional)": summary["skew"],
        })
    return rows


def _compare_two_teams(project, variable, visible_teams):
    cv_by_team = [
        (team_id, project["summaries"][(team_id, variable)]["cv"])
        for team_id in visible_teams
        if np.isfinite(project["summaries"][(team_id, variable)]["cv"])
    ]
    if len(cv_by_team) != 2:
        return None

    lowest_cv, highest_cv = sorted(cv_by_team, key=lambda pair: pair[1])
    iqr_by_team = sorted(
        ((team_id, project["summaries"][(team_id, variable)]["iqr"]) for team_id in visible_teams),
        key=lambda pair: pair[1],
    )
    narrowest_iqr, widest_iqr = iqr_by_team

    return {
        "variable": variable,
        "label": SCHEMA[variable]["label"],
        "low": visible_teams[lowest_cv[0]]["name"],
        "low_cv": lowest_cv[1],
        "high": visible_teams[highest_cv[0]]["name"],
        "high_cv": highest_cv[1],
        "tie": bool(np.isclose(lowest_cv[1], highest_cv[1])),
        "iqr_low_team": visible_teams[narrowest_iqr[0]]["name"],
        "iqr_low": narrowest_iqr[1],
        "iqr_high_team": visible_teams[widest_iqr[0]]["name"],
        "iqr_high": widest_iqr[1],
        "iqr_tie": bool(np.isclose(narrowest_iqr[1], widest_iqr[1])),
    }


def comparison_context(project, context):
    variable = context["variable"]
    measure = context["measure"]
    visible_teams = context["visible_teams"]

    zscore_reference = None
    if measure == "zscore":
        values_by_team, zscore_reference = standardized_team_means(
            project["df"], variable, TEAMS
        )
        unit = "desvios padrão (adimensional)"
    else:
        values_by_team = {
            team_id: project["summaries"][(team_id, variable)][measure]
            for team_id in visible_teams
        }
        unit = _unit_for_measure(measure, variable)

    detail_rows = []
    team_comparisons = []
    for each_variable in VARIABLES:
        detail_rows += _team_detail_rows(project, each_variable, visible_teams)
        comparison = _compare_two_teams(project, each_variable, visible_teams)
        if comparison:
            team_comparisons.append(comparison)

    bar_chart = build_bars(values_by_team, variable, visible_teams, MEASURES[measure], unit)
    measure_values = [
        {"team": team, "value": values_by_team.get(team_id, np.nan)}
        for team_id, team in visible_teams.items()
    ]
    return {
        "measure_values": measure_values,
        "measure_label": MEASURES[measure],
        "measure_unit": unit,
        "bar_chart": chart_html(bar_chart),
        "reference": zscore_reference,
        "cv_table": matrix_table(project, "cv", visible_teams),
        "iqr_table": matrix_table(project, "iqr", visible_teams),
        "skew_table": matrix_table(project, "skew", visible_teams),
        "comparison_details": table_html(pd.DataFrame(detail_rows)),
        "comparisons": team_comparisons,
    }


def _audit_for_selection(project, context):
    if context["selected_team"] == BOTH_TEAMS:
        return project["quality"]

    selected_rows = project["prepared"]["time_id"].isin(context["visible_teams"])
    return audit_quality(
        project["prepared"].loc[selected_rows],
        project["raw"].loc[selected_rows],
        TEAMS,
        project["original"],
    )


def _detector_overview(project, visible_teams):
    summary_rows = []
    flag_counts = []

    for variable in VARIABLES:
        counts_for_variable = []
        for method, method_name in METHODS.items():
            total_flagged = 0
            results = []
            for team_id, team in visible_teams.items():
                result = project["detectors"][(team_id, variable, method)]
                results.append(result)
                summary_rows.append({
                    "Equipe": team["short"],
                    "Variável": SCHEMA[variable]["label"],
                    "Método": method_name,
                    "n válido": result["n"],
                    "Sinalizados": result["count"],
                    "Estado": result["status"],
                })
                total_flagged += result["count"] or 0

            method_not_applicable_everywhere = all(
                result["count"] is None for result in results
            )
            counts_for_variable.append(
                None if method_not_applicable_everywhere else total_flagged
            )
        flag_counts.append(counts_for_variable)

    return summary_rows, flag_counts


def _flagged_rows(result):
    return result["rows"].loc[result["rows"]["sinalizado"]]


def quality_context(project, context):
    visible_teams = context["visible_teams"]
    variable = context["variable"]
    method = context["method"]
    unit = SCHEMA[variable]["unit"]
    audit = _audit_for_selection(project, context)

    detector_summary_rows, flag_counts = _detector_overview(project, visible_teams)

    detector_details = []
    occurrence_rows = []
    for team_id, team in visible_teams.items():
        result = project["detectors"][(team_id, variable, method)]
        detector_details.append({"team": team, "result": result})

        for row_id, flagged in _flagged_rows(result).iterrows():
            game = project["df"].loc[row_id]
            occurrence_rows.append({
                "Equipe": team["name"],
                "Data": game["data_partida"],
                "Confronto": game["confronto"],
                "Partida": game["partida_id"],
                "Linha CSV": int(row_id),
                f"Valor ({unit})": flagged["valor"],
                "Escore": flagged["escore"],
                "Método": result["name"],
                "Limiar": result["threshold"],
            })

    audit_summary = audit["summary"]
    issues = audit["issues"]
    heatmap = build_detection_heatmap(flag_counts, VARIABLES, METHODS.values())

    return {
        "audit_table": table_html(audit_summary),
        "issues_table": table_html(issues),
        "missing_count": int(audit_summary["Ausentes na leitura"].sum()),
        "invalid_count": int(issues["Linha CSV"].nunique()) if len(issues) else 0,
        "duplicate_count": audit["exact_duplicates"],
        "duplicate_key_rows": audit["duplicate_key_rows"],
        "detector_details": detector_details,
        "outlier_occurrences": table_html(pd.DataFrame(occurrence_rows)),
        "detectors_table": table_html(pd.DataFrame(detector_summary_rows)),
        "detection_heatmap": chart_html(heatmap),
    }


def _team_insight(team, summaries_by_variable):
    with_valid_skew = [
        (variable, summary) for variable, summary in summaries_by_variable
        if np.isfinite(summary["skew"])
    ]
    with_valid_cv = [
        (variable, summary) for variable, summary in summaries_by_variable
        if np.isfinite(summary["cv"])
    ]

    return {
        "team": team,
        "skewed": max(with_valid_skew, key=lambda pair: abs(pair[1]["skew"])) if with_valid_skew else None,
        "stable": min(with_valid_cv, key=lambda pair: pair[1]["cv"]) if with_valid_cv else None,
        "variable": max(with_valid_cv, key=lambda pair: pair[1]["cv"]) if with_valid_cv else None,
        "summaries": summaries_by_variable,
    }


def _percentage_change(original_value, new_value):
    if original_value > 0:
        return 100 * (original_value - new_value) / original_value
    return np.nan


def _outlier_sensitivity(team, variable, summary, series):
    without_outliers = describe_series(series.drop(index=summary["outliers"].index))
    std_drop = _percentage_change(summary["std"], without_outliers["std"])
    iqr_change = _percentage_change(summary["iqr"], without_outliers["iqr"])
    iqr_change = abs(iqr_change) if np.isfinite(iqr_change) else iqr_change

    row = {
        "Equipe": team["short"],
        "Variável": SCHEMA[variable]["label"],
        "Unidade": SCHEMA[variable]["unit"],
        "Sinalizados IQR": summary["outlier_count"],
        "Desvio completo": summary["std"],
        "Desvio sem sinalizados": without_outliers["std"],
        "IQR completo": summary["iqr"],
        "IQR sem sinalizados": without_outliers["iqr"],
        "Queda do desvio (%)": std_drop,
        "Mudança absoluta do IQR (%)": iqr_change,
    }
    return row, std_drop, iqr_change


def synthesis_context(project, context):
    visible_teams = context["visible_teams"]
    dataframe = project["df"]

    team_insights = []
    sensitivity_rows = []
    std_inflated_by_extremes = []

    for team_id, team in visible_teams.items():
        summaries_by_variable = [
            (variable, project["summaries"][(team_id, variable)]) for variable in VARIABLES
        ]
        team_insights.append(_team_insight(team, summaries_by_variable))

        for variable, summary in summaries_by_variable:
            series = dataframe.loc[dataframe["time_id"] == team_id, variable]
            row, std_drop, iqr_change = _outlier_sensitivity(team, variable, summary, series)
            sensitivity_rows.append(row)

            std_dropped_more_than_iqr = (
                summary["outlier_count"]
                and np.isfinite(std_drop)
                and np.isfinite(iqr_change)
                and std_drop > iqr_change
            )
            if std_dropped_more_than_iqr:
                std_inflated_by_extremes.append({
                    "team": team["name"],
                    "variable": SCHEMA[variable]["label"],
                    "std_drop": std_drop,
                    "iqr_change": iqr_change,
                })

    most_skewed_variables = [
        insight["skewed"][0] for insight in team_insights if insight["skewed"]
    ]
    same_skew_pattern_in_both_teams = (
        len(most_skewed_variables) == 2 and len(set(most_skewed_variables)) == 1
    )

    return {
        "team_insights": team_insights,
        "comparisons": comparison_context(project, context)["comparisons"],
        "cv_table": matrix_table(project, "cv", visible_teams),
        "iqr_table": matrix_table(project, "iqr", visible_teams),
        "repeated_skew": same_skew_pattern_in_both_teams,
        "influence": std_inflated_by_extremes,
        "sensitivity_all": table_html(pd.DataFrame(sensitivity_rows)),
    }


def _all_flagged_occurrences(project, variable, visible_teams):
    occurrences = []
    for team_id, team in visible_teams.items():
        for method, method_name in METHODS.items():
            result = project["detectors"][(team_id, variable, method)]
            for row_id, flagged in _flagged_rows(result).iterrows():
                game = project["df"].loc[row_id]
                occurrences.append({
                    "Equipe": team["name"],
                    "Data": game["data_partida"],
                    "Partida": game["partida_id"],
                    "Confronto": game["confronto"],
                    "Variável": SCHEMA[variable]["label"],
                    "Unidade": SCHEMA[variable]["unit"],
                    "Método": method_name,
                    "Valor": flagged["valor"],
                    "Escore": flagged["escore"],
                    "Limiar": result["threshold"],
                })
    return occurrences


def full_report_context(project, context):
    visible_teams = context["visible_teams"]

    report = {
        **dictionary_context(project),
        **preparation_context(project),
        **quality_context(project, context),
        **comparison_context(project, context),
        **synthesis_context(project, context),
    }

    variable_chapters = []
    all_occurrences = []
    for variable in VARIABLES:
        chapter_context = {**context, "variable": variable}
        mean_by_team = {
            team_id: project["summaries"][(team_id, variable)]["mean"]
            for team_id in visible_teams
        }
        mean_bar_chart = build_bars(
            mean_by_team, variable, visible_teams, "Média", SCHEMA[variable]["unit"]
        )
        variable_chapters.append({
            "variable": variable,
            **descriptive_context(project, chapter_context),
            "bar_chart": chart_html(mean_bar_chart),
        })
        all_occurrences += _all_flagged_occurrences(project, variable, visible_teams)

    report["variable_chapters"] = variable_chapters
    report["all_outlier_occurrences"] = table_html(pd.DataFrame(all_occurrences))
    return report
