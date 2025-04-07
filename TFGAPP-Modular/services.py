# services.py
import numpy as np
import pandas as pd
from pyRankMCDA.algorithm import rank_aggregation
from utils import ws_coefficient

class RankingService:
    def __init__(self, db):
        self.db = db

    def guardar_datos_excel(self, parsed_data):
        group_id = self.db.add_group(parsed_data['group_name'])
        ranking_ids = {}
        for j, name in enumerate(parsed_data['ranking_names'], start=1):
            ranking_ids[j] = self.db.add_ranking(group_id, name, j)

        element_ids = {}
        for i, name in enumerate(parsed_data['element_names'], start=2):
            element_ids[i] = self.db.add_ranking_element(group_id, name, i)

        for (i, j), pos in parsed_data['values'].items():
            self.db.add_ranking_value(ranking_ids[j], element_ids[i], pos)

        return group_id

    def ejecutar_agregacion(self, group_id, algoritmo):
        rankings = self.db.get_rankings(group_id)
        if not rankings:
            return None, "No hay rankings en este grupo."

        ranking_lists = []
        for ranking in rankings:
            values = self.db.get_ranking_values(ranking['id'])
            values_sorted = sorted(values, key=lambda x: x['row_index'])
            try:
                ranking_list = [int(item['posicion']) for item in values_sorted]
            except Exception as e:
                return None, f"Error convirtiendo valores: {e}"
            ranking_lists.append(ranking_list)

        try:
            ranks_array = np.array(ranking_lists).T
        except Exception as e:
            return None, f"Error al convertir rankings a matriz: {e}"

        ra = rank_aggregation(ranks_array)
        try:
            if algoritmo == "Borda":
                result = ra.borda_method(verbose=False)
            elif algoritmo == "Copeland":
                result = ra.copeland_method(verbose=False)
            elif algoritmo == "Kemey-Young":
                result = ra.kemeny_young(verbose=False)
            elif algoritmo == "Schulze":
                result = ra.schulze_method(verbose=False)
            elif algoritmo == "Footrule":
                result = ra.footrule_rank_aggregation(verbose=False)
            else:
                return None, "Algoritmo no válido."
        except Exception as e:
            return None, f"Error en algoritmo de agregación: {e}"

        return result, None

    def guardar_agregacion(self, group_id, algoritmo, aggregated_ranking):
        agg_id = self.db.add_aggregated_ranking(group_id, algoritmo)
        elements = self.db.get_ranking_elements(group_id)
        elements_sorted = sorted(elements, key=lambda x: x['row_index'])
        for idx, elem in enumerate(elements_sorted):
            pos = int(aggregated_ranking[idx])
            self.db.add_aggregated_ranking_value(agg_id, elem['id'], pos)
        return agg_id

    def calcular_metricas_comparacion(self, group_id, agg_ranking):
        rankings = self.db.get_rankings(group_id)
        kendall_list, spearman_list, ws_list = [], [], []
        for ranking in rankings:
            values = self.db.get_ranking_values(ranking['id'])
            values_sorted = sorted(values, key=lambda x: x['row_index'])
            individual = [int(item['posicion']) for item in values_sorted]
            ra = rank_aggregation(np.array(agg_ranking).reshape(-1, 1))
            kendall_list.append(ra.kendall_tau_distance(np.array(individual), np.array(agg_ranking)))
            spearman_list.append(ra.spearman_rank(np.array(individual), np.array(agg_ranking)))
            ws_list.append(ws_coefficient(individual, agg_ranking))

        return kendall_list, spearman_list, ws_list
