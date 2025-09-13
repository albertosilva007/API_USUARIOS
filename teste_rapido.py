import requests

# Listar usuários existentes
print("📋 Usuários existentes:")
response = requests.get("http://localhost:5000/usuarios")
data = response.json()
print(f"Total: {data.get('total', 0)} usuários")

for user in data.get('usuarios', []):
    print(f"- {user['nome']} ({user['email']})")

# Criar novo usuário
print("\n👤 Criando novo usuário:")
novo_usuario = {
    "nome": "Test User",
    "email": f"test{data.get('total', 0)}@email.com",
    "senha": "123456"
}

response = requests.post("http://localhost:5000/usuarios", json=novo_usuario)
print(f"Status: {response.status_code}")
print(f"Resposta: {response.json()}")
