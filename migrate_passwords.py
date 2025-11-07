
import sqlite3, os, shutil
from werkzeug.security import generate_password_hash

DB = 'chromebooks.db'
BACKUP = DB + '.bak'
if not os.path.exists(BACKUP):
    shutil.copy2(DB, BACKUP)
    print(f'Backup criado: {BACKUP}')

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT id, senha FROM usuarios")
rows = cur.fetchall()
for id, senha in rows:
    if senha and not senha.startswith('pbkdf2:'):
        cur.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(senha), id))
conn.commit()
conn.close()
print('Senhas convertidas com sucesso para formato seguro!')
