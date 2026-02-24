import google.generativeai as genai
import os

# New key provided by user
GEMINI_API_KEY = "AIzaSyCd5wNhgfAFZWpHdGDA9RSzpQ-YZeTHms0"
genai.configure(api_key=GEMINI_API_KEY)

try:
    print("Testing API Key...")
    model = genai.GenerativeModel('gemini-flash-latest')
    response = model.generate_content("Ping")
    print(f"STATUS: SUCCESS")
    print(f"RESPONSE: {response.text}")
except Exception as e:
    print(f"STATUS: ERROR")
    print(f"ERROR: {e}")
