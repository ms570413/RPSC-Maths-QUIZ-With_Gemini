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
# 🛑 GitHub Secrets se Data
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INPUT_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"

# Setup
os.makedirs(DONE_FOLDER, exist_ok=True)
client = genai.Client(api_key=GEMINI_API_KEY)

def send_photo_to_telegram(image_path, caption=""):
    print("📤 Telegram par photo bhej rahe hain...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    with open(image_path, 'rb') as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        response = requests.post(url, data=payload, files={"photo": photo})
        result = response.json()
        
        if not result.get("ok"):
            print(f"⚠️ Telegram ne Photo reject kar di. Document bhej rahe hain...")
            doc_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            photo.seek(0) 
            doc_response = requests.post(doc_url, data=payload, files={"document": photo})
            return doc_response.json()
            
    return result

def send_poll_to_telegram(correct_option_letter):
    print("📊 Telegram par Poll bhej rahe hain...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    
    clean_opt = correct_option_letter.replace('(', '').replace(')', '').strip().lower()
    option_map = {"a": 0, "b": 1, "c": 2, "d": 3, "1": 0, "2": 1, "3": 2, "4": 3}
    correct_id = option_map.get(clean_opt, 0)

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": "Q. Sahi uttar chunein:",
        "options": json.dumps(["Option A (ya 1)", "Option B (ya 2)", "Option C (ya 3)", "Option D (ya 4)"]),
        "type": "quiz",
        "correct_option_id": correct_id,
        "is_anonymous": False
    }
    requests.post(url, data=payload)

# 💡 Yahan se detailed_solution hata diya gaya hai
def generate_solution_image(smart_approach, output_filename="solution_hd.png"):
    print("🎨 Playwright se Smart HD Image bana rahe hain...")
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; padding: 30px; color: #333; margin: 0; }}
            #content-to-capture {{ width: 850px; background-color: #fff; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 10px solid #ff7e5f; margin: 0 auto; }}
            .header {{ font-size: 28px; font-weight: bold; color: #ff7e5f; margin-bottom: 25px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .smart-approach {{ background-color: #e8f5e9; padding: 25px; border-radius: 12px; margin-bottom: 10px; border-left: 6px solid #4caf50; font-size: 24px; line-height: 1.6; white-space: pre-wrap; }}
            .watermark {{ text-align: center; margin-top: 25px; font-size: 22px; font-weight: bold; color: #ff7e5f; opacity: 0.8; }}
            mjx-container {{ max-width: 100%; overflow-x: auto; overflow-y: hidden; }}
        </style>
    </head>
    <body>
        <div id="content-to-capture">
            <div class="header">💡 Smart Approach & Option Elimination</div>
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
        page.wait_for_timeout(3500) 
        element = page.locator("#content-to-capture")
        element.screenshot(path=output_filename)
        browser.close()
        
    return output_filename

def main():
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    if not files:
        print("🎉 बधाई हो! सारे सवाल पूरे हो चुके हैं। फोल्डर खाली है।")
        return

    # 💡 अब यह एक-एक करके सारे सवालों को प्रोसेस करेगा
    for current_question_file in files:
        question_path = os.path.join(INPUT_FOLDER, current_question_file)
        
        print(f"\n🚀 प्रोसेसिंग शुरू: {current_question_file}")

        send_photo_to_telegram(question_path, caption=f"🎯 Question ID: {current_question_file.split('.')[0]}")

        # 💡 नया प्रॉम्प्ट: एकदम कड़क और शॉर्टकट (आपका उदाहरण शामिल है)
        prompt = """
        तुम एक एक्सपर्ट RPSC 2nd Grade Mathematics टीचर हो।
        इस फोटो में दिए गए गणित के MCQ को सॉल्व करो। 
        
        RULE 1: कोई लंबा स्टेप-बाय-स्टेप हल बिलकुल नहीं देना है। पूरी कैलकुलेशन मत दिखाना।
        RULE 2: 'smart_approach' में केवल शॉर्ट ट्रिक, डायरेक्ट फार्मूला या ऑप्शन एलिमिनेशन (by options) का तरीका बताओ जिससे एग्जाम में 5-10 सेकंड में उत्तर निकाला जा सके। 
        RULE 3: (उदाहरण: अगर singular solution का सवाल हो, तो सिर्फ इतना बताओ कि "p के respect में derivative करके p को main equation और derivative equation की हेल्प से विलोप (eliminate) करते हैं", फालतू स्टेप्स मत लिखो)।
        RULE 4: गणित के सभी वेरिएबल्स (जैसे x, y, p) और फॉर्मूलों को हमेशा $$...$$ (LaTeX) के अंदर ही लिखना।

        STRICT INSTRUCTION: अपना जवाब सिर्फ और सिर्फ नीचे दिए गए XML फॉर्मेट में ही देना:
        
        <correct_option>C</correct_option>
        <smart_approach>यहाँ आपकी शॉर्ट ट्रिक या ऑप्शन एलिमिनेशन का तरीका...</smart_approach>
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
                    return # अगर सर्वर बिल्कुल डाउन है तो स्क्रिप्ट बंद कर दो

        if response is None:
            continue # अगर यह सवाल फेल हुआ, तो अगले सवाल पर जाओ
            
        try:
            text = response.text
            correct_opt = re.search(r'<correct_option>(.*?)</correct_option>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            smart_app = re.search(r'<smart_approach>(.*?)</smart_approach>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            
            send_poll_to_telegram(correct_opt)
            
            sol_image_path = generate_solution_image(smart_app)
            if os.path.exists(sol_image_path):
                send_photo_to_telegram(sol_image_path, caption="💡 Smart Solution by Master Bot")
            
            shutil.move(question_path, os.path.join(DONE_FOLDER, current_question_file))
            if os.path.exists(sol_image_path):
                os.remove(sol_image_path)
                
            print(f"✅ {current_question_file} का काम सफलतापूर्वक पूरा हुआ!")
            
            # 💡 10 सेकंड का ब्रेक ताकि Gemini API की लिमिट क्रॉस ना हो
            print("⏳ 10 सेकंड का ब्रेक ले रहे हैं ताकि API ब्लॉक ना हो...")
            time.sleep(10)

        except Exception as e:
            print(f"❌ आउटपुट पढ़ने या फोटो बनाने में एरर आ गई: {e}")
            print("AI Response:", response.text if response else "No response")
            continue # एरर आए तो अगले सवाल पर बढ़ जाओ

if __name__ == "__main__":
    main()
