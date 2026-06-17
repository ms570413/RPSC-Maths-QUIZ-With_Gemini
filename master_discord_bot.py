import os
import json
import time
import shutil
import random
import requests
from google import genai
from google.genai import types

# 💡 1. API Keys aur Discord Setup (Smart strip filter ke sath)
raw_keys = [
    os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3"), os.getenv("GEMINI_API_KEY_4"),
    os.getenv("GEMINI_API_KEY_5"), os.getenv("GEMINI_API_KEY_6"),
    os.getenv("GEMINI_API_KEY_7"), os.getenv("GEMINI_API_KEY_8"),
    os.getenv("GEMINI_API_KEY_9"), os.getenv("GEMINI_API_KEY_10")
]

# 🧹 Invisible space aur enter hatane ke liye
GEMINI_KEYS = [k.strip() for k in raw_keys if k is not None and k.strip() != ""]

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

SOURCE_FOLDER = "Final_Mixed_Bank"
DONE_FOLDER = "Done_Questions"
QUESTIONS_PER_RUN = 25

os.makedirs(DONE_FOLDER, exist_ok=True)

# 💡 2. Discord Function (Reaction Polls ke sath)
def send_to_discord(image_path, json_data):
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}"
    }
    
    content = f"🎯 **Question {json_data.get('question_number', 'N/A')}**\n\n"
    options = json_data.get('options', {})
    
    if 'A' in options: content += f"**A)** {options['A']}\n"
    if 'B' in options: content += f"**B)** {options['B']}\n"
    if 'C' in options: content += f"**C)** {options['C']}\n"
    if 'D' in options: content += f"**D)** {options['D']}\n"
    
    with open(image_path, 'rb') as f:
        files = {'file': (os.path.basename(image_path), f, 'image/jpeg')}
        payload = {'content': content}
        response = requests.post(url, headers=headers, data=payload, files=files)
        
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

# 💡 3. NAYA Gemini Processing Function (google.genai library)
def process_with_gemini(image_path, key_index):
    # Naya Client format
    client = genai.Client(api_key=GEMINI_KEYS[key_index])
    
    prompt = """
    Role & Objective: Expert Mathematics content creator for RPSC 2nd Grade Mathematics exam.
    Task: Extract the mathematics question and options from the uploaded image.

    CRITICAL IMAGE PARSING & OPTIONS RULES:
    1. Identify the Main Question: The primary question number is located on the far left. The actual question text starts to the right of this number.
    2. STRICTLY IGNORE TOP OPTIONS: If you see isolated options (like A, B, C, D or 1, 2, 3, 4) at the very TOP of the image (ABOVE the main question number), YOU MUST IGNORE THEM. They are leftover options from the previous question.
    3. True Options are BELOW: The actual options for the current question are always located strictly BELOW the question text.
    4. MISSING OPTIONS GENERATION (CRITICAL): 
       - Look for the options below the question. 
       - If all 4 options are clearly visible, extract them as A, B, C, and D.
       - IF OPTIONS ARE MISSING OR INCOMPLETE (e.g., 0 options, or only 2-3 options visible), YOU MUST ACT AS AN EXPERT AND GENERATE the missing plausible mathematical options yourself. 
       - You must always output exactly 4 standard options (A, B, C, D) in the final JSON.

    General Formatting Rules ('Clean Mode'):
    1. Enclose all mathematical equations, symbols, and variables within $$...$$ in Question and Options.
    2. No Hindi (Devanagari) words should appear within $$...$$ boundaries.
    3. No Math Delimiters in Reason: Never use $ or $$ signs in the reason field.
    4. Bold Variables: In the reason field, write mathematical variables in bold.
    5. Single Line Reason: The reason must be a continuous single line (no \n).

    Output strictly in this JSON template:
    {
      "question_number": "Extracted number",
      "question": "Question text with $$math$$",
      "options": {
        "A": "Option A with $$math$$",
        "B": "Option B with $$math$$",
        "C": "Option C with $$math$$",
        "D": "Option D with $$math$$"
      },
      "correct_id": "Randomly select A, B, C, or D",
      "reason": "Short explanation in mixed Hindi-English without latex dollars"
    }
    """
    
    try:
        # Naya file upload system
        sample_file = client.files.upload(file=image_path)
        
        # Naya content generation system
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
        return json.loads(response.text)
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
    
    # Check if we have valid keys
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
        
        # Round robin key rotation
        key_index = (key_index + 1) % len(GEMINI_KEYS)
        time.sleep(5) # API rate limit se bachne ke liye wait

if __name__ == "__main__":
    main()
