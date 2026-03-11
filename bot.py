import os
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USERS = {
    int(x) for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()
}
WORK_DIR = os.environ.get("WORK_DIR", "/workspace")
MAX_MSG = 4096


async def run_claude(prompt: str) -> str:
    """Run claude -p with the given prompt and return output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "-p",
            "--dangerously-skip-permissions",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=WORK_DIR,
        )
        stdout, stderr = await proc.communicate()
    except FileNotFoundError:
        return "Error: claude CLI not found."

    output = stdout.decode().strip()
    if not output and stderr:
        output = stderr.decode().strip()
    return output or "(empty response)"


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if ALLOWED_USERS and update.effective_user.id not in ALLOWED_USERS:
        logger.warning("Unauthorized user: %s", update.effective_user.id)
        return

    text = update.message.text
    if not text:
        return

    await context.bot.send_chat_action(update.effective_chat.id, "typing")
    response = await run_claude(text)

    for i in range(0, len(response), MAX_MSG):
        await update.message.reply_text(response[i : i + MAX_MSG])


async def cmd_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        "Claude Code proxy ready. Send any message."
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
