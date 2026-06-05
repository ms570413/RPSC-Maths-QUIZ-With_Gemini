import os
import shutil
import re
import time
import requests
import json
from google import genai
from PIL import Image
from playwright.sync_api import sync_playwright

# ==========================================
# 🛑 MULTI-KEY SYSTEM: Sari keys load karna
# ==========================================
API_KEYS = []
for i in range(1, 6): 
    k = os.environ.get(f"GEMINI_API_KEY_{i}")
    if k:
        API_KEYS.append(k)

# Agar purani key bhi hui toh use fallback me le lenge
if not API_KEYS:
    k = os.environ.get("GEMINI_API_KEY")
    if k:
        API_KEYS.append(k)

if not API_KEYS:
    print("❌ Koi API Key nahi mili! GitHub Secrets check karein.")
    exit()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INPUT_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
os.makedirs(DONE_FOLDER, exist_ok=True)

# 💡 Setup Global Client
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
    print("📤 Telegram par photo bhej rahe hain...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, 'rb') as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        response = requests.post(url, data=payload, files={"photo": photo})
        result = response.json()
        if not result.get("ok"):
            doc_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            photo.seek(0) 
            doc_response = requests.post(doc_url, data=payload, files={"document": photo})
            return doc_response.json()
    return result

def send_poll_to_telegram(correct_option_text):
    print(f"📊 Telegram par Poll bhej rahe hain... (AI Option: {correct_option_text})")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    opt_char = re.sub(r'[^a-dA-D1-4]', '', correct_option_text)
    clean_opt = opt_char[-1].lower() if opt_char else 'a'
    option_map = {"a": 0, "b": 1, "c": 2, "d": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    correct_id = option_map.get(clean_opt, 0)

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": "Q. सही उत्तर चुनें (Choose the correct option):",
        "options": json.dumps(["Option A (या 1)", "Option B (या 2)", "Option C (या 3)", "Option D (या 4)"]),
        "type": "quiz",
        "correct_option_id": correct_id,
        "is_anonymous": True 
    }
    requests.post(url, data=payload)

def generate_solution_image(question_id, smart_approach, output_filename="solution_hd.png"):
    print(f"🎨 Playwright se HD Image bana rahe hain (ID: {question_id})...")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script>
        MathJax = {{
          tex: {{
            inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
            displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']],
            processEscapes: true
          }}
        }};
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; padding: 30px; color: #333; margin: 0; }}
            #content-to-capture {{ width: 850px; background-color: #fff; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 10px solid #ff7e5f; margin: 0 auto; position: relative; }}
            .header {{ font-size: 28px; font-weight: bold; color: #ff7e5f; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .qid-badge {{ display: inline-block; background-color: #333; color: #fff; padding: 8px 18px; border-radius: 8px; font-size: 18px; font-weight: bold; margin-bottom: 20px; letter-spacing: 1px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
            .smart-approach {{ background-color: #e8f5e9; padding: 25px; border-radius: 12px; margin-bottom: 10px; border-left: 6px solid #4caf50; font-size: 24px; line-height: 1.6; white-space: pre-wrap; }}
            .watermark {{ text-align: center; margin-top: 25px; font-size: 22px; font-weight: bold; color: #ff7e5f; opacity: 0.8; }}
            mjx-container {{ max-width: 100%; overflow-x: auto; overflow-y: hidden; }}
        </style>
    </head>
    <body>
        <div id="content-to-capture">
            <div class="header">💡 Smart Approach & Option Elimination</div>
            <div class="qid-badge">🎯 Question ID: {question_id}</div>
            <div class="smart-approach">
{smart_approach}
            </div>
            <div class="watermark">@iam_MukeshManya_Rj08</div>
        </div>
    </body>
    </html>
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page(viewport={'width': 1000, 'height': 600}, device_scale_factor=2)
        page.set_content(html_content)
        page.wait_for_timeout(4000) 
        element = page.locator("#content-to-capture")
        element.screenshot(path=output_filename)
        browser.close()
    return output_filename

def main():
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    if not files:
        print("🎉 Badhai ho! Saare sawal pure ho chuke hain. Folder khali hai.")
        return

    # 💡 Ab ek baar me 100 questions process honge, bina lambe break ke!
    batch_limit = 100
    files_to_process = files[:batch_limit]
    
    print(f"📦 Is batch ke liye total {len(files_to_process)} questions process honge...")

    for current_question_file in files_to_process:
        question_path = os.path.join(INPUT_FOLDER, current_question_file)
        question_id = current_question_file.split('.')[0]
        
        print(f"\n🚀 Processing shuru: {current_question_file}")
        send_photo_to_telegram(question_path, caption=f"🎯 Question ID: {question_id}")

        prompt = """
        tum ek expert RPSC 2nd Grade Mathematics teacher ho.
        is photo mein diye gaye maths ke MCQ ko solve karo. 
        
        RULE 1: koi lamba step-by-step hal bilkul nahi dena hai. puri calculation mat dikhana.
        RULE 2: 'smart_approach' mein kewal short trick, direct formula ya option elimination ka tarika batao jisse exam mein 5-10 second mein uttar nikala ja sake. 
        RULE 3: maths ki har ek choti-badi equation, fraction (jaise \\frac), variables (x, y) ko LAZMI TAUR PAR $$...$$ ya $...$ (LaTeX) ke andar hi likhna. bina $ lagaye koi bhi math term mat likhna, warna error aayegi.

        STRICT INSTRUCTION: apna jawab sirf aur sirf niche diye gaye XML format mein hi dena:
        
        <correct_option>C</correct_option>
        <smart_approach>yahan aapki short trick ya option elimination ka tarika...</smart_approach>
        """
        
        max_retries = 5
        response = None
        
        for attempt in range(max_retries):
            try:
                print(f"🧠 Gemini dimaag laga raha hai... (Attempt {attempt + 1} with Key {current_key_index + 1})")
                img = Image.open(question_path)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt, img]
                )
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ Attempt {attempt + 1} fail hua: {error_msg}")
                
                # 💡 MULTI-KEY SWITCHING LOGIC
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    if switch_api_key():
                        time.sleep(2) # Key switch ki, 2 sec ruko aur aage badho
                        continue
                    else:
                        print("⏳ Sari API keys khatam ho gayi! 60 second ka break le rahe hain...")
                        time.sleep(60)
                else:
                    if attempt < max_retries - 1:
                        print("⏳ Server busy hai. 10 second baad wapas try kar raha hu...")
                        time.sleep(10)
                    else:
                        print("❌ 5 baar try karne ke baad bhi server busy hai. Is sawal ko skip kar rahe hain.")

        if response is None:
            continue
            
        try:
            text = response.text
            correct_opt = re.search(r'<correct_option>(.*?)</correct_option>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            smart_app = re.search(r'<smart_approach>(.*?)</smart_approach>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            
            send_poll_to_telegram(correct_opt)
            
            sol_image_path = generate_solution_image(question_id, smart_app)
            if os.path.exists(sol_image_path):
                send_photo_to_telegram(sol_image_path, caption=f"💡 Smart Solution by Master Bot | ID: {question_id}")
            
            shutil.move(question_path, os.path.join(DONE_FOLDER, current_question_file))
            if os.path.exists(sol_image_path):
                os.remove(sol_image_path)
                
            print(f"✅ {current_question_file} ka kaam successfully pura hua!")
            
            # Ab lambe break ki zarurat nahi, bas 5 second tak bot saans lega
            time.sleep(5)

        except Exception as e:
            print(f"❌ Output padhne ya photo banane mein error aa gayi: {e}")
            print("AI Response:", response.text if response else "No response")
            continue

if __name__ == "__main__":
    main()
