# Crie um arquivo teste_multiplos.py
import requests

usuarios = [
    {"nome": "João Silva", "email": "joao@email.com",
        "senha": "123456", "telefone": "(83) 99999-1111"},
    {"nome": "Maria Santos", "email": "maria@email.com",
        "senha": "maria123", "telefone": "(83) 88888-2222"},
    {"nome": "Pedro Oliveira", "email": "pedro@email.com", "senha": "pedro123"}
]

print("👥 Criando múltiplos usuários:")
for usuario in usuarios:
    response = requests.post("http://localhost:5000/usuarios", json=usuario)
    print(f"✅ {usuario['nome']}: Status {response.status_code}")

# Listar todos
print("\n📋 Lista final:")
response = requests.get("http://localhost:5000/usuarios")
data = response.json()
print(f"Total: {data['total']} usuários")

for user in data['usuarios']:
    print(f"- ID: {user['id']} | {user['nome']} | {user['email']}")
