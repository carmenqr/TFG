import sqlite3
import json

def init_db(db_name="rankings.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ranking TEXT  -- se almacena el ranking en formato JSON
        )
    """)
    conn.commit()
    return conn

def add_ranking(conn, name, ranking):
    cursor = conn.cursor()
    ranking_json = json.dumps(ranking)
    cursor.execute("INSERT INTO rankings (name, ranking) VALUES (?, ?)", (name, ranking_json))
    conn.commit()

def get_rankings(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, ranking FROM rankings")
    rows = cursor.fetchall()
    rankings = []
    for row in rows:
        ranking = json.loads(row[2])
        rankings.append({"id": row[0], "name": row[1], "ranking": ranking})
    return rankings
