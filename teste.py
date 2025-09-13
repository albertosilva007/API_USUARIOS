import requests

# Criar usuário
dados = {
    "nome": "Maria Silva",
    "email": "maria@email.com",
    "senha": "123456",
    "telefone": "(83) 99999-9999"
}

print("🔄 Criando usuário...")
response = requests.post("http://localhost:5000/usuarios", json=dados)
print(f"📝 Resposta: {response.json()}")
print(f"📊 Status: {response.status_code}")
