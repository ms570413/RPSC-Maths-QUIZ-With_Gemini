import os
import json
import time
import shutil
import random
import requests
from google import genai
from google.genai import types

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

# 💡 2. Discord Function (Bina text options ke, sirf Question No., Photo aur Spoiler Answer)
def send_to_discord(image_path, json_data):
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}"
    }
    
    # Sirf Question Number print hoga (Photo wale number ke hisab se)
    q_num = json_data.get('question_number', 'N/A')
    content = f"🎯 **Question {q_num}**\n\n"
    
    # 💡 NAYA JUGAD: Correct Answer aur Reason dono ko Spoiler ||...|| me chupa diya
    correct_ans = json_data.get('correct_id', '')
    reason = json_data.get('reason', '')
    
    content += f"||✅ **Correct Answer:** {correct_ans}"
    if reason:
        content += f"\n💡 **Solution:** {reason}"
    content += "||"
    
    with open(image_path, 'rb') as f:
        files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}
        payload = {'content': content}
        response = requests.post(url, headers=headers, data=payload, files=files)
        
        if response.status_code == 200:
            msg_id = response.json()['id']
            # A, B, C, D ke reaction buttons lagayega
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

# 💡 3. Gemini Processing Function
def process_with_gemini(image_path, key_index):
    client = genai.Client(api_key=GEMINI_KEYS[key_index])
    
    prompt = """
    Role & Objective: Expert Mathematics content creator for RPSC 2nd Grade Mathematics exam.
    Task: Extract the mathematics question details from the uploaded image.

    CRITICAL RULES:
    1. Identify the Main Question Number exactly as printed in the image (e.g., 38, 55, etc.).
    2. Read the image and extract the mathematical details.
    3. Generate a logical reason/solution for the question.
    
    General Formatting Rules ('Clean Mode'):
    1. No Math Delimiters in Reason: Never use $ or $$ signs in the reason field.
    2. Bold Variables: In the reason field, write mathematical variables in bold.
    3. Single Line Reason: The reason must be a continuous single line (no \n).

    Output strictly in this JSON template without any markdown backticks:
    {
      "question_number": "Extracted number exactly as seen in image",
      "correct_id": "Randomly select A, B, C, or D",
      "reason": "Short explanation in mixed Hindi-English without latex dollars"
    }
    """
    
    try:
        sample_file = client.files.upload(file=image_path)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[sample_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=1024,
                response_mime_type="application/json",
            )
        )
        
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        elif raw_text.startswith("
```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        return json.loads(raw_text.strip())
        
    except Exception as e:
        print(f"Gemini Error on key {key_index + 1}: {e}")
        return None

# 💡 4. Main Bot Logic
def main():
    if not os.path.exists(SOURCE_FOLDER):
        print(f"Folder {SOURCE_FOLDER} nahi mila!")
        return

    images = sorted([f for f in os.listdir(SOURCE_FOLDER) if f.endswith(('.png', '.jpg', '.jpeg'))])
    
    if not images:
        print("Bhai, Final_Mixed_Bank folder khali hai! Naye questions dalo.")
        return

    images_to_process = images[:QUESTIONS_PER_RUN]
    print(f"🚀 Processing {len(images_to_process)} questions for Discord...")

    key_index = 0
    
    if not GEMINI_KEYS:
        print("⚠️ Koi valid API key nahi mili! Secrets check karo.")
        return
    
    for img_name in images_to_process:
        img_path = os.path.join(SOURCE_FOLDER, img_name)
        print(f"⏳ Processing: {img_name}")
        
        json_data = process_with_gemini(img_path, key_index)
        
        if json_data:
            success = send_to_discord(img_path, json_data)
            if success:
                shutil.move(img_path, os.path.join(DONE_FOLDER, img_name))
                print(f"📁 Moved to Done: {img_name}\n")
        
        key_index = (key_index + 1) % len(GEMINI_KEYS)
        
        time.sleep(12) 

if __name__ == "__main__":
    main()
