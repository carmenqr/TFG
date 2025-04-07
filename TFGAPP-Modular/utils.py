# utils.py
import numpy as np
import pandas as pd

def ws_coefficient(rank1, rank2):
    """Coeficiente WS: mide la distancia relativa entre dos rankings"""
    n = len(rank1)
    max_distance = sum(abs(i - (n + 1 - i)) for i in range(1, n + 1))
    dist = sum(abs(r1 - r2) for r1, r2 in zip(rank1, rank2))
    return 1 - dist / max_distance if max_distance != 0 else 1

def parse_excel(df):
    """Parsea un DataFrame de Excel en formato personalizado a estructura interna"""
    group_name = df.iloc[0, 0]
    ranking_names = [df.iloc[1, j] for j in range(1, df.shape[1])]
    element_names = [df.iloc[i, 0] for i in range(2, df.shape[0])]

    values = {}
    for i in range(2, df.shape[0]):
        for j in range(1, df.shape[1]):
            try:
                pos = int(df.iloc[i, j])
            except:
                pos = df.iloc[i, j]
            values[(i, j)] = pos

    return {
        "group_name": group_name,
        "ranking_names": ranking_names,
        "element_names": element_names,
        "values": values
    }

def build_distance_rows(ranking_names, kendall_list, spearman_list, ws_list):
    """Construye las filas de distancias para agregar a la tabla final"""
    distance_rows = []
    row_kendall = {"Elemento": "Distancia Kendall"}
    row_spearman = {"Elemento": "Coeficiente Spearman"}
    row_ws = {"Elemento": "Coeficiente WS"}

    for i, name in enumerate(ranking_names):
        row_kendall[name] = kendall_list[i] if i < len(kendall_list) else np.nan
        row_spearman[name] = spearman_list[i] if i < len(spearman_list) else np.nan
        row_ws[name] = ws_list[i] if i < len(ws_list) else np.nan

    row_kendall["Ranking Agregado"] = np.nan
    row_spearman["Ranking Agregado"] = np.nan
    row_ws["Ranking Agregado"] = np.nan

    distance_rows.extend([row_kendall, row_spearman, row_ws])
    return pd.DataFrame(distance_rows)
