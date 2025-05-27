import streamlit as st
import pandas as pd
from pyRankMCDA.algorithm import rank_aggregation
from utils import custom_heatmap, custom_radar_chart, custom_mds_plot, show_comparison_graphs, ws_coefficient
import numpy as np

def comparar_algoritmos_tab(db):
    st.header("Tipo de resultado:")
    modo_comparacion = st.radio("Tipo de resultado", ["Resultado del problema general", "Resultado por tipo de solución ejecutada"], label_visibility="collapsed")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if not groups:
        st.info("No hay grupos disponibles.")
    else:
        group_options = {f"{group['nombre']} (Grupo: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Selecciona el grupo a comparar", list(group_options.keys()))
        group_id = group_options[selected_group]

        if modo_comparacion == "Resultado por tipo de solución ejecutada":                    
            # Recuperamos los rankings individuales del grupo
            rankings = db.get_rankings(group_id)
            if len(rankings) < 2:
                st.warning("Necesitas al menos dos rankings para comparar.")
            else:
                # Selector de la agregación disponible para el grupo
                agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
                if not agg_groups:
                    st.error("No hay ranking agregado para este grupo. Ejecuta una agregación primero.")
                else:
                    agg_options = {f"{agg['algoritmo']} (Agregación: {agg['id']})": agg['id'] for agg in agg_groups}
                    selected_agg = st.selectbox("Selecciona el algoritmo de agregación a comparar", list(agg_options.keys()))
                    agg_id = agg_options[selected_agg]
                    
                    # Obtenemos la vista pivot del grupo (tabla completa con todos los rankings)
                    pivot_data = db.get_group_excel_format(group_id)
                    if pivot_data:
                        pivot_df = pd.DataFrame(pivot_data["rows"])
                        pivot_df.columns = ["Elemento"] + pivot_data["ranking_names"]
                        # Obtenemos el ranking agregado para el grupo
                        agg_data = db.get_aggregated_ranking(agg_id)
                        if agg_data:
                            agg_df = pd.DataFrame([dict(row) for row in agg_data])
                            if "elemento" in agg_df.columns and "Elemento" not in agg_df.columns:
                                agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
                            agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)
                            merged_df = pivot_df.merge(agg_df, on="Elemento", how="left")
                            # Se omite la visualización de merged_df por separado
                        else:
                            st.error("No se encontraron datos en el ranking agregado.")
                            return
                    else:
                        st.write("No hay datos para este grupo.")
                        return
                    
                    # --- Calcular las comparaciones para cada ranking individual ---
                    agg_data = db.get_aggregated_ranking(agg_id)
                    agg_row = db.connection.execute("SELECT aggregation_type FROM RankingGroup WHERE id = ?", (group_id,)).fetchone()
                    agg_type = agg_row["aggregation_type"].strip().lower() if agg_row and agg_row["aggregation_type"] else ""

                    if agg_data:
                        agg_ranking = [int(item['posicion']) for item in agg_data]
                    else:
                        st.error("No se pudo obtener el ranking agregado para comparaciones.")
                        return
                            
                    kendall_list = []
                    kendall_corr_list = []
                    spearman_list = []
                    ws_list = []
                    
                    for ranking in rankings:
                        values = db.get_ranking_values(ranking['id'])
                        if agg_type == "ponderaciones":
                            values_sorted = sorted([v for v in values if v['row_index'] > 2], key=lambda x: x['row_index'])
                        else:
                            values_sorted = sorted(values, key=lambda x: x['row_index'])

                        try:
                            individual = [int(item['posicion']) for item in values_sorted]
                        except Exception as e:
                            st.error("Error al convertir ranking individual a números.")
                            continue
                        if len(individual) != len(agg_ranking):
                            st.error(f"El ranking individual tiene {len(individual)} elementos, pero el ranking agregado tiene {len(agg_ranking)} elementos.")
                            continue
                        ra = rank_aggregation(np.array(agg_ranking).reshape(-1, 1))
                        kd = ra.kendall_tau_distance(np.array(individual), np.array(agg_ranking))
                        kdc = ra.kendall_tau_corr(np.array(individual), np.array(agg_ranking))
                        sp = ra.spearman_rank(np.array(individual), np.array(agg_ranking))
                        ws_val = ws_coefficient(individual, agg_ranking)
                        kendall_list.append(kd)
                        kendall_corr_list.append(kdc)
                        spearman_list.append(sp)
                        ws_list.append(ws_val)
                    
                    # --- Agregar las filas de las comparaciones a la tabla ---
                    ranking_names = pivot_data["ranking_names"]
                    distance_rows = []
                    row_kendall = {"Elemento": "Distancia Kendall"}
                    for i, name in enumerate(ranking_names):
                        row_kendall[name] = kendall_list[i] if i < len(kendall_list) else np.nan
                    row_kendall["Ranking Agregado"] = np.nan
                    distance_rows.append(row_kendall)
                    
                    row_kendall_corr = {"Elemento": "Coeficiente Kendall"}
                    for i, name in enumerate(ranking_names):
                        row_kendall_corr[name] = kendall_corr_list[i] if i < len(kendall_corr_list) else np.nan
                    row_kendall_corr["Ranking Agregado"] = np.nan
                    distance_rows.append(row_kendall_corr)
                    
                    row_spearman = {"Elemento": "Coeficiente Spearman"}
                    for i, name in enumerate(ranking_names):
                        row_spearman[name] = spearman_list[i] if i < len(spearman_list) else np.nan
                    row_spearman["Ranking Agregado"] = np.nan
                    distance_rows.append(row_spearman)
                    
                    row_ws = {"Elemento": "Coeficiente WS"}
                    for i, name in enumerate(ranking_names):
                        row_ws[name] = ws_list[i] if i < len(ws_list) else np.nan
                    row_ws["Ranking Agregado"] = np.nan
                    distance_rows.append(row_ws)
                    
                    distance_df = pd.DataFrame(distance_rows)
                    final_df = pd.concat([merged_df, distance_df], ignore_index=True)
                    
                    st.subheader("Tabla comparativa con métricas de distancia")
                    st.write("Distancias entre el ranking agregado (con el algoritmo seleccionado) y los rankings individuales")
                    st.dataframe(final_df, use_container_width=False)
                    show_comparison_graphs(merged_df, ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list)

        else:  # Por Grupo
            agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
            if not agg_groups:
                st.warning("Este grupo no tiene agregaciones todavía.")
            else:
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
                        if (element_names[0] == "Ponderación"):
                            del element_names[0]
                        if len(posiciones) == len(element_names):
                            df_methods[algoritmo] = posiciones
                    except:
                        st.warning(f"No se pudieron cargar correctamente los datos de {algoritmo}.")

                df_methods.index = element_names

                if not df_methods.empty:
                    st.write("Gráficas comparativas entre los rankings agregados con los diferentes algoritmos de agregación aplicados al grupo de rankings seleccionado")
                    custom_heatmap(df_methods)
                    custom_radar_chart(df_methods)
                    custom_mds_plot(df_methods)
                else:
                    st.warning("No se generaron datos suficientes para visualizar rankings.")
