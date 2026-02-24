import google.generativeai as genai
import os

GEMINI_API_KEY = "AIzaSyCd5wNhgfAFZWpHdGDA9RSzpQ-YZeTHms0"
genai.configure(api_key=GEMINI_API_KEY)

try:
    print("Testing gemini-2.0-flash...")
    model = genai.GenerativeModel('models/gemini-2.0-flash')
    response = model.generate_content("Ping")
    print(f"STATUS: SUCCESS")
    print(f"RESPONSE: {response.text}")
except Exception as e:
    print(f"STATUS: ERROR")
    print(f"ERROR: {e}")
