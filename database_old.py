import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.db_name = 'chromebooks.db'
    
    def get_connection(self):
        return sqlite3.connect(self.db_name)
    
    def criar_tabelas(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                nome TEXT NOT NULL
            )
        ''')
        
        # Tabela de chromebooks
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
        
        # Tabela de histórico
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
                (username, senha, nome)
            )
            conn.commit()
            conn.close()
            return True, "Usuário criado com sucesso"
        except sqlite3.IntegrityError:
            return False, "Usuário já existe"
        except Exception as e:
            return False, str(e)
    
    def verificar_login(self, username, senha):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM usuarios WHERE username = ? AND senha = ?",
            (username, senha)
        )
        usuario = cursor.fetchone()
        conn.close()
        return usuario
    
    def registrar_emprestimo(self, numero_chromebook, carrinho, nome_aluno, professor):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Verificar se chromebook existe
            cursor.execute(
                "SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?",
                (numero_chromebook, carrinho)
            )
            chromebook = cursor.fetchone()
            
            if not chromebook:
                # Criar novo chromebook
                cursor.execute(
                    "INSERT INTO chromebooks (numero, carrinho, status, aluno_emprestado, data_emprestimo, professor_emprestimo) VALUES (?, ?, ?, ?, ?, ?)",
                    (numero_chromebook, carrinho, 'Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor)
                )
            else:
                if chromebook[3] == 'Emprestado':
                    return False, "Chromebook já está emprestado"
                
                # Atualizar status
                cursor.execute(
                    "UPDATE chromebooks SET status = ?, aluno_emprestado = ?, data_emprestimo = ?, professor_emprestimo = ? WHERE numero = ? AND carrinho = ?",
                    ('Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor, numero_chromebook, carrinho)
                )
            
            # Registrar no histórico
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
            
            # Verificar se chromebook existe e está emprestado
            cursor.execute(
                "SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?",
                (numero_chromebook, carrinho)
            )
            chromebook = cursor.fetchone()
            
            if not chromebook:
                return False, "Chromebook não encontrado"
            
            if chromebook[3] == 'Disponível':
                return False, "Chromebook já está disponível"
            
            # Atualizar status
            cursor.execute(
                "UPDATE chromebooks SET status = 'Disponível', aluno_emprestado = NULL, data_emprestimo = NULL, professor_emprestimo = NULL WHERE numero = ? AND carrinho = ?",
                (numero_chromebook, carrinho)
            )
            
            # Registrar no histórico
            cursor.execute(
                "INSERT INTO historico (chromebook_numero, carrinho, aluno, professor, data_devolucao, tipo_acao) VALUES (?, ?, ?, ?, ?, ?)",
                (numero_chromebook, carrinho, chromebook[4], chromebook[6], datetime.now().strftime("%d/%m/%Y %H:%M"), 'Devolução')
            )
            
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
        
        return {
            'disponiveis': disponiveis,
            'emprestados': emprestados,
            'total': total
        }
    
    def obter_chromebooks_status(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT numero, carrinho, status, aluno_emprestado, professor_emprestimo, data_emprestimo 
            FROM chromebooks 
            ORDER BY carrinho, numero
        ''')
        
        chromebooks = cursor.fetchall()
        conn.close()
        
        return chromebooks
    
    def obter_historico(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM historico 
            ORDER BY datetime(substr(data_emprestimo, 7, 4) || '-' || 
                   substr(data_emprestimo, 4, 2) || '-' || 
                   substr(data_emprestimo, 1, 2) || ' ' || 
                   substr(data_emprestimo, 12, 5)) DESC
            LIMIT 50
        ''')
        
        historico = cursor.fetchall()
        conn.close()
        
        return historico
    
    def obter_chromebooks_disponiveis(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT numero, carrinho FROM chromebooks WHERE status = 'Disponível' ORDER BY carrinho, numero")
        chromebooks = cursor.fetchall()
        conn.close()
        
        return [{'numero': cb[0], 'carrinho': cb[1]} for cb in chromebooks]
    
    def obter_chromebooks_emprestados(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT numero, carrinho, aluno_emprestado FROM chromebooks WHERE status = 'Emprestado' ORDER BY carrinho, numero")
        chromebooks = cursor.fetchall()
        conn.close()
        
        return [{'numero': cb[0], 'carrinho': cb[1], 'aluno': cb[2]} for cb in chromebooks]