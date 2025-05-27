import streamlit as st
import pandas as pd
from pyRankMCDA.algorithm import rank_aggregation
from utils import borda_with_ties, copeland_ponderado
import numpy as np

def agregar_rankings_tab(db):
    st.header("Resolver")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        #group_options = {f"{group['id']} - {group['nombre']}": group['id'] for group in groups}
        group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Seleccione el problema a resolver", list(group_options.keys()))
        
        group_id = group_options[selected_group]
        agg_row = db.connection.execute("SELECT aggregation_type FROM RankingGroup WHERE id = ?", (group_id,)).fetchone()
        agg_type = agg_row["aggregation_type"].strip().lower() if agg_row and agg_row["aggregation_type"] else ""


        # Mostrar opciones según tipo detectado
        if agg_type == "empates":
            algorithm_options = ["Borda con Empates"]
            st.info("Solo se permite el algoritmo **Borda** porque se detectaron empates en el archivo Excel.")
        elif agg_type == "ponderaciones":
            algorithm_options = ["Borda Ponderado", "Copeland Ponderado"]
            st.info("Solo se permiten los algoritmos **Borda** y **Copeland** porque se detectaron ponderaciones.")
        else:
            algorithm_options = ["Borda", "Copeland", "Kemey-Young", "Schulze", "Footrule"]

        algorithm = st.selectbox("Seleccione el algoritmo de agregación con el que resolver el problema", algorithm_options)

        if st.button("Resolver"):
            group_id = group_options[selected_group]
            rankings = db.get_rankings(group_id)
            if not rankings:
                st.error("No hay rankings en este problema.")
            else:
                ranking_lists = []
                ponderaciones = []

                # Si es tipo ponderaciones, extraer los pesos desde la fila 2
                if agg_type == "ponderaciones":
                    pivot_data = db.get_group_excel_format(group_id)
                    df_ponderacion = pd.DataFrame(pivot_data["rows"])
                    try:
                        ponderaciones = [float(val) for val in df_ponderacion.iloc[0, 1:].tolist()]
                    except Exception as e:
                        st.error("Error al leer las ponderaciones. Asegúrate de que estén en la fila 2 del Excel.")
                        return

                for idx, ranking in enumerate(rankings):
                    values = db.get_ranking_values(ranking['id'])

                    if agg_type == "ponderaciones":
                        values_sorted = sorted([v for v in values if v['row_index'] > 2], key=lambda x: x['row_index'])
                    else:
                        values_sorted = sorted(values, key=lambda x: x['row_index'])

                    try:
                        ranking_list = [int(item['posicion']) for item in values_sorted]
                        # Aplicar ponderación si corresponde
                        if agg_type == "ponderaciones":
                            weight = ponderaciones[idx]
                            ranking_list = [val * weight for val in ranking_list]
                    except Exception as e:
                        st.error("Error al convertir o ponderar los valores del ranking.")
                        return

                    ranking_lists.append(ranking_list)            
                
                try:
                    ranks_array = np.array(ranking_lists).T
                except Exception as e:
                    st.error("Error al convertir los rankings a matriz numérica.")
                    return

                ra = rank_aggregation(ranks_array)
                if algorithm == "Borda" or algorithm == "Borda Ponderado":
                    elementos_ordenados = ra.borda_method(verbose=False)
                elif algorithm == "Borda con Empates":
                    aggregated_ranking = borda_with_ties(ranks_array)
                elif algorithm == "Copeland":
                    elementos_ordenados = ra.copeland_method(verbose=False)
                elif algorithm == "Copeland Ponderado":
                    aggregated_ranking = copeland_ponderado(ranks_array, ponderaciones)
                elif algorithm == "Kemey-Young":
                    aggregated_ranking = ra.kemeny_young(verbose=False)
                elif algorithm == "Schulze":
                    elementos_ordenados = ra.schulze_method(verbose=False)
                elif algorithm == "Footrule":
                    elementos_ordenados = ra.footrule_rank_aggregation(verbose=False)

                # Convertimos de "elementos en orden" → "posición final por elemento", menos en kemey que los devuelve así
                if(algorithm != "Kemey-Young" and algorithm != "Borda con Empates" and algorithm != "Copeland Ponderado"):
                    aggregated_ranking = np.empty_like(elementos_ordenados)
                    aggregated_ranking[elementos_ordenados - 1] = np.arange(1, len(elementos_ordenados) + 1)
                
                st.subheader("Ranking Agregado")
                st.write(aggregated_ranking)
                
                # Guardar el ranking agregado en la BD
                agg_id = db.add_aggregated_ranking(group_id, algorithm)
                elements = db.get_ranking_elements(group_id)

                # Si es ponderaciones, excluir la fila de ponderaciones
                if agg_type == "ponderaciones":
                    elements_sorted = sorted([e for e in elements if e['row_index'] > 2], key=lambda x: x['row_index'])
                else:
                    elements_sorted = sorted(elements, key=lambda x: x['row_index'])

                for idx, elem in enumerate(elements_sorted):
                    try:
                        pos = int(aggregated_ranking[idx])
                    except Exception:
                        pos = aggregated_ranking[idx]
                    db.add_aggregated_ranking_value(agg_id, elem['id'], pos)
                st.success("Ranking agregado guardado correctamente.")
    else:
        st.info("No hay problemas disponibles para resolver.")
        
def ver_agregaciones_tab(db):
    st.header("Ver Soluciones")
    # Selector de grupo: muestra "NombreDelGrupo (Grupo: id)"
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Seleccione el problema del que ver la solución", list(group_options.keys()))
        group_id = group_options[selected_group]
        
        # Selector de agregación para el grupo seleccionado: muestra "Algoritmo (Agregación: id)"
        agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
        if agg_groups:
            agg_options = {f"{agg['algoritmo']} (Agregación: {agg['id']})": agg['id'] for agg in agg_groups}
            selected_agg = st.selectbox("Seleccione el algoritmo del que desee ver la solucón para el problema seleccionado", list(agg_options.keys()))
            agg_id = agg_options[selected_agg]
            
            # Obtenemos la vista pivot del grupo (tabla completa con todos los rankings)
            pivot_data = db.get_group_excel_format(group_id)
            if pivot_data:
                pivot_df = pd.DataFrame(pivot_data["rows"])
                pivot_df.columns = ["Elemento"] + pivot_data["ranking_names"]
                
                # Obtenemos el ranking agregado para el grupo
                agg_data = db.get_aggregated_ranking(agg_id)
                if not agg_data:
                    st.write("No hay valores para esta agregación.")
                else:
                    # Convertimos cada fila a diccionario para garantizar las claves correctas
                    agg_df = pd.DataFrame([dict(row) for row in agg_data])
                    # Aseguramos que la columna del nombre del elemento se llame "Elemento"
                    if "elemento" in agg_df.columns and "Elemento" not in agg_df.columns:
                        agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
                    # Renombramos la columna 'posicion' a 'Ranking Agregado'
                    agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)
                    # Fusionamos usando la columna "Elemento"
                    merged_df = pivot_df.merge(agg_df, on="Elemento", how="left")
                    st.dataframe(merged_df, use_container_width=False)

            else:
                st.write("No hay datos para este problema.")
        else:
            st.info("No hay soluciones ejecutadas para este problema.")
    else:
        st.info("No hay problemas guardados.")
    
def eliminar_agregaciones_tab(db):
    st.header("Eliminar Soluciones")
    # Primero, obtenemos los grupos de rankings
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Seleccione el problema del que eliminar una solución ejecutada", list(group_options.keys()))
        group_id = group_options[selected_group]
        
        # Ahora, obtenemos las agregaciones correspondientes al grupo seleccionado
        agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
        if agg_groups:
            agg_options = {f"{agg['algoritmo']} (Agregación: {agg['id']})": agg['id'] for agg in agg_groups}
            selected_agg = st.selectbox("Seleccione la solución que desea eliminar", list(agg_options.keys()))
            agg_id = agg_options[selected_agg]
            
            if st.button("Eliminar Solución"):
                try:
                    db.delete_aggregated_ranking(agg_id)
                    st.success("Solución eliminada correctamente.")
                except Exception as e:
                    st.error(f"Error al eliminar la solución: {e}")
        else:
            st.info("No hay soluciones ejecutadas para el problema seleccionado.")
    else:
        st.info("No hay problemas guardados.")