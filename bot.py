import os
import asyncio
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

# .env ফাইল থেকে ভেরিয়েবল লোড করুন
load_dotenv()

# টেলিগ্রাম API কনফিগারেশন
API_ID = "20716719"
API_HASH = "c929824683800816ddf0faac845d89c9"
BOT_TOKEN = "7479613855:AAG7u7WbmJwpKG3qZI2o_ucseQ4Jz6TFoaU"

# ফ্লাস্ক API এন্ডপয়েন্ট
UPLOAD_API_ENDPOINT = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app/up"
FINAL_API_ENDPOINT = "https://7f8f6e2e-9c68-4880-939b-61d184b126b0-00-3n5zk13i6o9mt.sisko.replit.dev/add"

# ক্লায়েন্ট তৈরি করুন
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ব্যবহারকারীর তথ্য সংরক্ষণের জন্য ডিকশনারি
user_data = {}

async def upload_video_to_api(file_path):
    """ভিডিও ফাইল ফ্লাস্ক API-তে আপলোড করুন"""
    try:
        with open(file_path, 'rb') as f:
            files = {'video': f}
            response = requests.post(UPLOAD_API_ENDPOINT, files=files)

        if response.status_code == 202:
            return response.json()  # প্রসেসিং ডেটা রিটার্ন করুন
        else:
            return None
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None

async def check_processing_status(process_id):
    """প্রসেসিং স্ট্যাটাস চেক করুন"""
    try:
        check_url = f"{UPLOAD_API_ENDPOINT.rsplit('/',1)[0]}/check_status/{process_id}"
        response = requests.get(check_url, headers={'Accept': 'application/json'})

        if response.status_code == 200:
            return response.json()  # স্ট্যাটাস ডেটা রিটার্ন করুন
        else:
            return None
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def convert_dropbox_link(link):
    """Dropbox লিংককে raw ফরম্যাটে পরিবর্তন করুন"""
    return link.replace("dl=0", "raw=1")

@client.on(events.NewMessage(pattern=r'/add (.+)'))
async def add_title(event):
    """ভিডিও টাইটেল সংরক্ষণ করুন"""
    user_id = event.sender_id
    title = event.pattern_match.group(1)
    user_data[user_id] = {'title': title, 'hd': None, 'sd': None}
    
    await event.reply(f"✅ Title added: *{title}*\nNow, send the HD video.", parse_mode="md")

@client.on(events.NewMessage)
async def handle_video(event):
    """ভিডিও মেসেজ হ্যান্ডলার"""
    user_id = event.sender_id

    if user_id not in user_data or 'title' not in user_data[user_id]:
        await event.reply("⚠️ Please set a title first using `/add {title}`")
        return

    try:
        # ভিডিও ডাউনলোড করুন
        temp_file = f"temp_{event.message.id}.mp4"
        await event.download_media(file=temp_file)

        # প্রথমে HD ভিডিও নেওয়া হবে
        if not user_data[user_id]['hd']:
            await event.reply("🔄 Uploading HD video...")
            upload_response = await upload_video_to_api(temp_file)

            if upload_response:
                process_id = upload_response['process_id']

                while True:
                    status_response = await check_processing_status(process_id)
                    if status_response:
                        if status_response['status'] == 'success':
                            hd_link = convert_dropbox_link(status_response['url'])
                            user_data[user_id]['hd'] = hd_link
                            await event.reply("✅ HD video uploaded!\nNow, send the SD video.")
                            break
                        elif status_response['status'] == 'error':
                            await event.reply(f"❌ Error: {status_response['message']}")
                            break
                    await asyncio.sleep(5)
            else:
                await event.reply("⚠️ Failed to upload HD video.")

        # এরপর SD ভিডিও নেওয়া হবে
        elif not user_data[user_id]['sd']:
            await event.reply("🔄 Uploading SD video...")
            upload_response = await upload_video_to_api(temp_file)

            if upload_response:
                process_id = upload_response['process_id']

                while True:
                    status_response = await check_processing_status(process_id)
                    if status_response:
                        if status_response['status'] == 'success':
                            sd_link = convert_dropbox_link(status_response['url'])
                            user_data[user_id]['sd'] = sd_link
                            await event.reply("✅ SD video uploaded! Now generating final link...")
                            break
                        elif status_response['status'] == 'error':
                            await event.reply(f"❌ Error: {status_response['message']}")
                            break
                    await asyncio.sleep(5)

            else:
                await event.reply("⚠️ Failed to upload SD video.")

        # দুইটি ভিডিও থাকলে ফাইনাল রিকোয়েস্ট পাঠানো হবে
        if user_data[user_id]['hd'] and user_data[user_id]['sd']:
            final_request_url = f"{FINAL_API_ENDPOINT}?hd={user_data[user_id]['hd']}&sd={user_data[user_id]['sd']}"
            final_response = requests.get(final_request_url)

            if final_response.status_code == 200:
                final_data = final_response.json()
                final_video_url = final_data.get("url", "❌ Could not retrieve final link.")
                await event.reply(f"✅ Final Video Link: {final_video_url}")
            else:
                await event.reply("⚠️ Failed to generate final video link.")

            # ইউজারের ডাটা মুছে ফেলা
            del user_data[user_id]

        # টেম্প ফাইল ডিলিট করুন
        os.remove(temp_file)

    except Exception as e:
        await event.reply(f"❌ Error: {str(e)}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

# বট চালান
print("Bot is running...")
client.run_until_disconnected()
