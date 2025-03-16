import streamlit as st
import pandas as pd
import numpy as np
from streamlit_option_menu import option_menu
from db import RankingDB  # Se asume que bd.py define la clase RankingDB
from pyRankMCDA.algorithm import rank_aggregation  # Algoritmo de agregación

# Función de ejemplo para el coeficiente WS
def ws_coefficient(rank1, rank2):
    n = len(rank1)
    max_distance = sum(abs(i - (n + 1 - i)) for i in range(1, n + 1))
    dist = sum(abs(r1 - r2) for r1, r2 in zip(rank1, rank2))
    return 1 - dist / max_distance if max_distance != 0 else 1

def main():
    st.set_page_config(layout="wide")
    st.title("App para la Agregación de Rankings")
    db = RankingDB()  # Inicializa la base de datos

    # --- Menú principal en la barra lateral ---
    main_choice = option_menu(
        menu_title="Menú Principal",  # Título del menú
        options=["Rankings", "Agregaciones"],
        icons=["clipboard-data", "bar-chart-line"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

    # --- Sección Rankings ---
    if main_choice == "Rankings":
        sub_choice = option_menu(
            menu_title="Rankings",
            options=["Añadir rankings", "Eliminar rankings", "Ver rankings"],
            icons=["plus-square", "dash-square", "eye"],
            menu_icon="list-task",
            default_index=0,
            orientation="vertical"
        )

        if sub_choice == "Añadir rankings":
            st.header("Añadir Rankings desde Excel")
            uploaded_file = st.file_uploader("Carga un archivo Excel (.xlsx)", type=["xlsx"])
            if uploaded_file is not None:
                try:
                    df = pd.read_excel(uploaded_file, header=None)
                    st.write("Vista previa del Excel:")
                    st.dataframe(df)
                    if st.button("Guardar en la base de datos"):
                        group_name = df.iloc[0, 0]
                        group_id = db.add_group(group_name)
                        ranking_ids = {}
                        for j in range(1, df.shape[1]):
                            ranking_name = df.iloc[1, j]
                            ranking_id = db.add_ranking(group_id, ranking_name, j)
                            ranking_ids[j] = ranking_id
                        element_ids = {}
                        for i in range(2, df.shape[0]):
                            element_name = df.iloc[i, 0]
                            element_id = db.add_ranking_element(group_id, element_name, i)
                            element_ids[i] = element_id
                        for i in range(2, df.shape[0]):
                            for j in range(1, df.shape[1]):
                                value = df.iloc[i, j]
                                try:
                                    pos = int(value)
                                except:
                                    pos = value
                                db.add_ranking_value(ranking_ids[j], element_ids[i], pos)
                        st.success("Datos guardados correctamente en la base de datos.")
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")

        elif sub_choice == "Eliminar rankings":
            st.header("Eliminar Grupo de Rankings")
            groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
            if groups:
                group_options = {f"{group['id']} - {group['nombre']}": group['id'] for group in groups}
                selected_group = st.selectbox("Selecciona el grupo a eliminar", list(group_options.keys()))
                if st.button("Eliminar grupo"):
                    group_id = group_options[selected_group]
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

        elif sub_choice == "Ver rankings":
            st.header("Ver Rankings")
            groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
            if groups:
                group_options = {f"{group['nombre']} (ID: {group['id']})": group['id'] for group in groups}
                selected_group = st.selectbox("Selecciona el grupo a visualizar", list(group_options.keys()))
                group_id = group_options[selected_group]
                pivot_data = db.get_group_excel_format(group_id)
                if pivot_data:
                    df_pivot = pd.DataFrame(pivot_data["rows"])
                    df_pivot.columns = ["Elemento"] + pivot_data["ranking_names"]
                    st.dataframe(df_pivot)
                else:
                    st.write("No hay datos para este grupo.")
            else:
                st.info("No hay grupos de rankings guardados.")

    # --- Sección Agregaciones ---
    else:  # main_choice == "Agregaciones"
        sub_choice = option_menu(
            menu_title="Agregaciones",
            options=["Agregar rankings", "Ver agregaciones", "Eliminar agregaciones", "Comparación"],
            icons=["plus-circle", "eye", "dash-circle", "graph-up"],
            menu_icon="activity",
            default_index=0,
            orientation="vertical"
        )

        if sub_choice == "Agregar rankings":
            st.header("Agregar Rankings (Agregación)")
            groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
            if groups:
                group_options = {f"{group['id']} - {group['nombre']}": group['id'] for group in groups}
                selected_group = st.selectbox("Selecciona el grupo de rankings a agregar", list(group_options.keys()))
                algorithm = st.selectbox("Selecciona el algoritmo de agregación", 
                                         ["Borda", "Copeland", "Kemey-Young", "Schulze", "Footrule"])
                if st.button("Ejecutar Agregación"):
                    group_id = group_options[selected_group]
                    rankings = db.get_rankings(group_id)
                    if not rankings:
                        st.error("No hay rankings en este grupo.")
                    else:
                        ranking_lists = []
                        for ranking in rankings:
                            values = db.get_ranking_values(ranking['id'])
                            values_sorted = sorted(values, key=lambda x: x['row_index'])
                            try:
                                ranking_list = [int(item['posicion']) for item in values_sorted]
                            except Exception as e:
                                st.error("Error al convertir los valores del ranking a números.")
                                return
                            ranking_lists.append(ranking_list)
                        try:
                            ranks_array = np.array(ranking_lists).T
                        except Exception as e:
                            st.error("Error al convertir los rankings a matriz numérica.")
                            return
                        ra = rank_aggregation(ranks_array)
                        if algorithm == "Borda":
                            aggregated_ranking = ra.borda_method(verbose=False)
                        elif algorithm == "Copeland":
                            aggregated_ranking = ra.copeland_method(verbose=False)
                        elif algorithm == "Kemey-Young":
                            aggregated_ranking = ra.fast_kemeny_young(verbose=False)
                        elif algorithm == "Schulze":
                            aggregated_ranking = ra.schulze_method(verbose=False)
                        elif algorithm == "Footrule":
                            aggregated_ranking = ra.footrule_rank_aggregation(verbose=False)
                        st.subheader("Ranking Agregado")
                        st.write(aggregated_ranking)
                        agg_id = db.add_aggregated_ranking(group_id, algorithm)
                        elements = db.get_ranking_elements(group_id)
                        elements_sorted = sorted(elements, key=lambda x: x['row_index'])
                        for idx, elem in enumerate(elements_sorted):
                            try:
                                pos = int(aggregated_ranking[idx])
                            except Exception as e:
                                pos = aggregated_ranking[idx]
                            db.add_aggregated_ranking_value(agg_id, elem['id'], pos)
                        st.success("Ranking agregado guardado correctamente.")
            else:
                st.info("No hay grupos disponibles para agregar rankings.")

        elif sub_choice == "Ver agregaciones":
            st.header("Ver Agregaciones")
            agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking").fetchall()
            if agg_groups:
                agg_options = {f"{agg['id']} - {agg['algoritmo']} (Grupo {agg['grupo_id']})": agg['id']
                               for agg in agg_groups}
                selected_agg = st.selectbox("Selecciona el ranking agregado a ver", list(agg_options.keys()))
                agg_id = agg_options[selected_agg]
                cursor = db.connection.cursor()
                cursor.execute("SELECT * FROM AggregatedRanking WHERE id = ?", (agg_id,))
                agg_record = cursor.fetchone()
                if not agg_record:
                    st.error("No se encontró la agregación.")
                else:
                    group_id = agg_record["grupo_id"]
                    pivot_data = db.get_group_excel_format(group_id)
                    if pivot_data:
                        pivot_df = pd.DataFrame(pivot_data["rows"])
                        pivot_df.columns = ["Elemento"] + pivot_data["ranking_names"]
                        agg_data = db.get_aggregated_ranking(agg_id)
                        if not agg_data:
                            st.write("No hay valores para esta agregación.")
                        else:
                            agg_df = pd.DataFrame([dict(row) for row in agg_data])
                            if "elemento" in agg_df.columns and "Elemento" not in agg_df.columns:
                                agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
                            agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)
                            merged_df = pivot_df.merge(agg_df, on="Elemento", how="left")
                            st.dataframe(merged_df)
                    else:
                        st.write("No hay datos para este grupo.")
            else:
                st.info("No hay agregaciones guardadas.")

        elif sub_choice == "Eliminar agregaciones":
            st.header("Eliminar Agregaciones")
            agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking").fetchall()
            if agg_groups:
                agg_options = {f"{agg['id']} - {agg['algoritmo']} (Grupo {agg['grupo_id']})": agg['id']
                               for agg in agg_groups}
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

        elif sub_choice == "Comparación":
            st.header("Comparar Agregaciones")
            groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
            if groups:
                group_options = {f"{group['id']} - {group['nombre']}": group['id'] for group in groups}
                selected_group = st.selectbox("Selecciona el grupo a comparar", list(group_options.keys()))
                group_id = group_options[selected_group]
                rankings = db.get_rankings(group_id)
                if len(rankings) < 2:
                    st.warning("Necesitas al menos dos rankings para comparar.")
                else:
                    agg_groups = db.connection.execute("SELECT * FROM AggregatedRanking WHERE grupo_id = ?", (group_id,)).fetchall()
                    if not agg_groups:
                        st.error("No hay ranking agregado para este grupo. Ejecuta una agregación primero.")
                    else:
                        agg_options = {f"{agg['id']} - {agg['algoritmo']}": agg['id'] for agg in agg_groups}
                        selected_agg = st.selectbox("Selecciona la agregación a comparar", list(agg_options.keys()))
                        agg_id = agg_options[selected_agg]
                        pivot_data = db.get_group_excel_format(group_id)
                        if pivot_data:
                            pivot_df = pd.DataFrame(pivot_data["rows"])
                            pivot_df.columns = ["Elemento"] + pivot_data["ranking_names"]
                            agg_data = db.get_aggregated_ranking(agg_id)
                            if agg_data:
                                agg_df = pd.DataFrame([dict(row) for row in agg_data])
                                if "elemento" in agg_df.columns and "Elemento" not in agg_df.columns:
                                    agg_df.rename(columns={"elemento": "Elemento"}, inplace=True)
                                agg_df.rename(columns={"posicion": "Ranking Agregado"}, inplace=True)
                                merged_df = pivot_df.merge(agg_df, on="Elemento", how="left")
                                st.subheader("Tabla Completa con Ranking Agregado")
                                st.dataframe(merged_df)
                            else:
                                st.error("No se encontraron datos en el ranking agregado.")
                        else:
                            st.write("No hay datos para este grupo.")
                        
                        if agg_data:
                            agg_ranking = [int(item['posicion']) for item in agg_data]
                        else:
                            st.error("No se pudo obtener el ranking agregado para comparaciones.")
                            return
                            
                        kendall_list = []
                        spearman_list = []
                        ws_list = []
                        
                        for ranking in rankings:
                            values = db.get_ranking_values(ranking['id'])
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
                            sp = ra.spearman_rank(np.array(individual), np.array(agg_ranking))
                            ws_val = ws_coefficient(individual, agg_ranking)
                            kendall_list.append(kd)
                            spearman_list.append(sp)
                            ws_list.append(ws_val)
                        
                        ranking_names = pivot_data["ranking_names"]
                        distance_rows = []
                        row_kendall = {"Elemento": "Distancia Kendall"}
                        for i, name in enumerate(ranking_names):
                            row_kendall[name] = kendall_list[i] if i < len(kendall_list) else np.nan
                        row_kendall["Ranking Agregado"] = np.nan
                        distance_rows.append(row_kendall)
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
                        
                        st.subheader("Tabla Comparativa con Métricas de Distancia")
                        st.dataframe(final_df)
            else:
                st.info("No hay grupos de rankings disponibles.")

if __name__ == '__main__':
    main()
