import os
import logging
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
import requests

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_BASE_URL = os.getenv('API_BASE_URL')

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\! Send me a job title to search for vacancies',
        reply_markup=ForceReply(selective=True),
    )

def search_jobs(update: Update, context: CallbackContext) -> None:
    """Fetch job data from API and send it back to the user."""
    job_title = update.message.text
    try:
        response = requests.get(f"{API_BASE_URL}/jobs", params={"title": job_title})
        jobs = response.json()
        for job in jobs:
            message = f"{job['company']} - {job['vacancy']}\nApply here: {job['apply_link']}"
            update.message.reply_text(message)
    except Exception as e:
        update.message.reply_text('Failed to fetch job data.')
        logger.error(f"Error fetching jobs: {e}")

def main() -> None:
    """Start the bot."""
    updater = Updater(TELEGRAM_BOT_TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(filters.text & ~filters.command, search_jobs))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
