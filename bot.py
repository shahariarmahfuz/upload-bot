import os
import asyncio
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

# .env ফাইল থেকে ভেরিয়েবল লোড করুন
load_dotenv()

# টেলিগ্রাম API কনফিগারেশন
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ফ্লাস্ক API এন্ডপয়েন্ট
API_ENDPOINT = os.getenv("FLASK_API_ENDPOINT")

# ক্লায়েন্ট তৈরি করুন
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def upload_video_to_api(file_path):
    """ভিডিও ফাইল ফ্লাস্ক API-তে আপলোড করুন"""
    try:
        with open(file_path, 'rb') as f:
            files = {'video': f}
            response = requests.post(API_ENDPOINT, files=files)
        
        if response.status_code == 202:
            return response.json()  # প্রসেসিং ডেটা রিটার্ন করুন
        else:
            return None
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None

async def check_processing_status(process_id):
    """প্রসেসিং স্ট্যাটাস চেক করুন"""
    try:
        check_url = f"{API_ENDPOINT.rsplit('/',1)[0]}/check_status/{process_id}"
        response = requests.get(check_url, headers={'Accept': 'application/json'})
        
        if response.status_code == 200:
            return response.json()  # স্ট্যাটাস ডেটা রিটার্ন করুন
        else:
            return None
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """/start কমান্ড হ্যান্ডলার"""
    await event.reply("Hello! Send me a video file to process.")

@client.on(events.NewMessage)
async def handle_video(event):
    """ভিডিও মেসেজ হ্যান্ডলার"""
    if event.message.video:
        try:
            # ভিডিও ডাউনলোড করুন
            temp_file = f"temp_{event.message.id}.mp4"
            await event.download_media(file=temp_file)
            
            # ইউজারকে প্রসেসিং শুরু হয়েছে জানান
            await event.reply("🔄 Processing your video...")
            
            # ভিডিও ফ্লাস্ক API-তে আপলোড করুন
            upload_response = await upload_video_to_api(temp_file)
            
            if upload_response:
                process_id = upload_response['process_id']
                
                # প্রসেসিং স্ট্যাটাস চেক করুন
                while True:
                    status_response = await check_processing_status(process_id)
                    if status_response:
                        if status_response['status'] == 'success':
                            await event.reply(f"✅ Processed!\nURL: {status_response['url']}")
                            break
                        elif status_response['status'] == 'error':
                            await event.reply(f"❌ Error: {status_response['message']}")
                            break
                    await asyncio.sleep(5)
            else:
                await event.reply("⚠️ Failed to start processing.")
            
            # টেম্প ফাইল ডিলিট করুন
            os.remove(temp_file)
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

# বট চালান
print("Bot is running...")
client.run_until_disconnected()
