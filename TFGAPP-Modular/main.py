# main.py
import streamlit as st
import pandas as pd
from db import RankingDB
from services import RankingService
from utils import parse_excel, build_distance_rows


def tab_añadir_rankings(db, service):
    st.header("Añadir Rankings desde Excel")
    uploaded_file = st.file_uploader("Carga un archivo Excel (.xlsx)", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file, header=None)
        st.write("Vista previa del Excel:")
        st.dataframe(df)
        if st.button("Guardar en la base de datos"):
            parsed = parse_excel(df)
            group_id = service.guardar_datos_excel(parsed)
            st.success(f"Datos guardados correctamente. Grupo ID: {group_id}")


def tab_agregar_rankings(db, service):
    st.header("Agregar Rankings")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        options = {f"{g['nombre']} (ID: {g['id']})": g['id'] for g in groups}
        selected = st.selectbox("Selecciona el grupo", list(options.keys()))
        algorithm = st.selectbox("Algoritmo", ["Borda", "Copeland", "Kemey-Young", "Schulze", "Footrule"])
        if st.button("Ejecutar Agregación"):
            group_id = options[selected]
            result, error = service.ejecutar_agregacion(group_id, algorithm)
            if error:
                st.error(error)
            else:
                st.subheader("Ranking Agregado")
                st.write(result)
                agg_id = service.guardar_agregacion(group_id, algorithm, result)
                st.success(f"Agregación guardada con ID: {agg_id}")
    else:
        st.info("No hay grupos disponibles.")


def tab_comparar_agregaciones(db, service):
    st.header("Comparar Agregaciones")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        group_opts = {f"{g['nombre']} (ID: {g['id']})": g['id'] for g in groups}
        sel_group = st.selectbox("Selecciona grupo", list(group_opts.keys()))
        group_id = group_opts[sel_group]

        aggs = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
        if aggs:
            agg_opts = {f"{a['algoritmo']} (ID: {a['id']})": a['id'] for a in aggs}
            sel_agg = st.selectbox("Selecciona agregación", list(agg_opts.keys()))
            agg_id = agg_opts[sel_agg]

            agg_data = db.get_aggregated_ranking(agg_id)
            if agg_data:
                agg_ranking = [int(r['posicion']) for r in agg_data]
                pivot_data = db.get_group_excel_format(group_id)
                if pivot_data:
                    df_pivot = pd.DataFrame(pivot_data["rows"])
                    df_pivot.columns = ["Elemento"] + pivot_data["ranking_names"]

                    agg_df = pd.DataFrame([dict(row) for row in agg_data])
                    agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)
                    if "elemento" in agg_df.columns:
                        agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
                    merged = df_pivot.merge(agg_df, on="Elemento", how="left")

                    kendall, spearman, ws = service.calcular_metricas_comparacion(group_id, agg_ranking)
                    metric_df = build_distance_rows(pivot_data["ranking_names"], kendall, spearman, ws)

                    final_df = pd.concat([merged, metric_df], ignore_index=True)
                    st.subheader("Tabla Comparativa con Métricas")
                    st.dataframe(final_df)
                else:
                    st.warning("No hay datos pivot para este grupo.")
            else:
                st.warning("No se encontraron datos del ranking agregado.")
        else:
            st.info("No hay agregaciones para este grupo.")
    else:
        st.info("No hay grupos disponibles.")


def tab_ver_rankings(db):
    st.header("Ver Rankings")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        options = {f"{g['nombre']} (Grupo: {g['id']})": g['id'] for g in groups}
        selected = st.selectbox("Selecciona el grupo a visualizar", list(options.keys()))
        group_id = options[selected]
        pivot_data = db.get_group_excel_format(group_id)
        if pivot_data:
            df_pivot = pd.DataFrame(pivot_data["rows"])
            df_pivot.columns = ["Elemento"] + pivot_data["ranking_names"]
            st.dataframe(df_pivot)
        else:
            st.info("No hay datos para este grupo.")
    else:
        st.info("No hay grupos guardados.")


def tab_eliminar_grupo(db):
    st.header("Eliminar Grupo de Rankings")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        options = {f"{g['nombre']} (Grupo: {g['id']})": g['id'] for g in groups}
        selected = st.selectbox("Selecciona el grupo a eliminar", list(options.keys()))
        if st.button("Eliminar grupo"):
            group_id = options[selected]
            try:
                db.connection.execute("DELETE FROM RankingValue WHERE ranking_id IN (SELECT id FROM Ranking WHERE grupo_id = ?)", (group_id,))
                db.connection.execute("DELETE FROM Ranking WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM RankingElement WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM AggregatedRankingValue WHERE aggregated_ranking_id IN (SELECT id FROM AggregatedRanking WHERE grupo_id = ?)", (group_id,))
                db.connection.execute("DELETE FROM AggregatedRanking WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM RankingGroup WHERE id = ?", (group_id,))
                db.connection.commit()
                st.success("Grupo eliminado correctamente.")
            except Exception as e:
                st.error(f"Error al eliminar el grupo: {e}")
    else:
        st.info("No hay grupos disponibles para eliminar.")

def tab_ver_agregaciones(db):
    st.header("Ver Agregaciones")
    agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking").fetchall()
    if agg_groups:
        agg_options = {}
        for agg in agg_groups:
            grupo = db.get_group(agg['grupo_id'])
            nombre = grupo['nombre'] if grupo else "Desconocido"
            label = f"{nombre} (Grupo: {agg['grupo_id']}) - {agg['algoritmo']} (Agregación: {agg['id']})"
            agg_options[label] = agg['id']

        selected_agg = st.selectbox("Selecciona el ranking agregado a ver", list(agg_options.keys()))
        agg_id = agg_options[selected_agg]

        agg_data = db.get_aggregated_ranking(agg_id)
        if agg_data:
            agg_df = pd.DataFrame([dict(row) for row in agg_data])
            if "elemento" in agg_df.columns:
                agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
            agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)

            grupo_id = db.connection.execute("SELECT grupo_id FROM AggregatedRanking WHERE id = ?", (agg_id,)).fetchone()['grupo_id']
            pivot_data = db.get_group_excel_format(grupo_id)
            if pivot_data:
                df_pivot = pd.DataFrame(pivot_data["rows"])
                df_pivot.columns = ["Elemento"] + pivot_data["ranking_names"]
                merged = df_pivot.merge(agg_df, on="Elemento", how="left")
                st.dataframe(merged)
            else:
                st.write("No hay datos para este grupo.")
        else:
            st.write("No hay valores para esta agregación.")
    else:
        st.info("No hay agregaciones guardadas.")


def tab_eliminar_agregacion(db):
    st.header("Eliminar Agregaciones")
    agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking").fetchall()
    if agg_groups:
        agg_options = {}
        for agg in agg_groups:
            grupo = db.get_group(agg['grupo_id'])
            nombre = grupo['nombre'] if grupo else "Desconocido"
            label = f"{nombre} (Grupo: {agg['grupo_id']}) - {agg['algoritmo']} (Agregación: {agg['id']})"
            agg_options[label] = agg['id']

        selected_agg = st.selectbox("Selecciona la agregación a eliminar", list(agg_options.keys()))
        agg_id = agg_options[selected_agg]

        if st.button("Eliminar Agregación"):
            try:
                db.delete_aggregated_ranking(agg_id)
                st.success("Agregación eliminada correctamente.")
            except Exception as e:
                st.error(f"Error al eliminar la agregación: {e}")
    else:
        st.info("No hay agregaciones guardadas.")


def main():
    st.set_page_config(layout="wide")
    st.title("App para la Agregación de Rankings")

    db = RankingDB()
    service = RankingService(db)

    tabs = st.tabs([
        "Añadir Rankings",
        "Ver Rankings",
        "Eliminar Rankings",
        "Agregar Rankings",
        "Comparar Agregaciones",
        "Ver Agregaciones",
        "Eliminar Agregaciones"
    ])

    with tabs[0]:
        tab_añadir_rankings(db, service)
    with tabs[1]:
        tab_ver_rankings(db)
    with tabs[2]:
        tab_eliminar_grupo(db)
    with tabs[3]:
        tab_agregar_rankings(db, service)
    with tabs[4]:
        tab_comparar_agregaciones(db, service)
    with tabs[5]:
        tab_ver_agregaciones(db)
    with tabs[6]:
        tab_eliminar_agregacion(db)


if __name__ == '__main__':
    main()
