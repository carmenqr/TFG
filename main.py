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
    
    st.markdown("""
        <style>
            .app-title {
                font-size: 3em;
                font-weight: bold;
                color: #003366;
                text-align: center;
                margin-bottom: 0.3em;
            }
            .app-subtitle {
                font-size: 1.2em;
                color: #333333;
                text-align: center;
                max-width: 750px;
                margin: 0 auto 2em auto;
            }
            .app-question {
                font-size: 1.1em;
                text-align: center;
                margin-top: 2em;
                margin-bottom: 1em;
            }
            div.stButton > button {
                display: block;
                margin: 0 auto;
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                font-size: 1.2em;
                padding: 0.6em 1.5em;
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)


    if "start_app" not in st.session_state:
        st.session_state["start_app"] = False

    if not st.session_state.get("start_app", False):
        st.markdown('<div class="app-title">ARPAR: Asistente para Resolución de Problemas de Agregación de Rankings</div>', unsafe_allow_html=True)
        st.markdown("""
            <div class="app-subtitle">
            Esta herramienta está diseñada con el objetivo asistirle en la resolución de problemas
            de agregación de rankings de forma eficaz, intuitiva y confiable.
            </div>
            <div class="app-subtitle">
                Con ella podrá importar conjuntos de rankings desde archivos excel, aplicar distintos
                métodos de agregación personalizados y visualizar graficamente los resultados obtenidos.
            </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="app-question">¿Desea comenzar?</div>', unsafe_allow_html=True)

        if st.button("Empezar"):
            st.session_state["start_app"] = True
            st.rerun()
        # Pie de página discreto
        st.markdown("""
            <p style='text-align: center; font-size: 0.8em; color: gray; margin-top: 2em;'>
                Desarrollada por <strong>Carmen Quiles Ramírez</strong> como parte del Trabajo de Fin de Grado (TFG) – Junio de 2025.
            </p>
        """, unsafe_allow_html=True)

        st.stop()


    db = RankingDB()

    main_section = st.sidebar.radio("PASOS:", [
        "📝 1º) NUEVO PROBLEMA",
        "⚙️ 2º) RESOLVER PROBLEMA",
        "📊 3º) VER RESULTADOS"
    ])


    if main_section == "📝 1º) NUEVO PROBLEMA":
        st.title("NUEVO PROBLEMA")
        sub_tabs = st.tabs(["Añadir Rankings", "Eliminar Rankings", "Ver Rankings"])
        with sub_tabs[0]: añadir_rankings_tab(db)
        with sub_tabs[1]: eliminar_rankings_tab(db)
        with sub_tabs[2]: ver_rankings_tab(db)

    elif main_section == "⚙️ 2º) RESOLVER PROBLEMA":
        st.title("RESOLVER PROBLEMA")
        sub_tabs = st.tabs(["Resolver", "Ver Soluciones", "Eliminar Soluciones"])
        with sub_tabs[0]: agregar_rankings_tab(db)
        with sub_tabs[1]: ver_agregaciones_tab(db)
        with sub_tabs[2]: eliminar_agregaciones_tab(db)

    elif main_section == "📊 3º) VER RESULTADOS":
        st.title("VER RESULTADOS")
        comparar_algoritmos_tab(db)


if __name__ == '__main__':
    main()
