import os
import logging
import random

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

chat_id = 117288777
df = pd.read_csv("telegram_quizzes.csv")
df["is_published"] = False


async def quiz(context: ContextTypes.DEFAULT_TYPE) -> None:
    not_published_df = df[df["is_published"] == False]
    rand_question_loc = random.randint(0, len(not_published_df) - 1)
    question = df.loc[rand_question_loc].to_dict()
    df.loc[df.id == question.get("id"), "is_published"] = True
    options = question.get("choices").split("|")
    options = [op.strip() for op in options]
    correct_choice_index = options.index(question.get("correct_choice"))
    await context.bot.send_poll(
        chat_id=chat_id,
        question=question.get("question_text"),
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_choice_index,
        explanation=question.get("tip_short"),
    )


async def create_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.job_queue.run_custom(
        callback=quiz,
        job_kwargs={
            "trigger": "cron",
            "day": "*",
            "hour": "8-22",
            "minute": "1",
            "second": "1",
            "month": "*",
        },
    )


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv("TOKEN")).build()
    application.add_handler(CommandHandler("quiz", create_quiz))
    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
