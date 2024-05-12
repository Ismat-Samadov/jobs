from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from telegram.ext import filters
import requests
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Ensure you've set this environment variable
API_BASE_URL = 'https://job-api-cv1f.onrender.com/data/'

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! Send me a job title and I will look for available vacancies.')

def fetch_jobs(job_title):
    """Fetches jobs from the job API."""
    try:
        response = requests.get(f"{API_BASE_URL}?position={job_title}")
        response.raise_for_status()  # Raises an exception for HTTP errors
        return response.json()
    except requests.RequestException as e:
        print(f"HTTP Error: {e}")
        return []

def reply_jobs(update: Update, context: CallbackContext) -> None:
    """Replies with job data based on user input."""
    user_text = update.message.text
    jobs = fetch_jobs(user_text)
    if jobs:
        for job in jobs[:5]:  # Limiting the number of jobs sent to 5
            message = f"{job['company']} - {job['vacancy']}\nApply here: {job['apply_link']}"
            update.message.reply_text(message)
    else:
        update.message.reply_text("No jobs found for your query.")

def main():
    """Starts the bot."""
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(filters.text & ~filters.command, reply_jobs))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
