import streamlit as st
import sqlite3
import pandas as pd

# Funciones para manejar la base de datos
def init_db():
    # Conecta o crea la base de datos 'datos.db'
    conn = sqlite3.connect('datos.db')
    c = conn.cursor()
    # Crea la tabla si no existe
    c.execute('''
        CREATE TABLE IF NOT EXISTS datos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            valor INTEGER NOT NULL
        )
    ''')
    conn.commit()
    return conn

def insert_data(conn, nombre, valor):
    c = conn.cursor()
    c.execute("INSERT INTO datos (nombre, valor) VALUES (?, ?)", (nombre, valor))
    conn.commit()

def get_data(conn):
    # Lee los datos de la tabla y los retorna en un DataFrame
    df = pd.read_sql_query("SELECT * FROM datos", conn)
    return df

# Inicializa la base de datos
conn = init_db()

# Título de la aplicación
st.title("Aplicación de Ejemplo con Streamlit y SQLite")

# Barra lateral para la navegación entre secciones
opcion = st.sidebar.selectbox("Selecciona una opción", ("Ver datos", "Agregar datos", "Gráficos"))

if opcion == "Ver datos":
    st.header("Tabla de Datos")
    df = get_data(conn)
    st.dataframe(df)

elif opcion == "Agregar datos":
    st.header("Agregar Nuevo Dato")
    with st.form(key='form_data'):
        nombre = st.text_input("Nombre")
        valor = st.number_input("Valor", min_value=0, step=1)
        submit_button = st.form_submit_button("Agregar")
    
    if submit_button:
        insert_data(conn, nombre, valor)
        st.success("¡Dato agregado correctamente!")
        st.write("Datos actualizados:")
        df = get_data(conn)
        st.dataframe(df)

elif opcion == "Gráficos":
    st.header("Visualización de Datos")
    df = get_data(conn)
    if not df.empty:
        # Se utiliza la columna 'nombre' como índice y se muestran los valores con un gráfico de barras
        st.bar_chart(df.set_index('nombre')['valor'])
    else:
        st.info("No hay datos para mostrar.")
