import os
import re
import time
import asyncio
import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from aiohttp import ClientSession
from subprocess import getstatusoutput

import core as helper
from utils import progress_bar
from wasabi_client import wasabi_client

logger = logging.getLogger(__name__)

# Global variable to track if stop command was issued
STOP_TASK = False

@Client.on_message(filters.command("stop"))
async def stop_handler(client: Client, message: Message):
    global STOP_TASK
    STOP_TASK = True
    await message.reply_text("**🛑 Stopping current task...**", True)
    await asyncio.sleep(2)
    STOP_TASK = False

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    if not name:
        return "unknown"
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
            if i.strip():
                if "://" in i:
                    parts = i.split("://", 1)
                    links.append([parts[0], parts[1]])
                else:
                    links.append(["", i])
        return links
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        return []

async def process_single_link(client, message, url, name, quality, batch_name, caption, thumb, count, use_wasabi=False):
    """Process a single link - download and upload"""
    global STOP_TASK
    
    if STOP_TASK:
        return False, count

    try:
        if "://" not in url:
            url = "https://" + url
            
        V = url.replace("file/d/","uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing","")
        
        # Handle specific sites
        if "visionias" in V:
            async with ClientSession() as session:
                async with session.get(V, headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36',
                }) as resp:
                    text = await resp.text()
                    url_match = re.search(r"(https://.*?playlist.m3u8.*?)\"", text)
                    if url_match:
                        V = url_match.group(1)

        elif 'videos.classplusapp' in V:
            try:
                response = requests.get(
                    f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={V}',
                    headers={
                        'x-access-token': 'eyJhbGciOiJIUzM4NCIsInR5cCI6IkpXVCJ9.eyJpZCI6MzgzNjkyMTIsIm9yZ0lkIjoyNjA1LCJ0eXBlIjoxLCJtb2JpbGUiOiI5MTcwODI3NzQyODkiLCJuYW1lIjoiQWNlIiwiZW1haWwiOm51bGwsImlzRmlyc3RMb2dpbiI6dHJ1ZSwiZGVmYXVsdExhbmd1YWdlIjpudWxsLCJjb3VudHJ5Q29kZSI6IklOIiwiaXNJbnRlcm5hdGlvbmFsIjowLCJpYXQiOjE2NDMyODE4NzcsImV4cCI6MTY0Mzg4NjY3N30.hM33P2ai6ivdzxPPfm01LAd4JWv-vnrSxGXqvCirCSpUfhhofpeqyeHPxtstXwe0'
                    }
                )
                if response.status_code == 200:
                    V = response.json().get('url', V)
            except:
                pass

        elif '/master.mpd' in V:
            id = V.split("/")[-2]
            V = "https://d26g5bnklkwsh4.cloudfront.net/" + id + "/master.m3u8"

        # Prepare filename
        name1 = sanitize_filename(name)
        name = f'{str(count).zfill(3)}) {name1}'

        # Prepare yt-dlp format
        if "youtu" in V:
            ytf = f"b[height<={quality}][ext=mp4]/bv[height<={quality}][ext=mp4]+ba[ext=m4a]/b[ext=mp4]"
        else:
            ytf = f"b[height<={quality}]/bv[height<={quality}]+ba/b/bv+ba"

        if "jw-prod" in V:
            cmd = f'yt-dlp -o "{name}.mp4" "{V}"'
        else:
            cmd = f'yt-dlp -f "{ytf}" "{V}" -o "{name}.mp4"'

        # Prepare captions
        cc = f'**[📽️] Video:** {str(count).zfill(3)}. {name1}\n{caption}\n**Batch:** {batch_name}'
        cc1 = f'**[📁] Document:** {str(count).zfill(3)}. {name1}\n{caption}\n**Batch:** {batch_name}'

        # Process based on file type
        if "drive" in V:
            try:
                ka = await helper.download(V, name)
                if use_wasabi:
                    success, new_count = await helper.send_doc(client, message, cc, ka, cc1, None, count, name, use_wasabi=True)
                else:
                    success, new_count = await helper.send_doc(client, message, cc, ka, cc1, None, count, name)
                if success:
                    count = new_count
                await asyncio.sleep(1)
            except FloodWait as e:
                await message.reply_text(f"⏳ FloodWait: Sleeping for {e.x} seconds")
                await asyncio.sleep(e.x)
                return True, count
            except Exception as e:
                await message.reply_text(f"❌ Error downloading: {str(e)}")
                return False, count
        
        elif ".pdf" in V:
            try:
                cmd = f'yt-dlp -o "{name}.pdf" "{V}"'
                download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                os.system(download_cmd)
                
                if use_wasabi:
                    success, new_count = await helper.send_doc(client, message, cc, f'{name}.pdf', cc1, None, count, name, use_wasabi=True)
                else:
                    await client.send_document(chat_id=message.chat.id, document=f'{name}.pdf', caption=cc1)
                    count += 1
                    success = True
                
                if os.path.exists(f'{name}.pdf'):
                    os.remove(f'{name}.pdf')
                    
            except FloodWait as e:
                await message.reply_text(f"⏳ FloodWait: Sleeping for {e.x} seconds")
                await asyncio.sleep(e.x)
                return True, count
            except Exception as e:
                await message.reply_text(f"❌ Error processing PDF: {str(e)}")
                return False, count
        
        else:
            # Video files
            Show = f"**⥥ Downloading... ⬇️**\n\n**📝 Name:** `{name}`\n**🎯 Quality:** `{quality}p`\n\n**🔗 URL:** `{V}`"
            prog = await message.reply_text(Show)
            
            try:
                res_file = await helper.download_video(V, cmd, name)
                filename = res_file
                
                await prog.delete()
                
                if use_wasabi:
                    success = await helper.send_vid(client, message, cc, filename, thumb, name, prog, use_wasabi=True)
                else:
                    success = await helper.send_vid(client, message, cc, filename, thumb, name, prog)
                
                if success:
                    count += 1
                
                await asyncio.sleep(1)
            except Exception as e:
                await prog.delete()
                await message.reply_text(f"❌ Error downloading video: {str(e)}")
                return False, count

        return True, count

    except Exception as e:
        error_msg = f"**❌ Download Interrupted**\n**Error:** `{str(e)}`\n**File:** {name}\n**URL:** `{V}`"
        await message.reply_text(error_msg)
        logger.error(f"Error processing link: {e}")
        return False, count

@Client.on_message(filters.command(["upload", "wasabi_upload"]))
async def upload_handler(client: Client, message: Message):
    global STOP_TASK
    STOP_TASK = False
    
    use_wasabi = message.command[0] == "wasabi_upload"
    upload_type = "Wasabi Cloud" if use_wasabi else "Telegram"
    
    editable = await message.reply_text(f'📁 **Send TXT file with links for {upload_type} upload**')
    
    # Get TXT file
    try:
        input_msg = await client.listen(message.chat.id, timeout=300)
        if input_msg.document or (input_msg.text and input_msg.text.endswith('.txt')):
            file_path = await input_msg.download()
        else:
            await editable.edit("❌ **Please send a TXT file.**")
            return
        await input_msg.delete()
    except Exception as e:
        await editable.edit(f"❌ **File input timeout or error:** {str(e)}")
        return

    # Parse links from file
    links = parse_links_from_file(file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    if not links:
        await message.reply_text("❌ **No valid links found in the file.**")
        return
    
    await editable.edit(f"✅ **Total links found:** **{len(links)}**\n\n**📥 Send starting index (default: 1):**")
    
    # Get starting index
    try:
        input0 = await client.listen(message.chat.id, timeout=60)
        raw_text = input0.text
        await input0.delete()
        start_index = max(1, int(raw_text)) if raw_text.isdigit() else 1
    except:
        start_index = 1

    await editable.edit("**📛 Now Please Send Your Batch Name**")
    
    # Get batch name
    try:
        input1 = await client.listen(message.chat.id, timeout=60)
        batch_name = input1.text
        await input1.delete()
    except:
        await editable.edit("❌ **Batch name input timeout.**")
        return

    await editable.edit("**🎬 Enter resolution:**\n`144, 240, 360, 480, 720, 1080`")
    
    # Get resolution
    try:
        input2 = await client.listen(message.chat.id, timeout=60)
        quality = input2.text
        await input2.delete()
    except:
        quality = "720"

    await editable.edit("**📝 Enter caption for your files:**")
    
    # Get caption
    try:
        input3 = await client.listen(message.chat.id, timeout=60)
        caption = input3.text
        await input3.delete()
    except:
        caption = ""

    await editable.edit("**🖼️ Send thumbnail URL**\nOr send `no` for no thumbnail")
    
    # Get thumbnail
    try:
        input6 = await client.listen(message.chat.id, timeout=60)
        thumb_url = input6.text
        await input6.delete()
        
        thumb = thumb_url
        if thumb and thumb != "no" and (thumb.startswith("http://") or thumb.startswith("https://")):
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

    progress_msg = await message.reply_text(
        f"**🚀 Starting {upload_type} Upload**\n"
        f"**📊 Total:** {total_links} links\n"
        f"**🔢 Starting from:** {start_index}\n"
        f"**✅ Processed:** {processed}\n"
        f"**❌ Failed:** {failed}\n"
        f"**🔄 Status:** Starting..."
    )

    for i in range(start_index - 1, len(links)):
        if STOP_TASK:
            await progress_msg.edit("**🛑 Task stopped by user.**")
            break

        if i >= len(links):
            break

        link_data = links[i]
        if len(link_data) < 2:
            failed += 1
            continue

        name_part = link_data[0] if link_data[0] else f"file_{i+1}"
        url_part = link_data[1] if len(link_data) > 1 else ""

        if not url_part:
            failed += 1
            continue

        success, new_count = await process_single_link(
            client, message, url_part, name_part, quality, 
            batch_name, caption, thumb, count, use_wasabi
        )

        if success:
            processed += 1
            count = new_count
        else:
            failed += 1

        # Update progress
        if processed % 3 == 0 or i == len(links) - 1:
            try:
                await progress_msg.edit(
                    f"**📊 Upload Progress ({upload_type})**\n"
                    f"**📁 Total:** {total_links} links\n"
                    f"**✅ Processed:** {processed}\n"
                    f"**❌ Failed:** {failed}\n"
                    f"**🔢 Current:** {count}\n"
                    f"**🔄 Status:** {'🛑 Stopped' if STOP_TASK else '🟢 Running'}"
                )
            except:
                pass

        await asyncio.sleep(2)

    # Final status
    try:
        if STOP_TASK:
            await message.reply_text("**🛑 Task stopped by user.**")
        else:
            await message.reply_text(
                f"**🎉 Task Completed!**\n\n"
                f"**☁️ Upload Type:** {upload_type}\n"
                f"**✅ Total Processed:** {processed}\n"
                f"**❌ Failed:** {failed}\n"
                f"**📛 Batch:** {batch_name}\n"
                f"**🎯 Quality:** {quality}p\n"
                f"**📊 Success Rate:** {round((processed/total_links)*100, 2)}%\n\n"
                f"**Thanks for using the bot!** 🤖"
            )
    except:
        pass

    # Cleanup
    if thumb != "no" and os.path.exists("thumb.jpg"):
        os.remove("thumb.jpg")

@Client.on_message(filters.command(["wasabi_files", "list_files"]))
async def list_wasabi_files(client: Client, message: Message):
    """List files in Wasabi bucket"""
    try:
        result = wasabi_client.list_files()
        if result['success']:
            files = result['files']
            if files:
                message_text = "**📁 Files in Wasabi Bucket:**\n\n"
                for i, file in enumerate(files[:15], 1):
                    message_text += f"**{i}.** `{file['key']}` - {file['size']}\n"
                
                if len(files) > 15:
                    message_text += f"\n**... and {len(files) - 15} more files**"
                
                await message.reply_text(message_text)
            else:
                await message.reply_text("**📭 No files found in Wasabi bucket.**")
        else:
            await message.reply_text(f"**❌ Error accessing Wasabi:** {result['error']}")
    except Exception as e:
        await message.reply_text(f"**❌ Error:** {str(e)}")
