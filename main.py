import os
import pytz
import logging
import random
from datetime import tzinfo, datetime

from telegram import (
    KeyboardButton,
    KeyboardButtonPollType,
    Poll,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PollAnswerHandler,
    PollHandler,
    filters,
    Defaults,
)
import pandas as pd

from dotenv import load_dotenv


load_dotenv()

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

df = pd.read_csv("telegram_quizzes.csv")
df["is_published"] = False


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def quiz(context: ContextTypes.DEFAULT_TYPE) -> None:
    not_published_df = df[df["is_published"] == False]
    rand_question_loc = random.randint(0, len(not_published_df) - 1)
    question = df.loc[rand_question_loc].to_dict()
    df.loc[df.id == question.get("id"), "is_published"] = True
    options = question.get("choices").split("|")
    options = [op.strip() for op in options]
    correct_choice_index = options.index(question.get("correct_choice"))
    await context.bot.send_poll(
        chat_id=os.getenv("CHAT_ID"),
        question=question.get("question_text"),
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_choice_index,
        explanation=question.get("tip_short"),
    )


async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.chat_id
    text = "Quiz successfully started"
    job_removed = remove_job_if_exists(str(chat_id), context)
    if job_removed:
        text += " and the old one removed"
    context.job_queue.run_custom(
        callback=quiz,
        job_kwargs={
            "trigger": "cron",
            "day": "*",
            "hour": "6-23",
            "minute": "59",
            "second": "1",
            "month": "*",
            "timezone": pytz.timezone("Asia/Tehran"),
        },
    )
    await update.effective_message.reply_text(text)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Quiz successfully cancelled!" if job_removed else "You have no active Quiz."
    await update.message.reply_text(text)


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv("TOKEN")).build()
    application.add_handler(CommandHandler("quiz", create_quiz))
    application.add_handler(CommandHandler("stop", stop))
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
