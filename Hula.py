import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pytube import YouTube
import instaloader
import requests

# Bot Token from @BotFathe
BOT_TOKEN = "7704220520:AAEI_ouYgKUdt52-ec9JJDjdo44pme781Ls"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🔗 Send me an Instagram or YouTube link to download the video!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    chat_id = update.message.chat_id

    if "instagram.com" in message_text:
        await download_instagram_video(update, message_text)
    elif "youtube.com" in message_text or "youtu.be" in message_text:
        await download_youtube_video(update, message_text)
    else:
        await update.message.reply_text("❌ Invalid link! Send a valid Instagram or YouTube URL.")

async def download_instagram_video(update: Update, url: str):
    try:
        L = instaloader.Instaloader()
        post = instaloader.Post.from_shortcode(L.context, url.split("/")[-2])
        video_url = post.video_url
        
        if video_url:
            response = requests.get(video_url, stream=True)
            with open("instagram_video.mp4", "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            
            await update.message.reply_video(video=open("instagram_video.mp4", "rb"))
            os.remove("instagram_video.mp4")
        else:
            await update.message.reply_text("❌ No video found in this Instagram post.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def download_youtube_video(update: Update, url: str):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(file_extension="mp4", progressive=True).first()
        if stream:
            stream.download(filename="youtube_video.mp4")
            await update.message.reply_video(video=open("youtube_video.mp4", "rb"))
            os.remove("youtube_video.mp4")
        else:
            await update.message.reply_text("❌ No downloadable video found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))

    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
