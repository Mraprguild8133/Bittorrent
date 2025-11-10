import os
import re
import sys
import json
import time
import asyncio
import requests
import subprocess
import logging

import core as helper
from utils import progress_bar
from vars import API_ID, API_HASH, BOT_TOKEN
from wasabi_client import wasabi_client
from aiohttp import ClientSession
from pyromod import listen
from subprocess import getstatusoutput

from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import StickerEmojiInvalid
from pyrogram.types.messages_and_media import message
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

bot = Client(
    "bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Global variable to track if stop command was issued
STOP_TASK = False

@bot.on_message(filters.command(["start"]))
async def start(bot: Client, m: Message):
    await m.reply_text(
        f"<b>Hello {m.from_user.mention} 👋\n\n"
        "I Am A Bot For Downloading Links From Your **.TXT** File And Then Uploading "
        "That File On Telegram or Wasabi Cloud.\n\n"
        "Available Commands:\n"
        "• /upload - Upload files to Telegram\n"
        "• /wasabi_upload - Upload files to Wasabi Cloud\n"
        "• /stop - Stop any ongoing task\n\n"
        "Send /upload or /wasabi_upload to get started!</b>"
    )

@bot.on_message(filters.command("stop"))
async def stop_handler(_, m):
    global STOP_TASK
    STOP_TASK = True
    await m.reply_text("**Stopping current task...** 🚦", True)
    await asyncio.sleep(2)
    STOP_TASK = False

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    if not name:
        return "unknown"
    # Remove special characters and limit length
    cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
    return cleaned[:60]

def parse_links_from_file(file_path):
    """Parse links from text file"""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            content = f.read()
        
        content = content.split("\n")
        links = []
        for i in content:
            if i.strip():  # Skip empty lines
                links.append(i.split("://", 1))
        return links
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return []

async def process_link(bot, m, url, name, raw_text2, raw_text0, MR, thumb, count, use_wasabi=False):
    """Process a single link - download and upload"""
    global STOP_TASK
    
    if STOP_TASK:
        return False, count

    try:
        V = url.replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
        url = "https://" + V

        # Handle specific sites
        if "visionias" in url:
            async with ClientSession() as session:
                async with session.get(url, headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'Referer': 'http://www.visionias.in/',
                    'Sec-Fetch-Dest': 'iframe',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'cross-site',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36',
                    'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                }) as resp:
                    text = await resp.text()
                    url_match = re.search(r"(https://.*?playlist.m3u8.*?)\"", text)
                    if url_match:
                        url = url_match.group(1)

        elif 'videos.classplusapp' in url:
            url = requests.get(
                f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}',
                headers={
                    'x-access-token': 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MzgzNjkyMTIsIm9yZ0lkIjoyNjA1LCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTcwODI3NzQyODkiLCJuYW1lIjoiQWNlIiwiZW1haWwiOm51bGwsImlzRmlyc3RMb2dpbiI6dHJ1ZSwiZGVmYXVsdExhbmd1YWdlIjpudWxsLCJjb3VudHJ5Q29kZSI6IklOIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJpYXQiOjE2NDMyODE4NzcsImV4cCI6MTY0Mzg4NjY3N30.hM33P2ai6ivdzxPPfm01LAd4JWv-vnrSxGXqvCirCSpUfhhofpeqyeHPxtstXwe0'
                }
            ).json().get('url', url)

        elif '/master.mpd' in url:
            id = url.split("/")[-2]
            url = "https://d26g5bnklkwsh4.cloudfront.net/" + id + "/master.m3u8"

        # Prepare filename
        name1 = sanitize_filename(name)
        name = f'{str(count).zfill(3)}) {name1}'

        # Prepare yt-dlp format
        if "youtu" in url:
            ytf = f"b[height<={raw_text2}][ext=mp4]/bv[height<={raw_text2}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
        else:
            ytf = f"b[height<={raw_text2}]/bv[height<={raw_text2}]+ba/b/bv+ba"

        if "jw-prod" in url:
            cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
        else:
            cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

        # Prepare captions
        cc = f'**[📽️] Vid_ID:** {str(count).zfill(3)}. {name1}{MR}\n**𝔹ᴀᴛᴄʜ** » **{raw_text0}**'
        cc1 = f'**[📁] Pdf_ID:** {str(count).zfill(3)}. {name1}{MR}\n**𝔹ᴀᴛᴄʜ** » **{raw_text0}**'

        # Process based on file type
        if "drive" in url:
            try:
                ka = await helper.download(url, name)
                if use_wasabi:
                    success = await helper.send_doc(bot, m, cc, ka, cc1, None, count, name, use_wasabi=True)
                else:
                    success = await helper.send_doc(bot, m, cc, ka, cc1, None, count, name)
                if success:
                    count += 1
                await asyncio.sleep(1)
            except FloodWait as e:
                await m.reply_text(f"FloodWait: Sleeping for {e.x} seconds")
                await asyncio.sleep(e.x)
                return True, count
        
        elif ".pdf" in url:
            try:
                cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                os.system(download_cmd)
                
                if use_wasabi:
                    success = await helper.send_doc(bot, m, cc, f'{name}.pdf', cc1, None, count, name, use_wasabi=True)
                else:
                    await bot.send_document(chat_id=m.chat.id, document=f'{name}.pdf', caption=cc1)
                    count += 1
                    success = True
                
                if os.path.exists(f'{name}.pdf'):
                    os.remove(f'{name}.pdf')
                    
            except FloodWait as e:
                await m.reply_text(f"FloodWait: Sleeping for {e.x} seconds")
                await asyncio.sleep(e.x)
                return True, count
        
        else:
            # Video files
            Show = f"**⥥ Downloading... ⬇️**\n\n**📝 Name »** `{name}`\n**❄ Quality »** `{raw_text2}p`\n\n**🔗 URL »** `{url}`"
            prog = await m.reply_text(Show)
            
            res_file = await helper.download_video(url, cmd, name)
            filename = res_file
            
            await prog.delete(True)
            
            if use_wasabi:
                success = await helper.send_vid(bot, m, cc, filename, thumb, name, prog, use_wasabi=True)
            else:
                success = await helper.send_vid(bot, m, cc, filename, thumb, name, prog)
            
            if success:
                count += 1
            
            await asyncio.sleep(1)

        return True, count

    except Exception as e:
        error_msg = f"**Downloading Interrupted**\nError: `{str(e)}`\n**Name** » {name}\n**Link** » `{url}`"
        await m.reply_text(error_msg)
        logger.error(f"Error processing link: {e}")
        return False, count

@bot.on_message(filters.command(["upload", "wasabi_upload"]))
async def upload_handler(bot: Client, m: Message):
    global STOP_TASK
    STOP_TASK = False
    
    use_wasabi = m.command[0] == "wasabi_upload"
    upload_type = "Wasabi Cloud" if use_wasabi else "Telegram"
    
    editable = await m.reply_text(f'📁 Send TXT file with links for {upload_type} upload')
    
    # Get TXT file
    try:
        input: Message = await bot.listen(editable.chat.id, timeout=300)
        if input.document:
            x = await input.download()
        else:
            await m.reply_text("Please send a TXT file.")
            return
        await input.delete(True)
    except Exception as e:
        await editable.edit("File input timeout or error.")
        return

    # Parse links from file
    links = parse_links_from_file(x)
    os.remove(x)
    
    if not links:
        await m.reply_text("**No valid links found in the file.**")
        return
    
    await editable.edit(f"**Total links found:** **{len(links)}**\n\n**Send starting index (default is 1):**")
    
    # Get starting index
    try:
        input0: Message = await bot.listen(editable.chat.id, timeout=60)
        raw_text = input0.text
        await input0.delete(True)
        start_index = max(1, int(raw_text)) if raw_text.isdigit() else 1
    except:
        start_index = 1

    await editable.edit("**Now Please Send Your Batch Name**")
    
    # Get batch name
    try:
        input1: Message = await bot.listen(editable.chat.id, timeout=60)
        raw_text0 = input1.text
        await input1.delete(True)
    except:
        await editable.edit("Batch name input timeout.")
        return

    await editable.edit("**Enter resolution**\n144, 240, 360, 480, 720, 1080")
    
    # Get resolution
    try:
        input2: Message = await bot.listen(editable.chat.id, timeout=60)
        raw_text2 = input2.text
        await input2.delete(True)
        
        resolution_map = {
            "144": "256x144",
            "240": "426x240", 
            "360": "640x360",
            "480": "854x480",
            "720": "1280x720",
            "1080": "1920x1080"
        }
        res = resolution_map.get(raw_text2, "UN")
    except:
        res = "UN"

    await editable.edit("**Enter caption for your files:**")
    
    # Get caption
    try:
        input3: Message = await bot.listen(editable.chat.id, timeout=60)
        raw_text3 = input3.text
        await input3.delete(True)
        MR = raw_text3
    except:
        MR = ""

    await editable.edit("**Send thumbnail URL**\nOr send 'no' for no thumbnail")
    
    # Get thumbnail
    try:
        input6: Message = await bot.listen(editable.chat.id, timeout=60)
        raw_text6 = input6.text
        await input6.delete(True)
        
        thumb = raw_text6
        if thumb.startswith("http://") or thumb.startswith("https://"):
            getstatusoutput(f"wget '{thumb}' -O 'thumb.jpg'")
            thumb = "thumb.jpg"
        else:
            thumb = "no"
    except:
        thumb = "no"

    await editable.delete()

    # Start processing
    count = start_index
    total_links = len(links)
    processed = 0
    failed = 0

    progress_msg = await m.reply_text(
        f"**🚀 Starting {upload_type} Upload**\n"
        f"**Total:** {total_links} links\n"
        f"**Starting from:** {start_index}\n"
        f"**Processed:** {processed}\n"
        f"**Failed:** {failed}\n"
        f"**Status:** Starting..."
    )

    for i in range(start_index - 1, len(links)):
        if STOP_TASK:
            await progress_msg.edit("**Task stopped by user.**")
            break

        link_data = links[i]
        if len(link_data) < 2:
            continue

        name_part = link_data[0] if link_data[0] else f"file_{i+1}"
        url_part = link_data[1] if len(link_data) > 1 else ""

        if not url_part:
            continue

        success, count = await process_link(
            bot, m, url_part, name_part, raw_text2, 
            raw_text0, MR, thumb, count, use_wasabi
        )

        if success:
            processed += 1
        else:
            failed += 1

        # Update progress every 5 files or when significant changes occur
        if processed % 5 == 0 or i == len(links) - 1:
            await progress_msg.edit(
                f"**📊 Upload Progress ({upload_type})**\n"
                f"**Total:** {total_links} links\n"
                f"**Processed:** {processed}\n"
                f"**Failed:** {failed}\n"
                f"**Current:** {count}\n"
                f"**Status:** {'Stopped' if STOP_TASK else 'Running'}"
            )

        await asyncio.sleep(2)  # Small delay between processing

    # Final status
    if STOP_TASK:
        await m.reply_text("**Task stopped by user.** ⚠️")
    else:
        await m.reply_text(
            f"**✅ Task Completed!**\n\n"
            f"**Upload Type:** {upload_type}\n"
            f"**Total Processed:** {processed}\n"
            f"**Failed:** {failed}\n"
            f"**Batch:** {raw_text0}\n"
            f"**Thanks for using the bot!** 🎉"
        )

    # Cleanup
    if thumb != "no" and os.path.exists("thumb.jpg"):
        os.remove("thumb.jpg")

@bot.on_message(filters.command(["wasabi_files"]))
async def list_wasabi_files(bot: Client, m: Message):
    """List files in Wasabi bucket"""
    try:
        result = await wasabi_client.list_files()
        if result['success']:
            files = result['files']
            if files:
                message_text = "**📁 Files in Wasabi Bucket:**\n\n"
                for file in files[:10]:  # Show first 10 files
                    message_text += f"• `{file['key']}` - {file['size']}\n"
                
                if len(files) > 10:
                    message_text += f"\n... and {len(files) - 10} more files"
                
                await m.reply_text(message_text)
            else:
                await m.reply_text("**No files found in Wasabi bucket.**")
        else:
            await m.reply_text(f"**Error accessing Wasabi:** {result['error']}")
    except Exception as e:
        await m.reply_text(f"**Error:** {str(e)}")

@bot.on_message(filters.command(["help"]))
async def help_command(bot: Client, m: Message):
    help_text = """
**🤖 Bot Help Guide**

**Available Commands:**
• /start - Start the bot
• /upload - Upload files to Telegram
• /wasabi_upload - Upload files to Wasabi Cloud
• /wasabi_files - List files in Wasabi bucket
• /stop - Stop current task
• /help - Show this help

**Upload Process:**
1. Send /upload or /wasabi_upload
2. Send a TXT file with links (one per line)
3. Follow the interactive steps:
   - Starting index
   - Batch name
   - Resolution
   - Caption
   - Thumbnail

**Supported Links:**
• Google Drive
• YouTube
• Direct video links
• PDF files
• And many more!

**Note:** Use /stop to cancel any ongoing upload task.
"""
    await m.reply_text(help_text)

if __name__ == "__main__":
    logger.info("Starting Telegram Bot...")
    bot.run()
