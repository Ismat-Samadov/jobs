#telegram/background_worker.py
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import os
from dotenv import load_dotenv
import requests
import os
from requests.exceptions import RequestException



# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = 'https://job-api-cv1f.onrender.com/data/'


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a job title and I will look for available vacancies.')


async def fetch_jobs(job_title):
    # Setting up the proxy
    proxies = {
        'http': 'http://193.187.175.217:3128',  # Use the same proxy for HTTP
        'https': 'http://193.187.175.217:3128'  # And HTTPS if the proxy supports it
    }
    try:
        response = requests.get(f"{API_BASE_URL}?position={job_title}", proxies=proxies)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f"HTTP Error: {e}")
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


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_jobs))

    application.run_polling()


if __name__ == '__main__':
    main()