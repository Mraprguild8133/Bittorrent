# Add these imports at the top
from wasabi_client import wasabi_client
import boto3

# Add new Wasabi functions
async def upload_to_wasabi(file_path, object_name=None):
    """Upload file to Wasabi and return URL"""
    try:
        result = await wasabi_client.upload_file(file_path, object_name)
        return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def download_from_wasabi(object_name, file_path):
    """Download file from Wasabi"""
    try:
        result = await wasabi_client.download_file(object_name, file_path)
        return result
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def send_wasabi_link(bot: Client, m: Message, file_path, caption, name):
    """Upload file to Wasabi and send link to user"""
    try:
        # Upload to Wasabi
        upload_result = await upload_to_wasabi(file_path, name)
        
        if upload_result['success']:
            wasabi_url = upload_result['url']
            file_size = os.path.getsize(file_path)
            human_size = human_readable_size(file_size)
            
            # Create a nice message with the Wasabi link
            message_text = f"""
<b>📁 File Uploaded to Wasabi Successfully!</b>

📝 <b>Name:</b> <code>{name}</code>
💾 <b>Size:</b> {human_size}
🔗 <b>Download Link:</b> <a href="{wasabi_url}">Click Here</a>

{caption}

<i>Link valid for 7 days</i>
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
            await m.reply_text(f"❌ Failed to upload to Wasabi: {upload_result['error']}")
            return False
            
    except Exception as e:
        await m.reply_text(f"❌ Error: {str(e)}")
        return False

# Update the send_doc function to support Wasabi
async def send_doc(bot: Client, m: Message, cc, ka, cc1, prog, count, name, use_wasabi=False):
    if use_wasabi:
        # Upload to Wasabi instead of Telegram
        success = await send_wasabi_link(bot, m, ka, cc1, name)
        if success:
            count += 1
        return success
    else:
        # Original Telegram upload code
        reply = await m.reply_text(f"Uploading » `{name}`")
        time.sleep(1)
        start_time = time.time()
        await m.reply_document(ka, caption=cc1)
        count += 1
        await reply.delete(True)
        time.sleep(1)
        os.remove(ka)
        time.sleep(3)
        return True

# Update the send_vid function to support Wasabi
async def send_vid(bot: Client, m: Message, cc, filename, thumb, name, prog, use_wasabi=False):
    if use_wasabi:
        # Upload to Wasabi instead of Telegram
        success = await send_wasabi_link(bot, m, filename, cc, name)
        if success and os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        return success
    else:
        # Original Telegram upload code
        subprocess.run(f'ffmpeg -i "{filename}" -ss 00:00:12 -vframes 1 "{filename}.jpg"', shell=True)
        await prog.delete(True)
        reply = await m.reply_text(f"**Uploading ...** - `{name}`")
        
        try:
            if thumb == "no":
                thumbnail = f"{filename}.jpg"
            else:
                thumbnail = thumb
        except Exception as e:
            await m.reply_text(str(e))

        dur = int(duration(filename))
        start_time = time.time()

        try:
            await m.reply_video(
                filename, caption=cc, supports_streaming=True,
                height=720, width=1280, thumb=thumbnail, duration=dur,
                progress=progress_bar, progress_args=(reply, start_time)
            )
        except Exception:
            await m.reply_document(
                filename, caption=cc,
                progress=progress_bar, progress_args=(reply, start_time)
            )

        os.remove(filename)
        if os.path.exists(f"{filename}.jpg"):
            os.remove(f"{filename}.jpg")
        await reply.delete(True)
        return True
