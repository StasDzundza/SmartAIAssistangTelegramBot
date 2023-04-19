import logging
import os
import constants
from OpenAIClients.ChatGPT.chat_gpt_client import ChatGPTClient
from telegram import Update
from telegram.ext import filters, Updater, CommandHandler, MessageHandler, CallbackContext, Defaults

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
        self.updater = Updater(token)
        self.configure_handlers()

    def configure_handlers(self):
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", self.start_handler))
        dispatcher.add_handler(CommandHandler("apikey", self.set_api_key_handler))
        dispatcher.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.message_handler))
        
    def start_handler(self, update: Update, context: CallbackContext):
        update.message.reply_text("Welcome to the ChatGPT Telegram bot! Set your OpenAI API key with /apikey YOUR_API_KEY command.")

    def set_api_key_handler(self, update: Update, context: CallbackContext):
        api_key = " ".join(context.args)
        if not api_key:
            update.message.reply_text("Please provide an API key: /apikey YOUR_API_KEY")
        else:
            context.user_data["api_key"] = api_key
            update.message.reply_text("API key set successfully!")

    def message_handler(self, update: Update, context: CallbackContext):
        api_key = context.user_data.get("api_key")
        if not api_key:
            update.message.reply_text("Please set your OpenAI API key first using /apikey command.")
            return
        update.message.reply_text("You entered: " + update.message.text)

    def run(self):
        self.updater.start_polling()

    def stop(self):
        self.updater.stop()


if __name__ == "__main__":
    token = os.getenv(constants.TELEGRAM_BOT_API_KEY_ENV)
    bot = ChatGPTBot(token)
    bot.run()