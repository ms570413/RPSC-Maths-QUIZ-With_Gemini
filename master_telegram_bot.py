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
# 🛑 GitHub Secrets से डेटा
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INPUT_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"

# सेटअप
os.makedirs(DONE_FOLDER, exist_ok=True)
client = genai.Client(api_key=GEMINI_API_KEY)

def send_photo_to_telegram(image_path, caption=""):
    print("📤 Telegram पर फोटो भेज रहे हैं...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    with open(image_path, 'rb') as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        response = requests.post(url, data=payload, files={"photo": photo})
        result = response.json()
        
        # 💡 स्मार्ट फॉलबैक: अगर Telegram फोटो रिजेक्ट कर दे, तो फाइल (Document) बनाकर भेजें
        if not result.get("ok"):
            error_msg = result.get('description', 'Unknown Error')
            print(f"⚠️ Telegram ने Photo रिजेक्ट कर दी ({error_msg})। अब Document की तरह भेज रहे हैं...")
            
            doc_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            photo.seek(0) # फाइल को वापस शुरू से पढने के लिए
            doc_response = requests.post(doc_url, data=payload, files={"document": photo})
            return doc_response.json()
            
    return result

def send_poll_to_telegram(correct_option_letter):
    print("📊 Telegram पर Poll भेज रहे हैं...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    
    clean_opt = correct_option_letter.replace('(', '').replace(')', '').strip().lower()
    option_map = {"a": 0, "b": 1, "c": 2, "d": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    correct_id = option_map.get(clean_opt, 0)

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": "Q. सही उत्तर चुनें:",
        "options": json.dumps(["Option A (या 1)", "Option B (या 2)", "Option C (या 3)", "Option D (या 4)"]),
        "type": "quiz",
        "correct_option_id": correct_id,
        "is_anonymous": False
    }
    requests.post(url, data=payload)

def generate_solution_image(smart_approach, detailed_solution, output_filename="solution_hd.png"):
    print("🎨 Playwright से HD Solution Image बना रहे हैं...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; padding: 40px; color: #333; margin: 0; }}
            #content-to-capture {{ width: 850px; background-color: #fff; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 10px solid #ff7e5f; margin: 0 auto; }}
            .header {{ font-size: 28px; font-weight: bold; color: #ff7e5f; margin-bottom: 25px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .smart-approach {{ background-color: #e8f5e9; padding: 25px; border-radius: 12px; margin-bottom: 25px; border-left: 6px solid #4caf50; font-size: 22px; white-space: pre-wrap; }}
            .detailed-solution {{ font-size: 22px; line-height: 1.8; padding: 10px; white-space: pre-wrap; }}
            .watermark {{ text-align: center; margin-top: 35px; font-size: 24px; font-weight: bold; color: #ff7e5f; opacity: 0.8; }}
            mjx-container {{ max-width: 100%; overflow-x: auto; overflow-y: hidden; }}
        </style>
    </head>
    <body>
        <div id="content-to-capture">
            <div class="header">💡 Solution & Approach</div>
            <div class="smart-approach">
                <strong>🚀 Smart Approach (Trick):</strong><br><br>{smart_approach}
            </div>
            <div class="detailed-solution">
                <strong>📝 Detailed Solution:</strong><br><br>{detailed_solution}
            </div>
            <div class="watermark">@iam_MukeshManya_Rj08</div>
        </div>
    </body>
    </html>
    """
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
        # 💡 scale 2x किया है ताकि लिमिट क्रॉस ना हो
        page = browser.new_page(viewport={'width': 1000, 'height': 800}, device_scale_factor=2)
        page.set_content(html_content)
        page.wait_for_timeout(4000) 
        element = page.locator("#content-to-capture")
        element.screenshot(path=output_filename)
        browser.close()
        
    return output_filename

def main():
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    if not files:
        print("🎉 बधाई हो! सारे सवाल पूरे हो चुके हैं। फोल्डर खाली है।")
        return

    current_question_file = files[0]
    question_path = os.path.join(INPUT_FOLDER, current_question_file)
    
    print(f"\n🚀 प्रोसेसिंग शुरू: {current_question_file}")

    send_photo_to_telegram(question_path, caption=f"🎯 Question ID: {current_question_file.split('.')[0]}")

    prompt = """
    तुम एक एक्सपर्ट RPSC 2nd Grade Mathematics टीचर हो।
    इस फोटो में दिए गए गणित के MCQ को सॉल्व करो। 
    - 'smart_approach' में वह शॉर्ट ट्रिक या ऑप्शन एलिमिनेशन का तरीका बताओ जिससे एग्जाम में 5-10 सेकंड में उत्तर निकाला जा सके।
    - 'detailed_solution' में पूरा स्टेप-बाय-स्टेप गणितीय हल एकदम शुद्ध हिंदी में समझाओ।
    - गणित के सभी वेरिएबल्स और फॉर्मूलों को हमेशा $$...$$ (LaTeX) के अंदर ही लिखना।

    STRICT INSTRUCTION: अपना जवाब सिर्फ और सिर्फ नीचे दिए गए XML फॉर्मेट में ही देना:
    
    <correct_option>C</correct_option>
    <smart_approach>यहाँ आपकी शॉर्ट ट्रिक...</smart_approach>
    <detailed_solution>यहाँ पूरा स्टेप-बाय-स्टेप हल...</detailed_solution>
    """
    
    max_retries = 3
    response = None
    
    for attempt in range(max_retries):
        try:
            print(f"🧠 Gemini दिमाग लगा रहा है... (Attempt {attempt + 1})")
            img = Image.open(question_path)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, img]
            )
            break
            
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} फेल हुआ: {e}")
            if attempt < max_retries - 1:
                print("⏳ सर्वर बिजी है। 15 सेकंड बाद वापस ट्राई कर रहा हूँ...")
                time.sleep(15)
            else:
                print("❌ 3 बार ट्राई करने के बाद भी सर्वर बिजी है।")
                return

    if response is None:
        return
        
    try:
        text = response.text
        correct_opt = re.search(r'<correct_option>(.*?)</correct_option>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
        smart_app = re.search(r'<smart_approach>(.*?)</smart_approach>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
        detailed_sol = re.search(r'<detailed_solution>(.*?)</detailed_solution>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
        
        send_poll_to_telegram(correct_opt)
        
        sol_image_path = generate_solution_image(smart_app, detailed_sol)
        if os.path.exists(sol_image_path):
            send_photo_to_telegram(sol_image_path, caption="💡 Solution by Master Bot")
        
        shutil.move(question_path, os.path.join(DONE_FOLDER, current_question_file))
        if os.path.exists(sol_image_path):
            os.remove(sol_image_path)
            
        print(f"✅ {current_question_file} का काम सफलतापूर्वक पूरा हुआ!")

    except Exception as e:
        print(f"❌ आउटपुट पढ़ने या फोटो बनाने में एरर आ गई: {e}")
        print("AI Response:", response.text if response else "No response")

if __name__ == "__main__":
    main()
