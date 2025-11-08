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

# ---------- Database ----------
try:
    from database import Database
    db = Database()
    # Garantir que as tabelas sejam criadas
    db.criar_tabelas()
    print("✅ Banco de dados inicializado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao inicializar banco de dados: {e}")
    exit(1)

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
    try:
        # Buscar dados usando o método do banco
        chromebooks = db.obter_todos_chromebooks()

        # Calcular estatísticas básicas
        total = len(chromebooks)
        disponiveis = sum(1 for c in chromebooks if c[2] == 'Disponível')
        emprestados = sum(1 for c in chromebooks if c[2] == 'Emprestado')

        # Dicionário para o template
        stats = {
            "total": total,
            "disponiveis": disponiveis,
            "emprestados": emprestados
        }

        return safe_render("dashboard.html", chromebooks=chromebooks, stats=stats)
    except Exception as e:
        flash(f"Erro ao carregar dashboard: {e}", "danger")
        return redirect(url_for('login'))

# ... (restante das rotas permanece igual) ...

@app.route('/emprestimo', methods=['GET', 'POST'])
@login_required
def emprestimo():
    if request.method == 'POST':
        numero = request.form.get('numero_chromebook')
        carrinho = request.form.get('carrinho')
        nome_aluno = request.form.get('nome_aluno')
        turma = request.form.get('turma')
        professor = current_user.nome
        
        if numero and carrinho and nome_aluno and turma:
            success, message = db.registrar_emprestimo(int(numero), carrinho, nome_aluno, turma, professor)
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
    chromebooks = db.obter_chromebooks_disponiveis()
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