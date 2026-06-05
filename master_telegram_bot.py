import os
import shutil
import re
import time
import requests
import json
from google import genai
from PIL import Image
from html2image import Html2Image

# ==========================================
# 🛑 GitHub Secrets से डेटा (यहाँ कुछ नहीं लिखना है) 🛑
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

INPUT_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
# ==========================================

# फोल्डर चेक करना और सेटअप
os.makedirs(DONE_FOLDER, exist_ok=True)
client = genai.Client(api_key=GEMINI_API_KEY)

# 🔧 Server-Safe Chrome Flags (The Ultimate Fix)
hti = Html2Image(
    browser_executable='/usr/bin/google-chrome',
    custom_flags=[
        '--headless=new',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-zygote',
        '--single-process',
        '--disable-software-rasterizer',
        '--disable-background-networking',
        '--disable-extensions',
        '--log-level=3',
        '--hide-scrollbars'
    ]
)

def send_photo_to_telegram(image_path, caption=""):
    print("📤 Telegram पर फोटो भेज रहे हैं...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    with open(image_path, 'rb') as photo:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption}
        response = requests.post(url, data=payload, files={"photo": photo})
    return response.json()

def send_poll_to_telegram(correct_option_letter):
    print("📊 Telegram पर Poll भेज रहे हैं...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    
    # साफ़ करना (जैसे 'C' या '(c)' को 'c' बनाना)
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
    print("🎨 HD Solution Image बना रहे हैं...")
    
    # HTML में लाइन ब्रेक को सही करने के लिए \n को <br> में बदलना
    smart_approach = smart_approach.replace('\n', '<br>')
    detailed_solution = detailed_solution.replace('\n', '<br>')

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
        <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f9; padding: 40px; color: #333; width: 800px; }}
            .container {{ background-color: #fff; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left: 8px solid #ff7e5f; }}
            .header {{ font-size: 26px; font-weight: bold; color: #ff7e5f; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .smart-approach {{ background-color: #e8f5e9; padding: 20px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #4caf50; font-size: 20px; }}
            .detailed-solution {{ font-size: 20px; line-height: 1.8; padding: 10px; }}
            .watermark {{ text-align: center; margin-top: 25px; font-size: 22px; font-weight: bold; color: #ff7e5f; opacity: 0.9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">💡 Solution & Approach</div>
            <div class="smart-approach">
                <strong>🚀 Smart Approach (Trick):</strong><br> {smart_approach}
            </div>
            <div class="detailed-solution">
                <strong>📝 Detailed Solution:</strong><br> {detailed_solution}
            </div>
        </div>
        <div class="watermark">@iam_MukeshManya_Rj08</div>
    </body>
    </html>
    """
    
    hti.screenshot(html_str=html_content, save_as=output_filename)
    time.sleep(2) 
    return output_filename

def main():
    files = sorted([f for f in os.listdir(INPUT_FOLDER) if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    if not files:
        print("🎉 बधाई हो! सारे सवाल पूरे हो चुके हैं। फोल्डर खाली है।")
        return

    current_question_file = files[0]
    question_path = os.path.join(INPUT_FOLDER, current_question_file)
    
    print(f"\n🚀 प्रोसेसिंग शुरू: {current_question_file}")

    # 1. Telegram पर सवाल भेजना
    send_photo_to_telegram(question_path, caption=f"🎯 Question ID: {current_question_file.split('.')[0]}")

    # 2. Gemini से सॉल्व करवाना (बिना JSON के)
    prompt = """
    तुम एक एक्सपर्ट RPSC 2nd Grade Mathematics टीचर हो।
    इस फोटो में दिए गए गणित के MCQ को सॉल्व करो। 
    - 'smart_approach' में वह शॉर्ट ट्रिक या ऑप्शन एलिमिनेशन का तरीका बताओ जिससे एग्जाम में 5-10 सेकंड में उत्तर निकाला जा सके।
    - 'detailed_solution' में पूरा स्टेप-बाय-स्टेप गणितीय हल एकदम शुद्ध हिंदी में समझाओ।
    - गणित के सभी वेरिएबल्स और फॉर्मूलों को हमेशा $$...$$ (LaTeX) के अंदर ही लिखना।

    STRICT INSTRUCTION: अपना जवाब सिर्फ और सिर्फ नीचे दिए गए XML फॉर्मेट में ही देना (कोई JSON नहीं, कोई फालतू टेक्स्ट नहीं):
    
    <correct_option>C</correct_option>
    <smart_approach>यहाँ आपकी शॉर्ट ट्रिक...</smart_approach>
    <detailed_solution>यहाँ पूरा स्टेप-बाय-स्टेप हल...</detailed_solution>
    """
    
    try:
        print("🧠 Gemini दिमाग लगा रहा है...")
        img = Image.open(question_path)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )
        
        text = response.text
        
        # Regex से डेटा निकालना (Error-Free तरीका)
        try:
            correct_opt = re.search(r'<correct_option>(.*?)</correct_option>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            smart_app = re.search(r'<smart_approach>(.*?)</smart_approach>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
            detailed_sol = re.search(r'<detailed_solution>(.*?)</detailed_solution>', text, re.DOTALL | re.IGNORECASE).group(1).strip()
        except Exception as e:
            print("❌ AI आउटपुट को पढ़ने में फेल रहा।")
            print("AI Response:", text)
            return
        
        # 3. Telegram पर Poll भेजना
        send_poll_to_telegram(correct_opt)
        
        # 4. HD Solution Image बनाना और भेजना
        sol_image_path = generate_solution_image(smart_app, detailed_sol)
        send_photo_to_telegram(sol_image_path, caption="💡 Solution by Master Bot")
        
        # 5. सफाई करना (फाइल को Done में डालना)
        shutil.move(question_path, os.path.join(DONE_FOLDER, current_question_file))
        if os.path.exists(sol_image_path):
            os.remove(sol_image_path)
            
        print(f"✅ {current_question_file} का काम सफलतापूर्वक पूरा हुआ!")

    except Exception as e:
        print(f"❌ एरर आ गई: {e}")

if __name__ == "__main__":
    main()
