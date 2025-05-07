import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import MDS
import plotly.express as px
import plotly.graph_objects as go
from pyRankMCDA.algorithm import rank_aggregation 

#MÉTRICA COEFICIENTE WS
""" def ws_coefficient(rank1, rank2):
    n = len(rank1)
    ws_sum = 0
    for rxi, ryi in zip(rank1, rank2):
        penalty = 2 ** (-rxi)
        normalization = max(abs(1 - rxi), abs(n - rxi))
        diff = abs(rxi - ryi)
        ws_sum += penalty * (diff / normalization if normalization != 0 else 0)
    return 1 - ws_sum """

def ws_coefficient(rank1, rank2):
    try:
        n = len(rank1)
        ws_sum = 0
        for idx, (rxi, ryi) in enumerate(zip(rank1, rank2)):
            try:
                penalty = 2 ** (-float(rxi))  # Convertir a float para evitar error con enteros negativos
                normalization = max(abs(1 - rxi), abs(n - rxi))
                diff = abs(rxi - ryi)
                ws_sum += penalty * (diff / normalization if normalization != 0 else 0)
            except Exception as inner_e:
                print(f"[WS ERROR] Elemento #{idx} → rxi={rxi}, ryi={ryi} → Error: {inner_e}")
                raise inner_e

        return 1 - ws_sum

    except Exception as outer_e:
        print(f"[WS COEFFICIENT ERROR] rank1={rank1}, rank2={rank2} → Error: {outer_e}")
        raise outer_e


#VARIANTES DE ALGORITMOS DE AGREGACIÓN
def borda_with_ties(rankings_matrix):
    rankings_matrix = np.array(rankings_matrix)
    n_elements, n_rankings = rankings_matrix.shape
    scores = np.zeros(n_elements)

    for j in range(n_rankings):
        col = rankings_matrix[:, j]
        pos_to_indices = {}
        for idx, val in enumerate(col):
            pos_to_indices.setdefault(val, []).append(idx)

        for pos, indices in pos_to_indices.items():
            base_scores = [n_elements - pos for _ in indices]
            avg_score = np.mean(base_scores)
            for idx in indices:
                scores[idx] += avg_score

    ordered_indices = np.argsort(-scores)
    final_ranking = np.empty_like(ordered_indices)
    for i, idx in enumerate(ordered_indices):
        final_ranking[idx] = i + 1
    return final_ranking

def copeland_ponderado(rankings_matrix, pesos):
    rankings_matrix = np.array(rankings_matrix)
    n_elements, n_rankings = rankings_matrix.shape
    scores = np.zeros(n_elements)

    for i in range(n_elements):
        for j in range(n_elements):
            if i != j:
                win_score = 0
                for k in range(n_rankings):
                    if rankings_matrix[i][k] < rankings_matrix[j][k]:
                        win_score += pesos[k]
                    elif rankings_matrix[i][k] > rankings_matrix[j][k]:
                        win_score -= pesos[k]
                scores[i] += (win_score > 0) - (win_score < 0)

    ordered_indices = np.argsort(-scores)
    final_ranking = np.empty_like(ordered_indices)
    for i, idx in enumerate(ordered_indices):
        final_ranking[idx] = i + 1
    return final_ranking

def custom_heatmap(df):
    st.markdown("#### Heatmap con las posiciones de los rankings agregados")
    try:
        z = df.values
        x = list(df.columns)
        y = list(df.index)

        fig = go.Figure(data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            colorscale='RdBu',
            reversescale=True,
            showscale=True,
            colorbar=dict(title="Ranking")
        ))

        annotations = []
        for i in range(len(y)):
            for j in range(len(x)):
                annotations.append(dict(
                    x=x[j],
                    y=y[i],
                    text=str(z[i][j]),
                    showarrow=False,
                    font=dict(color="black", size=16)
                ))

        fig.update_layout(
            xaxis_title="Método",
            yaxis_title="Elemento",
            annotations=annotations,
            height=500,
            xaxis=dict(tickfont=dict(size=16), title_font=dict(size=18)),
            yaxis=dict(tickfont=dict(size=16), title_font=dict(size=18)),
        )

        st.plotly_chart(fig, use_container_width=True)
        return fig
    except Exception as e:
        st.warning(f"No se pudo generar el heatmap interactivo: {e}")
        return None

def custom_radar_chart(df):
    st.markdown("#### Radar Charts por Método de Agregación")
    num_vars = df.shape[0]
    categories = list(df.index)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    n_cols = 5
    n_rows = int(np.ceil(len(df.columns) / n_cols))
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(2.2 * n_cols, 2.2 * n_rows), subplot_kw=dict(polar=True))
    axs = axs.flatten()

    colors = plt.cm.tab10(np.linspace(0, 1, len(df.columns)))

    for i, (method, color) in enumerate(zip(df.columns, colors)):
        ax = axs[i]
        values = df[method].tolist()
        values += values[:1]
        ax.plot(angles, values, label=method, color=color)
        ax.fill(angles, values, alpha=0.1, color=color)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=6)
        ax.set_title(method, fontsize=8)
        ax.set_yticks(range(1, num_vars + 1))
        ax.set_yticklabels(range(1, num_vars + 1), fontsize=5, color='gray')
        ax.yaxis.grid(True, linestyle='--', linewidth=0.5, color='lightgray')

    for j in range(i + 1, len(axs)):
        fig.delaxes(axs[j])

    plt.tight_layout()
    st.pyplot(fig)
    
def custom_mds_plot(df):
    st.markdown("#### MDS - Comparación de Distancias entre Métodos de agregación")
    methods = df.columns
    distances = np.zeros((len(methods), len(methods)))

    resumen = []
    for i in range(len(methods)):
        for j in range(len(methods)):
            if i != j:
                r1 = df.iloc[:, i].values
                r2 = df.iloc[:, j].values
                ra = rank_aggregation(np.array(r1).reshape(-1, 1))
                try:
                    kendall = ra.kendall_tau_distance(np.array(r2), np.array(r1))
                except:
                    kendall = 0.0
                try:
                    kendall_corr = ra.kendall_tau_corr(np.array(r2), np.array(r1))
                except:
                    kendall_corr = 0.0
                try:
                    spearman = ra.spearman_rank(np.array(r2), np.array(r1))
                except:
                    spearman = 0.0
                try:
                    ws = ws_coefficient(r2, r1)
                except:
                    ws = 0.0
                    
                total = spearman + kendall + ws + kendall_corr
                value = total if np.isfinite(total) else 0.0
                distances[i, j] = value
                distances[j, i] = value


                if j > i:
                    resumen.append({
                        "Método 1": methods[i],
                        "Método 2": methods[j],
                        "Distancia Kendall": round(kendall, 3),
                        "Coeficiente Kendall": round(kendall_corr, 3),
                        "Coeficiente Spearman": round(spearman, 3),
                        "Coeficiente WS": round(ws, 3)
                        })

    if np.any(np.isnan(distances)) or np.any(np.isinf(distances)):
        st.warning("La matriz de distancias contiene valores no válidos. No se puede generar el MDS.")
        return

    mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42)
    coords = mds.fit_transform(distances)

    df_coords = pd.DataFrame(coords, columns=["Dim 1", "Dim 2"])
    df_coords["Método"] = methods

    fig = px.scatter(
        df_coords,
        x="Dim 1",
        y="Dim 2",
        text="Método",
        width=800,
        height=500
    )

    fig.update_traces(
        marker=dict(size=14),
        textposition='top center',
        textfont=dict(size=14)
    )

    fig.update_layout(
        showlegend=False,
        plot_bgcolor="white",
        xaxis=dict(
            title="x",
            showgrid=True,
            zeroline=True,
            tickfont=dict(size=14)
        ),
        yaxis=dict(
            title="y",
            showgrid=True,
            zeroline=True,
            tickfont=dict(size=14)
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Tabla de distancias entre rankings agregados con los diferentes métodos de agregación")
    st.dataframe(pd.DataFrame(resumen))

# GRÁFICAS PARA COMPARACIÓN POR ALGORITMO DE AGREGACIÓN

def plot_ranking_positions(merged_df):
    try:
        df_plot = merged_df.copy().dropna()
        df_melted = df_plot.melt(id_vars=["Elemento"], var_name="Ranking", value_name="Posición")
        df_melted["Elemento"] = df_melted["Elemento"].astype(str)

        fig = px.bar(
            df_melted,
            x="Elemento",
            y="Posición",
            color="Ranking",
            barmode="group",
            labels={"Posición": "Posición", "Elemento": "Elemento"}
        )

        fig.update_layout(
            legend_title="Ranking",
            xaxis_tickangle=-45,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)
        return fig
    except Exception as e:
        st.warning(f"No se pudo generar el gráfico interactivo: {e}")
        return None

def plot_all_metrics(ranking_names, kendall, kendall_corr, spearman, ws):
    try:
        df = pd.DataFrame({
            "Ranking": ranking_names * 4,
            "Métrica": ["Dist Kendall"] * len(ranking_names) +
                       ["Coef Kendall"] * len(ranking_names) +
                       ["Coef Spearman"] * len(ranking_names) +
                       ["Coef WS"] * len(ranking_names),
            "Valor": kendall + kendall_corr + spearman + ws
        })

        fig = px.line(
            df,
            x="Ranking",
            y="Valor",
            color="Métrica",
            markers=True,
            labels={"Valor": "Valor", "Ranking": "Ranking"}
        )

        fig.update_layout(
            legend_title="Métrica",
            xaxis_tickangle=-45,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)
        return fig
    except Exception as e:
        st.warning(f"Error al generar gráfico de líneas interactivo: {e}")
        return None
      
def plot_all_distances_grouped(ranking_names, kendall, kendall_corr, spearman, ws):
    try:
        df = pd.DataFrame({
            "Ranking": ranking_names * 4,
            "Métrica": ["Dist Kendall"] * len(ranking_names) +
                       ["Coef Kendall"] * len(ranking_names) +
                       ["Coef Spearman"] * len(ranking_names) +
                       ["Coef WS"] * len(ranking_names),
            "Valor": kendall + kendall_corr + spearman +  ws
        })

        fig = px.bar(
            df,
            x="Ranking",
            y="Valor",
            color="Métrica",
            barmode="group",
            labels={"Valor": "Valor", "Ranking": "Ranking"}
        )

        fig.update_layout(
            legend_title="Métrica",
            xaxis_tickangle=-45,
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)
        return fig
    except Exception as e:
        st.warning(f"Error al generar gráfico interactivo de resumen: {e}")
        return None

# ORGANIZADOR DE GRÁFICAS POR ALGORITMO DE AGREGACIÓN
def show_comparison_graphs(merged_df, ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list):
    st.markdown("### Comparación de posiciones")
    plot_ranking_positions(merged_df)
    
    st.markdown("### Comparación de métricas")   
    plot_all_metrics(ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list)

    plot_all_distances_grouped(ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list)
