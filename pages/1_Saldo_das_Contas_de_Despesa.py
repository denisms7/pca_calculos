"""
Pagina: Saldo das Contas de Despesa
===================================

Le o CSV saldo_contas_despesa.csv (relatorio do Equiplano - Prefeitura de
Centenario do Sul) e mostra, por Orgao/Secretaria, Unidade, Projeto/Atividade,
Conta de Despesa e Fonte de Recurso:

- Dotacao inicial (valor_autorizado)
- Dotacao atualizada (valor_atualizado)
- Empenhado/liquidado (liquido_empenhado)
- Saldo disponivel (saldo_atual)

Esta pagina fica no grupo "Execução Orçamentária" da navegacao (definida em
app.py via st.navigation/st.Page).

NAO chama st.set_page_config aqui -- isso e' feito uma unica vez em app.py,
antes de st.navigation(), como exige o Streamlit quando se usa esse modelo
de navegacao.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Esta pagina fica em <raiz_projeto>/pages/, entao a raiz do projeto e' o pai
# da pasta pages. Os CSVs ficam em <raiz_projeto>/data (mesma convencao do
# app.py). Se a pasta "data" nao existir (ex.: outra maquina), cai de volta
# para a raiz do projeto.
_PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_PADRAO = _PASTA_RAIZ / "data" if (_PASTA_RAIZ / "data").is_dir() else _PASTA_RAIZ

ARQ_SALDO = "saldo_contas_despesa.csv"

# Mesmos elementos de despesa de Pessoal usados no app.py (grupo 3.1 +
# terceirizacao de mao de obra 3.3.90.34, que a LRF tambem soma a despesa de
# pessoal). Repetido aqui para esta pagina ficar independente/autocontida.
PREFIXOS_PESSOAL = {
    "3.1.90.11", "3.1.90.13", "3.1.91.13", "3.1.90.01", "3.1.90.03",
    "3.1.90.16", "3.1.90.91", "3.1.71.70", "3.3.90.34",
}


def _prefixo_elemento(codigo: str) -> str:
    """Reduz um codigo de natureza/conta de despesa aos 4 primeiros
    segmentos (categoria.grupo.modalidade.elemento)."""
    partes = (codigo or "").split(".")
    return ".".join(partes[:4])


def formatar_reais(valor: float) -> str:
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {texto}"


@st.cache_data(show_spinner=False)
def carregar_csv(caminho: Path) -> pd.DataFrame:
    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig", dtype=str)


def obter_arquivo(nome_esperado: str):
    caminho = PASTA_PADRAO / nome_esperado
    return caminho if caminho.exists() else None


# --------------------------------------------------------------------------
# Carregamento dos dados
# --------------------------------------------------------------------------
fonte_saldo = obter_arquivo(ARQ_SALDO)
if fonte_saldo is None:
    st.error(
        f"Não encontrei o arquivo {ARQ_SALDO} em {PASTA_PADRAO}. "
        "Verifique se ele está na pasta 'data' do projeto."
    )
    st.stop()

df_raw = carregar_csv(fonte_saldo)

df = df_raw.copy()
for col in ["valor_autorizado", "valor_atualizado", "liquido_empenhado", "saldo_atual"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

df["prefixo4"] = df["conta_despesa_codigo"].astype(str).apply(_prefixo_elemento)
df["e_pessoal"] = df["prefixo4"].isin(PREFIXOS_PESSOAL)

# --------------------------------------------------------------------------
# Filtros
# --------------------------------------------------------------------------
st.sidebar.title("Filtros")

orgaos_disponiveis = sorted(df["orgao_nome"].dropna().unique())
orgaos_sel = st.sidebar.multiselect(
    "Secretaria (Órgão)", orgaos_disponiveis, default=orgaos_disponiveis
)

df_orgao = df[df["orgao_nome"].isin(orgaos_sel)]

unidades_disponiveis = sorted(df_orgao["unidade_nome"].dropna().unique())
unidades_sel = st.sidebar.multiselect(
    "Unidade Orçamentária", unidades_disponiveis, default=unidades_disponiveis
)

fontes_disponiveis = sorted(df_orgao["fonte_descricao"].dropna().unique())
fontes_sel = st.sidebar.multiselect(
    "Fonte de Recurso", fontes_disponiveis, default=fontes_disponiveis
)

somente_pessoal = st.sidebar.checkbox(
    "Somente contas de Pessoal (3.1.xx + terceirização 3.3.90.34)",
    value=False,
    help="Mesma classificação usada na página principal para aproximar a "
    "Despesa Bruta com Pessoal do RGF Anexo 1 (LRF).",
)

busca_conta = st.sidebar.text_input(
    "Buscar por nome/código da conta de despesa", value=""
)

df_f = df[
    df["orgao_nome"].isin(orgaos_sel)
    & df["unidade_nome"].isin(unidades_sel)
    & df["fonte_descricao"].isin(fontes_sel)
]
if somente_pessoal:
    df_f = df_f[df_f["e_pessoal"]]
if busca_conta.strip():
    termo = busca_conta.strip().upper()
    df_f = df_f[
        df_f["conta_despesa_nome"].str.upper().str.contains(termo, na=False)
        | df_f["conta_despesa_codigo"].str.upper().str.contains(termo, na=False)
    ]

# --------------------------------------------------------------------------
# Cabecalho e KPIs
# --------------------------------------------------------------------------
st.title("Saldo das Contas de Despesa")
st.caption(
    "Fonte: saldo_contas_despesa.csv (Equiplano). Dotação inicial, dotação "
    "atualizada, empenhado/liquidado e saldo disponível, por secretaria, "
    "unidade, conta de despesa e fonte de recurso."
)

total_inicial = df_f["valor_autorizado"].sum()
total_atualizado = df_f["valor_atualizado"].sum()
total_empenhado = df_f["liquido_empenhado"].sum()
total_saldo = df_f["saldo_atual"].sum()
pct_executado = (total_empenhado / total_atualizado * 100) if total_atualizado else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Dotação inicial", formatar_reais(total_inicial))
c2.metric("Dotação atualizada", formatar_reais(total_atualizado))
c3.metric("Empenhado/liquidado", formatar_reais(total_empenhado))
c4.metric("Saldo disponível", formatar_reais(total_saldo))
c5.metric("% executado", f"{pct_executado:.1f}%")

st.divider()

# --------------------------------------------------------------------------
# Grafico: por secretaria ou por conta de despesa
# --------------------------------------------------------------------------
st.subheader("Dotação atualizada x Empenhado/liquidado")

agrupar_por = st.radio(
    "Agrupar gráfico e tabela por", ["Secretaria", "Conta de despesa", "Fonte de recurso"],
    horizontal=True,
)
coluna_grupo = {
    "Secretaria": "orgao_nome",
    "Conta de despesa": "conta_despesa_nome",
    "Fonte de recurso": "fonte_descricao",
}[agrupar_por]

resumo = (
    df_f.groupby(coluna_grupo, as_index=False)[
        ["valor_autorizado", "valor_atualizado", "liquido_empenhado", "saldo_atual"]
    ]
    .sum()
    .sort_values("valor_atualizado", ascending=False)
)

top_n = 20
resumo_grafico = resumo.head(top_n)

fig = go.Figure()
fig.add_bar(
    name="Empenhado/liquidado",
    y=resumo_grafico[coluna_grupo],
    x=resumo_grafico["liquido_empenhado"],
    orientation="h",
)
fig.add_bar(
    name="Saldo disponível",
    y=resumo_grafico[coluna_grupo],
    x=resumo_grafico["saldo_atual"],
    orientation="h",
)
fig.update_layout(
    barmode="stack",
    height=max(420, 30 * len(resumo_grafico)),
    xaxis_title="R$",
    yaxis_title="",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=10, r=10, t=40, b=10),
    title=f"Top {top_n} por dotação atualizada" if len(resumo) > top_n else None,
)
fig.update_yaxes(autorange="reversed")
st.plotly_chart(fig, width="stretch")

if len(resumo) > top_n:
    st.caption(
        f"Mostrando os {top_n} maiores de {len(resumo)} grupos por dotação "
        "atualizada. A tabela abaixo traz todos."
    )

# --------------------------------------------------------------------------
# Tabela resumo (agrupada)
# --------------------------------------------------------------------------
st.subheader(f"Tabela resumo por {agrupar_por.lower()}")

resumo_fmt = resumo.copy()
for col in ["valor_autorizado", "valor_atualizado", "liquido_empenhado", "saldo_atual"]:
    resumo_fmt[col] = resumo_fmt[col].map(formatar_reais)
resumo_fmt.columns = [
    agrupar_por, "Dotação inicial", "Dotação atualizada", "Empenhado/liquidado", "Saldo disponível",
]
st.dataframe(resumo_fmt, width="stretch", hide_index=True)

st.download_button(
    "Baixar resumo em CSV",
    resumo.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name=f"saldo_contas_despesa_por_{coluna_grupo}.csv",
    mime="text/csv",
)

st.divider()

# --------------------------------------------------------------------------
# Detalhe linha a linha
# --------------------------------------------------------------------------
st.subheader("Detalhe (linha a linha)")
st.caption(f"{len(df_f):,} linhas no filtro atual".replace(",", "."))

cols_detalhe = [
    "orgao_nome", "unidade_nome", "projeto_atividade_nome", "conta_despesa_codigo",
    "conta_despesa_nome", "fonte_descricao", "valor_autorizado", "valor_atualizado",
    "liquido_empenhado", "saldo_atual",
]
st.dataframe(
    df_f[cols_detalhe].sort_values("valor_atualizado", ascending=False),
    width="stretch",
    hide_index=True,
)

st.download_button(
    "Baixar detalhe completo em CSV",
    df_f[cols_detalhe].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
    file_name="saldo_contas_despesa_detalhe.csv",
    mime="text/csv",
)
