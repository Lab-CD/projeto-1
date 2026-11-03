from datetime import date, datetime
from numbers import Integral, Real

import numpy as np
import pandas as pd
from markupsafe import Markup, escape

EMPTY_VALUE = "—"
NO_INFORMATIVE_MODE = "Sem moda informativa"
DATE_DISPLAY_FORMAT = "%d/%m/%Y"
WIDE_COLUMNS = {"Data", "Partida", "Linha CSV"}
WIDE_COLUMN_WIDTH = 110
BRAZILIAN_SEPARATORS = str.maketrans({",": ".", ".": ","})

CHART_CONFIG = {
    "responsive": True,
    "displaylogo": False,
    "toImageButtonOptions": {"format": "svg"},
}


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict)):
        return False
    return pd.isna(value)


def _format_integer(value):
    return f"{value:,}".replace(",", ".")


def _format_decimal(value, decimals):
    if not np.isfinite(value):
        return "Indefinido"
    return f"{value:,.{decimals}f}".translate(BRAZILIAN_SEPARATORS)


def fmt(value, decimals=2):
    if _is_missing(value):
        return EMPTY_VALUE
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime(DATE_DISPLAY_FORMAT)
    if isinstance(value, (bool, np.bool_)):
        return "Sim" if value else "Não"
    if isinstance(value, Integral):
        return _format_integer(value)
    if isinstance(value, Real):
        return _format_decimal(value, decimals)
    if isinstance(value, (list, tuple)):
        if not value:
            return NO_INFORMATIVE_MODE
        return "; ".join(fmt(item) for item in value)
    return str(value)


def table_html(dataframe, caption=None):
    if dataframe.empty:
        return Markup('<p class="empty-state">Nenhuma ocorrência neste recorte.</p>')

    formatted = dataframe.copy().astype(object)
    for column in formatted.columns:
        formatted[column] = formatted[column].map(fmt)

    minimum_widths = {
        column: WIDE_COLUMN_WIDTH
        for column in formatted.columns
        if column in WIDE_COLUMNS
    }
    table = formatted.to_html(
        index=False,
        border=0,
        classes="data-table",
        escape=True,
        col_space=minimum_widths,
    )
    if caption:
        table = table.replace("<thead>", f"<caption>{escape(caption)}</caption><thead>", 1)
    return Markup(table)


def chart_html(figure):
    html = figure.to_html(
        full_html=False,
        include_plotlyjs=False,
        config=CHART_CONFIG,
    )
    return Markup(html)
