import streamlit as st
import json
import sqlite3
import numpy as np

# Importa las funciones de la base de datos
from db import init_db, add_ranking, get_rankings

# Importa el algoritmo de agregación de rankings
from pyRankMCDA.algorithm import rank_aggregation

# Función para calcular el coeficiente WS (ejemplo básico)
def ws_coefficient(rank1, rank2):
    n = len(rank1)
    max_distance = sum(abs(i - (n + 1 - i)) for i in range(1, n + 1))
    dist = sum(abs(r1 - r2) for r1, r2 in zip(rank1, rank2))
    return 1 - dist / max_distance if max_distance != 0 else 1

def main():
    st.title("Aplicación de Agregación de Rankings")
    
    # Inicializa la base de datos
    conn = init_db()
    
    # Menú de navegación lateral
    menu = st.sidebar.selectbox("Selecciona una opción", ["Agregar Ranking", "Ver Rankings", "Comparar Agregaciones"])
    
    if menu == "Agregar Ranking":
        st.header("Agregar un nuevo Ranking")
        name = st.text_input("Nombre del Ranking")
        ranking_input = st.text_area("Introduce el ranking separado por comas (ej: 1,2,3,4 o A,B,C,D)")
        if st.button("Guardar Ranking"):
            if name and ranking_input:
                ranking_items = [item.strip() for item in ranking_input.split(",")]
                # Intenta convertir los elementos a números; si falla, asigna el orden de aparición
                try:
                    ranking = [int(item) for item in ranking_items]
                except ValueError:
                    ranking = list(range(1, len(ranking_items) + 1))
                add_ranking(conn, name, ranking)
                st.success("Ranking guardado correctamente.")
            else:
                st.error("Por favor ingresa un nombre y un ranking.")
    
    elif menu == "Ver Rankings":
        st.header("Lista de Rankings Guardados")
        rankings = get_rankings(conn)
        if rankings:
            for item in rankings:
                st.write(f"ID: {item['id']} - Nombre: {item['name']} - Ranking: {item['ranking']}")
        else:
            st.write("No hay rankings guardados.")
    
    elif menu == "Comparar Agregaciones":
        st.header("Comparación de Agregación de Rankings")
        rankings = get_rankings(conn)
        if len(rankings) < 2:
            st.warning("Necesitas al menos dos rankings para comparar.")
        else:
            # Permite seleccionar el algoritmo de agregación
            algorithm = st.selectbox("Selecciona el método de agregación", 
                                     ["Borda", "Copeland", "Kemey-Young", "Schulze", "Footrule"])
            
            if st.button("Ejecutar Agregación"):
                # Convierte los rankings a arrays numéricos
                try:
                    ranking_lists = [list(map(int, item["ranking"])) for item in rankings]
                except Exception as e:
                    st.error("Error al convertir rankings a números. Asegúrate de que sean numéricos.")
                    return
                ranks_array = np.array(ranking_lists)
                
                # Inicializa el objeto de agregación
                ra = rank_aggregation(ranks_array)
                
                # Ejecuta el método seleccionado
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
                
                # Comparación con cada ranking individual
                st.subheader("Comparación con Rankings Individuales")
                kendall_list = []
                spearman_list = []
                ws_list = []
                
                aggregated_ranking = aggregated_ranking.astype(int)
                for item in rankings:
                    try:
                        individual = np.array(list(map(int, item["ranking"])))
                    except Exception as e:
                        st.error("Error al convertir un ranking individual a números.")
                        continue
                    kd = ra.kendall_tau_distance(individual, aggregated_ranking)
                    sp = ra.spearman_rank(individual, aggregated_ranking)
                    ws = ws_coefficient(individual, aggregated_ranking)
                    kendall_list.append(kd)
                    spearman_list.append(sp)
                    ws_list.append(ws)
                
                st.write("Distancia de Kendall:", kendall_list)
                st.write("Coeficiente de Spearman:", spearman_list)
                st.write("Coeficiente WS:", ws_list)

if __name__ == '__main__':
    main()
