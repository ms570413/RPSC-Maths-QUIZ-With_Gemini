import os
import json
import time
import shutil
import requests
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# 💡 1. API Keys aur Telegram Setup
raw_keys = [
    os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"), os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"), os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"), os.getenv("GEMINI_API_KEY_8"),
    os.getenv("GEMINI_API_KEY_9"), os.getenv("GEMINI_API_KEY_10")
]
GEMINI_KEYS = [k.strip() for k in raw_keys if k is not None and k.strip() != ""]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SOURCE_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
QUESTIONS_PER_RUN = 25

os.makedirs(DONE_FOLDER, exist_ok=True)

# 🚀 AUTO-SWITCH MODELS LIST
GEMINI_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash'
]

# 💡 2. Playwright se Blank Page par MathJax + Q-ID Render karna
def create_solution_image(reason_text, q_num, output_path="SPOILER_solution.png"):
    reason_html = reason_text.replace('\n', '<br>')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600&display=swap" rel="stylesheet">
        <script>
          window.MathJax = {{
            tex: {{
              inlineMath: [['$', '$'], ['$$', '$$'], ['\\\\(', '\\\\)']],
              displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            }}
          }};
        </script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Noto Sans Devanagari', sans-serif; padding: 20px; background: white; font-size: 20px; color: #222; line-height: 1.6; }}
            .box {{ border: 2px solid #5865F2; padding: 25px; border-radius: 10px; background: #fdfdfd; display: inline-block; min-width: 400px; max-width: 800px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }}
            h3 {{ color: #5865F2; margin-top: 0; margin-bottom: 15px; font-family: sans-serif; font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
            .q-id {{ font-size: 16px; color: #555; background: #e0e6ed; padding: 5px 12px; border-radius: 6px; font-weight: bold; letter-spacing: 0.5px; border: 1px solid #cdd6e0; }}
            p {{ margin: 0; font-weight: 500; }}
            mjx-container {{ font-size: 115% !important; }}
        </style>
    </head>
    <body>
        <div class="box" id="solution-box">
            <h3><span>💡 Solution</span> <span class="q-id">ID: {q_num}</span></h3>
            <p>{reason_html}</p>
        </div>
    </body>
    </html>
    """
    with open("temp_solution.html", "w", encoding="utf-8") as f:
        f.write(html_content)
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("file://" + os.path.abspath("temp_solution.html"))
        time.sleep(3) 
        element = page.locator("#solution-box")
        element.screenshot(path=output_path)
        browser.close()
        
    return output_path

# 💡 3. File Sorting
def sort_by_first_number(filename):
    try:
        return int(filename.split('-')[0])
    except:
        return 999999

# 💡 4. Telegram API (Photo -> Poll -> Spoiler Solution)
def send_to_telegram(image_path, json_data):
    q_num = os.path.splitext(os.path.basename(image_path))[0]
    
    # --- STEP 1: Send Question Photo ---
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"🎯 **Question ID: {q_num}**"
    with open(image_path, 'rb') as photo:
        res_photo = requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': photo})
        if res_photo.status_code != 200:
            print(f"⚠️ Telegram Photo Error: {res_photo.text}")
            return False

    # --- STEP 2: Send Quiz Poll ---
    poll_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    correct_ans = json_data.get('correct_id', 'A').upper()
    correct_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
    
    poll_data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'question': f"Select correct answer for {q_num}:",
        'options': json.dumps(["A", "B", "C", "D"]),
        'is_anonymous': False,
        'type': 'quiz',
        'correct_option_id': correct_map.get(correct_ans, 0)
    }
    res_poll = requests.post(poll_url, data=poll_data)
    if res_poll.status_code != 200:
        print(f"⚠️ Telegram Poll Error: {res_poll.text}")

    # --- STEP 3: Send Solution Image (Spoiler with ID Badge) ---
    reason = json_data.get('reason', '')
    if reason:
        sol_img = create_solution_image(reason, q_num)
        with open(sol_img, 'rb') as sol_photo:
            requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID, 'has_spoiler': True}, files={'photo': sol_photo})
        os.remove(sol_img)

    print(f"✅ Master Quiz sent successfully for {q_num}!")
    return True

# 💡 5. Gemini Processing (Auto-Switch & Smart Approach)
def process_with_gemini(image_path, key_index):
    client = genai.Client(api_key=GEMINI_KEYS[key_index])
    
    # 🚀 NAYA MASTER PROMPT (Smart Approach + Option Elimination)
    prompt = """Role & Objective: Expert Mathematics content creator for RPSC competitive exam.
    Task: Extract math question details and provide a high-quality, time-saving solution.

    SMART SOLVING STRATEGY (CRITICAL):
    1. Smart & Short Approach: Solution ko lamba khinchne ke bajay short, crisp aur smart tarike se samjhao. Pura concept clear hona chahiye par faaltu steps avoid karein.
    2. Option Elimination Trick: Agar question bina full solve kiye, direct options se (Value putting, Dimension/Unit check, ya Elimination method se) ho sakta hai, toh wo "Smart Trick" solution me jarur shamil karein taaki exam me time bache.

    CRITICAL JSON FORMATTING & RENDERING RULES:
    1. DOUBLE ESCAPE LATEX: Use \\\\sqrt, \\\\frac.
    2. NO REAL LINE BREAKS: Use \\n for newlines.
    3. MATH DELIMITERS: Enclose math in $$...$$. Example: $$\\\\sqrt{x^2+1}$$.
    4. LANGUAGE: Pure Hindi (Devanagari) mixed with standard English math terms.

    Output strictly in this JSON template without any markdown backticks:
    {
      "correct_id": "A",
      "reason": "Detailed smart solution applying the above tricks and rules."
    }"""
    
    try:
        sample_file = client.files.upload(file=image_path)
        
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[sample_file, prompt],
                    config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json")
                )
                
                raw_text = response.text.strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                elif raw_text.startswith("
```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                
                print(f"✅ Success with model: {model_name}")
                return json.loads(raw_text.strip(), strict=False)
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"⚠️ Limit reached for {model_name}, switching to next...")
                    continue 
                else:
                    print(f"❌ Other Error on {model_name}: {e}")
                    break 
                    
        print(f"❌ All models limit exhausted for this key!")
        return None
        
    except Exception as e:
        print(f"File upload error: {e}")
        return None
