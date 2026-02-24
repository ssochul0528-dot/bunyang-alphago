import google.generativeai as genai
import os

GEMINI_API_KEY = "AIzaSyCd5wNhgfAFZWpHdGDA9RSzpQ-YZeTHms0"
genai.configure(api_key=GEMINI_API_KEY)

try:
    print("Available Models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"ERROR: {e}")
