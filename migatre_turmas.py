# migrate_turmas.py - Script para adicionar colunas de turma ao banco de dados
import sqlite3
import os

def migrar_banco_dados():
    db_path = os.path.join(os.path.dirname(__file__), 'chromebooks.db')
    
    if not os.path.exists(db_path):
        print("❌ Banco de dados não encontrado!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna turma_aluno já existe na tabela chromebooks
        cursor.execute("PRAGMA table_info(chromebooks)")
        colunas_chromebooks = [coluna[1] for coluna in cursor.fetchall()]
        
        if 'turma_aluno' not in colunas_chromebooks:
            print("🔄 Adicionando coluna 'turma_aluno' à tabela chromebooks...")
            cursor.execute("ALTER TABLE chromebooks ADD COLUMN turma_aluno TEXT")
            print("✅ Coluna 'turma_aluno' adicionada com sucesso!")
        else:
            print("✅ Coluna 'turma_aluno' já existe na tabela chromebooks")
        
        # Verificar se a coluna turma já existe na tabela historico
        cursor.execute("PRAGMA table_info(historico)")
        colunas_historico = [coluna[1] for coluna in cursor.fetchall()]
        
        if 'turma' not in colunas_historico:
            print("🔄 Adicionando coluna 'turma' à tabela historico...")
            cursor.execute("ALTER TABLE historico ADD COLUMN turma TEXT")
            print("✅ Coluna 'turma' adicionada com sucesso!")
        else:
            print("✅ Coluna 'turma' já existe na tabela historico")
        
        conn.commit()
        print("🎉 Migração concluída com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("🚀 Iniciando migração do banco de dados...")
    migrar_banco_dados()
    print("\n📝 Próximos passos:")
    print("1. Execute este script: python migrate_turmas.py")
    print("2. Execute o servidor: python app.py")