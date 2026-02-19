import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBlZMZOEpfCkXiRWjfUADR_nVmyZdsTBRE")
genai.configure(api_key=GEMINI_API_KEY)

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
