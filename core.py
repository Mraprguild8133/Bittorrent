# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import time
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import tgcrypto
import subprocess
import concurrent.futures

from utils import progress_bar, hrb

from pyrogram import Client, filters
from pyrogram.types import Message

# Initialize failed_counter
failed_counter = 0

def duration(filename):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return float(result.stdout)
    
def exec(cmd):
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = process.stdout.decode()
    print(output)
    return output

def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        fut = executor.map(exec, cmds)

async def aio(url, name):
    k = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(k, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return k

async def download(url, name):
    ka = f'{name}.pdf'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                f = await aiofiles.open(ka, mode='wb')
                await f.write(await resp.read())
                await f.close()
    return ka

def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 2)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info

def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 3)
            try:
                if "RESOLUTION" not in i[2] and i[2] not in temp and "audio" not in i[2]:
                    temp.append(i[2])
                    new_info.update({f'{i[2]}': f'{i[0]}'})
            except:
                pass
    return new_info

async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    print(f'[{cmd!r} exited with {proc.returncode}]')
    if proc.returncode == 1:
        return False
    if stdout:
        return f'[stdout]\n{stdout.decode()}'
    if stderr:
        return f'[stderr]\n{stderr.decode()}'

def old_download(url, file_name, chunk_size=1024 * 10):
    if os.path.exists(file_name):
        os.remove(file_name)
    r = requests.get(url, allow_redirects=True, stream=True)
    with open(file_name, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:
                fd.write(chunk)
    return file_name

def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"

def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"

async def download_video(url, cmd, name):
    global failed_counter
    download_cmd = f'{cmd} -R 25 --fragment-retries 25 --external-downloader aria2c --downloader-args "aria2c: -x 16 -j 32"'
    print(download_cmd)
    logging.info(download_cmd)
    
    # Use asyncio for subprocess
    process = await asyncio.create_subprocess_shell(
        download_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.wait()
    
    if "visionias" in cmd and process.returncode != 0 and failed_counter <= 10:
        failed_counter += 1
        await asyncio.sleep(5)
        return await download_video(url, cmd, name)
    
    failed_counter = 0
    
    # Check for existing files with different extensions
    possible_extensions = ['', '.webm', '.mkv', '.mp4', '.mp4.webm']
    for ext in possible_extensions:
        filename = f"{name}{ext}" if ext else name
        if os.path.isfile(filename):
            return filename
    
    # If no file found, return the original name
    return name

# Wasabi-related functions (synchronous version)
def upload_to_wasabi_sync(file_path, object_name=None):
    """Upload file to Wasabi synchronously"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        from vars import WASABI_ACCESS_KEY, WASABI_SECRET_KEY, WASABI_BUCKET, WASABI_REGION
        
        if object_name is None:
            object_name = os.path.basename(file_path)
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=WASABI_ACCESS_KEY,
            aws_secret_access_key=WASABI_SECRET_KEY,
            endpoint_url=f"https://s3.{WASABI_REGION}.wasabisys.com",
            region_name=WASABI_REGION
        )
        
        # Upload the file
        s3_client.upload_file(file_path, WASABI_BUCKET, object_name)
        
        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': WASABI_BUCKET, 'Key': object_name},
            ExpiresIn=604800  # 7 days
        )
        
        file_size = os.path.getsize(file_path)
        human_size = human_readable_size(file_size)
        
        logging.info(f"File uploaded to Wasabi: {object_name}")
        return {
            'success': True,
            'url': url,
            'object_name': object_name,
            'file_size': human_size
        }
        
    except Exception as e:
        logging.error(f"Wasabi upload error: {str(e)}")
        return {'success': False, 'error': str(e)}

async def send_wasabi_link(bot: Client, m: Message, file_path, caption, name):
    """Upload file to Wasabi and send link to user"""
    try:
        # Run Wasabi upload in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        upload_result = await loop.run_in_executor(
            None, 
            upload_to_wasabi_sync, 
            file_path, 
            name
        )
        
        if upload_result['success']:
            wasabi_url = upload_result['url']
            file_size = upload_result['file_size']
            
            # Create message with Wasabi link
            message_text = f"""
<b>📁 File Uploaded to Wasabi Successfully!</b>

📝 <b>Name:</b> <code>{name}</code>
💾 <b>Size:</b> {file_size}
🔗 <b>Download Link:</b> <a href="{wasabi_url}">Click Here</a>

{caption}

<i>✨ Link valid for 7 days</i>
"""
            # Send message with download link
            await m.reply_text(
                message_text,
                disable_web_page_preview=False
            )
            
            # Clean up local file
            if os.path.exists(file_path):
                os.remove(file_path)
                
            return True
        else:
            await m.reply_text(f"❌ Failed to upload to Wasabi: {upload_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        await m.reply_text(f"❌ Error uploading to Wasabi: {str(e)}")
        return False

async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name, use_wasabi=False):
    """Send document to Telegram or Wasabi"""
    if use_wasabi:
        # Upload to Wasabi instead of Telegram
        success = await send_wasabi_link(bot, m, ka, cc1, name)
        if success:
            return True, count + 1
        return False, count
    else:
        # Original Telegram upload code
        reply = await m.reply_text(f"Uploading to Telegram » `{name}`")
        start_time = time.time()
        try:
            await m.reply_document(ka, caption=cc1)
            await reply.delete()
            if os.path.exists(ka):
                os.remove(ka)
            return True, count + 1
        except Exception as e:
            await reply.edit(f"❌ Upload failed: {str(e)}")
            return False, count

async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog, use_wasabi=False):
    """Send video to Telegram or Wasabi"""
    if use_wasabi:
        # Upload to Wasabi instead of Telegram
        success = await send_wasabi_link(bot, m, filename, cc, name)
        # Clean up thumbnail if exists
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        return success
    else:
        # Original Telegram upload code
        # Create thumbnail
        thumbnail_cmd = f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 "{filename}.jpg"'
        process = await asyncio.create_subprocess_shell(thumbnail_cmd)
        await process.wait()
        
        await prog.delete()
        reply = await m.reply_text(f"**Uploading to Telegram...** - `{name}`")
        
        try:
            if thumb == "no":
                thumbnail = f"{filename}.jpg"
            else:
                thumbnail = thumb
        except Exception as e:
            await m.reply_text(str(e))
            thumbnail = f"{filename}.jpg"

        dur = int(duration(filename))
        start_time = time.time()

        try:
            await m.reply_video(
                filename, 
                caption=cc, 
                supports_streaming=True,
                height=720, 
                width=1280, 
                thumb=thumbnail, 
                duration=dur,
                progress=progress_bar,
                progress_args=(reply, start_time)
            )
        except Exception as e:
            logging.error(f"Video upload failed, trying as document: {e}")
            await m.reply_document(
                filename, 
                caption=cc,
                progress=progress_bar,
                progress_args=(reply, start_time)
            )

        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        await reply.delete()
        return True
