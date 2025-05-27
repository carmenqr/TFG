import streamlit as st
import pandas as pd

def añadir_rankings_tab(db):
    st.header("Añadir Rankings desde Excel")
    st.markdown("Añada el grupo de rankings que contiene su problema")
    uploaded_file = st.file_uploader("Cargue un archivo Excel (.xlsx)", type=["xlsx"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file, header=None)
            st.write("Vista previa del Excel:")
            st.dataframe(df, use_container_width=False)
            if st.button("Guardar"):
                group_name = df.iloc[0, 0]
                aggregation_type = ""
                if df.shape[1] > 1:
                    aggregation_type = str(df.iloc[0, 1]).strip().lower()
                group_id = db.add_group(group_name, aggregation_type)

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

def eliminar_rankings_tab(db):
    st.header("Eliminar Rankings")
    st.markdown("Se eliminará el grupo de rankings que cargó desde un excel para resolver su problema")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Seleccione el problema a eliminar", list(group_options.keys()))
        if st.button("Eliminar problema"):
            group_id = group_options[selected_group]
            try:
                db.connection.execute("DELETE FROM RankingValue WHERE ranking_id IN (SELECT id FROM Ranking WHERE grupo_id = ?)", (group_id,))
                db.connection.execute("DELETE FROM Ranking WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM RankingElement WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM AggregatedRankingValue WHERE aggregated_ranking_id IN (SELECT id FROM AggregatedRanking WHERE grupo_id = ?)", (group_id,))
                db.connection.execute("DELETE FROM AggregatedRanking WHERE grupo_id = ?", (group_id,))
                db.connection.execute("DELETE FROM RankingGroup WHERE id = ?", (group_id,))
                db.connection.commit()
                st.success("problema eliminado correctamente.")
            except Exception as e:
                st.error(f"Error al eliminar el problema: {e}")
    else:
        st.info("No hay problemas disponibles para eliminar.")

def ver_rankings_tab(db):
    st.header("Ver Rankings")
    groups = db.connection.execute("SELECT * FROM RankingGroup").fetchall()
    if groups:
        group_options = {f"{group['nombre']} (Problema: {group['id']})": group['id'] for group in groups}
        selected_group = st.selectbox("Seleccione el problema a visualizar", list(group_options.keys()))
        group_id = group_options[selected_group]
        pivot_data = db.get_group_excel_format(group_id)
        if pivot_data:
            df_pivot = pd.DataFrame(pivot_data["rows"])
            df_pivot.columns = ["Elemento"] + pivot_data["ranking_names"]
            st.dataframe(df_pivot, use_container_width=False)
        else:
            st.write("No hay datos para este problema.")
    else:
        st.info("No hay problemas de rankings guardados.")
