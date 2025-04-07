import sqlite3

class RankingDB:
    def __init__(self, db_file="rankings.db"):
        try:
            self.connection = sqlite3.connect(db_file)
            self.connection.row_factory = sqlite3.Row  # Permite acceder a las filas como diccionarios
            self.create_tables()
        except sqlite3.Error as e:
            print("Error al conectar con la base de datos:", e)
    
    def create_tables(self):
        cursor = self.connection.cursor()
        
        # Tabla para el grupo de rankings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RankingGroup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL
            )
        """)
        
        # Tabla para los rankings individuales (columnas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Ranking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                col_index INTEGER NOT NULL,
                FOREIGN KEY(grupo_id) REFERENCES RankingGroup(id)
            )
        """)
        
        # Tabla para los elementos de ranking (filas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RankingElement (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                row_index INTEGER NOT NULL,
                FOREIGN KEY(grupo_id) REFERENCES RankingGroup(id)
            )
        """)
        
        # Tabla para los valores (la intersección de rankings y elementos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS RankingValue (
                ranking_id INTEGER NOT NULL,
                elemento_id INTEGER NOT NULL,
                posicion INTEGER NOT NULL,
                PRIMARY KEY (ranking_id, elemento_id),
                FOREIGN KEY(ranking_id) REFERENCES Ranking(id),
                FOREIGN KEY(elemento_id) REFERENCES RankingElement(id)
            )
        """)
        
        # Tabla para almacenar rankings agregados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AggregatedRanking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id INTEGER NOT NULL,
                algoritmo TEXT NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(grupo_id) REFERENCES RankingGroup(id)
            )
        """)
        
        # Tabla para los valores del ranking agregado
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS AggregatedRankingValue (
                aggregated_ranking_id INTEGER NOT NULL,
                elemento_id INTEGER NOT NULL,
                posicion INTEGER NOT NULL,
                PRIMARY KEY (aggregated_ranking_id, elemento_id),
                FOREIGN KEY(aggregated_ranking_id) REFERENCES AggregatedRanking(id),
                FOREIGN KEY(elemento_id) REFERENCES RankingElement(id)
            )
        """)
        
        self.connection.commit()
    
    # Métodos para el grupo de rankings
    def add_group(self, nombre):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO RankingGroup (nombre) VALUES (?)", (nombre,))
        self.connection.commit()
        return cursor.lastrowid

    def get_group(self, group_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM RankingGroup WHERE id = ?", (group_id,))
        return cursor.fetchone()
    
    # Métodos para los rankings individuales (columnas)
    def add_ranking(self, grupo_id, nombre, col_index):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO Ranking (grupo_id, nombre, col_index) VALUES (?, ?, ?)",
                       (grupo_id, nombre, col_index))
        self.connection.commit()
        return cursor.lastrowid

    def get_rankings(self, grupo_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM Ranking WHERE grupo_id = ? ORDER BY col_index", (grupo_id,))
        return cursor.fetchall()
    
    # Métodos para los elementos del ranking (filas)
    def add_ranking_element(self, grupo_id, nombre, row_index):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO RankingElement (grupo_id, nombre, row_index) VALUES (?, ?, ?)",
                       (grupo_id, nombre, row_index))
        self.connection.commit()
        return cursor.lastrowid

    def get_ranking_elements(self, grupo_id):
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM RankingElement WHERE grupo_id = ? ORDER BY row_index", (grupo_id,))
        return cursor.fetchall()
    
    # Métodos para gestionar los valores (posición de cada elemento en cada ranking)
    def add_ranking_value(self, ranking_id, elemento_id, posicion):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO RankingValue (ranking_id, elemento_id, posicion) VALUES (?, ?, ?)",
                       (ranking_id, elemento_id, posicion))
        self.connection.commit()

    def get_ranking_values(self, ranking_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT re.row_index, re.nombre AS elemento, rv.posicion
            FROM RankingValue rv
            JOIN RankingElement re ON rv.elemento_id = re.id
            WHERE rv.ranking_id = ?
            ORDER BY re.row_index
        """, (ranking_id,))
        return cursor.fetchall()
    
    # Métodos para gestionar las agregaciones de rankings
    def add_aggregated_ranking(self, grupo_id, algoritmo):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO AggregatedRanking (grupo_id, algoritmo) VALUES (?, ?)",
                       (grupo_id, algoritmo))
        self.connection.commit()
        return cursor.lastrowid

    def add_aggregated_ranking_value(self, aggregated_ranking_id, elemento_id, posicion):
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO AggregatedRankingValue (aggregated_ranking_id, elemento_id, posicion) VALUES (?, ?, ?)",
                       (aggregated_ranking_id, elemento_id, posicion))
        self.connection.commit()

    def get_aggregated_ranking(self, aggregated_ranking_id):
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT re.nombre AS Elemento, arv.posicion
            FROM AggregatedRankingValue arv
            JOIN RankingElement re ON arv.elemento_id = re.id
            WHERE arv.aggregated_ranking_id = ?
            ORDER BY re.row_index
        """, (aggregated_ranking_id,))
        return cursor.fetchall()
    
    def delete_aggregated_ranking(self, aggregated_ranking_id):
        """
        Elimina una agregación de rankings y todos sus valores asociados.
        """
        cursor = self.connection.cursor()
        # Primero, eliminar los valores asociados a la agregación
        cursor.execute("DELETE FROM AggregatedRankingValue WHERE aggregated_ranking_id = ?", (aggregated_ranking_id,))
        # Luego, eliminar el registro de la agregación
        cursor.execute("DELETE FROM AggregatedRanking WHERE id = ?", (aggregated_ranking_id,))
        self.connection.commit()

    
    def get_group_excel_format(self, group_id):
        """
        Recupera la información del grupo en el mismo formato que el Excel:
         - La cabecera incluirá el nombre del grupo y los rankings con sus nombres (ej. R1, R2, etc)
         - Cada fila tendrá el nombre del elemento y los valores (posiciones) de cada ranking.
         
        La consulta pivot se construye dinámicamente en función de los rankings asociados al grupo.
        """
        cursor = self.connection.cursor()
        
        # Recupera el nombre del grupo
        cursor.execute("SELECT nombre FROM RankingGroup WHERE id = ?", (group_id,))
        group = cursor.fetchone()
        if not group:
            return None
        group_name = group["nombre"]
        
        # Recupera los nombres de los rankings, ordenados según col_index
        cursor.execute("SELECT nombre FROM Ranking WHERE grupo_id = ? ORDER BY col_index", (group_id,))
        ranking_rows = cursor.fetchall()
        ranking_names = [row["nombre"] for row in ranking_rows]
        
        # Construye dinámicamente la parte de la consulta para pivotear usando los nombres reales de los rankings
        cases = []
        for ranking_name in ranking_names:
            cases.append(f"MAX(CASE WHEN r.nombre = '{ranking_name}' THEN rv.posicion END) AS '{ranking_name}'")
        cases_str = ", ".join(cases)
        
        # Consulta pivot: se agrupa por el nombre del elemento y su row_index para mantener el orden original
        pivot_query = f"""
            SELECT 
                re.nombre AS Elemento, {cases_str}
            FROM RankingElement re
            JOIN RankingValue rv ON re.id = rv.elemento_id
            JOIN Ranking r ON r.id = rv.ranking_id
            WHERE re.grupo_id = ?
            GROUP BY re.nombre, re.row_index
            ORDER BY re.row_index;
        """
        cursor.execute(pivot_query, (group_id,))
        pivot_data = cursor.fetchall()
        
        return {
            "group_name": group_name,
            "ranking_names": ranking_names,
            "rows": pivot_data
        }
        
""" if __name__ == "__main__":
    # Ejemplo de prueba rápida
    db = RankingDB()
    group_id = db.add_group("Grupo de Prueba")
    print("Grupo creado con id:", group_id) """
