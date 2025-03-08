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
BOT_TOKEN = "7479613855:AAGVHnXaJI6VmkZXbyzgmgI0G7Myi3tYR64"

# ফ্লাস্ক API এন্ডপয়েন্ট (ভিডিও আপলোডের জন্য)
UPLOAD_API_ENDPOINT = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app/up"
# নতুন API এন্ডপয়েন্ট (HD এবং SD লিঙ্ক যুক্ত করার জন্য)
ADD_VIDEO_API_ENDPOINT = "https://7f8f6e2e-9c68-4880-939b-61d184b126b0-00-3n5zk13i6o9mt.sisko.replit.dev/add"
# প্রসেসিং স্ট্যাটাস চেক করার জন্য API এন্ডপয়েন্ট
CHECK_STATUS_API_ENDPOINT_BASE = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app"

# ক্লায়েন্ট তৈরি করুন
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ব্যবহারকারীর অবস্থা ট্র্যাক করার জন্য ডিকশনারি
user_states = {}
WAITING_TITLE = 0
WAITING_HD_VIDEO = 1
WAITING_SD_VIDEO = 2
IDLE = 3

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
        check_url = f"{CHECK_STATUS_API_ENDPOINT_BASE}/check_status/{process_id}"
        response = requests.get(check_url, headers={'Accept': 'application/json'})

        if response.status_code == 200:
            return response.json()  # স্ট্যাটাস ডেটা রিটার্ন করুন
        else:
            return None
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def modify_dropbox_link(dropbox_link):
    """Dropbox লিঙ্কে dl=0 কে raw=1 তে পরিবর্তন করুন"""
    return dropbox_link.replace("&dl=0", "@raw=1")

async def add_hd_sd_links_to_api(hd_link, sd_link):
    """HD এবং SD লিঙ্ক API তে পোস্ট করুন"""
    try:
        api_url = f"{ADD_VIDEO_API_ENDPOINT}?hd={hd_link}&sd={sd_link}"
        response = requests.get(api_url) # এখানে GET রিকোয়েস্ট ব্যবহার করা হয়েছে যেমনটি আপনি উল্লেখ করেছেন

        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Error adding HD and SD links: {e}")
        return None


@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    """/start কমান্ড হ্যান্ডলার"""
    user_states[event.sender_id] = {'state': IDLE} # ইউজার স্টেট রিসেট করুন
    await event.reply("Hello! Use /add {video title} to start adding a new video.")

@client.on(events.NewMessage(pattern=r'/add (.+)'))
async def add_title(event):
    """/add কমান্ড হ্যান্ডলার এবং টাইটেল গ্রহণ"""
    title = event.pattern_match.group(1).strip()
    user_states[event.sender_id] = {'state': WAITING_HD_VIDEO, 'title': title, 'hd_file': None, 'sd_file': None}
    await event.reply(f"Title '{title}' added. Now, please send the HD video.")


@client.on(events.NewMessage)
async def handle_video(event):
    """ভিডিও মেসেজ হ্যান্ডলার"""
    sender_id = event.sender_id
    state_data = user_states.get(sender_id)

    if state_data is None:
        return # যদি state_data না থাকে, তাহলে কিছু করবেন না

    current_state = state_data.get('state', IDLE)

    if current_state == WAITING_HD_VIDEO and event.message.video:
        # এইচডি ভিডিও পাওয়া গেছে, কিন্তু ডাউনলোড করবেন না
        user_states[sender_id]['hd_file'] = event.message.id  # শুধুমাত্র মেসেজ আইডি সংরক্ষণ করুন
        user_states[sender_id]['state'] = WAITING_SD_VIDEO
        await event.reply("HD video received. Now, please send the SD video.")

    elif current_state == WAITING_SD_VIDEO and event.message.video:
        # এসডি ভিডিও পাওয়া গেছে, এখন HD এবং SD ভিডিও ডাউনলোড করুন
        temp_file_sd = f"temp_sd_{event.message.id}.mp4"
        user_states[sender_id]['sd_file'] = temp_file_sd # এসডি ফাইলের পাথ সংরক্ষণ করুন
        await event.download_media(file=temp_file_sd)

        # HD ভিডিও ডাউনলোড করুন
        hd_message_id = user_states[sender_id]['hd_file']
        temp_file_hd = f"temp_hd_{hd_message_id}.mp4"
        user_states[sender_id]['hd_file'] = temp_file_hd # HD ফাইলের পাথ সংরক্ষণ করুন
        hd_message = await client.get_messages(event.chat_id, ids=hd_message_id)
        await hd_message.download_media(file=temp_file_hd)

        await event.reply("SD video received. Processing started...")

        hd_file_path = user_states[sender_id]['hd_file']
        sd_file_path = user_states[sender_id]['sd_file']

        hd_processed_link = None
        sd_processed_link = None

        # এইচডি ভিডিও প্রসেসিং শুরু করুন
        if hd_file_path:
            await event.reply("🔄 Processing HD video...")
            upload_response_hd = await upload_video_to_api(hd_file_path)

            if upload_response_hd:
                process_id_hd = upload_response_hd['process_id']

                # প্রসেসিং স্ট্যাটাস চেক করুন HD
                while True:
                    status_response_hd = await check_processing_status(process_id_hd)
                    if status_response_hd:
                        if status_response_hd['status'] == 'success':
                            hd_processed_link = modify_dropbox_link(status_response_hd['url'])
                            break
                        elif status_response_hd['status'] == 'error':
                            await event.reply(f"❌ HD Video Processing Error: {status_response_hd['message']}")
                            user_states[sender_id]['state'] = IDLE # রিসেট স্টেট
                            if os.path.exists(hd_file_path):
                                os.remove(hd_file_path)
                            if os.path.exists(sd_file_path):
                                os.remove(sd_file_path)
                            return # প্রসেসিং এরর হলে SD ভিডিও এর জন্য অপেক্ষা না করে ফিরে যান
                    await asyncio.sleep(5)
            else:
                await event.reply("⚠️ Failed to start processing HD video.")
                user_states[sender_id]['state'] = IDLE # রিসেট স্টেট
                if os.path.exists(hd_file_path):
                    os.remove(hd_file_path)
                if os.path.exists(sd_file_path):
                    os.remove(sd_file_path)
                return

        # এসডি ভিডিও প্রসেসিং শুরু করুন
        if sd_file_path:
            await event.reply("🔄 Processing SD video...")
            upload_response_sd = await upload_video_to_api(sd_file_path)

            if upload_response_sd:
                process_id_sd = upload_response_sd['process_id']

                # প্রসেসিং স্ট্যাটাস চেক করুন SD
                while True:
                    status_response_sd = await check_processing_status(process_id_sd)
                    if status_response_sd:
                        if status_response_sd['status'] == 'success':
                            sd_processed_link = modify_dropbox_link(status_response_sd['url'])
                            break
                        elif status_response_sd['status'] == 'error':
                            await event.reply(f"❌ SD Video Processing Error: {status_response_sd['message']}")
                            user_states[sender_id]['state'] = IDLE # রিসেট স্টেট
                            if os.path.exists(hd_file_path):
                                os.remove(hd_file_path)
                            if os.path.exists(sd_file_path):
                                os.remove(sd_file_path)
                            return # প্রসেসিং এরর হলে HD ভিডিও এর জন্য অপেক্ষা না করে ফিরে যান
                    await asyncio.sleep(5)
            else:
                await event.reply("⚠️ Failed to start processing SD video.")
                user_states[sender_id]['state'] = IDLE # রিসেট স্টেট
                if os.path.exists(hd_file_path):
                    os.remove(hd_file_path)
                if os.path.exists(sd_file_path):
                    os.remove(sd_file_path)
                return

        # HD এবং SD লিঙ্ক API তে যুক্ত করুন এবং ফাইনাল URL পাঠান
        if hd_processed_link and sd_processed_link:
            final_api_response = await add_hd_sd_links_to_api(hd_processed_link, sd_processed_link)

            if final_api_response and 'url' in final_api_response:
                final_url = final_api_response['url']
                await event.reply(f"✅ Both HD and SD videos processed!\nFinal URL: {final_url}")
            else:
                await event.reply("⚠️ Failed to generate final URL.")
        else:
             await event.reply("⚠️ Failed to process one or both videos completely.")

        user_states[sender_id]['state'] = IDLE # রিসেট স্টেট

        # টেম্প ফাইল ডিলিট করুন HD and SD
        if os.path.exists(hd_file_path):
            os.remove(hd_file_path)
        if os.path.exists(sd_file_path):
            os.remove(sd_file_path)

    elif current_state != IDLE and not event.message.video:
        if current_state == WAITING_HD_VIDEO:
            await event.reply("Please send the HD video.")
        elif current_state == WAITING_SD_VIDEO:
            await event.reply("Please send the SD video.")
        else:
             await event.reply("Invalid input. Please use /add {video title} to start or send HD video after adding title.")


# বট চালান
print("Bot is running...")
client.run_until_disconnected()
