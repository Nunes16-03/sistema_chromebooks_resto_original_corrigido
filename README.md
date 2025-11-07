
# Sistema Chromebook (versão corrigida)
- Senhas agora são armazenadas de forma segura (criptografadas com hash).
- A chave secreta (`app.secret_key`) é lida de uma variável de ambiente.
- O modo debug só liga se `FLASK_DEBUG=1` for definido.
- Incluídos `requirements.txt` e `migrate_passwords.py` para facilitar manutenção.

## Como usar
1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
2. Execute a migração de senhas (gera backup automático):
   ```bash
   python migrate_passwords.py
   ```
3. Rode o sistema:
   ```bash
   export FLASK_SECRET_KEY="chave_segura_123"
   export FLASK_DEBUG=1
   python app.py
   ```
