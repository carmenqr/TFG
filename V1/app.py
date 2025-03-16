from shiny import App, ui, render, reactive
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pyRankMCDA.algorithm import rank_aggregation

def compute_metrics(ra, aggregated, rankings_matrix):
    n = rankings_matrix.shape[1]  # número de rankings individuales (cada columna)
    kendall_total = 0
    spearman_total = 0
    footrule_total = 0
    for i in range(n):
        r_ind = rankings_matrix[:, i]
        kendall_total += ra.kendall_tau_distance(aggregated, r_ind)
        spearman_total += ra.spearman_rank(aggregated, r_ind)
        footrule_total += ra.footrule_distance(aggregated, r_ind)
    metrics = {
        "Kendall Tau Dist": kendall_total / n,
        "Spearman Corr": spearman_total / n,
        "Footrule Dist": footrule_total / n
    }
    return metrics

app_ui = ui.page_fluid(
    ui.panel_title("Agregación y Comparación de Rankings"),
    ui.layout_sidebar(
        ui.sidebar(
            ui.input_text_area(
                "rankings_input",
                "Introduce tus rankings (cada línea un ranking, separa los valores por comas):",
                rows=6,
                placeholder="Ejemplo:\n1, 2, 3, 4\n2, 1, 4, 3\n3, 4, 1, 2"
            ),
            ui.input_action_button("run", "Ejecutar Agregación")
        ),
        ui.panel_absolute(
            ui.output_table("results_table"),
            ui.output_plot("metrics_plot")
        )
    )
)

def server(input, output, session):
    
    @reactive.Effect
    @reactive.event(input.run)
    def process():
        raw = input.rankings_input()
        if not raw:
            return
        rankings_list = []
        for line in raw.splitlines():
            if line.strip():
                try:
                    ranking = [int(item.strip()) for item in line.split(",")]
                except ValueError:
                    print("Error: Asegúrate de ingresar números separados por comas.")
                    return
                rankings_list.append(ranking)
        if len(rankings_list) == 0:
            return
        rankings_array = np.array(rankings_list)
        # Transponemos para que cada columna represente un ranking (como espera el paquete)
        rankings_matrix = rankings_array.T
        
        # Inicializar el objeto de agregación según el ejemplo:
        ra = rank_aggregation(rankings_matrix)
        
        aggregated_results = {}
        metrics_results = {}
        
        try:
            aggregated_results["Borda"] = ra.borda_method(verbose=False)
            aggregated_results["Copeland"] = ra.copeland_method(verbose=False)
            aggregated_results["Kemeny-Young"] = ra.kemeny_young(verbose=False)
            aggregated_results["Schulze"] = ra.schulze_method(verbose=False)
            aggregated_results["Footrule"] = ra.footrule_rank_aggregation(verbose=False)
            aggregated_results["Markov (PageRank)"] = ra.page_rank(verbose=False)
        except Exception as e:
            print("Error al ejecutar los métodos de agregación:", e)
            return
        
        for method_name, agg_ranking in aggregated_results.items():
            metrics_results[method_name] = compute_metrics(ra, agg_ranking, rankings_matrix)
        
        data = []
        for method, met in metrics_results.items():
            data.append({
                "Método": method,
                "Kendall Tau Dist": met["Kendall Tau Dist"],
                "Spearman Corr": met["Spearman Corr"],
                "Footrule Dist": met["Footrule Dist"]
            })
        df = pd.DataFrame(data)
        session.user_data["df"] = df
        session.user_data["aggregated"] = aggregated_results

    @output
    @render.table
    def results_table():
        if "df" in session.user_data:
            return session.user_data["df"]

    @output
    @render.plot
    def metrics_plot():
        if "df" not in session.user_data:
            return
        df = session.user_data["df"]
        methods = df["Método"].tolist()
        kendall = df["Kendall Tau Dist"].tolist()
        spearman = df["Spearman Corr"].tolist()
        footrule = df["Footrule Dist"].tolist()
        
        fig, ax = plt.subplots(figsize=(9, 6))
        x = np.arange(len(methods))
        ancho = 0.25
        
        ax.bar(x - ancho, kendall, ancho, label="Kendall Tau Dist")
        ax.bar(x, spearman, ancho, label="Spearman Corr")
        ax.bar(x + ancho, footrule, ancho, label="Footrule Dist")
        
        ax.set_xticks(x)
        ax.set_xticklabels(methods)
        ax.set_ylabel("Valor de la métrica")
        ax.set_title("Comparación de métricas entre métodos de agregación")
        ax.legend()
        plt.tight_layout()
        return fig

app = App(app_ui, server)

if __name__ == '__main__':
    app.run()
