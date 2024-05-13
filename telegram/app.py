from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os
from dotenv import load_dotenv
import threading
import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = 'https://job-api-cv1f.onrender.com/data/'

# Initialize Flask
app = Flask(__name__)

@app.route('/')
def home():
    """ Provide a simple route on the web server to confirm it's running. """
    return "Bot is running"

async def start(update: Update, context: CallbackContext) -> None:
    """ Respond to the /start command with a welcome message. """
    await update.message.reply_text('Hi! Send me a job title and I will look for available vacancies.')

# async def fetch_jobs(job_title):
#     """ Fetch job listings from an external API asynchronously using aiohttp. """
#     async with aiohttp.ClientSession() as session:
#         async with session.get(f"{API_BASE_URL}?position={job_title}") as response:
#             if response.status == 200:
#                 return await response.json()
#             else:
#                 print(f"HTTP Error: {response.status}")
#                 return []

async def fetch_jobs(job_title):
    url = f"{API_BASE_URL}?position={job_title}"
    logging.info(f"Fetching jobs from URL: {url}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logging.info(f"Response Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                logging.info(f"Data received: {data}")
                return data
            else:
                logging.info(f"Failed to fetch data: {response.status}")
                return []



async def reply_jobs(update: Update, context: CallbackContext) -> None:
    """ Reply to user messages with job listings. """
    user_text = update.message.text
    jobs = await fetch_jobs(user_text)
    if jobs:
        for job in jobs[:5]:  # Limiting to the first 5 jobs for simplicity.
            message = f"{job['company']} - {job['vacancy']}\nApply here: {job['apply_link']}"
            await update.message.reply_text(message)
    else:
        await update.message.reply_text("No jobs found for your query.")

def run_bot():
    """ Set up a new event loop and run the Telegram bot. """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_jobs))
    application.run_polling()

def run_web_server():
    """ Run the Flask web server on the designated port. """
    port = int(os.environ.get('PORT', 5000))  # Use PORT environment variable or default to 5000.
    app.run(host='0.0.0.0', port=port, use_reloader=False)

if __name__ == '__main__':
    # Run the bot and the web server in parallel using daemon threads.
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=run_web_server, daemon=True).start()
