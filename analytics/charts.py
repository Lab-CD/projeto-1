import numpy as np
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

from analytics.descriptive import valid_values
from analytics.schema import SCHEMA

MEAN_COLOR = "#192d3d"
MODE_COLOR = "#a87420"
LIMIT_LINE_COLOR = "#7a8a83"
DENSITY_LINE_COLOR = "#203649"
TEXT_COLOR = "#253849"
GRID_COLOR = "#edf0ef"
ZERO_LINE_COLOR = "#d9e1dd"
HEATMAP_COLORSCALE = [[0, "#f2f6f3"], [0.4, "#9ac8ad"], [1, "#1c705c"]]

BOXPLOT_HEIGHT = 450
HEATMAP_HEIGHT = 460
HISTOGRAM_BINS = 15
KDE_GRID_POINTS = 250


def style_figure(figure, title, x_title, y_title, height=410):
    figure.update_layout(
        title={"text": title, "font": {"size": 16}, "x": 0.02},
        template="plotly_white",
        height=height,
        autosize=True,
        font={"family": "Inter, Segoe UI, Arial, sans-serif", "color": TEXT_COLOR, "size": 12},
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin={"l": 65, "r": 28, "t": 65, "b": 100},
        legend={"orientation": "h", "yanchor": "top", "y": -0.22, "x": 0},
        separators=",.",
        hoverlabel={"bgcolor": "white"},
        xaxis_title=x_title,
        yaxis_title=y_title,
    )
    figure.update_xaxes(showgrid=False, zeroline=False)
    figure.update_yaxes(gridcolor=GRID_COLOR, zerolinecolor=ZERO_LINE_COLOR)
    return figure


def _add_box(figure, position, team, summary):
    figure.add_trace(go.Box(
        x=[position],
        q1=[summary["q1"]],
        median=[summary["median"]],
        q3=[summary["q3"]],
        lowerfence=[summary["whisker_low"]],
        upperfence=[summary["whisker_high"]],
        width=0.34,
        name=team["name"],
        marker_color=team["color"],
        fillcolor=team["color"],
        opacity=0.6,
        boxpoints=False,
    ))


def _add_mean_and_mode_markers(figure, position, summary):
    markers = [
        ("Média", [summary["mean"]], "diamond", MEAN_COLOR),
        ("Moda(s)", summary["modes"], "x", MODE_COLOR),
    ]
    for name, values, symbol, color in markers:
        figure.add_trace(go.Scatter(
            x=[position] * len(values),
            y=values,
            mode="markers",
            name=name,
            marker={"symbol": symbol, "size": 10, "color": color},
            showlegend=position == 0,
            hovertemplate=name + ": %{y:.2f}<extra></extra>",
        ))


def _add_limit_lines(figure, position, summary):
    limits = [
        ("Limite inferior", summary["lower"]),
        ("Limite superior", summary["upper"]),
    ]
    for limit_index, (label, limit_value) in enumerate(limits):
        is_first_limit_of_first_team = position == 0 and limit_index == 0
        figure.add_trace(go.Scatter(
            x=[position - 0.24, position + 0.24],
            y=[limit_value, limit_value],
            mode="lines",
            line={"color": LIMIT_LINE_COLOR, "dash": "dot", "width": 1.5},
            name="Limites teóricos (1,5 × IQR)",
            showlegend=is_first_limit_of_first_team,
            hovertemplate=label + ": %{y:.2f}<extra></extra>",
        ))


def _format_game_date(game_date):
    if str(game_date) == "NaT":
        return "Data indisponível"
    return game_date.strftime("%d/%m/%Y")


def _hover_details_for_games(team_games, row_ids):
    return [
        [
            str(team_games.at[row_id, "partida_id"]),
            _format_game_date(team_games.at[row_id, "data_partida"]),
            str(team_games.at[row_id, "confronto"]),
        ]
        for row_id in row_ids
    ]


def _add_extreme_points(figure, position, team, summary, team_games, variable, legends_already_shown):
    values = valid_values(team_games[variable])
    extreme_groups = [
        ("Outliers inferiores", values < summary["lower"], "triangle-down"),
        ("Outliers superiores", values > summary["upper"], "triangle-up"),
    ]

    for label, is_in_group, symbol in extreme_groups:
        extreme_values = values.loc[is_in_group]
        hover_details = _hover_details_for_games(team_games, extreme_values.index)
        should_show_legend = bool(len(extreme_values)) and label not in legends_already_shown

        figure.add_trace(go.Scatter(
            x=[position] * len(extreme_values),
            y=extreme_values.to_list(),
            name=label,
            mode="markers",
            customdata=hover_details,
            marker={"color": team["color"], "size": 10, "symbol": symbol},
            showlegend=should_show_legend,
            hovertemplate=(
                "%{y:.0f}<br>%{customdata[1]} · %{customdata[2]}"
                "<br>ID %{customdata[0]}<extra>" + label + "</extra>"
            ),
        ))
        if len(extreme_values):
            legends_already_shown.add(label)


def build_boxplot(dataframe, variable, summaries, teams):
    figure = go.Figure()
    metadata = SCHEMA[variable]
    legends_already_shown = set()

    for position, (team_id, team) in enumerate(teams.items()):
        summary = summaries[(team_id, variable)]
        if not summary["n"]:
            continue

        team_games = dataframe.loc[dataframe["time_id"] == team_id]
        _add_box(figure, position, team, summary)
        _add_mean_and_mode_markers(figure, position, summary)
        _add_limit_lines(figure, position, summary)
        _add_extreme_points(
            figure, position, team, summary, team_games, variable, legends_already_shown
        )

    figure.update_xaxes(
        tickmode="array",
        tickvals=list(range(len(teams))),
        ticktext=[team["name"] for team in teams.values()],
    )
    return style_figure(
        figure,
        f"Distribuição de {metadata['label'].lower()} · boxplot",
        "Equipe",
        metadata["unit"],
        BOXPLOT_HEIGHT,
    )


def _histogram_bins(values):
    if not len(values):
        return {"start": 0, "end": 1, "size": 1}

    value_range = values.max() - values.min()
    return {
        "start": float(values.min() - 0.5),
        "end": float(values.max() + 0.5),
        "size": max(1, float(np.ceil(value_range / HISTOGRAM_BINS))),
    }


def _kde_curve(values):
    margin = 2 * values.std(ddof=1)
    grid = np.linspace(max(0, values.min() - margin), values.max() + margin, KDE_GRID_POINTS)
    density_estimator = gaussian_kde(values, bw_method="scott")
    return grid, density_estimator(grid)


def build_histogram(series, variable, team):
    values = valid_values(series)
    metadata = SCHEMA[variable]
    figure = go.Figure()

    figure.add_trace(go.Histogram(
        x=values,
        histnorm="probability density",
        name="Histograma (densidade)",
        marker_color=team["color"],
        opacity=0.6,
        xbins=_histogram_bins(values),
    ))

    can_estimate_density = len(values) >= 3 and values.nunique() > 1
    if can_estimate_density:
        grid, density = _kde_curve(values)
        figure.add_trace(go.Scatter(
            x=grid,
            y=density,
            mode="lines",
            name="KDE · Scott",
            line={"color": DENSITY_LINE_COLOR, "width": 2.5},
        ))

    figure.update_xaxes(rangemode="nonnegative")
    return style_figure(
        figure,
        f"{metadata['label']} · {team['name']}",
        metadata["unit"],
        f"Densidade [1/({metadata['unit']})]",
    )


def _format_bar_label(value):
    if np.isfinite(value):
        return f"{value:.2f}".replace(".", ",")
    return "Indisponível"


def build_bars(values_by_team, variable, teams, measure_label, unit):
    figure = go.Figure()

    for team_id, team in teams.items():
        value = values_by_team.get(team_id, np.nan)
        figure.add_trace(go.Bar(
            x=[team["short"]],
            y=[value],
            name=team["name"],
            marker_color=team["color"],
            width=0.42,
            text=[_format_bar_label(value)],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                f"{team['name']}<br>{measure_label}: %{{y:.2f}} {unit}<extra></extra>"
            ),
        ))

    return style_figure(
        figure,
        f"{SCHEMA[variable]['label']} · {measure_label.lower()}",
        "Equipe",
        unit,
    )


def build_timeline(dataframe, teams):
    figure = go.Figure()

    for team_id, team in teams.items():
        team_games = dataframe.loc[dataframe["time_id"] == team_id].sort_values("data_partida")
        figure.add_trace(go.Scatter(
            x=team_games["data_partida"],
            y=team_games["pontos"].astype(float),
            name=team["name"],
            mode="lines+markers",
            line={"color": team["color"], "width": 1.5},
            marker={"size": 4},
            hovertemplate="%{x|%d/%m/%Y}<br>%{y:.0f} pontos<extra>%{fullData.name}</extra>",
        ))

    figure.update_xaxes(tickformat="%d/%m/%Y", nticks=6)
    return style_figure(
        figure,
        "Pontuação ao longo dos jogos",
        "Data da partida",
        "pontos/jogo",
    )


def build_detection_heatmap(flag_counts, variables, method_names):
    figure = go.Figure(go.Heatmap(
        z=flag_counts,
        x=list(method_names),
        y=[SCHEMA[variable]["label"] for variable in variables],
        text=flag_counts,
        texttemplate="%{text}",
        colorscale=HEATMAP_COLORSCALE,
        colorbar={"title": {"text": "Jogos<br>sinalizados"}},
        hovertemplate="%{y}<br>%{x}: %{z} sinalizações<extra></extra>",
    ))
    return style_figure(
        figure,
        "Sinalizações por variável e método",
        "Método",
        "Variável",
        HEATMAP_HEIGHT,
    )
