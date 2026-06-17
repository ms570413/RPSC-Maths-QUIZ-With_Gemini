import os
import json
import time
import shutil
import random
import requests
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# 💡 1. API Keys aur Discord Setup
raw_keys = [
    os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"), os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"), os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"), os.getenv("GEMINI_API_KEY_8"),
    os.getenv("GEMINI_API_KEY_9"), os.getenv("GEMINI_API_KEY_10")
]

GEMINI_KEYS = [k.strip() for k in raw_keys if k is not None and k.strip() != ""]

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

SOURCE_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
QUESTIONS_PER_RUN = 25

os.makedirs(DONE_FOLDER, exist_ok=True)

# 💡 2. Playwright se Blank Page par MathJax + Devanagari Render karna
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

# 💡 3. Discord Function
def send_to_discord(image_path, json_data):
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}
    
    q_num = os.path.splitext(os.path.basename(image_path))[0]
    content = f"🎯 **Question ID: {q_num}**\n\n"
    
    correct_ans = json_data.get('correct_id', '')
    content += f"||✅ **Correct Answer: {correct_ans}** ||"
    reason = json_data.get('reason', '')
    
    with open(image_path, 'rb') as f1:
        files = {'files[0]': (os.path.basename(image_path), f1, 'image/jpeg')}
        f2 = None
        if reason:
            solution_img_path = create_solution_image(reason)
            f2 = open(solution_img_path, 'rb')
            files['files[1]'] = ("SPOILER_solution.png", f2, 'image/png')
            
        payload = {'content': content}
        response = requests.post(url, headers=headers, data=payload, files=files)
        
        if f2:
            f2.close()
            if os.path.exists("SPOILER_solution.png"):
                os.remove("SPOILER_solution.png")
            
        if response.status_code == 200:
            msg_id = response.json()['id']
            reactions = ['🇦', '🇧', '🇨', '🇩']
            for reaction in reactions:
                react_url = f"{url}/{msg_id}/reactions/{reaction}/@me"
                requests.put(react_url, headers=headers)
                time.sleep(0.5)
            print(f"✅ Discord poll sent successfully for {os.path.basename(image_path)}!")
            return True
        else:
            print(f"⚠️ Discord Error: {response.text}")
            return False

# 💡 4. Gemini Processing Function
def process_with_gemini(image_path, key_index):
    client = genai.Client(api_key=GEMINI_KEYS[key_index])
    
    prompt = """
    Role & Objective: Expert Mathematics content creator for RPSC exam.
    Task: Extract the mathematics question details from the image and provide a solution.

    CRITICAL JSON FORMATTING & RENDERING RULES:
    1. DOUBLE ESCAPE LATEX: Since output is JSON, you MUST double-escape all LaTeX backslashes. Write \\\\sqrt instead of \\sqrt, \\\\frac instead of \\frac.
    2. NO REAL LINE BREAKS: DO NOT press the Enter key. Use the literal text \\n for newlines.
    3. MATH DELIMITERS: Enclose all math expressions in $$...$$. Example: $$\\\\sqrt{x^2 + 1}$$.
    4. LANGUAGE: Use Devanagari Hindi mixed with standard English math terms.

    Output strictly in this JSON template without any markdown backticks:
    {
      "correct_id": "Randomly select A, B, C, or D",
      "reason": "Detailed mathematical solution using double escaped \\\\sqrt and \\n"
    }
    """
    try:
        sample_file = client.files.upload(file=image_path)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[sample_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.2, top_p=0.95, top_k=40, max_output_tokens=1024, response_mime_type="application/json",
            )
        )
        
        raw_text = response.text.strip()
        
        # Safe String Parsing
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("```"):
            raw_text = raw_text[3:]
            
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip(), strict=False)
        
    except Exception as e:
        print(f"Gemini Error on key {key_index + 1}: {e}")
        return None

# 💡 5. Main Bot Logic (Target 25)
def main():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"Folder {SOURCE_FOLDER} nahi mila!")
        return

    images = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))])
    if not images:
        print("Bhai, Final_Mixed_Bank folder khali hai! Naye questions dalo.")
        return

    if not GEMINI_KEYS:
        print("⚠️ Koi valid API key nahi mili! Secrets check karo.")
        return

    print(f"🚀 Target: Discord par {QUESTIONS_PER_RUN} successful questions bhejna...")
    
    success_count = 0
    key_index = 0
    
    for img_name in images:
        if success_count >= QUESTIONS_PER_RUN:
            print(f"🎉 Target complete! {QUESTIONS_PER_RUN} questions processed.")
            break
            
        img_path = os.path.join(SOURCE_FOLDER, img_name)
        print(f"⏳ Processing: {img_name}")
        
        json_data = process_with_gemini(img_path, key_index)
        
        if json_data:
            success = send_to_discord(img_path, json_data)
            if success:
                shutil.move(img_path, os.path.join(DONE_FOLDER, img_name))
                print(f"📁 Moved to Done: {img_name}")
                success_count += 1
            else:
                print(f"❌ Discord error, question skipped: {img_name}")
        else:
            print(f"❌ JSON generation fail, skipping for now: {img_name}")
            
        key_index = (key_index + 1) % len(GEMINI_KEYS)
        time.sleep(12) 

if __name__ == "__main__":
    main()
