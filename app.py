from flask import Flask, request, jsonify
from datetime import datetime, timezone
import sqlite3
import hashlib
import re
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count

# --- CORREÇÃO PARA ERRO DO HADOOP NO WINDOWS ---
# Garante que o PySpark funcione corretamente em ambientes Windows.
os.environ['HADOOP_USER_NAME'] = 'Administrador'
# ---------------------------------------------

app = Flask(__name__)

# --- Configuração do PySpark ---
# É necessário baixar o driver JDBC para SQLite e colocar o caminho para o arquivo .jar aqui.
# Exemplo de download: https://github.com/xerial/sqlite-jdbc
# Altere "caminho/para/o/sqlite-jdbc-3.34.0.jar" para o caminho real no seu sistema.
spark = SparkSession.builder \
    .appName("API com PySpark e SQLite") \
    .config("spark.driver.extraClassPath", "caminho/para/o/sqlite-jdbc-3.34.0.jar") \
    .getOrCreate()

# --- Configuração do Banco de Dados ---
# Corrigido para o nome do arquivo fornecido
DATABASE = 'database.db'


def get_db_connection():
    """Conecta ao banco de dados para operações não-Spark (CRUD)"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_spark_dataframe(table_name):
    """Cria um DataFrame do Spark a partir de uma tabela do banco de dados"""
    return spark.read.format("jdbc") \
        .option("url", f"jdbc:sqlite:{DATABASE}") \
        .option("dbtable", table_name) \
        .option("driver", "org.sqlite.JDBC") \
        .load()


def validar_email(email):
    """Valida formato do email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None


def hash_senha(senha):
    """Cria hash da senha usando SHA256"""
    return hashlib.sha256(senha.encode()).hexdigest()


# --- ENDPOINTS COM OPERAÇÕES DIRETAS NO BANCO (Mais eficientes para registros únicos) ---

@app.route('/usuarios', methods=['POST'])
def criar_usuario():
    """Cria um novo usuário (usando sqlite3 para eficiência)"""
    try:
        dados = request.get_json()
        if not dados or not dados.get('nome') or not dados.get('email') or not dados.get('senha'):
            return jsonify({'erro': 'Nome, email e senha são obrigatórios'}), 400

        nome = dados['nome'].strip()
        email = dados['email'].strip().lower()
        senha = dados['senha']
        telefone = dados.get('telefone', '').strip()

        if len(nome) < 2:
            return jsonify({'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400
        if not validar_email(email):
            return jsonify({'erro': 'Email inválido'}), 400
        if len(senha) < 6:
            return jsonify({'erro': 'Senha deve ter pelo menos 6 caracteres'}), 400

        senha_hash = hash_senha(senha)
        data_cadastro = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO usuarios (nome, email, senha, telefone, data_cadastro) VALUES (?, ?, ?, ?, ?)',
                           (nome, email, senha_hash, telefone, data_cadastro))
            user_id = cursor.lastrowid
            conn.commit()
            return jsonify({'mensagem': 'Usuário criado com sucesso', 'id': user_id, 'nome': nome, 'email': email}), 201
        except sqlite3.IntegrityError:
            return jsonify({'erro': 'Email já cadastrado'}), 409
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['GET'])
def obter_usuario(user_id):
    """Obtém um usuário específico (usando sqlite3 para eficiência)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, nome, email, telefone, data_cadastro FROM usuarios WHERE id = ? AND ativo = 1', (user_id,))
        usuario = cursor.fetchone()
        conn.close()
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        return jsonify(dict(usuario)), 200
    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['PUT'])
def atualizar_usuario(user_id):
    """Atualiza um usuário (usando sqlite3 para eficiência)"""
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Dados não fornecidos'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM usuarios WHERE id = ? AND ativo = 1', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        campos_update, valores = [], []
        if 'nome' in dados:
            nome = dados['nome'].strip()
            if len(nome) < 2:
                return jsonify({'erro': 'Nome deve ter pelo menos 2 caracteres'}), 400
            campos_update.append('nome = ?')
            valores.append(nome)
        if 'email' in dados:
            email = dados['email'].strip().lower()
            if not validar_email(email):
                return jsonify({'erro': 'Email inválido'}), 400
            campos_update.append('email = ?')
            valores.append(email)
        if 'telefone' in dados:
            campos_update.append('telefone = ?')
            valores.append(dados['telefone'].strip())
        if 'senha' in dados:
            senha = dados['senha']
            if len(senha) < 6:
                return jsonify({'erro': 'Senha deve ter pelo menos 6 caracteres'}), 400
            campos_update.append('senha = ?')
            valores.append(hash_senha(senha))

        if not campos_update:
            return jsonify({'erro': 'Nenhum campo para atualizar'}), 400

        valores.append(user_id)
        query = f'UPDATE usuarios SET {", ".join(campos_update)} WHERE id = ?'
        try:
            cursor.execute(query, valores)
            conn.commit()
            cursor.execute(
                'SELECT id, nome, email, telefone, data_cadastro FROM usuarios WHERE id = ?', (user_id,))
            usuario = cursor.fetchone()
            return jsonify({'mensagem': 'Usuário atualizado com sucesso', 'usuario': dict(usuario)}), 200
        except sqlite3.IntegrityError:
            return jsonify({'erro': 'Email já cadastrado por outro usuário'}), 409
        finally:
            conn.close()
    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


@app.route('/usuarios/<int:user_id>', methods=['DELETE'])
def deletar_usuario(user_id):
    """Deleta um usuário (soft delete, usando sqlite3 para eficiência)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id FROM usuarios WHERE id = ? AND ativo = 1', (user_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        cursor.execute(
            'UPDATE usuarios SET ativo = 0 WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'mensagem': 'Usuário deletado com sucesso'}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500


# --- ENDPOINTS COM CONSULTA E TRATAMENTO DE DADOS USANDO PYSPARK ---

@app.route('/usuarios', methods=['GET'])
def listar_usuarios_pyspark():
    """Lista todos os usuários ativos (usando PySpark)"""
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 100)

        df_usuarios = get_spark_dataframe('usuarios')

        # Tratamento dos dados com PySpark
        df_ativos = df_usuarios.filter(col("ativo") == 1)

        total = df_ativos.count()

        # Paginação com PySpark
        # Nota: Em um cluster real e com dados massivos, a paginação com offset pode ser ineficiente.
        # Outras estratégias como "keyset pagination" são recomendadas.
        offset = (page - 1) * per_page
        df_paginado = df_ativos.orderBy(col("data_cadastro").desc()) \
                               .select("id", "nome", "email", "telefone", "data_cadastro") \
                               .limit(per_page).offset(offset)

        usuarios = [row.asDict() for row in df_paginado.collect()]

        return jsonify({
            'usuarios': usuarios,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro interno com PySpark: {str(e)}'}), 500


@app.route('/usuarios/buscar', methods=['GET'])
def buscar_usuarios_pyspark():
    """Busca usuários por nome ou email (usando PySpark)"""
    try:
        termo = request.args.get('q', '').strip()
        if not termo or len(termo) < 2:
            return jsonify({'erro': 'Termo de busca deve ter pelo menos 2 caracteres'}), 400

        df_usuarios = get_spark_dataframe('usuarios')

        # Tratamento de busca com PySpark
        termo_busca = f"%{termo}%"
        df_resultado = df_usuarios.filter(
            (col("ativo") == 1) &
            ((col("nome").like(termo_busca)) | (col("email").like(termo_busca)))
        ).select("id", "nome", "email", "telefone", "data_cadastro") \
         .orderBy("nome") \
         .limit(20)

        usuarios = [row.asDict() for row in df_resultado.collect()]

        return jsonify({'usuarios': usuarios, 'total': len(usuarios)}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro interno com PySpark: {str(e)}'}), 500

# --- ENDPOINTS AUXILIARES ---


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar a saúde da API"""
    return jsonify({'status': 'OK', 'timestamp': datetime.now(timezone.utc).isoformat()}), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({'erro': 'Endpoint não encontrado'}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'erro': 'Método não permitido'}), 405


if __name__ == '__main__':
    # Garante que o diretório do banco de dados exista
    if not os.path.exists(DATABASE):
        raise FileNotFoundError(
            f"Arquivo de banco de dados '{DATABASE}' não encontrado. Certifique-se de que ele está no mesmo diretório do script.")

    app.run(debug=True, host='0.0.0.0', port=5000)
