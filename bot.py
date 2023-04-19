import logging
import os
import constants
from OpenAIClients.ChatGPT.chat_gpt_client import ChatGPTClient
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

    def _openai_api_key_provided(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        return "api_key" in context.user_data

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome to the ChatGPT Telegram bot! Set your OpenAI API key with /apikey YOUR_API_KEY command.")

    async def _set_api_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        api_key = " ".join(context.args)
        if not api_key:
            await update.message.reply_text("Please provide an API key: /apikey YOUR_API_KEY")
        else:
            context.user_data["api_key"] = api_key
            await update.message.reply_text("API key set successfully!")

    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if self._openai_api_key_provided(context):
            await update.message.reply_text("You entered: " + update.message.text)
        else:
            await update.message.reply_text("Please set your OpenAI API key first using /apikey command.")


if __name__ == "__main__":
    bot_token = os.getenv(constants.TELEGRAM_BOT_TOKEN_ENV)
    bot = ChatGPTBot(bot_token)
    bot.run()