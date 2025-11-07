import sqlite3

conn = sqlite3.connect('chromebooks.db')
cur = conn.cursor()
cur.execute("SELECT id, username, senha, nome FROM usuarios;")
rows = cur.fetchall()
conn.close()

for r in rows:
    print(r)
