"""
Painel PCA - Prefeitura de Centenário do Sul
=============================================

Ponto de entrada do painel. Define a navegacao (agrupada por tema) e delega
a execucao para a pagina selecionada -- o conteudo de cada pagina fica em
"pages/", nao aqui.

Como rodar
----------
    pip install streamlit pandas plotly
    streamlit run app.py

Para adicionar uma pagina nova: crie o arquivo em "pages/", inclua-o em um
dos grupos abaixo (ou crie um grupo novo) com st.Page(...) e pronto -- ele
aparece na barra lateral automaticamente.
"""

import streamlit as st

st.set_page_config(
    page_title="Painel PCA - Centenário do Sul",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Execução Orçamentária": [
        st.Page(
            "pages/0_Pago_x_Falta_Pagar.py",
            title="Pago x Falta Pagar",
            default=True,
        ),
        st.Page(
            "pages/1_Saldo_das_Contas_de_Despesa.py",
            title="Saldo das Contas de Despesa",
        ),
    ],
    "Arquivos": [
        st.Page("pages/2_Downloads.py", title="Downloads"),
    ],
}

pg = st.navigation(pages)
pg.run()
