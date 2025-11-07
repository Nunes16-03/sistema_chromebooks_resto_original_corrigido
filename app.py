# app.py - versão completa com todas as rotas
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from jinja2 import TemplateNotFound
import os
import sqlite3
from datetime import datetime
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)

# Inicializar Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ---------- Database minimal wrapper (usa database.py se existir) ----------
try:
    from database import Database as ExternalDatabase
    class Database(ExternalDatabase):
        pass
    db = Database()
    print("Usando database.py externo.")
except Exception as e:
    print("database.py não disponível ou apresentou erro — usando fallback interno.", e)
    class Database:
        def __init__(self):
            self.db_name = os.path.join(os.path.dirname(__file__), 'chromebooks.db')
            self.criar_tabelas()
            self.criar_usuario_padrao()
        def get_connection(self):
            return sqlite3.connect(self.db_name)
        def criar_tabelas(self):
            conn = self.get_connection(); c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL, nome TEXT NOT NULL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS chromebooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT, numero INTEGER NOT NULL,
                carrinho TEXT NOT NULL, status TEXT DEFAULT 'Disponível',
                aluno_emprestado TEXT, data_emprestimo TEXT, professor_emprestimo TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT, chromebook_numero INTEGER, carrinho TEXT,
                aluno TEXT, professor TEXT, data_emprestimo TEXT, data_devolucao TEXT, tipo_acao TEXT)''')
            conn.commit(); conn.close()
        def criar_usuario_padrao(self):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT id FROM usuarios WHERE username = 'admin'")
            if not c.fetchone():
                c.execute("INSERT INTO usuarios (username, senha, nome) VALUES (?, ?, ?)",
                          ('admin', generate_password_hash('1234'), 'Administrador'))
                conn.commit()
            conn.close()
        def verificar_login(self, username, senha_digitada):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT id, username, senha, nome FROM usuarios WHERE username = ?", (username,))
            u = c.fetchone(); conn.close()
            if u:
                user_id, username_db, senha_hash, nome = u
                try:
                    if check_password_hash(senha_hash, senha_digitada):
                        return {'id': user_id, 'nome': nome, 'is_admin': (username_db.lower() == 'admin')}
                except Exception:
                    pass
                # fallback texto plano
                if senha_hash == senha_digitada:
                    return {'id': user_id, 'nome': nome, 'is_admin': (username_db.lower() == 'admin')}
            return None
        
        def buscar_usuario_por_id(self, user_id):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT id, username, nome FROM usuarios WHERE id = ?", (user_id,))
            u = c.fetchone(); conn.close()
            if u:
                return {'id': u[0], 'username': u[1], 'nome': u[2], 'is_admin': (u[1].lower() == 'admin')}
            return None

        def verificar_se_admin(self, usuario_id):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT username FROM usuarios WHERE id = ?", (usuario_id,))
            u = c.fetchone(); conn.close()
            return bool(u and u[0].lower() == 'admin')
        def obter_estatisticas(self):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM chromebooks WHERE status='Disponível'"); disponiveis = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM chromebooks WHERE status='Emprestado'"); emprestados = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM chromebooks"); total = c.fetchone()[0]
            conn.close(); return {'disponiveis': disponiveis, 'emprestados': emprestados, 'total': total}
        def obter_todos_chromebooks(self):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT numero, carrinho, status, aluno_emprestado, professor_emprestimo, data_emprestimo FROM chromebooks ORDER BY carrinho, numero")
            r = c.fetchall(); conn.close(); return r
        def registrar_emprestimo(self, numero, carrinho, nome_aluno, professor):
            try:
                conn = self.get_connection(); c = conn.cursor()
                c.execute("SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?", (numero, carrinho))
                chromebook = c.fetchone()
                if chromebook and chromebook[3] == 'Emprestado':
                    conn.close(); return False, "Chromebook já está emprestado!"
                if not chromebook:
                    c.execute("INSERT INTO chromebooks (numero, carrinho, status, aluno_emprestado, data_emprestimo, professor_emprestimo) VALUES (?, ?, ?, ?, ?, ?)",
                              (numero, carrinho, 'Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor))
                else:
                    c.execute("UPDATE chromebooks SET status=?, aluno_emprestado=?, data_emprestimo=?, professor_emprestimo=? WHERE numero=? AND carrinho=?",
                              ('Emprestado', nome_aluno, datetime.now().strftime("%d/%m/%Y %H:%M"), professor, numero, carrinho))
                c.execute("INSERT INTO historico (chromebook_numero, carrinho, aluno, professor, data_emprestimo, tipo_acao) VALUES (?, ?, ?, ?, ?, ?)",
                          (numero, carrinho, nome_aluno, professor, datetime.now().strftime("%d/%m/%Y %H:%M"), 'Empréstimo'))
                conn.commit(); conn.close(); return True, "Empréstimo registrado com sucesso!"
            except Exception as ex:
                try: conn.close()
                except: pass
                return False, str(ex)
        def registrar_devolucao(self, numero, carrinho):
            try:
                conn = self.get_connection(); c = conn.cursor()
                c.execute("SELECT * FROM chromebooks WHERE numero = ? AND carrinho = ?", (numero, carrinho))
                chromebook = c.fetchone()
                if not chromebook:
                    conn.close(); return False, "Chromebook não encontrado!"
                if chromebook[3] == 'Disponível':
                    conn.close(); return False, "Chromebook já está disponível!"
                c.execute("UPDATE chromebooks SET status='Disponível', aluno_emprestado=NULL, data_emprestimo=NULL, professor_emprestimo=NULL WHERE numero=? AND carrinho=?", (numero, carrinho))
                c.execute("INSERT INTO historico (chromebook_numero, carrinho, aluno, professor, data_devolucao, tipo_acao) VALUES (?, ?, ?, ?, ?, ?)",
                          (numero, carrinho, chromebook[4], chromebook[6], datetime.now().strftime("%d/%m/%Y %H:%M"), 'Devolução'))
                conn.commit(); conn.close(); return True, "Devolução registrada!"
            except Exception as ex:
                try: conn.close()
                except: pass
                return False, str(ex)
        
        def cadastrar_chromebook(self, numero, carrinho):
            try:
                conn = self.get_connection(); c = conn.cursor()
                c.execute("INSERT INTO chromebooks (numero, carrinho, status) VALUES (?, ?, 'Disponível')", (numero, carrinho))
                conn.commit(); conn.close()
                return True, "Chromebook cadastrado com sucesso!"
            except sqlite3.IntegrityError:
                return False, "Chromebook com este número já existe!"
            except Exception as ex:
                return False, str(ex)
        
        def obter_usuarios(self):
            conn = self.get_connection(); c = conn.cursor()
            c.execute("SELECT id, username, senha, nome FROM usuarios")
            usuarios = c.fetchall(); conn.close()
            return usuarios

    db = Database()

# Classe User para Flask-Login
class User(UserMixin):
    def __init__(self, user_dict):
        self.id = user_dict['id']
        self.nome = user_dict['nome']
        self.is_admin = user_dict.get('is_admin', False)

@login_manager.user_loader
def load_user(user_id):
    user_data = db.buscar_usuario_por_id(user_id)
    if user_data:
        return User(user_data)
    return None

# ---------- Helper: safe render_template with fallback ----------
def safe_render(template_name, **context):
    try:
        return render_template(template_name, **context)
    except TemplateNotFound:
        fallback = f"""
        <html><head><meta charset="utf-8"><title>Fallback - {template_name}</title></head>
        <body>
        <h2>Template ausente: {template_name}</h2>
        <p>Context: {context.keys()}</p>
        <p><a href="/">Voltar</a></p>
        </body></html>
        """
        return fallback

# ---------- ROTAS ----------
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print("📥 Form recebido:", request.form)
        username = request.form.get('username')
        senha = request.form.get('senha')

        usuario = None
        try:
            usuario = db.verificar_login(username, senha)
        except Exception as e:
            traceback.print_exc()
            flash('Erro interno durante verificação de usuário. Veja o log.', 'error')
            return render_template('login.html')

        if not usuario:
            flash('Usuário ou senha incorretos.', 'danger')
            return render_template('login.html')

        # Criar objeto User e fazer login
        user_obj = User(usuario)
        login_user(user_obj)

        flash(f"Bem-vindo(a), {usuario.get('nome')}!", 'success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Buscar dados usando o método do banco
    chromebooks = db.obter_todos_chromebooks()

    # Calcular estatísticas básicas
    total = len(chromebooks)
    disponiveis = sum(1 for c in chromebooks if c[2] == 'Disponível')
    emprestados = sum(1 for c in chromebooks if c[2] == 'Emprestado')
    manutencao = sum(1 for c in chromebooks if c[2] == 'Manutenção')

    # Dicionário para o template
    stats = {
        "total": total,
        "disponiveis": disponiveis,
        "emprestados": emprestados,
        "manutencao": manutencao
    }

    return safe_render("dashboard.html", chromebooks=chromebooks, stats=stats)

# ---------- ROTAS DE EMPRÉSTIMO E DEVOLUÇÃO ----------
@app.route('/emprestimo', methods=['GET', 'POST'])
@login_required
def emprestimo():
    if request.method == 'POST':
        numero = request.form.get('numero_chromebook')
        carrinho = request.form.get('carrinho')
        nome_aluno = request.form.get('nome_aluno')
        professor = current_user.nome
        
        if numero and carrinho and nome_aluno:
            success, message = db.registrar_emprestimo(int(numero), carrinho, nome_aluno, professor)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('emprestimo'))
        else:
            flash('Preencha todos os campos!', 'danger')
    
    return safe_render("emprestimo.html")

@app.route('/devolucao', methods=['GET', 'POST'])
@login_required
def devolucao():
    if request.method == 'POST':
        numero = request.form.get('numero_chromebook')
        carrinho = request.form.get('carrinho')
        
        if numero and carrinho:
            success, message = db.registrar_devolucao(int(numero), carrinho)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('devolucao'))
        else:
            flash('Preencha todos os campos!', 'danger')
    
    return safe_render("devolucao.html")

# ---------- ROTAS DE CADASTRO ----------
@app.route('/cadastro_chromebook', methods=['GET', 'POST'])
@login_required
def cadastro_chromebook():
    if not current_user.is_admin:
        flash('Acesso restrito a administradores!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        numero = request.form.get('numero')
        carrinho = request.form.get('carrinho')
        
        if numero and carrinho:
            success, message = db.cadastrar_chromebook(int(numero), carrinho)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('cadastro_chromebook'))
        else:
            flash('Preencha todos os campos!', 'danger')
    
    chromebooks = db.obter_todos_chromebooks()
    return safe_render("cadastro_chromebook.html", chromebooks=chromebooks)

@app.route('/cadastro_professor', methods=['GET', 'POST'])
@login_required
def cadastro_professor():
    if not current_user.is_admin:
        flash('Acesso restrito a administradores!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('senha')
        nome = request.form.get('nome')
        
        if username and senha and nome:
            success, message = db.criar_usuario(username, senha, nome)
            if success:
                flash(message, 'success')
            else:
                flash(message, 'danger')
            return redirect(url_for('cadastro_professor'))
        else:
            flash('Preencha todos os campos!', 'danger')
    
    return safe_render("cadastro_professor.html")

# ---------- ROTAS ADMINISTRATIVAS ----------
@app.route('/admin_banco_dados')
@login_required
def admin_banco_dados():
    if not current_user.is_admin:
        flash('Acesso restrito a administradores!', 'danger')
        return redirect(url_for('dashboard'))
    
    usuarios = db.obter_usuarios()
    chromebooks = db.obter_todos_chromebooks()
    historico = db.obter_historico()
    
    return safe_render("admin_banco.html", 
                      usuarios=usuarios, 
                      chromebooks=chromebooks, 
                      historico=historico)

@app.route('/historico')
@login_required
def historico():
    historico = db.obter_historico()
    return safe_render("historico.html", historico=historico)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

# ---------- APIs ----------
@app.route('/api/chromebooks_disponiveis')
def api_chromebooks_disponiveis():
    chromebooks = db.obter_chromebooks_disponiveis() if hasattr(db, 'obter_chromebooks_disponiveis') else []
    return jsonify(chromebooks)

@app.route('/api/chromebooks_emprestados')
def api_chromebooks_emprestados():
    try:
        chromebooks = db.obter_chromebooks_emprestados()
        print(f"📦 {len(chromebooks)} Chromebooks emprestados encontrados")
        return jsonify(chromebooks)
    except Exception as e:
        print(f"❌ Erro na API de chromebooks_emprestados: {e}")
        return jsonify({"erro": str(e)}), 500

# ---------- Run ----------
if __name__ == '__main__':
    print("🚀 Servidor rodando em: http://127.0.0.1:5000")
    print("🔐 Login padrão: admin / 1234")
    app.run(host='0.0.0.0', port=5000, debug=True)