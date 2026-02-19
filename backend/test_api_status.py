import google.generativeai as genai
import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBlZMZOEpfCkXiRWjfUADR_nVmyZdsTBRE")
genai.configure(api_key=GEMINI_API_KEY)

try:
    model = genai.GenerativeModel('models/gemini-1.5-flash')
    response = model.generate_content("Hello, are you working?")
    print(f"STATUS: SUCCESS")
    print(f"RESPONSE: {response.text}")
except Exception as e:
    print(f"STATUS: ERROR")
    print(f"ERROR: {e}")
