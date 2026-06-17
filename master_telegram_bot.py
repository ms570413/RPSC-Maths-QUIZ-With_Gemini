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

# 🚀 MUKESH BHAI KA AUTO-SWITCH IDEA (MODELS LIST)
GEMINI_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash'
]

# 💡 2. Playwright se Blank Page par MathJax Render
def create_solution_image(reason_text, output_path="SPOILER_solution.png"):
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
            h3 {{ color: #5865F2; margin-top: 0; margin-bottom: 15px; font-family: sans-serif; font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            p {{ margin: 0; font-weight: 500; }}
            mjx-container {{ font-size: 115% !important; }}
        </style>
    </head>
    <body>
        <div class="box" id="solution-box">
            <h3>💡 Solution</h3>
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

# 💡 4. Telegram API (Photo -> Poll -> Spoiler)
def send_to_telegram(image_path, json_data):
    q_num = os.path.splitext(os.path.basename(image_path))[0]
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"🎯 **Question ID: {q_num}**"
    
    with open(image_path, 'rb') as photo:
        res_photo = requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, files={'photo': photo})
        if res_photo.status_code != 200: return False

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
    requests.post(poll_url, data=poll_data)

    reason = json_data.get('reason', '')
    if reason:
        sol_img = create_solution_image(reason)
        with open(sol_img, 'rb') as sol_photo:
            requests.post(photo_url, data={'chat_id': TELEGRAM_CHAT_ID, 'has_spoiler': True}, files={'photo': sol_photo})
        os.remove(sol_img)

    return True

# 💡 5. Gemini Processing (AUTO-SWITCH LOGIC)
def process_with_gemini(image_path, key_index):
    client = genai.Client(api_key=GEMINI_KEYS[key_index])
    prompt = """Role & Objective: Expert Mathematics content creator for RPSC exam.
    Task: Extract math question details and provide solution.
    1. DOUBLE ESCAPE LATEX: Use \\\\sqrt, \\\\frac.
    2. NO REAL LINE BREAKS: Use \\n for newlines.
    3. MATH DELIMITERS: Enclose math in $$...$$. Example: $$\\\\sqrt{x^2+1}$$.
    4. LANGUAGE: Pure Hindi mixed with standard English math terms.
    Output JSON: {"correct_id": "A", "reason": "Explanation"}"""
    
    try:
        sample_file = client.files.upload(file=image_path)
        
        # 🔄 Yaha apka logic lagaya hai: Ek ek karke model try karega
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[sample_file, prompt],
                    config=types.GenerateContentConfig(temperature=0.2, response_mime_type="application/json")
                )
                
                raw_text = response.text.strip()
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                elif raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                
                print(f"✅ Success with model: {model_name}")
                return json.loads(raw_text.strip(), strict=False)
                
            except Exception as e:
                error_msg = str(e)
                # Agar 429 limit ka error hai, toh agle model par jump karega
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"⚠️ Limit reached for {model_name}, switching to next model...")
                    continue 
                else:
                    print(f"❌ Other Gemini Error on {model_name}: {e}")
                    break # Agar koi aur error (jaise internet) hai, toh loop tod dega
                    
        print(f"❌ Saare models ki limit khtm ho gayi is Key ke liye!")
        return None
        
    except Exception as e:
        print(f"File upload error: {e}")
        return None

# 💡 6. Main Bot Logic
def main():
    if not os.path.exists(SOURCE_FOLDER): return
    images = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))], key=sort_by_first_number)
    if not images or not GEMINI_KEYS: return

    images_to_process = images[:QUESTIONS_PER_RUN]
    key_index = 0
    
    for img_name in images_to_process:
        img_path = os.path.join(SOURCE_FOLDER, img_name)
        print(f"\n⏳ Processing: {img_name}")
        
        json_data = process_with_gemini(img_path, key_index)
        
        if json_data and send_to_telegram(img_path, json_data):
            shutil.move(img_path, os.path.join(DONE_FOLDER, img_name))
            print(f"📁 Moved to Done: {img_name}")
            
        key_index = (key_index + 1) % len(GEMINI_KEYS)
        time.sleep(10) # 10 second break (RPM limit cross na ho isliye)

if __name__ == "__main__":
    main()
