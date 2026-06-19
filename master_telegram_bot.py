import os
import shutil
import re
import time
import requests
import json
from google import genai
from google.genai import types
from PIL import Image
from playwright.sync_api import sync_playwright

# ==========================================
# 🛑 MULTI-KEY & MULTI-MODEL SYSTEM
# ==========================================
API_KEYS = [os.environ.get(f"GEMINI_API_KEY_{i}") for i in range(1, 11) if os.environ.get(f"GEMINI_API_KEY_{i}")]
if not API_KEYS and os.environ.get("GEMINI_API_KEY"): API_KEYS.append(os.environ.get("GEMINI_API_KEY"))

if not API_KEYS:
    print("❌ Koi API Key nahi mili! GitHub Secrets check karein.")
    exit()

# 🚀 AUTO-SWITCH MODELS LIST
GEMINI_MODELS = ['gemini-3.1-flash-lite', 'gemini-2.5-flash-lite', 'gemini-2.5-flash']

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INPUT_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
os.makedirs(DONE_FOLDER, exist_ok=True)

current_key_index = 0
client = genai.Client(api_key=API_KEYS[current_key_index])

def switch_api_key():
    global current_key_index, client
    current_key_index += 1
    if current_key_index < len(API_KEYS):
        print(f"🔄 Limit khtam! Nayi Key (Key {current_key_index + 1}) par switch kar rahe hain...")
        client = genai.Client(api_key=API_KEYS[current_key_index])
        return True
    return False

def send_photo_to_telegram(image_path, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, 'rb') as photo:
        return requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption}, files={"photo": photo}).json()

def send_poll_to_telegram(correct_option_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    opt_char = re.sub(r'[^a-dA-D1-4]', '', correct_option_text)
    clean_opt = opt_char[-1].lower() if opt_char else 'a'
    option_map = {"a": 0, "b": 1, "c": 2, "d": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": "Q. सही उत्तर चुनें (Choose the correct option):",
        "options": json.dumps(["Option A", "Option B", "Option C", "Option D"]),
        "type": "quiz",
        "correct_option_id": option_map.get(clean_opt, 0),
        "is_anonymous": True 
    }
    requests.post(url, data=payload)

def generate_solution_image(question_id, smart_approach, output_filename="solution_hd.png"):
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script>MathJax = {{ tex: {{ inlineMath: [['$', '$']], displayMath: [['$$', '$$']] }} }};</script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: sans-serif; background: #f4f4f9; padding: 30px; }}
            #content {{ width: 850px; background: #fff; padding: 40px; border-radius: 15px; border-left: 10px solid #ff7e5f; }}
            .smart-approach {{ background: #e8f5e9; padding: 25px; border-radius: 12px; border-left: 6px solid #4caf50; font-size: 22px; white-space: pre-wrap; }}
        </style>
    </head>
    <body>
        <div id="content">
            <div style="font-size:28px; font-weight:bold; color:#ff7e5f;">💡 Smart Approach</div>
            <div style="margin:20px 0; font-weight:bold;">🎯 ID: {question_id}</div>
            <div class="smart-approach">{smart_approach}</div>
        </div>
    </body>
    </html>"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1000, 'height': 600})
        page.set_content(html_content)
        page.wait_for_timeout(4000) 
        page.locator("#content").screenshot(path=output_filename)
        browser.close()
    return output_filename

def main():
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png'))])
    if not files: return
    
    # 50 Sawal ka batch
    files_to_process = files[:50]
    
    for current_question_file in files_to_process:
        question_path = os.path.join(INPUT_FOLDER, current_question_file)
        question_id = current_question_file.split('.')[0]
        
        send_photo_to_telegram(question_path, caption=f"🎯 Question ID: {question_id}")
        
        prompt = """तुम एक expert RPSC 2nd Grade Mathematics teacher हो।
        Task: इस फोटो में दिए गए maths के MCQ को solve करो।

        RULES:
        1. Language: अपना पूरा solution 'smart_approach' के अंदर सिर्फ और सिर्फ Pure Hindi (Devanagari script) में देना। (Math terms English में रख सकते हो)।
        2. Approach: कोई लम्बा step-by-step हल नहीं देना है। सिर्फ short trick, direct formula या option elimination का तरीका बताओ जिससे एग्जाम में 5-10 सेकंड में उत्तर निकाला जा सके।
        3. Formatting: Maths की हर एक equation, fraction, और variables (जैसे x, y) को हमेशा LaTeX यानी $$...$$ या $...$ के अंदर ही लिखना।

        STRICT INSTRUCTION: अपना जवाब strictly इस XML format में दो:
        <correct_option>C</correct_option>
        <smart_approach>यहाँ आपकी हिंदी में शॉर्ट ट्रिक...</smart_approach>"""
        response = None
        for model in GEMINI_MODELS:
            try:
                print(f"🧠 Trying {model}...")
                response = client.models.generate_content(model=model, contents=[prompt, Image.open(question_path)])
                break
            except Exception: continue
        
        if response:
            text = response.text
            try:
                correct_opt = re.search(r'<correct_option>(.*?)</correct_option>', text, re.DOTALL).group(1).strip()
                smart_app = re.search(r'<smart_approach>(.*?)</smart_approach>', text, re.DOTALL).group(1).strip()
                send_poll_to_telegram(correct_opt)
                sol = generate_solution_image(question_id, smart_app)
                send_photo_to_telegram(sol, caption=f"💡 Solution | ID: {question_id}")
                shutil.move(question_path, os.path.join(DONE_FOLDER, current_question_file))
                if os.path.exists(sol): os.remove(sol)
            except: print("❌ Parse error")
        
        time.sleep(30)

if __name__ == "__main__":
    main()
