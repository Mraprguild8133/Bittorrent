
If you encounter issues:
• Ensure your magnet link is valid
• Check file size limits
• Try again later if servers are busy
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("status") & filters.private)
async def status_command(client: Client, message: types.Message):
    """Handle /status command"""
    user_id = message.from_user.id
    last_request = user_requests.get(user_id, "Never")
    if last_request != "Never":
        last_request = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_request))
    
    status_text = """
🟢 **Bot Status: Online**

**System Info:**
• Max File Size: 2GB
• Request Cooldown: {cooldown} minutes
• Download Path: Configured

**Your Status:**
• User ID: {user_id}
• Last Request: {last_request}
""".format(
    cooldown=config.REQUEST_COOLDOWN // 60,
    user_id=user_id,
    last_request=last_request
)
    
    await message.reply_text(status_text)

@app.on_message(filters.text & filters.private)
async def handle_text_input(client: Client, message: types.Message):
    """Handle incoming text messages"""
    text = message.text.strip()
    user_id = message.from_user.id

    # Check for magnet link
    if MAGNET_PATTERN.match(text):
        logger.info(f"Magnet link received from user {user_id}")
        
        # Rate limiting check
        if not is_user_allowed(user_id):
            await message.reply_text(
                f"⏳ Please wait {config.REQUEST_COOLDOWN // 60} minutes between requests."
            )
            return
        
        # Process magnet link
        await process_magnet_link(client, message, text)
    else:
        await message.reply_text(
            "❌ That doesn't look like a valid magnet link.\n"
            "Please send a magnet URI that starts with `magnet:?xt=urn...`\n\n"
            "Use /help for more information."
        )

async def process_magnet_link(client: Client, message: types.Message, magnet_uri: str):
    """Process magnet link and handle download/upload"""
    user_id = message.from_user.id
    
    try:
        # Send initial response
        status_msg = await message.reply_text(
            "🔍 **Processing Magnet Link...**\n"
            "• Validating link... ✅\n"
            "• Preparing download... ⏳"
        )
        
        # Update status
        await status_msg.edit_text(
            "📥 **Download Starting...**\n"
            "• Link validated... ✅\n"
            "• Download prepared... ✅\n"
            "• Starting torrent... ⏳"
        )
        
        # Simulate download process
        await asyncio.sleep(3)
        
        # Update to processing
        await status_msg.edit_text(
            "⚙️ **Processing Content...**\n"
            "• Download completed... ✅\n"
            "• Analyzing files... ✅\n"
            "• Preparing upload... ⏳"
        )
        
        # Simulate file processing
        await asyncio.sleep(2)
        
        # Final simulation response
        await status_msg.edit_text(
            "🎉 **Conversion Complete!**\n\n"
            "In a production environment, your video file would now be uploaded.\n\n"
            "**Next Steps for Implementation:**\n"
            "1. Integrate libtorrent for actual torrent downloading\n"
            "2. Implement file type detection\n"
            "3. Add video conversion if needed\n"
            "4. Implement actual file upload with send_video()"
        )
        
        logger.info(f"Successfully processed magnet link for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing magnet link for user {user_id}: {e}")
        await message.reply_text(
            f"❌ **Error Processing Request**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please try again later or contact support if the issue persists."
        )

@app.on_message(filters.document | filters.video)
async def handle_files(client: Client, message: types.Message):
    """Handle files sent to bot"""
    await message.reply_text(
        "📁 **File Received**\n\n"
        "I currently only process magnet links. "
        "Please send a magnet URI to convert torrents to videos.\n\n"
        "Use /help for more information."
    )

if __name__ == "__main__":
    logger.info("Starting Magnet Converter Bot...")
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
