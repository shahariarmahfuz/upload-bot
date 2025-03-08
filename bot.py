import os
import asyncio
import requests
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

API_ID = "20716719"
API_HASH = "c929824683800816ddf0faac845d89c9"
BOT_TOKEN = "7479613855:AAGVHnXaJI6VmkZXbyzgmgI0G7Myi3tYR64"

UPLOAD_API_ENDPOINT = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app/up"
ADD_VIDEO_API_ENDPOINT = "https://7f8f6e2e-9c68-4880-939b-61d184b126b0-00-3n5zk13i6o9mt.sisko.replit.dev/add"
CHECK_STATUS_API_ENDPOINT_BASE = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app"

client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_states = {}
WAITING_HD_VIDEO = 1
WAITING_SD_VIDEO = 2
IDLE = 3

async def upload_video_to_api(file_path):
    try:
        with open(file_path, 'rb') as f:
            files = {'video': f}
            response = requests.post(UPLOAD_API_ENDPOINT, files=files)
        return response.json() if response.status_code == 202 else None
    except Exception as e:
        print(f"Error uploading video: {e}")
        return None

async def check_processing_status(process_id):
    try:
        check_url = f"{CHECK_STATUS_API_ENDPOINT_BASE}/check_status/{process_id}"
        response = requests.get(check_url, headers={'Accept': 'application/json'})
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def modify_dropbox_link(dropbox_link):
    return dropbox_link.replace("&dl=0", "@raw=1")

async def add_hd_sd_links_to_api(hd_link, sd_link):
    try:
        api_url = f"{ADD_VIDEO_API_ENDPOINT}?hd={hd_link}&sd={sd_link}"
        response = requests.get(api_url)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        print(f"Error adding links: {e}")
        return None

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_states[event.sender_id] = {'state': IDLE}
    await event.reply("Hello! Use /add {video title} to start adding a new video.")

@client.on(events.NewMessage(pattern=r'/add (.+)'))
async def add_title(event):
    title = event.pattern_match.group(1).strip()
    user_states[event.sender_id] = {
        'state': WAITING_HD_VIDEO,
        'title': title,
        'hd_message': None,
        'sd_message': None
    }
    await event.reply(f"Title '{title}' added. Now, please send the HD video.")

@client.on(events.NewMessage)
async def handle_video(event):
    sender_id = event.sender_id
    if sender_id not in user_states:
        return

    state_data = user_states[sender_id]
    current_state = state_data['state']

    if current_state == WAITING_HD_VIDEO and event.message.video:
        # Store HD message reference
        state_data['hd_message'] = (event.chat_id, event.message.id)
        state_data['state'] = WAITING_SD_VIDEO
        await event.reply("HD video received. Now, please send the SD video.")

    elif current_state == WAITING_SD_VIDEO and event.message.video:
        # Store SD message reference
        state_data['sd_message'] = (event.chat_id, event.message.id)
        await event.reply("SD video received. Starting processing...")

        # Retrieve both messages
        hd_chat_id, hd_msg_id = state_data['hd_message']
        sd_chat_id, sd_msg_id = state_data['sd_message']

        try:
            # Download HD video
            hd_msg = await client.get_messages(hd_chat_id, ids=hd_msg_id)
            hd_path = f"temp_hd_{hd_msg_id}.mp4"
            await hd_msg.download_media(file=hd_path)

            # Download SD video
            sd_msg = await client.get_messages(sd_chat_id, ids=sd_msg_id)
            sd_path = f"temp_sd_{sd_msg_id}.mp4"
            await sd_msg.download_media(file=sd_path)

            # Process both videos
            await process_videos(event, hd_path, sd_path)

        except Exception as e:
            await event.reply(f"Error: {str(e)}")
            state_data['state'] = IDLE
        finally:
            # Cleanup
            if os.path.exists(hd_path):
                os.remove(hd_path)
            if os.path.exists(sd_path):
                os.remove(sd_path)
            user_states[sender_id] = {'state': IDLE}

async def process_videos(event, hd_path, sd_path):
    # HD Processing
    await event.reply("🔄 Processing HD video...")
    hd_response = await upload_video_to_api(hd_path)
    if not hd_response:
        await event.reply("⚠️ HD video upload failed")
        return

    hd_process_id = hd_response['process_id']
    hd_link = await track_processing(event, hd_process_id, "HD")
    if not hd_link:
        return

    # SD Processing
    await event.reply("🔄 Processing SD video...")
    sd_response = await upload_video_to_api(sd_path)
    if not sd_response:
        await event.reply("⚠️ SD video upload failed")
        return

    sd_process_id = sd_response['process_id']
    sd_link = await track_processing(event, sd_process_id, "SD")
    if not sd_link:
        return

    # Finalize
    final_response = await add_hd_sd_links_to_api(hd_link, sd_link)
    if final_response and 'url' in final_response:
        await event.reply(f"✅ Processing Complete!\nFinal URL: {final_response['url']}")
    else:
        await event.reply("⚠️ Failed to generate final URL")

async def track_processing(event, process_id, video_type):
    while True:
        status = await check_processing_status(process_id)
        if not status:
            await event.reply(f"⚠️ {video_type} status check failed")
            return None
        
        if status['status'] == 'success':
            return modify_dropbox_link(status['url'])
        elif status['status'] == 'error':
            await event.reply(f"❌ {video_type} Error: {status['message']}")
            return None
        
        await asyncio.sleep(5)

print("Bot is running...")
client.run_until_disconnected()
