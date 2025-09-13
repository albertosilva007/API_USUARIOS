import urllib.request
import urllib.parse
import json

BASE_URL = "http://localhost:5000"


def fazer_request(url, method='GET', data=None, headers=None):
    """Faz requisições HTTP usando urllib"""
    if headers is None:
        headers = {}

    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(
        url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            return response.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode('utf-8')
        return e.code, json.loads(content) if content else {}
    except Exception as e:
        return 0, {'erro': str(e)}


def test_health():
    print("🔍 TESTE 1: Health Check")
    print("-" * 30)

    status, data = fazer_request(f"{BASE_URL}/health")
    print(f"Status: {status}")
    print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")

    sucesso = status == 200
    print(f"Resultado: {'✅ PASSOU' if sucesso else '❌ FALHOU'}")
    return sucesso


def test_criar_usuario():
    print("\n👤 TESTE 2: Criar Usuário")
    print("-" * 30)

    dados = {
        "nome": "João da Silva",
        "email": "joao@email.com",
        "senha": "senha123",
        "telefone": "(83) 99999-8888"
    }

    status, data = fazer_request(f"{BASE_URL}/usuarios", 'POST', dados)
    print(f"Status: {status}")
    print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")

    sucesso = status == 201
    user_id = data.get('id') if sucesso else None
    print(f"Resultado: {'✅ PASSOU' if sucesso else '❌ FALHOU'}")

    return user_id


def test_listar_usuarios():
    print("\n📋 TESTE 3: Listar Usuários")
    print("-" * 30)

    status, data = fazer_request(f"{BASE_URL}/usuarios")
    print(f"Status: {status}")
    print(f"Total de usuários: {data.get('total', 0)}")

    if data.get('usuarios'):
        print("Usuários encontrados:")
        for i, usuario in enumerate(data['usuarios'], 1):
            print(f"  {i}. {usuario['nome']} ({usuario['email']})")

    sucesso = status == 200
    print(f"Resultado: {'✅ PASSOU' if sucesso else '❌ FALHOU'}")
    return sucesso


def test_buscar_usuario(user_id):
    print(f"\n🔎 TESTE 4: Buscar Usuário ID {user_id}")
    print("-" * 30)

    if not user_id:
        print("❌ Não foi possível testar (usuário não foi criado)")
        return False

    status, data = fazer_request(f"{BASE_URL}/usuarios/{user_id}")
    print(f"Status: {status}")
    print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")

    sucesso = status == 200
    print(f"Resultado: {'✅ PASSOU' if sucesso else '❌ FALHOU'}")
    return sucesso


def test_buscar_por_termo():
    print("\n🔍 TESTE 5: Buscar por Termo")
    print("-" * 30)

    termo = "João"
    url = f"{BASE_URL}/usuarios/buscar?q={urllib.parse.quote(termo)}"
    status, data = fazer_request(url)

    print(f"Status: {status}")
    print(f"Buscando por: '{termo}'")
    print(f"Usuários encontrados: {data.get('total', 0)}")

    if data.get('usuarios'):
        for usuario in data['usuarios']:
            print(f"  - {usuario['nome']} ({usuario['email']})")

    sucesso = status == 200
    print(f"Resultado: {'✅ PASSOU' if sucesso else '❌ FALHOU'}")
    return sucesso


def test_email_duplicado():
    print("\n⚠️ TESTE 6: Email Duplicado (deve dar erro)")
    print("-" * 30)

    dados = {
        "nome": "Outro João",
        "email": "joao@email.com",  # Email já usado
        "senha": "outrasenha"
    }

    status, data = fazer_request(f"{BASE_URL}/usuarios", 'POST', dados)
    print(f"Status: {status}")
    print(f"Resposta: {json.dumps(data, indent=2, ensure_ascii=False)}")

    sucesso = status == 409  # Deve dar erro de conflito
    print(
        f"Resultado: {'✅ PASSOU (validação funcionou)' if sucesso else '❌ FALHOU (deveria dar erro 409)'}")
    return sucesso


def main():
    print("🚀 INICIANDO TESTES DA API DE USUÁRIOS")
    print(f"🌐 Base URL: {BASE_URL}")
    print("=" * 50)

    resultados = []

    # Executar testes
    resultados.append(("Health Check", test_health()))
    user_id = test_criar_usuario()
    resultados.append(("Criar Usuário", user_id is not None))
    resultados.append(("Listar Usuários", test_listar_usuarios()))
    resultados.append(("Buscar Usuário", test_buscar_usuario(user_id)))
    resultados.append(("Buscar por Termo", test_buscar_por_termo()))
    resultados.append(("Validação Email", test_email_duplicado()))

    # Resumo
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES")
    print("=" * 50)

    sucessos = 0
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{nome:20} {status}")
        if sucesso:
            sucessos += 1

    print("-" * 50)
    print(f"🎯 Resultado Final: {sucessos}/{len(resultados)} testes passaram")

    if sucessos == len(resultados):
        print("🎉 PARABÉNS! Sua API está funcionando perfeitamente!")
    else:
        print("⚠️ Alguns testes falharam. Verifique se a API está rodando.")

    print("\n💡 Para mais testes, instale requests: pip install requests")


if __name__ == "__main__":
    main()
