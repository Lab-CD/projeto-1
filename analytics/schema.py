NUMERIC_KINDS = {
    "contagem",
    "contagem acumulada",
    "proporção",
    "proporção acumulada",
    "binária",
}
MEASUREMENT_KINDS = {"contagem", "proporção"}


def _column(original_name, internal_name, label, kind, unit, description):
    metadata = {
        "original": original_name,
        "label": label,
        "kind": kind,
        "unit": unit,
        "description": description,
    }
    return internal_name, metadata


SCHEMA = dict([
    _column(
        original_name="Team_ID",
        internal_name="time_id",
        label="ID do time",
        kind="identificador",
        unit="sem unidade",
        description="Identifica a equipe; números usados como código, não como medida.",
    ),
    _column(
        original_name="Game_ID",
        internal_name="partida_id",
        label="ID da partida",
        kind="identificador",
        unit="sem unidade",
        description="Identifica a partida; a chave do registro é time + partida.",
    ),
    _column(
        original_name="GAME_DATE",
        internal_name="data_partida",
        label="Data da partida",
        kind="data",
        unit="data",
        description="Dia do jogo, sem horário ou fuso informado.",
    ),
    _column(
        original_name="MATCHUP",
        internal_name="confronto",
        label="Confronto",
        kind="texto",
        unit="sem unidade",
        description="Equipes e mando: vs. indica casa; @ indica visitante.",
    ),
    _column(
        original_name="WL",
        internal_name="venceu",
        label="Vitória",
        kind="binária",
        unit="0 ou 1",
        description="Resultado da partida: 1 = vitória, 0 = derrota.",
    ),
    _column(
        original_name="W",
        internal_name="vitorias_acumuladas",
        label="Vitórias acumuladas",
        kind="contagem acumulada",
        unit="vitórias",
        description="Vitórias acumuladas até a partida, incluindo o jogo atual.",
    ),
    _column(
        original_name="L",
        internal_name="derrotas_acumuladas",
        label="Derrotas acumuladas",
        kind="contagem acumulada",
        unit="derrotas",
        description="Derrotas acumuladas até a partida, incluindo o jogo atual.",
    ),
    _column(
        original_name="W_PCT",
        internal_name="proporcao_vitorias",
        label="Aproveitamento acumulado",
        kind="proporção acumulada",
        unit="%",
        description="Vitórias divididas por vitórias + derrotas; armazenada em [0, 1].",
    ),
    _column(
        original_name="MIN",
        internal_name="minutos_equipe",
        label="Minutos da equipe",
        kind="contagem",
        unit="minutos-equipe/jogo",
        description=(
            "Soma dos minutos em quadra dos cinco jogadores da equipe "
            "(240 no tempo regulamentar; +25 por prorrogação)."
        ),
    ),
    _column(
        original_name="FGM",
        internal_name="arremessos_quadra_convertidos",
        label="Cestas de quadra",
        kind="contagem",
        unit="cestas/jogo",
        description="Arremessos de quadra convertidos, incluindo cestas de três.",
    ),
    _column(
        original_name="FGA",
        internal_name="arremessos_quadra_tentados",
        label="Tentativas de quadra",
        kind="contagem",
        unit="tentativas/jogo",
        description="Todos os arremessos de quadra tentados.",
    ),
    _column(
        original_name="FG_PCT",
        internal_name="aproveitamento_quadra",
        label="Aproveitamento de quadra",
        kind="proporção",
        unit="%",
        description="Razão FGM/FGA, armazenada em [0, 1].",
    ),
    _column(
        original_name="FG3M",
        internal_name="cestas_tres_convertidas",
        label="Cestas de três",
        kind="contagem",
        unit="cestas de três/jogo",
        description="Arremessos de três pontos convertidos.",
    ),
    _column(
        original_name="FG3A",
        internal_name="cestas_tres_tentadas",
        label="Tentativas de três",
        kind="contagem",
        unit="tentativas/jogo",
        description="Arremessos de três pontos tentados.",
    ),
    _column(
        original_name="FG3_PCT",
        internal_name="aproveitamento_tres",
        label="Aproveitamento de três",
        kind="proporção",
        unit="%",
        description="Razão FG3M/FG3A, armazenada em [0, 1].",
    ),
    _column(
        original_name="FTM",
        internal_name="lances_livres_convertidos",
        label="Lances livres convertidos",
        kind="contagem",
        unit="lances livres/jogo",
        description="Lances livres convertidos.",
    ),
    _column(
        original_name="FTA",
        internal_name="lances_livres_tentados",
        label="Lances livres tentados",
        kind="contagem",
        unit="tentativas/jogo",
        description="Lances livres tentados.",
    ),
    _column(
        original_name="FT_PCT",
        internal_name="aproveitamento_lance_livre",
        label="Aproveitamento de lance livre",
        kind="proporção",
        unit="%",
        description="Razão FTM/FTA, armazenada em [0, 1].",
    ),
    _column(
        original_name="OREB",
        internal_name="rebotes_ofensivos",
        label="Rebotes ofensivos",
        kind="contagem",
        unit="rebotes/jogo",
        description="Rebotes recuperados no ataque.",
    ),
    _column(
        original_name="DREB",
        internal_name="rebotes_defensivos",
        label="Rebotes defensivos",
        kind="contagem",
        unit="rebotes/jogo",
        description="Rebotes recuperados na defesa.",
    ),
    _column(
        original_name="REB",
        internal_name="rebotes",
        label="Rebotes",
        kind="contagem",
        unit="rebotes/jogo",
        description="Total de rebotes ofensivos e defensivos.",
    ),
    _column(
        original_name="AST",
        internal_name="assistencias",
        label="Assistências",
        kind="contagem",
        unit="assistências/jogo",
        description="Passes registrados como assistência.",
    ),
    _column(
        original_name="STL",
        internal_name="roubos_bola",
        label="Roubos de bola",
        kind="contagem",
        unit="roubos/jogo",
        description="Roubos de bola registrados; zero é válido.",
    ),
    _column(
        original_name="BLK",
        internal_name="tocos",
        label="Tocos",
        kind="contagem",
        unit="tocos/jogo",
        description="Bloqueios de arremesso; zero é válido.",
    ),
    _column(
        original_name="TOV",
        internal_name="desperdicios_bola",
        label="Perdas de bola",
        kind="contagem",
        unit="perdas/jogo",
        description="Posses perdidas (turnovers).",
    ),
    _column(
        original_name="PF",
        internal_name="faltas_pessoais",
        label="Faltas pessoais",
        kind="contagem",
        unit="faltas/jogo",
        description="Faltas pessoais cometidas pela equipe.",
    ),
    _column(
        original_name="PTS",
        internal_name="pontos",
        label="Pontos",
        kind="contagem",
        unit="pontos/jogo",
        description="Pontuação total da equipe na partida.",
    ),
    _column(
        original_name="TEAM_NAME",
        internal_name="time",
        label="Time",
        kind="categórica",
        unit="sem unidade",
        description="Nome da equipe, associado a um ID de time.",
    ),
])

RENAME = {metadata["original"]: name for name, metadata in SCHEMA.items()}

NUMERIC = tuple(
    name for name, metadata in SCHEMA.items()
    if metadata["kind"] in NUMERIC_KINDS
)

MEASUREMENTS = tuple(
    name for name, metadata in SCHEMA.items()
    if metadata["kind"] in MEASUREMENT_KINDS
)


def describe_domain(kind):
    if "contagem" in kind:
        return "inteiro ≥ 0"
    if "proporção" in kind:
        return "[0, 1]"
    if kind == "binária":
        return "{0, 1}"
    if kind == "data":
        return "data válida"
    return "código / texto não vazio"


def dictionary_rows(dataframe):
    rows = []
    for name, metadata in SCHEMA.items():
        rows.append({
            "Original": metadata["original"],
            "Nome interno": name,
            "Rótulo": metadata["label"],
            "Natureza": metadata["kind"],
            "Tipo Python/pandas": str(dataframe[name].dtype),
            "Unidade": metadata["unit"],
            "Domínio": describe_domain(metadata["kind"]),
            "Significado": metadata["description"],
        })
    return rows
