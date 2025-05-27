import streamlit as st
from db import RankingDB

from tabs.rankings import (
    añadir_rankings_tab,
    eliminar_rankings_tab,
    ver_rankings_tab,
)

from tabs.agregaciones import (
    agregar_rankings_tab,
    ver_agregaciones_tab,
    eliminar_agregaciones_tab,
)

from tabs.resultados import comparar_algoritmos_tab


def main():
    st.set_page_config(layout="wide")

    if "start_app" not in st.session_state:
        st.session_state["start_app"] = False

    if not st.session_state["start_app"]:
        st.markdown("## Bienvenido a la herramienta para resolver problemas de agregación de rankings")
        st.markdown("¿Desea comenzar?")
        if st.button("Empezar"):
            st.session_state["start_app"] = True
        st.stop()

    db = RankingDB()

    main_section = st.sidebar.radio("MENÚ", ["1º) NUEVO PROBLEMA", "2º) RESOLVER PROBLEMA", "3º) VER RESULTADOS"])

    if main_section == "1º) NUEVO PROBLEMA":
        st.title("NUEVO PROBLEMA")
        sub_tabs = st.tabs(["Añadir Rankings", "Eliminar Rankings", "Ver Rankings"])
        with sub_tabs[0]: añadir_rankings_tab(db)
        with sub_tabs[1]: eliminar_rankings_tab(db)
        with sub_tabs[2]: ver_rankings_tab(db)

    elif main_section == "2º) RESOLVER PROBLEMA":
        st.title("RESOLVER PROBLEMA")
        sub_tabs = st.tabs(["Resolver", "Ver Soluciones", "Eliminar Soluciones"])
        with sub_tabs[0]: agregar_rankings_tab(db)
        with sub_tabs[1]: ver_agregaciones_tab(db)
        with sub_tabs[2]: eliminar_agregaciones_tab(db)

    elif main_section == "3º) VER RESULTADOS":
        st.title("VER RESULTADOS")
        comparar_algoritmos_tab(db)


if __name__ == '__main__':
    main()
