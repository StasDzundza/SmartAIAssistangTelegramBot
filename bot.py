import logging
import os
import constants
from OpenAIClients.ChatGPT.chat_gpt_client import ChatGPTClient
from Database.user_db_service import UserDatabaseService
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackContext, Defaults

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_bot.log"),
    ]
)

class ChatGPTBot:
    def __init__(self, token):
        db_encryption_key = os.getenv(constants.TELEGRAM_BOT_DB_ENCRYPTION_KEY_ENV)
        self._db_service = UserDatabaseService(db_encryption_key)
        self._application = ApplicationBuilder().token(token).build()
        self._configure_handlers()

    def __del__(self):
        logging.info("Bot ended polling updates")

    def run(self):
        logging.info("Bot started polling updates")
        self._application.run_polling()

    def _configure_handlers(self):
        self._application.add_handler(CommandHandler("start", self._start_handler))
        self._application.add_handler(CommandHandler("apikey", self._set_api_key_handler))
        self._application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._message_handler))

    def _openai_api_key_provided(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if constants.API_KEY_FIELD not in context.user_data:
            api_key = self._db_service.get_api_key(user_id)
            if api_key:
                context.user_data[constants.API_KEY_FIELD] = api_key
            else:
                return False
        return True

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        reply_message = constants.WELCOME_USER_MESSAGE
        if not self._openai_api_key_provided(update.effective_user.id, context):
            reply_message += f" {constants.API_KEY_REQUEST_MESSAGE}"
        await update.message.reply_text(reply_message)

    async def _set_api_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        api_key = " ".join(context.args)
        if not api_key:
            await update.message.reply_text(f"{constants.SOMETHING_WENT_WRONG_MESSAGE} {constants.API_KEY_REQUEST_MESSAGE}")
        else:
            context.user_data[constants.API_KEY_FIELD] = api_key
            self._db_service.store_api_key(update.effective_user.id, api_key)
            await update.message.reply_text("API key set successfully!")

    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self._openai_api_key_provided(update.effective_user.id, context):
            await update.message.reply_text("You entered: " + update.message.text)
            await update.message.reply_text("You key is: " + self._db_service.get_api_key(update.effective_user.id))
        else:
            await update.message.reply_text(constants.API_KEY_REQUEST_MESSAGE)


if __name__ == "__main__":
    bot_token = os.getenv(constants.TELEGRAM_BOT_TOKEN_ENV)
    bot = ChatGPTBot(bot_token)
    bot.run()
