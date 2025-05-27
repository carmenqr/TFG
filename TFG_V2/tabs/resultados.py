
import streamlit as st
import pandas as pd
import numpy as np
from pyRankMCDA.algorithm import rank_aggregation
from utils import (
    custom_heatmap, custom_radar_chart, custom_mds_plot,
    show_comparison_graphs, ws_coefficient, draw_distance_heatmap
)

def comparar_algoritmos_tab(db):
    st.markdown("### Tipo de resultado")
    modo_comparacion = st.radio(
        label="Tipo de resultado",
        options=["Resultado del problema general", "Resultado por tipo de solución ejecutada"],
        label_visibility="collapsed"
    )

    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if not groups:
        st.info("No hay problemas disponibles.")
        return

    group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
    selected_group = st.selectbox("Seleccione el problema del que ver los resultados", list(group_options.keys()))
    group_id = group_options[selected_group]

    if modo_comparacion == "Resultado por tipo de solución ejecutada":
        rankings = db.get_rankings(group_id)
        if len(rankings) < 2:
            st.warning("Necesita al menos dos rankings para comparar.")
            return

        agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
        if not agg_groups:
            st.error("No hay ranking de consenso para este problema.")
            return

        agg_options = {f"{agg['algoritmo']} (Agregación: {agg['id']})": agg['id'] for agg in agg_groups}
        selected_agg = st.selectbox("Seleccione una solución ejecutada", list(agg_options.keys()))
        agg_id = agg_options[selected_agg]

        pivot_data = db.get_group_excel_format(group_id)
        if not pivot_data:
            st.warning("No hay datos para este problema.")
            return

        pivot_df = pd.DataFrame(pivot_data["rows"])
        pivot_df.columns = ["Elemento"] + pivot_data["ranking_names"]
        agg_data = db.get_aggregated_ranking(agg_id)
        if not agg_data:
            st.error("No se encontraron datos del ranking de consenso.")
            return

        agg_df = pd.DataFrame([dict(row) for row in agg_data])
        if "elemento" in agg_df.columns and "Elemento" not in agg_df.columns:
            agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
        agg_df.rename(columns={"posicion": "Ranking de consenso"}, inplace=True)
        merged_df = pivot_df.merge(agg_df, on="Elemento", how="left")

        agg_row = db.connection.execute("SELECT aggregation_type FROM RankingGroup WHERE id = ?", (group_id,)).fetchone()
        agg_type = agg_row["aggregation_type"].strip().lower() if agg_row and agg_row["aggregation_type"] else ""
        agg_ranking = [int(item['posicion']) for item in agg_data]

        kendall_list, kendall_corr_list, spearman_list, ws_list = [], [], [], []
        ranking_vectors, ranking_labels = [], []

        for i, ranking in enumerate(rankings):
            values = db.get_ranking_values(ranking['id'])
            values_sorted = sorted(
                [v for v in values if v['row_index'] > 2] if agg_type == "ponderaciones" else values,
                key=lambda x: x['row_index']
            )
            individual = [int(item['posicion']) for item in values_sorted]
            ranking_vectors.append(individual)
            ranking_labels.append(pivot_data["ranking_names"][i])

            ra = rank_aggregation(np.array(agg_ranking).reshape(-1, 1))
            kendall_list.append(ra.kendall_tau_distance(np.array(individual), np.array(agg_ranking)))
            kendall_corr_list.append(ra.kendall_tau_corr(np.array(individual), np.array(agg_ranking)))
            spearman_list.append(ra.spearman_rank(np.array(individual), np.array(agg_ranking)))
            ws_list.append(ws_coefficient(individual, agg_ranking))

        ranking_vectors.append(agg_ranking)
        ranking_labels.append("Ranking de consenso")

        # Calcular matrices de distancia
        n = len(ranking_vectors)
        kendall_matrix = np.zeros((n, n))
        kendall_corr_matrix = np.zeros((n, n))
        spearman_matrix = np.zeros((n, n))
        ws_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                r1, r2 = ranking_vectors[i], ranking_vectors[j]
                ra = rank_aggregation(np.array(r1).reshape(-1, 1))
                kendall_matrix[i, j] = ra.kendall_tau_distance(r2, r1)
                kendall_corr_matrix[i, j] = ra.kendall_tau_corr(r2, r1)
                spearman_matrix[i, j] = ra.spearman_rank(r2, r1)
                ws_matrix[i, j] = ws_coefficient(r2, r1)

        
        st.subheader("Tabla con métricas de distancia")
        st.write("Distancias entre el ranking de consenso y los rankings individuales")

        # Añadir filas con métricas a la tabla
        distance_rows = []

        row_kendall = {"Elemento": "Distancia Kendall"}
        for i, name in enumerate(pivot_data["ranking_names"]):
            row_kendall[name] = kendall_list[i] if i < len(kendall_list) else np.nan
        row_kendall["Ranking de consenso"] = np.nan
        distance_rows.append(row_kendall)

        row_kendall_corr = {"Elemento": "Coeficiente Kendall"}
        for i, name in enumerate(pivot_data["ranking_names"]):
            row_kendall_corr[name] = kendall_corr_list[i] if i < len(kendall_corr_list) else np.nan
        row_kendall_corr["Ranking de consenso"] = np.nan
        distance_rows.append(row_kendall_corr)

        row_spearman = {"Elemento": "Coeficiente Spearman"}
        for i, name in enumerate(pivot_data["ranking_names"]):
            row_spearman[name] = spearman_list[i] if i < len(spearman_list) else np.nan
        row_spearman["Ranking de consenso"] = np.nan
        distance_rows.append(row_spearman)

        row_ws = {"Elemento": "Coeficiente WS"}
        for i, name in enumerate(pivot_data["ranking_names"]):
            row_ws[name] = ws_list[i] if i < len(ws_list) else np.nan
        row_ws["Ranking de consenso"] = np.nan
        distance_rows.append(row_ws)

        distance_df = pd.DataFrame(distance_rows)
        final_df = pd.concat([merged_df, distance_df], ignore_index=True)

        st.dataframe(final_df, use_container_width=False)


        show_comparison_graphs(merged_df, pivot_data["ranking_names"], kendall_list, kendall_corr_list, spearman_list, ws_list)

        st.markdown("## Mapas de calor de distancias entre todos los rankings")
        tabs = st.tabs(["Distancia Kendall", "Coef. Kendall", "Coef. Spearman", "Coef. WS"])
        with tabs[0]:
            draw_distance_heatmap(kendall_matrix, ranking_labels, "Distancia Kendall")
        with tabs[1]:
            draw_distance_heatmap(kendall_corr_matrix, ranking_labels, "Coeficiente de Kendall")
        with tabs[2]:
            draw_distance_heatmap(spearman_matrix, ranking_labels, "Coeficiente de Spearman")
        with tabs[3]:
            draw_distance_heatmap(ws_matrix, ranking_labels, "Coeficiente WS")


    else:
        # Resultado del problema general
        agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
        if not agg_groups:
            st.warning("Este problema no tiene soluciones todavía.")
            return

        elementos = db.get_ranking_elements(group_id)
        elementos_sorted = sorted(elementos, key=lambda x: x['row_index'])
        element_names = [e['nombre'] for e in elementos_sorted]

        df_methods = pd.DataFrame()
        for agg in agg_groups:
            agg_id = agg["id"]
            algoritmo = agg["algoritmo"]
            agg_values = db.get_aggregated_ranking(agg_id)
            agg_values_sorted = sorted(agg_values, key=lambda x: x['Elemento'])
            try:
                posiciones = [int(row["posicion"]) for row in agg_values_sorted]
                if element_names[0] == "Ponderación":
                    del element_names[0]
                if len(posiciones) == len(element_names):
                    df_methods[algoritmo] = posiciones
            except:
                st.warning(f"No se pudieron cargar correctamente los datos de {algoritmo}.")

        df_methods.index = element_names

        if not df_methods.empty:
            st.markdown("### Comparación entre soluciones del problema")
            custom_heatmap(df_methods)
            custom_radar_chart(df_methods)
            # custom_mds_plot(df_methods)
        else:
            st.warning("No se generaron datos suficientes para visualizar rankings.")