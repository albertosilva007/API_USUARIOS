from flask import Flask, request, jsonify
from datetime import datetime, timezone
import sqlite3
import hashlib
import re
import os

app = Flask(__name__)

# Configuração do banco de dados
DATABASE = 'usuarios.db'


def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            telefone TEXT,
            data_cadastro TEXT NOT NULL,
            ativo BOOLEAN DEFAULT 1
        )
    ''')

    conn.commit()
    conn.close()


def get_db_connection():
    """Conecta ao banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def validar_email(email):
    """Valida formato do email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None


def hash_senha(senha):
    """Cria hash da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()


@app.route('/usuarios', methods=['POST'])
def criar_usuario():
    """Cria um novo usuário"""
    try:
        dados = request.get_json()

        # Validação dos campos obrigatórios
        if not dados or not dados.get('nome') or not dados.get('email') or not dados.get('senha'):
            return jsonify({'erro': 'Nome, email e senha são obrigatórios'}), 400

        nome = dados['nome'].strip()
        email = dados['email'].strip().lower()
        senha = dados['senha']
        telefone = dados.get('telefone', '').strip()

        # Validações
        if len(nome) < 2:
            return jsonify({'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400

        if not validar_email(email):
            return jsonify({'erro': 'Email inválido'}), 400

        if len(senha) < 6:
            return jsonify({'erro': 'Senha deve ter pelo menos 6 caracteres'}), 400

        # Hash da senha
        senha_hash = hash_senha(senha)

        # Data atual
        data_cadastro = datetime.now(timezone.utc).isoformat()

        # Inserir no banco
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha, telefone, data_cadastro)
                VALUES (?, ?, ?, ?, ?)
            ''', (nome, email, senha_hash, telefone, data_cadastro))

            user_id = cursor.lastrowid
            conn.commit()

            return jsonify({
                'mensagem': 'Usuário criado com sucesso',
                'id': user_id,
                'nome': nome,
                'email': email
            }), 201

        except sqlite3.IntegrityError:
            return jsonify({'erro': 'Email já cadastrado'}), 409
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    """Lista todos os usuários ativos"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)),
                       100)  # Máximo 100 por página
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor()

        # Contar total de usuários
        cursor.execute('SELECT COUNT(*) FROM usuarios WHERE ativo = 1')
        total = cursor.fetchone()[0]

        # Buscar usuários com paginação
        cursor.execute('''
            SELECT id, nome, email, telefone, data_cadastro 
            FROM usuarios 
            WHERE ativo = 1 
            ORDER BY data_cadastro DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))

        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'id': row['id'],
                'nome': row['nome'],
                'email': row['email'],
                'telefone': row['telefone'],
                'data_cadastro': row['data_cadastro']
            })

        conn.close()

        return jsonify({
            'usuarios': usuarios,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['GET'])
def obter_usuario(user_id):
    """Obtém um usuário específico"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, nome, email, telefone, data_cadastro 
            FROM usuarios 
            WHERE id = ? AND ativo = 1
        ''', (user_id,))

        usuario = cursor.fetchone()
        conn.close()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        return jsonify({
            'id': usuario['id'],
            'nome': usuario['nome'],
            'email': usuario['email'],
            'telefone': usuario['telefone'],
            'data_cadastro': usuario['data_cadastro']
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['PUT'])
def atualizar_usuario(user_id):
    """Atualiza um usuário"""
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400

        # Verificar se usuário existe
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT id FROM usuarios WHERE id = ? AND ativo = 1', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Preparar campos para atualização
        campos_update = []
        valores = []

        if 'nome' in dados:
            nome = dados['nome'].strip()
            if len(nome) < 2:
                conn.close()
                return jsonify({'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400
            campos_update.append('nome = ?')
            valores.append(nome)

        if 'email' in dados:
            email = dados['email'].strip().lower()
            if not validar_email(email):
                conn.close()
                return jsonify({'erro': 'Email inválido'}), 400
            campos_update.append('email = ?')
            valores.append(email)

        if 'telefone' in dados:
            campos_update.append('telefone = ?')
            valores.append(dados['telefone'].strip())

        if 'senha' in dados:
            senha = dados['senha']
            if len(senha) < 6:
                conn.close()
                return jsonify({'erro': 'Senha deve ter pelo menos 6 caracteres'}), 400
            campos_update.append('senha = ?')
            valores.append(hash_senha(senha))

        if not campos_update:
            conn.close()
            return jsonify({'erro': 'Nenhum campo para atualizar'}), 400

        # Executar atualização
        valores.append(user_id)
        query = f'UPDATE usuarios SET {", ".join(campos_update)} WHERE id = ?'

        try:
            cursor.execute(query, valores)
            conn.commit()

            # Buscar dados atualizados
            cursor.execute('''
                SELECT id, nome, email, telefone, data_cadastro 
                FROM usuarios WHERE id = ?
            ''', (user_id,))

            usuario = cursor.fetchone()
            conn.close()

            return jsonify({
                'mensagem': 'Usuário atualizado com sucesso',
                'usuario': {
                    'id': usuario['id'],
                    'nome': usuario['nome'],
                    'email': usuario['email'],
                    'telefone': usuario['telefone'],
                    'data_cadastro': usuario['data_cadastro']
                }
            }), 200

        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'erro': 'Email já cadastrado por outro usuário'}), 409

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['DELETE'])
def deletar_usuario(user_id):
    """Deleta um usuário (soft delete)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar se usuário existe e está ativo
        cursor.execute(
            'SELECT id FROM usuarios WHERE id = ? AND ativo = 1', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Soft delete
        cursor.execute(
            'UPDATE usuarios SET ativo = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()

        return jsonify({'mensagem': 'Usuário deletado com sucesso'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/buscar', methods=['GET'])
def buscar_usuarios():
    """Busca usuários por nome ou email"""
    try:
        termo = request.args.get('q', '').strip()
        if not termo:
            return jsonify({'erro': 'Termo de busca não fornecido'}), 400

        if len(termo) < 2:
            return jsonify({'erro': 'Termo deve ter pelo menos 2 caracteres'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, nome, email, telefone, data_cadastro 
            FROM usuarios 
            WHERE (nome LIKE ? OR email LIKE ?) AND ativo = 1
            ORDER BY nome
            LIMIT 20
        ''', (f'%{termo}%', f'%{termo}%'))

        usuarios = []
        for row in cursor.fetchall():
            usuarios.append({
                'id': row['id'],
                'nome': row['nome'],
                'email': row['email'],
                'telefone': row['telefone'],
                'data_cadastro': row['data_cadastro']
            })

        conn.close()

        return jsonify({
            'usuarios': usuarios,
            'total': len(usuarios)
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar saúde da API"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'erro': 'Endpoint não encontrado'}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'erro': 'Método não permitido'}), 405


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
