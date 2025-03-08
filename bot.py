import os
import asyncio
import requests
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_ID = "20716719"
API_HASH = "c929824683800816ddf0faac845d89c9"
BOT_TOKEN = "7479613855:AAGiNlYTt5FiiQfYvGO5rTznaYJV_Y762rc"
FLASK_API = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app/up"
FINAL_ENDPOINT = "https://7f8f6e2e-9c68-4880-939b-61d184b126b0-00-3n5zk13i6o9mt.sisko.replit.dev/add"

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# User state management
user_states = {}

def modify_dropbox_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if 'dl' in query:
        query['raw'] = ['1']
        del query['dl']
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

async def upload_and_process(file_path, event):
    try:
        with open(file_path, 'rb') as f:
            response = requests.post(FLASK_API, files={'video': f})
        
        if response.status_code == 202:
            process_id = response.json().get('process_id')
            while True:
                status_url = f"{FLASK_API.rsplit('/',1)[0]}/check_status/{process_id}"
                status_response = requests.get(status_url)
                
                if status_response.status_code == 200:
                    data = status_response.json()
                    if data['status'] == 'success':
                        return modify_dropbox_url(data['url'])
                    elif data['status'] == 'error':
                        await event.reply(f"❌ Error: {data['message']}")
                        return None
                await asyncio.sleep(5)
        return None
    except Exception as e:
        await event.reply(f"⚠️ Upload error: {str(e)}")
        return None

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply("Send /add <title> to start uploading videos")

@client.on(events.NewMessage(pattern='/add (.*)'))
async def add_video(event):
    title = event.pattern_match.group(1).strip()
    if not title:
        await event.reply("⚠️ Please provide a title")
        return

    user_id = event.sender_id
    user_states[user_id] = {
        'title': title,
        'step': 'awaiting_hd',
        'hd_file': None,
        'sd_file': None
    }
    await event.reply(f"📝 Title saved: {title}\nPlease send HD video now")

@client.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    
    if event.message.video:
        if state['step'] == 'awaiting_hd':
            # Handle HD video
            hd_path = f"temp_hd_{user_id}.mp4"
            await event.download_media(hd_path)
            state['hd_file'] = hd_path
            state['step'] = 'awaiting_sd'
            await event.reply("✅ HD video received\nPlease send SD video now")
        
        elif state['step'] == 'awaiting_sd':
            # Handle SD video
            sd_path = f"temp_sd_{user_id}.mp4"
            await event.download_media(sd_path)
            state['sd_file'] = sd_path
            await event.reply("🔄 Processing videos...")

            # Process HD
            hd_url = await upload_and_process(state['hd_file'], event)
            if not hd_url:
                return await cleanup(user_id)

            # Process SD
            sd_url = await upload_and_process(state['sd_file'], event)
            if not sd_url:
                return await cleanup(user_id)

            # Send to final endpoint
            try:
                response = requests.get(
                    FINAL_ENDPOINT,
                    params={'hd': hd_url, 'sd': sd_url}
                )
                if response.status_code == 200:
                    final_url = response.json().get('url')
                    await event.reply(f"🎉 Your video is ready!\n{final_url}")
                else:
                    await event.reply("⚠️ Failed to generate final URL")
            except Exception as e:
                await event.reply(f"⚠️ API Error: {str(e)}")
            
            await cleanup(user_id)

async def cleanup(user_id):
    if user_id in user_states:
        state = user_states.pop(user_id)
        for f in [state['hd_file'], state['sd_file']]:
            if f and os.path.exists(f):
                os.remove(f)

print("Bot is running...")
client.run_until_disconnected()
