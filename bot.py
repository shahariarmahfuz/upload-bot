import os
import asyncio
import requests
from telethon import TelegramClient, events, types
from dotenv import load_dotenv

# .env ফাইল থেকে ভেরিয়েবল লোড করুন
load_dotenv()

# টেলিগ্রাম API কনফিগারেশন
API_ID = "20716719"
API_HASH = "c929824683800816ddf0faac845d89c9"
BOT_TOKEN = "7479613855:AAFaJT8jkJfUMOTRV14YoH6KyFM_Z3ZwlEc"

# ফ্লাস্ক API এন্ডপয়েন্ট (ভিডিও আপলোডের জন্য)
UPLOAD_API_ENDPOINT = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app/up"
# নতুন API এন্ডপয়েন্ট (HD এবং SD লিঙ্ক যুক্ত করার জন্য)
ADD_VIDEO_API_ENDPOINT = "https://getterlink.onrender.com/add"
# প্রসেসিং স্ট্যাটাস চেক করার জন্য API এন্ডপয়েন্ট
CHECK_STATUS_API_ENDPOINT_BASE = "https://molecular-angel-itachivai-e6c91c4d.koyeb.app"

# ক্লায়েন্ট তৈরি করুন
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ব্যবহারকারীর অবস্থা ট্র্যাক করার জন্য ডিকশনারি
user_states = {}
WAITING_TITLE = 0
WAITING_HD_VIDEO = 1
WAITING_SD_VIDEO = 2
WAITING_CONFIRMATION = 3
IDLE = 4
PROCESSING_ALL_EPISODES = 5

# ব্যবহারকারীর এপিসোড ডেটা ট্র্যাক করার জন্য ডিকশনারি
user_episodes_data = {}


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
    user_states[event.sender_id] = {'state': IDLE, 'episode_count': 1} # ইউজার স্টেট রিসেট করুন, episode_count শুরু করুন
    user_episodes_data[event.sender_id] = [] # এপিসোড ডেটা রিসেট করুন
    await event.reply("Hello! Use /add {video title} to start adding a new video.")

@client.on(events.NewMessage(pattern=r'/add (.+)'))
async def add_title(event):
    """/add কমান্ড হ্যান্ডলার এবং প্রথম এপিসোডের টাইটেল গ্রহণ"""
    title = event.pattern_match.group(1).strip()
    user_id = event.sender_id
    user_states[user_id] = {'state': WAITING_HD_VIDEO, 'title': title, 'hd_file': None, 'sd_file': None, 'episode_count': 1} # episode_count সেট করুন
    user_episodes_data[user_id] = [] # Ensure episode data is initialized for the user
    user_episodes_data[user_id].append({'title': title, 'hd_file': None, 'sd_file': None}) # প্রথম এপিসোড ডেটা যোগ করুন
    await event.reply(f"Episode 1 Title '{title}' added. Now, please send the HD video for Episode 1.")


@client.on(events.NewMessage(pattern=r'/add(\d+) (.+)'))
async def add_title_n(event):
    """/add2, /add3, ... কমান্ড হ্যান্ডলার এবং পরবর্তী এপিসোডের টাইটেল গ্রহণ"""
    episode_number = int(event.pattern_match.group(1))
    title = event.pattern_match.group(2).strip()
    user_id = event.sender_id

    if user_states.get(user_id, {}).get('state') not in [WAITING_CONFIRMATION, IDLE, PROCESSING_ALL_EPISODES]:
        await event.reply("Please complete adding videos for the current episode or use /start to begin a new session.")
        return

    user_states[user_id] = {'state': WAITING_HD_VIDEO, 'title': title, 'hd_file': None, 'sd_file': None, 'episode_count': episode_number}
    if user_id not in user_episodes_data:
        user_episodes_data[user_id] = []
    user_episodes_data[user_id].append({'title': title, 'hd_file': None, 'sd_file': None}) # নতুন এপিসোড ডেটা যোগ করুন
    await event.reply(f"Episode {episode_number} Title '{title}' added. Now, please send the HD video for Episode {episode_number}.")


@client.on(events.NewMessage(pattern='/send'))
async def send_all_episodes(event):
    """/send কমান্ড হ্যান্ডলার, সমস্ত এপিসোড প্রসেসিং শুরু করবে"""
    user_id = event.sender_id
    if user_states.get(user_id, {}).get('state') == WAITING_CONFIRMATION or user_states.get(user_id, {}).get('state') == IDLE:
        if not user_episodes_data.get(user_id):
            await event.reply("No episodes added yet. Please use /add {video title} to add episodes.")
            user_states[user_id]['state'] = IDLE
            return

        user_states[user_id]['state'] = PROCESSING_ALL_EPISODES
        await event.reply("Processing all episodes...")
        await process_all_episodes(event)
    else:
        await event.reply("Please complete adding videos for the current episode or confirmation process.")


async def process_all_episodes(event):
    """সমস্ত এপিসোড প্রসেস করুন এবং ফাইনাল URL তৈরি করুন"""
    user_id = event.sender_id
    episodes = user_episodes_data.get(user_id, [])
    final_links_text = ""
    all_processed = True # track if all episodes processed successfully

    for episode_index, episode_data in enumerate(episodes):
        episode_number = episode_index + 1
        title = episode_data['title']
        hd_file_path = episode_data['hd_file']
        sd_file_path = episode_data['sd_file']
        hd_processed_link = None
        sd_processed_link = None

        await event.reply(f"🎬 Processing Episode {episode_number}: {title}...")

        # এইচডি ভিডিও প্রসেসিং শুরু করুন
        if hd_file_path:
            await event.reply(f"🔄 Processing HD video for Episode {episode_number}...")
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
                            await event.reply(f"❌ HD Video Processing Error for Episode {episode_number}: {status_response_hd['message']}")
                            all_processed = False # set flag to false if any episode processing fails
                            break
                    await asyncio.sleep(5)
            else:
                await event.reply(f"⚠️ Failed to start processing HD video for Episode {episode_number}.")
                all_processed = False # set flag to false if any episode processing fails


        # এসডি ভিডিও প্রসেসিং শুরু করুন
        if sd_file_path:
            await event.reply(f"🔄 Processing SD video for Episode {episode_number}...")
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
                            await event.reply(f"❌ SD Video Processing Error for Episode {episode_number}: {status_response_sd['message']}")
                            all_processed = False # set flag to false if any episode processing fails
                            break
                    await asyncio.sleep(5)
            else:
                await event.reply(f"⚠️ Failed to start processing SD video for Episode {episode_number}.")
                all_processed = False # set flag to false if any episode processing fails

        # HD এবং SD লিঙ্ক API তে যুক্ত করুন এবং ফিনাল URL তৈরি করুন প্রতি এপিসোডের জন্য
        if hd_processed_link and sd_processed_link:
            final_api_response = await add_hd_sd_links_to_api(hd_processed_link, sd_processed_link)

            if final_api_response and 'url' in final_api_response:
                final_url = final_api_response['url']
                final_links_text += f"Episode {episode_number}: {title}\nLink: {final_url}\n\n"
            else:
                await event.reply(f"⚠️ Failed to generate final URL for Episode {episode_number}: {title}.")
                all_processed = False # set flag to false if any episode processing fails
        else:
             await event.reply(f"⚠️ Failed to process one or both videos completely for Episode {episode_number}: {title}.")
             all_processed = False # set flag to false if any episode processing fails

        # টেম্প ফাইল ডিলিট করুন HD and SD
        if os.path.exists(episode_data['hd_file']):
            os.remove(episode_data['hd_file'])
        if os.path.exists(episode_data['sd_file']):
            os.remove(episode_data['sd_file'])


    if all_processed:
        await event.reply(f"✅ All episodes processed successfully!\n\n{final_links_text}")
    else:
        await event.reply("⚠️ Some episodes failed to process completely. Please check error messages for details.")

    user_states[user_id]['state'] = IDLE # রিসেট স্টেট
    user_episodes_data[user_id] = [] # clear episode data after processing


@client.on(events.NewMessage)
async def handle_video(event):
    """ভিডিও মেসেজ হ্যান্ডলার"""
    sender_id = event.sender_id
    state_data = user_states.get(sender_id)

    if state_data is None:
        return  # যদি state_data না থাকে, তাহলে কিছু করবেন না

    current_state = state_data.get('state', IDLE)
    episode_count = state_data.get('episode_count', 1) # এপিসোড নাম্বার পান, ডিফল্ট 1

    if current_state == WAITING_HD_VIDEO and event.message.video:
        # এইচডি ভিডিও পাওয়া গেছে, কিন্তু ডাউনলোড করবেন না
        episode_data = user_episodes_data[sender_id][-1] # বর্তমান এপিসোড ডেটা পান
        episode_data['hd_file'] = f"temp_hd_ep{episode_count}_{event.message.id}.mp4" # এপিসোড নম্বর যোগ করুন
        await event.download_media(file=episode_data['hd_file']) # HD ফাইল ডাউনলোড করুন
        user_states[sender_id]['state'] = WAITING_SD_VIDEO
        await event.reply(f"HD video for Episode {episode_count} received. Now, please send the SD video for Episode {episode_count}.")

    elif current_state == WAITING_SD_VIDEO and event.message.video:
        # এসডি ভিডিও পাওয়া গেছে
        episode_data = user_episodes_data[sender_id][-1] # বর্তমান এপিসোড ডেটা পান
        episode_data['sd_file'] = f"temp_sd_ep{episode_count}_{event.message.id}.mp4" # এপিসোড নম্বর যোগ করুন
        await event.download_media(file=episode_data['sd_file']) # SD ফাইল ডাউনলোড করুন


        user_states[sender_id]['state'] = WAITING_CONFIRMATION
        await event.reply("SD video received. Do you want to add more episodes? (yes/no or /send to finish)")


    elif current_state != IDLE and current_state != PROCESSING_ALL_EPISODES and not event.message.video:
        if current_state == WAITING_HD_VIDEO:
            await event.reply(f"Please send the HD video for Episode {episode_count}.")
        elif current_state == WAITING_SD_VIDEO:
            await event.reply(f"Please send the SD video for Episode {episode_count}.")
        elif current_state == WAITING_CONFIRMATION:
            await event.reply("Do you want to add more episodes? (yes/no or /send to finish)")
        else:
             await event.reply("Invalid input. Please use /add {video title} to start or send HD video after adding title.")


@client.on(events.NewMessage)
async def handle_text_confirmation(event):
    """টেক্সট মেসেজ হ্যান্ডলার কনফার্মেশন এবং অন্যান্য ইনপুটের জন্য"""
    sender_id = event.sender_id
    state_data = user_states.get(sender_id)

    if state_data is None:
        return # যদি state_data না থাকে, তাহলে কিছু করবেন না

    current_state = state_data.get('state', IDLE)

    if current_state == WAITING_CONFIRMATION:
        text = event.text.strip().lower()
        if text in ['yes', 'y']:
            next_episode_number = len(user_episodes_data[sender_id]) + 1
            user_states[sender_id]['state'] = WAITING_TITLE # পরবর্তী টাইটেলের জন্য অপেক্ষা করুন
            user_states[sender_id]['episode_count'] = next_episode_number # এপিসোড কাউন্ট আপডেট করুন
            await event.reply(f"Okay, use /add{next_episode_number} {{Title}} to add title for Episode {next_episode_number}.")
        elif text in ['no', 'n', '/send']:
            await send_all_episodes(event)
        else:
            await event.reply("Invalid confirmation. Please reply with 'yes', 'no' or use /send to finish.")
    elif current_state != IDLE and current_state != PROCESSING_ALL_EPISODES and not event.message.video and not event.message.text.startswith('/'):
         await event.reply("Invalid input. Please use /add {video title} to start or send HD video after adding title.")


# বট চালান
print("Bot is running...")
client.run_until_disconnected()
