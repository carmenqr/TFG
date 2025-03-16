import shiny
from shiny import ui, render, reactive
import pandas as pd
import pyRankMCDA as pr
from scipy.stats import kendalltau, spearmanr
import io

# Definir la interfaz de usuario
app_ui = ui.page_fluid(
    ui.panel_title("Comparador de Algoritmos de Agregación de Rankings"),
    ui.layout_sidebar(
        ui.sidebar(
            # Entrada para subir un archivo Excel con rankings
            ui.input_file("file_input", "Sube un archivo Excel con rankings", accept=[".xlsx"]),
            # Selector de método de agregación
            ui.input_select("aggregation_method", "Método de Agregación", 
                           choices=["Borda", "Copeland", "Kemeny", "Positional", "Owa"]),
            # Botón para procesar los rankings
            ui.input_action_button("process_button", "Procesar Rankings"),
        ),
        ui.panel_absolute(
            # Tabla para mostrar los rankings cargados
            ui.output_table("rankings_table"),
            # Texto para mostrar el ranking agregado
            ui.output_text("agg_result"),
            # Texto para mostrar la comparación de rankings
            ui.output_text("comparison_result")
        )
    )
)

# Definir la lógica de la aplicación
def server(input, output, session):
    # Variable reactiva para almacenar los rankings cargados
    rankings = reactive.Value([])  # Usamos reactive.Value para mantener el estado de ranking
    # Función para renderizar la tabla con los rankings cargados
    @render.table
    def rankings_table():
        # Si no hay datos cargados, no mostramos nada
        if not rankings():
            return pd.DataFrame()  # Devuelve una tabla vacía si no hay rankings
        return pd.DataFrame(rankings())  # Mostrar los rankings cargados en una tabla

    # Función reactiva para cargar y leer el archivo Excel
    @reactive.Effect
    def load_file():
        file = input.file_input()  # Obtener el archivo cargado desde la entrada
        if file:
            try:
                # Leer el archivo Excel desde el input y convertirlo en un DataFrame
                df = pd.read_excel(io.BytesIO(file["datapath"]))
                rankings.set(df.values.tolist())  # Guardamos los datos de rankings en la variable reactiva
            except Exception as e:
                print(f"Error al leer el archivo: {str(e)}")  # Manejo de errores en la lectura

    # Función para calcular y mostrar el ranking agregado
    @render.text
    def agg_result():
        # Mostrar solo cuando haya rankings cargados
        if not rankings():
            return ""  # No mostrar nada si no hay rankings cargados
        
        method = input.aggregation_method()  # Obtener el método de agregación seleccionado
        aggregated_rank = pr.aggregate(rankings(), method=method)  # Aplicar el método de agregación
        return f"Ranking Agregado ({method}): {aggregated_rank}"

    # Función para comparar el ranking agregado con los rankings originales
    @render.text
    def comparison_result():
        # Mostrar solo cuando haya rankings cargados
        if not rankings():
            return ""  # No mostrar nada si no hay rankings cargados
        
        method = input.aggregation_method()
        aggregated_rank = pr.aggregate(rankings(), method=method)  # Generar ranking agregado
        comparisons = []
        
        # Comparar cada ranking original con el ranking agregado usando Kendall y Spearman
        for rank in rankings():
            kendall_dist = kendalltau(aggregated_rank, rank)[0]  # Distancia de Kendall
            spearman_dist = spearmanr(aggregated_rank, rank)[0]  # Distancia de Spearman
            comparisons.append(f"Kendall: {kendall_dist}, Spearman: {spearman_dist}")
        
        return "\n".join(comparisons)  # Unir los resultados en un solo texto

    # Función para manejar el botón "Procesar Rankings"
    @reactive.event(input.process_button)
    def process_rankings():
        # Aquí manejamos la lógica cuando el botón es presionado
        if not rankings():
            return "Por favor, carga un archivo con rankings."
        
        method = input.aggregation_method()
        aggregated_rank = pr.aggregate(rankings(), method=method)  # Aplicar el método de agregación
        return f"Ranking Agregado ({method}): {aggregated_rank}"

# Crear la aplicación Shiny con la interfaz y el servidor
app = shiny.App(app_ui, server)  # Cambié 'doc' por 'app'
