import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import MDS

def ws_coefficient(rank1, rank2):
    n = len(rank1)
    ws_sum = 0
    for rxi, ryi in zip(rank1, rank2):
        penalty = 2 ** (-rxi)
        normalization = max(abs(1 - rxi), abs(n - rxi))
        diff = abs(rxi - ryi)
        ws_sum += penalty * (diff / normalization if normalization != 0 else 0)
    return 1 - ws_sum

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
    plt.figure(figsize=(12, 6))
    sns.heatmap(df, annot=True, cmap='coolwarm', fmt='d', linewidths=0.5, cbar=True)
    plt.title("Heatmap de Rankings Agregados")
    plt.xlabel("Método")
    plt.ylabel("Elemento")
    st.pyplot(plt.gcf())

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
    st.markdown("#### MDS - Comparación de Distancias entre Métodos")
    methods = df.columns
    distances = np.zeros((len(methods), len(methods)))

    for i in range(len(methods)):
        for j in range(len(methods)):
            if i != j:
                r1 = df.iloc[:, i].values
                r2 = df.iloc[:, j].values
                kendall = np.sum([1 for a, b in zip(r1, r2) if a != b])
                try:
                    spearman = np.corrcoef(r1, r2)[0, 1]
                except:
                    spearman = 0.0
                try:
                    ws = ws_coefficient(r1, r2)
                except:
                    ws = 0.0
                total = (1 - spearman) + kendall + (1 - ws)
                if np.isfinite(total):
                    distances[i, j] = total
                else:
                    distances[i, j] = 0.0

    if np.any(np.isnan(distances)) or np.any(np.isinf(distances)):
        st.warning("La matriz de distancias contiene valores no válidos. No se puede generar el MDS.")
        return

    mds = MDS(n_components=2, dissimilarity='precomputed', random_state=42)
    coords = mds.fit_transform(distances)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(coords[:, 0], coords[:, 1], s=100)
    for i, method in enumerate(methods):
        ax.text(coords[i, 0], coords[i, 1], method, fontsize=10, ha='center')
    ax.set_title("MDS - Resumen de Distancias entre Rankings Agregados")
    ax.grid(True)
    st.pyplot(fig, use_container_width=False, clear_figure=True)
    
    resumen = []
    for i in range(len(methods)):
        for j in range(i + 1, len(methods)):
            r1 = df.iloc[:, i].values
            r2 = df.iloc[:, j].values
            kendall = np.sum([1 for a, b in zip(r1, r2) if a != b])
            try:
                spearman = np.corrcoef(r1, r2)[0, 1]
            except:
                spearman = 0.0
            try:
                ws = ws_coefficient(r1, r2)
            except:
                ws = 0.0
            total = (1 - spearman) + kendall + (1 - ws)
            resumen.append({
                "Método 1": methods[i],
                "Método 2": methods[j],
                "Kendall": round(kendall, 3),
                "1 - Spearman": round(1 - spearman, 3),
                "1 - WS": round(1 - ws, 3),
                "Total": round(total, 3)
            })
    st.markdown("#### Tabla de Distancias entre Rankings Agregados")
    st.dataframe(pd.DataFrame(resumen))

# GRÁFICAS PARA COMPARACIÓN POR ALGORITMO DE AGREGACIÓN

def plot_ranking_positions(merged_df):
    try:
        df_plot = merged_df.copy().dropna()
        df_melted = df_plot.melt(id_vars=["Elemento"], var_name="Ranking", value_name="Posición")

        df_melted["Elemento"] = df_melted["Elemento"].astype(str)  # Asegura etiquetas compatibles

        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df_melted, x="Elemento", y="Posición", hue="Ranking", ax=ax, dodge=True, palette="pastel")



        ax.set_title("Comparación de Posiciones (Barras)")
        ax.set_ylabel("Posición")
        ax.set_xlabel("Elemento")
        plt.xticks(rotation=45, ha='right')
        ax.legend(title="Ranking", loc='upper left', fontsize='small', title_fontsize='small', frameon=True)

        st.pyplot(fig, clear_figure=True)
    except Exception as e:
        st.warning(f"No se pudo generar el gráfico de posiciones en barras: {e}")


def plot_single_metric(ranking_names, values, title, color="tab:blue", kind="bar"):
    try:
        fig, ax = plt.subplots(figsize=(4.5, 3))
        if kind == "bar":
            ax.bar(ranking_names, values, color=color)
        elif kind == "line":
            ax.plot(ranking_names, values, marker="o", color=color)
        elif kind == "point":
            sns.stripplot(x=values, y=ranking_names, ax=ax, color=color, size=8, orient="h")
        ax.set_title(title)
        st.pyplot(fig, clear_figure=True)
    except Exception as e:
        st.warning(f"Error en gráfica {title}: {e}")

def plot_all_distances_grouped(ranking_names, kendall, kendall_corr, spearman, ws):
    try:
        df = pd.DataFrame({
            "Ranking": ranking_names * 4,
            "Métrica": ["Kendall"] * len(ranking_names) +
                       ["Coef Kendall"] * len(ranking_names) +
                       ["1 - Spearman"] * len(ranking_names) +
                       ["1 - WS"] * len(ranking_names),
            "Valor": kendall + kendall_corr + [1 - val for val in spearman] + [1 - val for val in ws]
        })

        # Pivot para gráfico de barras agrupadas
        df_pivot = df.pivot(index="Ranking", columns="Métrica", values="Valor").reset_index()

        fig, ax = plt.subplots(figsize=(10, 4))
        df_pivot.set_index("Ranking").plot(kind="bar", ax=ax, colormap="coolwarm")  # <- Aquí aplicamos la paleta pastel
        ax.set_title("Resumen de Métricas por Ranking")
        ax.set_ylabel("Valor")
        ax.set_xlabel("Ranking")
        ax.legend(title="Métrica", fontsize="small", title_fontsize="small")
        plt.xticks(rotation=45, ha='right')
        st.pyplot(fig, clear_figure=True)

    except Exception as e:
        st.warning(f"Error al generar gráfico de resumen: {e}")



# ORGANIZADOR DE GRÁFICAS

def show_comparison_graphs(merged_df, ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list):
    # Fila 1 - Solo la gráfica de posiciones
    st.markdown("### Comparación de Posiciones (Barras)")
    plot_ranking_positions(merged_df)

    # Fila 2 - Kendall y Kendall corregido
    col1, col2 = st.columns(2)
    with col1:
        plot_single_metric(ranking_names, kendall_list, "Distancia Kendall", color="tab:red", kind="line")
    with col2:
        plot_single_metric(ranking_names, kendall_corr_list, "Coeficiente Kendall", color="tab:orange", kind="line")

    # Fila 3 - Spearman y WS
    col3, col4 = st.columns(2)
    with col3:
        plot_single_metric(ranking_names, [1 - s for s in spearman_list], "1 - Spearman", color="tab:green", kind="line")
    with col4:
        plot_single_metric(ranking_names, [1 - w for w in ws_list], "1 - WS", color="tab:purple", kind="line")

    # Fila 4 - Gráfico resumen final
    st.markdown("### Resumen de Distancias por Ranking y Métrica")
    plot_all_distances_grouped(ranking_names, kendall_list, kendall_corr_list, spearman_list, ws_list)
