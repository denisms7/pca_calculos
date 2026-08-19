"""
Painel: Quanto foi pago x Quanto falta pagar, por Secretaria
================================================================

Le os CSVs gerados a partir dos relatorios do Equiplano (Prefeitura de
Centenario do Sul) e mostra, por secretaria:

- Quanto ja foi PAGO no exercicio de 2025 (relacao_despesa_liquida_paga.csv)
- Quanto ainda FALTA PAGAR, ou seja, os Restos a Pagar processados e ainda
  nao quitados (restos_a_pagar_detalhes.csv / restos_a_pagar_grupos.csv)

Como rodar
----------
    pip install streamlit pandas plotly
    streamlit run painel_pagamentos.py

Por padrao o script procura os 4 CSVs na MESMA PASTA do script. Se estiverem
em outro lugar, use a barra lateral para indicar a pasta ou envie os
arquivos diretamente pelo uploader.

Observacao sobre a classificacao por secretaria
------------------------------------------------
- Para o "PAGO": a planilha de despesa paga traz o codigo da Unidade
  orcamentaria (ex.: "09.001"). Esse codigo e' cruzado com
  saldo_contas_despesa.csv, que relaciona cada Unidade ao seu Orgao
  (Secretaria) -- mapeamento direto e confiavel.
- Para o "FALTA PAGAR": o relatorio de restos a pagar NAO traz o codigo do
  Orgao/Unidade, apenas o Projeto/Atividade (classificacao funcional
  programatica). Por isso a secretaria e' inferida por palavras-chave na
  descricao do Projeto/Atividade e, quando isso nao e' suficiente, pelo
  codigo de Funcao (os 2 primeiros digitos do codigo). Essa classificacao
  fica no dicionario REGRAS_SECRETARIA logo abaixo -- ajuste/complete as
  regras se a estrutura administrativa do municipio mudar ou se aparecerem
  itens como "Nao classificado".
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Configuracao da pagina
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Pago x Falta Pagar por Secretaria",
    layout="wide",
    initial_sidebar_state="expanded",
)

_PASTA_SCRIPT = Path(__file__).resolve().parent
# Os CSVs ficam em uma subpasta "data" ao lado do script. Se ela não existir
# (por exemplo, ao rodar em outra máquina), cai de volta para a pasta do
# próprio script.
PASTA_PADRAO = _PASTA_SCRIPT / "data" if (_PASTA_SCRIPT / "data").is_dir() else _PASTA_SCRIPT

ARQ_PAGO = "relacao_despesa_liquida_paga.csv"
ARQ_RESTOS_DET = "restos_a_pagar_detalhes.csv"
ARQ_RESTOS_GRP = "restos_a_pagar_grupos.csv"
ARQ_SALDO = "saldo_contas_despesa.csv"

# Elementos de despesa que o usuario pode escolher (via multiselecao na
# barra lateral) para compor a "Folha de Salario". As chaves sao os rotulos
# mostrados na tela; os valores sao o codigo no nivel "elemento de despesa"
# (categoria.grupo.modalidade.elemento -- 4 primeiros segmentos).
ELEMENTOS_FOLHA_SALARIO = {
    "Vencimentos e Vantagens Fixas - Pessoal Civil (3.1.90.11)": "3.1.90.11",
    "Contribuições Patronais (3.1.90.13)": "3.1.90.13",
    "Contribuições Patronais Intraorçamentárias (3.1.91.13)": "3.1.91.13",
}

# Selecionados por padrao ao abrir o painel (os dois elementos que de fato
# aparecem nos CSVs atuais). O usuario pode marcar/desmarcar livremente.
ELEMENTOS_FOLHA_SALARIO_PADRAO = [
    "Vencimentos e Vantagens Fixas - Pessoal Civil (3.1.90.11)",
    "Contribuições Patronais (3.1.90.13)",
    "Contribuições Patronais Intraorçamentárias (3.1.91.13)",
]


def _prefixo_elemento(codigo: str) -> str:
    """Reduz um codigo de natureza de despesa aos 4 primeiros segmentos
    (categoria.grupo.modalidade.elemento). E' nesse nivel que
    ELEMENTOS_FOLHA_SALARIO esta definido; os CSVs trazem o desdobramento
    completo (ex.: "3.1.90.11.01.01"), entao a comparacao usa so o prefixo
    comum."""
    partes = (codigo or "").split(".")
    return ".".join(partes[:4])


# --------------------------------------------------------------------------
# Regras de classificacao por secretaria (usadas nos Restos a Pagar)
# --------------------------------------------------------------------------
# Ordem importa: a primeira palavra-chave que bater na descricao "vence".
REGRAS_SECRETARIA = [
    ("GABINETE DO PREFEITO", "GABINETE DO PREFEITO"),
    ("PROCURADORIA", "PROCURADORIA MUNICIPAL"),
    ("CONTROLE INTERNO", "CONTROLADORIA"),
    ("ASSISTÊNCIA SOCIAL", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("CONSELHO TUTELAR", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("COZINHA POPULAR", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("CRIANÇA E AO ADOLESCENTE", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("SUAS", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("CREAS", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("CRAS", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("NECESSIDADES ESPECIAIS", "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL"),
    ("SANEPAR", "SECRETARIA DE FAZENDA"),
    ("SECRETARIA DE FAZENDA", "SECRETARIA DE FAZENDA"),
    ("DEPARTAMENTO DE FAZENDA", "SECRETARIA DE FAZENDA"),
    ("DÍVIDA COM SENTENÇAS", "SECRETARIA DE FAZENDA"),
    ("DÍVIDA DO INSS", "SECRETARIA DE FAZENDA"),
    ("PASEP", "SECRETARIA DE FAZENDA"),
    ("FGTS", "SECRETARIA DE FAZENDA"),
    ("PRECATÓRIOS", "SECRETARIA DE FAZENDA"),
    ("SECRETARIA DE ADMINISTRAÇÃO", "SECRETARIA DE ADMINISTRAÇÃO"),
    ("REFORMA DO PRÉDIO DA PREFEITURA", "SECRETARIA DE ADMINISTRAÇÃO"),
    ("SECRETARIA DE DESENVOLVIMENTO ECONÔMICO", "SECRETARIA DE DESELVOLVIMENTO ECONÔMICO E TURISMO"),
    ("SAÚDE", "SECRETARIA DE SAUDE"),
    ("SAUDE", "SECRETARIA DE SAUDE"),
    ("HOSPITAL", "SECRETARIA DE SAUDE"),
    ("SAMU", "SECRETARIA DE SAUDE"),
    ("VIGILANCIA SANITÁRIA", "SECRETARIA DE SAUDE"),
    ("VIGILÂNCIA SANITÁRIA", "SECRETARIA DE SAUDE"),
    ("MEDICAMENTOS", "SECRETARIA DE SAUDE"),
    ("VILA PROGRESSO", "SECRETARIA DE SAUDE"),
    ("ANITA CANET", "SECRETARIA DE SAUDE"),
    ("COVID", "SECRETARIA DE SAUDE"),
    ("SECRETARIA DE EDUCAÇÃO", "SECRETARIA DA EDUCAÇÃO"),
    ("ESCOLAS MUNICIPAIS", "SECRETARIA DA EDUCAÇÃO"),
    ("TRANSPORTE ESCOLAR", "SECRETARIA DA EDUCAÇÃO"),
    ("COZINHA CENTRAL", "SECRETARIA DA EDUCAÇÃO"),
    ("CULTURA", "SECRETARIA DE ESPORTE, CULTURA E LAZER"),
    ("ESPORTE", "SECRETARIA DE ESPORTE, CULTURA E LAZER"),
    ("UNIDADES ESPORTIVAS", "SECRETARIA DE ESPORTE, CULTURA E LAZER"),
    ("OPORTUNIDADE E TRABALHO", "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS"),
    ("INFRAESTRUTURA", "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS"),
    ("INFRA ESTRUTURA", "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS"),
    ("ILUMINAÇÃO PÚBLICA", "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS"),
    ("CINDEPAR", "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS"),
    ("FOMENTO AGROPECUÁRIO", "SECRETARIA DE AGRICULTURA E MEIO AMBIENTE"),
    ("TRATOR AGRÍCOLA", "SECRETARIA DE AGRICULTURA E MEIO AMBIENTE"),
    ("MEIO AMBIENTE", "SECRETARIA DE AGRICULTURA E MEIO AMBIENTE"),
]

# Se nenhuma palavra-chave bater, cai aqui pelo codigo de Funcao (2 primeiros
# digitos do codigo do Projeto/Atividade). Cobre casos genericos.
FUNCAO_SECRETARIA = {
    "08": "SECRETARIA MUNICIPAL DE ASSISTÊNCIA SOCIAL",
    "10": "SECRETARIA DE SAUDE",
    "12": "SECRETARIA DA EDUCAÇÃO",
    "13": "SECRETARIA DE ESPORTE, CULTURA E LAZER",
    "15": "SECRETARIA DE INFRAESTRUTURA E SERVIÇOS PÚBLICOS",
    "18": "SECRETARIA DE AGRICULTURA E MEIO AMBIENTE",
    "20": "SECRETARIA DE AGRICULTURA E MEIO AMBIENTE",
    "22": "SECRETARIA DE DESELVOLVIMENTO ECONÔMICO E TURISMO",
    "27": "SECRETARIA DE ESPORTE, CULTURA E LAZER",
}


def classificar_secretaria(codigo: str, descricao: str) -> str:
    d = (descricao or "").upper()
    for palavra, secretaria in REGRAS_SECRETARIA:
        if palavra in d:
            return secretaria
    funcao = (codigo or "").split(".")[0]
    return FUNCAO_SECRETARIA.get(funcao, "NÃO CLASSIFICADO")


# --------------------------------------------------------------------------
# Funcoes auxiliares de leitura / formatacao
# --------------------------------------------------------------------------
def formatar_reais(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


@st.cache_data(show_spinner=False)
def carregar_csv(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


def preparar_pago(df_pago: pd.DataFrame, mapa_unidade: dict, mapa_orgao: dict) -> pd.DataFrame:
    df = df_pago.copy()
    for col in ["valor_pago", "retencoes", "liquido"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")

    def resolver(unidade: str):
        if unidade in mapa_unidade:
            return mapa_unidade[unidade]
        # Unidade pode ter sido reorganizada/renomeada entre o ano da despesa
        # paga e o ano do relatorio de saldo. Nesse caso, usa-se o codigo do
        # orgao (2 primeiros digitos) para pelo menos identificar a secretaria.
        orgao_cod = unidade.split(".")[0]
        if orgao_cod in mapa_orgao:
            return (mapa_orgao[orgao_cod], f"(unidade {unidade} não encontrada no relatório de saldo atual)")
        return ("NÃO IDENTIFICADO", "")

    resolvido = df["unidade"].map(resolver)
    df["secretaria"] = resolvido.map(lambda t: t[0])
    df["unidade_nome"] = resolvido.map(lambda t: t[1])
    return df


def preparar_restos(df_restos: pd.DataFrame) -> pd.DataFrame:
    df = df_restos.copy()
    for col in ["saldo_a_pagar", "liquidado", "em_previsao", "saldo_a_provisionar"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["secretaria"] = df.apply(
        lambda r: classificar_secretaria(
            r["projeto_atividade_codigo"], r["projeto_atividade_descricao"]
        ),
        axis=1,
    )
    return df


def construir_mapa_unidade(df_saldo: pd.DataFrame) -> dict:
    tmp = df_saldo[["orgao_codigo", "unidade_codigo", "orgao_nome", "unidade_nome"]].drop_duplicates()
    mapa = {}
    for _, row in tmp.iterrows():
        chave = f"{row['orgao_codigo']}.{row['unidade_codigo']}"
        mapa[chave] = (row["orgao_nome"], row["unidade_nome"])
    return mapa


def construir_mapa_orgao(df_saldo: pd.DataFrame) -> dict:
    tmp = df_saldo[["orgao_codigo", "orgao_nome"]].drop_duplicates()
    return dict(zip(tmp["orgao_codigo"], tmp["orgao_nome"]))


# --------------------------------------------------------------------------
# Origem dos dados (pasta "data" ao lado do script, ver PASTA_PADRAO acima)
# --------------------------------------------------------------------------
pasta = PASTA_PADRAO


def obter_arquivo(nome_esperado: str):
    caminho = pasta / nome_esperado
    return caminho if caminho.exists() else None


fonte_pago = obter_arquivo(ARQ_PAGO)
fonte_restos_det = obter_arquivo(ARQ_RESTOS_DET)
fonte_restos_grp = obter_arquivo(ARQ_RESTOS_GRP)
fonte_saldo = obter_arquivo(ARQ_SALDO)

faltando = [
    nome
    for nome, fonte in [
        (ARQ_PAGO, fonte_pago),
        (ARQ_RESTOS_DET, fonte_restos_det) if fonte_restos_grp is None else (None, "ok"),
        (ARQ_SALDO, fonte_saldo),
    ]
    if fonte is None
]
if (fonte_restos_det is None) and (fonte_restos_grp is None):
    faltando.append(f"{ARQ_RESTOS_DET} ou {ARQ_RESTOS_GRP}")
faltando = [f for f in faltando if f]

if faltando:
    st.error(
        "Não encontrei os seguintes arquivos: "
        + ", ".join(faltando)
        + ". Informe a pasta correta na barra lateral ou envie os CSVs."
    )
    st.stop()

df_pago_raw = carregar_csv(fonte_pago)
df_saldo_raw = carregar_csv(fonte_saldo)
usar_detalhe_restos = fonte_restos_det is not None
df_restos_raw = carregar_csv(fonte_restos_det if usar_detalhe_restos else fonte_restos_grp)

mapa_unidade = construir_mapa_unidade(df_saldo_raw)
mapa_orgao = construir_mapa_orgao(df_saldo_raw)
df_pago = preparar_pago(df_pago_raw, mapa_unidade, mapa_orgao)
df_restos = preparar_restos(df_restos_raw)

# --------------------------------------------------------------------------
# Filtros
# --------------------------------------------------------------------------
st.sidebar.title("Filtros")
secretarias_disponiveis = sorted(
    set(df_pago["secretaria"]) | set(df_restos["secretaria"])
)
secretarias_sel = st.sidebar.multiselect(
    "Secretarias", secretarias_disponiveis, default=secretarias_disponiveis
)

data_min, data_max = df_pago["data"].min(), df_pago["data"].max()
periodo = st.sidebar.date_input(
    "Período de pagamento (aba 'Pago')",
    value=(data_min.date(), data_max.date()),
    min_value=data_min.date(),
    max_value=data_max.date(),
)

elementos_folha_sel = st.sidebar.multiselect(
    "Folha de Salário — elementos de despesa a somar",
    options=list(ELEMENTOS_FOLHA_SALARIO.keys()),
    default=ELEMENTOS_FOLHA_SALARIO_PADRAO,
    help="Marque ou desmarque os elementos que devem entrar no KPI e no "
    "filtro de Folha de Salário abaixo.",
)
_prefixos_folha_sel = {ELEMENTOS_FOLHA_SALARIO[r] for r in elementos_folha_sel}

filtro_folha = st.sidebar.radio(
    "Aplicar filtro de Folha de Salário na tabela/gráfico",
    ["Todas as despesas", "Somente Folha de Salário", "Excluir Folha de Salário"],
    index=0,
)

df_pago_f = df_pago[df_pago["secretaria"].isin(secretarias_sel)]
if isinstance(periodo, tuple) and len(periodo) == 2:
    ini, fim = periodo
    df_pago_f = df_pago_f[
        (df_pago_f["data"] >= pd.Timestamp(ini)) & (df_pago_f["data"] <= pd.Timestamp(fim))
    ]
df_restos_f = df_restos[df_restos["secretaria"].isin(secretarias_sel)]

# Classificacao de folha depende da multiselecao acima, entao e' calculada
# aqui (nao dentro de preparar_pago) sobre secretaria/período já filtrados.
df_pago_f = df_pago_f.copy()
df_pago_f["folha_salario"] = df_pago_f["natureza"].map(
    lambda n: _prefixo_elemento(n) in _prefixos_folha_sel
)

# Total de Folha de Salário sempre calculado antes de aplicar o próprio
# filtro de folha (para o KPI aparecer mesmo com "Todas as despesas").
total_folha = df_pago_f.loc[df_pago_f["folha_salario"], "liquido"].sum()

if filtro_folha == "Somente Folha de Salário":
    df_pago_f = df_pago_f[df_pago_f["folha_salario"]]
elif filtro_folha == "Excluir Folha de Salário":
    df_pago_f = df_pago_f[~df_pago_f["folha_salario"]]

# --------------------------------------------------------------------------
# Agregacoes
# --------------------------------------------------------------------------
pago_por_secretaria = (
    df_pago_f.groupby("secretaria", as_index=False)["liquido"].sum().rename(columns={"liquido": "pago"})
)
restos_por_secretaria = (
    df_restos_f.groupby("secretaria", as_index=False)["saldo_a_pagar"].sum().rename(
        columns={"saldo_a_pagar": "falta_pagar"}
    )
)

resumo = pd.merge(pago_por_secretaria, restos_por_secretaria, on="secretaria", how="outer").fillna(0.0)
resumo["total"] = resumo["pago"] + resumo["falta_pagar"]
resumo["% pago"] = (resumo["pago"] / resumo["total"].replace(0, pd.NA) * 100).fillna(0.0)
resumo = resumo.sort_values("total", ascending=False).reset_index(drop=True)

total_pago = resumo["pago"].sum()
total_falta = resumo["falta_pagar"].sum()
total_geral = total_pago + total_falta

# --------------------------------------------------------------------------
# Cabecalho e KPIs
# --------------------------------------------------------------------------
st.title("Pago x Falta Pagar, por Secretaria")
st.caption(
    "Pago = Relação da Despesa Líquida Paga (2025). "
    "Falta pagar = Restos a Pagar processados ainda não quitados (saldo em 19/08/2026)."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total pago", formatar_reais(total_pago))
c2.metric("Total ainda a pagar (Restos a Pagar)", formatar_reais(total_falta))
c3.metric(
    "% já pago do total",
    f"{(total_pago / total_geral * 100) if total_geral else 0:.1f}%",
)
c4.metric(
    "Folha de Salário (pago no período)",
    formatar_reais(total_folha),
    help="Soma dos elementos marcados em 'Folha de Salário — elementos de "
    "despesa a somar' (barra lateral), dentro das secretarias/período "
    "selecionados — independente do filtro 'Aplicar filtro de Folha de "
    "Salário'.",
)

if (df_restos["secretaria"] == "NÃO CLASSIFICADO").any():
    n_nc = (df_restos["secretaria"] == "NÃO CLASSIFICADO").sum()
    st.warning(
        f"{n_nc} item(ns) de Restos a Pagar não foram classificados em nenhuma "
        "secretaria pelas regras atuais. Veja a aba 'Restos a pagar (detalhe)' "
        "e ajuste o dicionário REGRAS_SECRETARIA no script, se necessário."
    )

st.divider()

# --------------------------------------------------------------------------
# Grafico comparativo
# --------------------------------------------------------------------------
st.subheader("Pago x Falta pagar por secretaria")

fig = go.Figure()
fig.add_bar(name="Pago", y=resumo["secretaria"], x=resumo["pago"], orientation="h")
fig.add_bar(name="Falta pagar", y=resumo["secretaria"], x=resumo["falta_pagar"], orientation="h")
fig.update_layout(
    barmode="stack",
    height=max(420, 34 * len(resumo)),
    xaxis_title="R$",
    yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=40, b=10),
)
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, width='stretch')

# --------------------------------------------------------------------------
# Tabela resumo
# --------------------------------------------------------------------------
st.subheader("Tabela resumo por secretaria")

resumo_fmt = resumo.copy()
for col in ["pago", "falta_pagar", "total"]:
    resumo_fmt[col] = resumo_fmt[col].map(formatar_reais)
resumo_fmt["% pago"] = resumo["% pago"].map(lambda v: f"{v:.1f}%")
resumo_fmt.columns = ["Secretaria", "Pago", "Falta pagar", "Total", "% pago"]
st.dataframe(resumo_fmt, width='stretch', hide_index=True)

st.download_button(
    "Baixar resumo em CSV",
    resumo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name="resumo_pago_x_falta_pagar_por_secretaria.csv",
    mime="text/csv",
)

st.divider()

# --------------------------------------------------------------------------
# Detalhes
# --------------------------------------------------------------------------
aba_pago, aba_restos = st.tabs(["Pago (detalhe)", "Restos a pagar (detalhe)"])

with aba_pago:
    st.caption(f"{len(df_pago_f):,} pagamentos no período/secretarias selecionados".replace(",", "."))
    cols = [
        "data", "secretaria", "unidade_nome", "empenho", "natureza", "folha_salario",
        "fornecedor_codigo", "fornecedor_nome", "valor_pago", "retencoes", "liquido",
    ]
    st.dataframe(
        df_pago_f[cols].sort_values("data", ascending=False),
        width='stretch',
        hide_index=True,
    )

with aba_restos:
    st.caption(f"{len(df_restos_f):,} itens de restos a pagar".replace(",", "."))
    cols_r = [
        "secretaria", "projeto_atividade_codigo", "projeto_atividade_descricao",
        "fornecedor_nome" if "fornecedor_nome" in df_restos_f.columns else "secretaria",
        "liquidado", "saldo_a_pagar",
    ]
    cols_r = [c for c in dict.fromkeys(cols_r) if c in df_restos_f.columns]
    st.dataframe(
        df_restos_f[cols_r].sort_values("saldo_a_pagar", ascending=False),
        width='stretch',
        hide_index=True,
    )
