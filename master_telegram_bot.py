import requests
import os
import time

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")

def send_to_discord(image_path, json_data):
    # 💡 Discord API URL
    url = f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}"
    }
    
    # 📝 Message Content (Question & Options)
    content = f"🎯 **Question {json_data.get('question_number', '')}**\n\n"
    options = json_data.get('options', {})
    
    # Options formatting
    if 'A' in options: content += f"**A)** {options['A']}\n"
    if 'B' in options: content += f"**B)** {options['B']}\n"
    if 'C' in options: content += f"**C)** {options['C']}\n"
    if 'D' in options: content += f"**D)** {options['D']}\n"
    
    # 🚀 Sending Image and Text together
    with open(image_path, 'rb') as f:
        files = {
            'file': (os.path.basename(image_path), f, 'image/jpeg')
        }
        payload = {
            'content': content
        }
        
        response = requests.post(url, headers=headers, data=payload, files=files)
        
        # 📊 Add Reaction Polls (A, B, C, D) if message sent successfully
        if response.status_code == 200:
            msg_id = response.json()['id']
            reactions = ['🇦', '🇧', '🇨', '🇩']
            
            for reaction in reactions:
                # Discord URL encoding for emojis
                react_url = f"{url}/{msg_id}/reactions/{reaction}/@me"
                requests.put(react_url, headers=headers)
                time.sleep(0.5) # Thoda wait takki Discord block na kare
            
            print(f"✅ Discord par Question successfully chala gaya aur Poll lag gaya!")
            return True
        else:
            print(f"⚠️ Discord Error: {response.text}")
            return False
