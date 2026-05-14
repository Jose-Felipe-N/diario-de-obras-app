import os
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega a chave
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Buscando modelos disponíveis na sua conta do Google...\n")

# Pede pro Google a lista de modelos que aceitam gerar texto
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Nome liberado: {m.name}")
except Exception as e:
    print(f"❌ Erro ao conectar: {e}")