import sqlite3
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash

class Database:
    def __init__(self):
        import os
        self.db_name = os.path.join(os.path.dirname(__file__), 'chromebooks.db')

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def criar_tabelas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chromebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero INTEGER UNIQUE NOT NULL,
                carrinho TEXT NOT NULL,
                status TEXT DEFAULT 'Disponível',
                aluno_emprestado TEXT,
                data_emprestimo TEXT,
                professor_emprestimo TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chromebook_numero INTEGER,
                carrinho TEXT,
                aluno TEXT,
                professor TEXT,
                data_emprestimo TEXT,
                data_devolucao TEXT,
                tipo_acao TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def criar_usuario_padrao(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO usuarios (username, senha, nome) VALUES (?, ?, ?)",
                          ('admin', generate_password_hash('1234'), 'Administrador'))
            conn.commit()
        conn.close()

    def verificar_usuario_existe(self, username):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None

    def criar_usuario(self, username, senha, nome):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usuarios (username, senha, nome) VALUES (?, ?, ?)",
                (username, generate_password_hash(senha), nome)
            )
            conn.commit()
            conn.close()
            return True, "Usuário criado com sucesso"
        except sqlite3.IntegrityError:
            return False, "Usuário já existe"
        except Exception as e:
            return False, str(e)

    # método de login (com suporte a hash e texto simples)
    def verificar_login(self, username, senha_digitada):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, senha, nome FROM usuarios WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        user_id, username_db, senha_db, nome = row

        # tenta verificar hash
        try:
            if check_password_hash(senha_db, senha_digitada):
                return {'id': user_id, 'nome': nome, 'is_admin': (username_db.lower() == 'admin')}
        except Exception:
            pass

        # fallback: comparar texto simples
        if senha_db == senha_digitada:
            return {'id': user_id, 'nome': nome, 'is_admin': (username_db.lower() == 'admin')}

        return None

    def buscar_usuario_por_id(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, nome FROM usuarios WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        user_id, username_db, nome = row
        return {'id': user_id, 'username': username_db, 'nome': nome, 'is_admin': (username_db.lower() == 'admin')}

    def obter_usuarios(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, senha, nome FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()
        return usuarios

    def cadastrar_chromebook(self, numero, carrinho):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO chromebooks (numero, carrinho, status) VALUES (?, ?, 'Disponível')", (numero, carrinho))
            conn.commit()
            conn.close()
            return True, "Chromebook cadastrado com sucesso!"
        except sqlite3.IntegrityError:
            return False, "Chromebook com este número já existe!"
        except Exception as ex:
            return False, str(ex)

    # resto das funções
    def registrar_emprestimo(self, numero_chromebook, carrinho, nome_aluno, professor):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?", (numero_chromebook, carrinho))
            chromebook = cursor.fetchone()
            if not chromebook:
                cursor.execute(
                    "INSERT INTO chromebooks (numero, carrinho, status, aluno_emprestado, data_emprestimo, professor_emprestimo) VALUES (?, ?, ?, ?, ?, ?)",
                    (numero_chromebook, carrinho, 'Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor)
                )
            else:
                if chromebook[3] == 'Emprestado':
                    return False, "Chromebook já está emprestado"
                cursor.execute(
                    "UPDATE chromebooks SET status = ?, aluno_emprestado = ?, data_emprestimo = ?, professor_emprestimo = ? WHERE numero = ? AND carrinho = ?",
                    ('Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor, numero_chromebook, carrinho)
                )
            cursor.execute(
                "INSERT INTO historico (chromebook_numero, carrinho, aluno, professor, data_emprestimo, tipo_acao) VALUES (?, ?, ?, ?, ?, ?)",
                (numero_chromebook, carrinho, nome_aluno, professor, datetime.now().strftime("%d/%m/%Y %H:%M"), 'Empréstimo')
            )
            conn.commit()
            conn.close()
            return True, f"Chromebook {numero_chromebook} emprestado para {nome_aluno}"
        except Exception as e:
            return False, str(e)

    def registrar_devolucao(self, numero_chromebook, carrinho):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?", (numero_chromebook, carrinho))
            chromebook = cursor.fetchone()
            if not chromebook:
                return False, "Chromebook não encontrado"
            if chromebook[3] == 'Disponível':
                return False, "Chromebook já está disponível"
            cursor.execute("UPDATE chromebooks SET status = 'Disponível', aluno_emprestado = NULL, data_emprestimo = NULL, professor_emprestimo = NULL WHERE numero = ? AND carrinho = ?", (numero_chromebook, carrinho))
            cursor.execute("INSERT INTO historico (chromebook_numero, carrinho, aluno, professor, data_devolucao, tipo_acao) VALUES (?, ?, ?, ?, ?, ?)",
                           (numero_chromebook, carrinho, chromebook[4], chromebook[6], datetime.now().strftime("%d/%m/%Y %H:%M"), 'Devolução'))
            conn.commit()
            conn.close()
            return True, f"Chromebook {numero_chromebook} devolvido"
        except Exception as e:
            return False, str(e)

    def obter_estatisticas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chromebooks WHERE status = 'Disponível'")
        disponiveis = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chromebooks WHERE status = 'Emprestado'")
        emprestados = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chromebooks")
        total = cursor.fetchone()[0]
        conn.close()
        return {'disponiveis': disponiveis, 'emprestados': emprestados, 'total': total}

    def obter_todos_chromebooks(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT numero, carrinho, status, aluno_emprestado, professor_emprestimo, data_emprestimo FROM chromebooks ORDER BY carrinho, numero")
        r = cursor.fetchall(); conn.close(); return r

    def obter_chromebooks_disponiveis(self):
        conn = self.get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT numero, carrinho FROM chromebooks WHERE status = 'Disponível' ORDER BY carrinho, numero")
        chromebooks = cursor.fetchall(); conn.close()
        return [{'numero': cb[0], 'carrinho': cb[1]} for cb in chromebooks]

    def obter_chromebooks_emprestados(self):
        conn = self.get_connection(); cursor = conn.cursor()
        cursor.execute("SELECT numero, carrinho, aluno_emprestado FROM chromebooks WHERE status = 'Emprestado' ORDER BY carrinho, numero")
        chromebooks = cursor.fetchall(); conn.close()
        return [{'numero': cb[0], 'carrinho': cb[1], 'aluno': cb[2]} for cb in chromebooks]

    def obter_historico(self):
        conn = self.get_connection(); cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM historico ORDER BY id DESC LIMIT 50
        ''')
        historico = cursor.fetchall(); conn.close(); return historico