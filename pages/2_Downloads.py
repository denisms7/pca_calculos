"""
Pagina: Downloads
=================

Lista os PDFs originais (pasta "pdf") baixados do Equiplano e os CSVs
convertidos a partir deles (pasta "data"), com um botao de download para
cada arquivo -- e um botao para baixar cada pasta inteira em .zip.

Fica no grupo "Arquivos" da navegacao (definida em app.py via
st.navigation/st.Page).

NAO chama st.set_page_config aqui -- isso e' feito uma unica vez em app.py,
antes de st.navigation(), como exige o Streamlit quando se usa esse modelo
de navegacao.
"""

import io
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st

_PASTA_RAIZ = Path(__file__).resolve().parent.parent
PASTA_PDF = _PASTA_RAIZ / "pdf"
PASTA_DATA = _PASTA_RAIZ / "data"

# Relaciona cada CSV ao PDF do qual ele foi extraido/convertido, so' para
# exibir essa relacao na tela. Ajuste aqui se novos PDFs/CSVs forem
# adicionados ao projeto.
CSV_ORIGEM = {
    "saldo_contas_despesa.csv": "Saldo das contas de despesa.pdf",
    "relacao_despesa_liquida_paga.csv": "Relação da despesa líquida paga.pdf",
    "restos_a_pagar_detalhes.csv": "Restos a pagar.pdf",
    "restos_a_pagar_grupos.csv": "Restos a pagar.pdf",
}


def formatar_tamanho(num_bytes: int) -> str:
    valor = float(num_bytes)
    for unidade in ["B", "KB", "MB", "GB"]:
        if valor < 1024:
            return f"{valor:.0f} {unidade}" if unidade == "B" else f"{valor:.1f} {unidade}"
        valor /= 1024
    return f"{valor:.1f} TB"


def formatar_data(mtime: float) -> str:
    return datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")


def listar_arquivos(pasta: Path, extensao: str):
    if not pasta.is_dir():
        return []
    return sorted(pasta.glob(f"*{extensao}"), key=lambda p: p.name.lower())


def zip_da_pasta(arquivos) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for caminho in arquivos:
            zf.write(caminho, arcname=caminho.name)
    return buffer.getvalue()


st.title("Fonte de Dados")
st.caption(
    "PDFs originais baixados do Equiplano e os CSVs "
    "correspondentes, já convertidos e usados nas demais páginas do painel."
)

pdfs = listar_arquivos(PASTA_PDF, ".pdf")
csvs = listar_arquivos(PASTA_DATA, ".csv")

# --------------------------------------------------------------------------
# PDFs originais
# --------------------------------------------------------------------------
st.subheader(f"PDFs originais ({len(pdfs)})")

if not pdfs:
    st.warning(f"Nenhum PDF encontrado em {PASTA_PDF}.")
else:
    if len(pdfs) > 1:
        st.download_button(
            "Baixar todos os PDFs (.zip)",
            zip_da_pasta(pdfs),
            file_name="pdfs_equiplano.zip",
            mime="application/zip",
        )
    for caminho in pdfs:
        stat = caminho.stat()
        c1, c2, c3, c4 = st.columns([5, 1, 2, 2])
        c1.write(f"**{caminho.name}**")
        c2.write(formatar_tamanho(stat.st_size))
        c3.write(formatar_data(stat.st_mtime))
        with c4:
            st.download_button(
                "Baixar",
                caminho.read_bytes(),
                file_name=caminho.name,
                mime="application/pdf",
                key=f"pdf_{caminho.name}",
            )

st.divider()

# --------------------------------------------------------------------------
# CSVs convertidos
# --------------------------------------------------------------------------
st.subheader(f"CSVs convertidos ({len(csvs)})")

if not csvs:
    st.warning(f"Nenhum CSV encontrado em {PASTA_DATA}.")
else:
    if len(csvs) > 1:
        st.download_button(
            "Baixar todos os CSVs (.zip)",
            zip_da_pasta(csvs),
            file_name="csvs_convertidos.zip",
            mime="application/zip",
        )
    for caminho in csvs:
        stat = caminho.stat()
        origem = CSV_ORIGEM.get(caminho.name, "—")
        c1, c2, c3, c4, c5 = st.columns([4, 1, 2, 3, 2])
        c1.write(f"**{caminho.name}**")
        c2.write(formatar_tamanho(stat.st_size))
        c3.write(formatar_data(stat.st_mtime))
        c4.write(f"Convertido de: {origem}")
        with c5:
            st.download_button(
                "Baixar",
                caminho.read_bytes(),
                file_name=caminho.name,
                mime="text/csv",
                key=f"csv_{caminho.name}",
            )

# --------------------------------------------------------------------------
# PDFs sem CSV correspondente (aviso)
# --------------------------------------------------------------------------
csvs_com_origem = set(CSV_ORIGEM.values())
pdfs_sem_csv = [p.name for p in pdfs if p.name not in csvs_com_origem]
if pdfs_sem_csv:
    st.caption(
        "Sem conversão para CSV neste projeto: " + ", ".join(pdfs_sem_csv) + "."
    )
