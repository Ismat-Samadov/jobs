# from telegram import Update, Bot
# from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
# import os
# from dotenv import load_dotenv
# import requests
#
# # Load environment variables
# load_dotenv()
#
# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# API_BASE_URL = 'https://job-api-cv1f.onrender.com/data/'
#
#
# async def start(update: Update, context: CallbackContext) -> None:
#     await update.message.reply_text('Hi! Send me a job title and I will look for available vacancies.')
#
#
# async def fetch_jobs(job_title):
#     try:
#         response = requests.get(f"{API_BASE_URL}?position={job_title}")
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         print(f"HTTP Error: {e}")
#         return []
#
#
# async def reply_jobs(update: Update, context: CallbackContext) -> None:
#     user_text = update.message.text
#     jobs = await fetch_jobs(user_text)
#     if jobs:
#         for job in jobs[:5]:
#             message = f"{job['company']} - {job['vacancy']}\nApply here: {job['apply_link']}"
#             await update.message.reply_text(message)
#     else:
#         await update.message.reply_text("No jobs found for your query.")
#
#
# def main():
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
#
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_jobs))
#
#     application.run_polling()
#
#
# if __name__ == '__main__':
#     main()
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os
from dotenv import load_dotenv
import threading
import asyncio
import aiohttp

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = 'https://job-api-cv1f.onrender.com/data/'

# Initialize Flask
app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is running"


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a job title and I will look for available vacancies.')


async def fetch_jobs(job_title):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE_URL}?position={job_title}") as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f"HTTP Error: {response.status}")
                return []


async def reply_jobs(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text
    jobs = await fetch_jobs(user_text)
    if jobs:
        for job in jobs[:5]:
            message = f"{job['company']} - {job['vacancy']}\nApply here: {job['apply_link']}"
            await update.message.reply_text(message)
    else:
        await update.message.reply_text("No jobs found for your query.")


def run_bot():
    # Set up a new event loop for the thread running the bot
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_jobs))

    # Run the bot with the new event loop
    application.run_polling()


def run_web_server():
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)


if __name__ == '__main__':
    # Run the bot and the web server in parallel
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=run_web_server, daemon=True).start()
