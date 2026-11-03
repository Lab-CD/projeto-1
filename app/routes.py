from pathlib import Path

import plotly
from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from analytics.outliers import METHODS
from app.context import (
    MEASURES,
    base_context,
    comparison_context,
    descriptive_context,
    dictionary_context,
    full_report_context,
    overview_context,
    preparation_context,
    quality_context,
)
from config import TEAMS, VARIABLES

report = Blueprint("report", __name__)

PLOTLY_CACHE_SECONDS = 86400
FILTER_PARAMETERS = ("time", "variavel", "metodo", "medida")
INVALID_SELECTION_MESSAGE = (
    "Seleção inválida. Escolha uma das duas equipes, variáveis e opções disponíveis."
)


def dictionary_page_context(project, context):
    return dictionary_context(project)


def preparation_page_context(project, context):
    return preparation_context(project)


PAGES = {
    "overview": ("/", "Visão geral", overview_context),
    "dictionary": ("/dicionario", "Dicionário de dados", dictionary_page_context),
    "preparation": ("/preparacao", "Preparação dos dados", preparation_page_context),
    "quality": ("/qualidade", "Qualidade dos dados", quality_context),
    "descriptive": ("/descritiva", "Análise univariada", descriptive_context),
    "comparison": ("/comparacao", "Comparação dos times", comparison_context),
    "full_report": ("/relatorio", "Relatório completo", full_report_context),
}


def read_selection():
    selection = {
        "team_id": request.args.get("time", "ambos"),
        "variable": request.args.get("variavel", "pontos"),
        "method": request.args.get("metodo", "iqr"),
        "measure": request.args.get("medida", "mean"),
    }
    allowed_values = {
        "team_id": {"ambos", *TEAMS},
        "variable": set(VARIABLES),
        "method": set(METHODS),
        "measure": set(MEASURES),
    }

    for field, chosen_value in selection.items():
        if chosen_value not in allowed_values[field]:
            abort(400, description=INVALID_SELECTION_MESSAGE)
    return selection


def render_report(page_name):
    project = current_app.extensions["project"]
    _, page_title, build_page_context = PAGES[page_name]

    context = base_context(project, **read_selection())
    context.update(build_page_context(project, context))
    context.update(page=page_name, page_title=page_title, pages=PAGES)
    return render_template(f"report/{page_name}.html", **context)


def register_page_routes():
    for page_name, (path, _, _) in PAGES.items():
        report.add_url_rule(
            path,
            endpoint=page_name,
            view_func=lambda page_name=page_name: render_report(page_name),
        )


register_page_routes()


def redirect_to_full_report(section_anchor):
    active_filters = {
        parameter: request.args[parameter]
        for parameter in FILTER_PARAMETERS
        if parameter in request.args
    }
    return redirect(url_for("report.full_report", _anchor=section_anchor, **active_filters))


@report.get("/metodologia")
def methodology():
    return redirect_to_full_report("metodologia")


@report.get("/sintese")
def synthesis():
    return redirect_to_full_report("sintese")


@report.get("/assets/plotly.min.js")
def plotly_asset():
    plotly_script = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    return send_file(plotly_script, max_age=PLOTLY_CACHE_SECONDS)


@report.app_errorhandler(400)
@report.app_errorhandler(404)
def error_page(error):
    return render_template("error.html", error=error), error.code
