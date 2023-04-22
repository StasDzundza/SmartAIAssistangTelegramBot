import logging
import os
import constants
from OpenAIClients.ChatGPT.chat_gpt_client import ChatGPTClient
from OpenAIClients.DALLE.dalle_client import DALLEClient
from Database.user_db_service import UserDatabaseService
from chat_state import ChatState
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import filters, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackContext, Defaults

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_bot.log"),
    ]
)
logger = logging.getLogger(__name__)

class ChatGPTBot:
    def __init__(self, token):
        db_encryption_key = os.getenv(constants.TELEGRAM_BOT_DB_ENCRYPTION_KEY_ENV)
        if not db_encryption_key:
            logger.error("TELEGRAM_BOT_DB_ENCRYPTION_KEY_ENV was not found in environment variables")
        self._db_service = UserDatabaseService(db_encryption_key)
        self._application = ApplicationBuilder().token(token).build()
        self._configure_handlers()

    def __del__(self):
        logger.info("Bot ended polling updates")

    def run(self):
        logger.info("Bot started polling updates")
        self._application.run_polling()

    def _configure_handlers(self):
        # Command handlers
        self._application.add_handler(CommandHandler("start", self._start_handler))

        # Menu hendlers
        self._application.add_handler(MessageHandler(filters.Regex(r'^Set API Key$'), self._api_key_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Cancel$'), self._cancel_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Help$'), self._help_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Generate Image$'), self._generate_image_handler))

        # Message handlers
        self._application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._message_handler))

    def _openai_api_key_provided(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if constants.API_KEY_FIELD not in context.user_data:
            api_key = self._db_service.get_api_key(user_id)
            if api_key:
                context.user_data[constants.API_KEY_FIELD] = api_key
            else:
                return False
        return True

    def _get_openai_api_key(self, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> str | None:
        return context.user_data[constants.API_KEY_FIELD].strip() if self._openai_api_key_provided(user_id, context) else None

    async def _start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"_start_handler called for User {update.effective_user.id}")

        reply_message = constants.WELCOME_USER_MESSAGE
        keyboard = constants.MAIN_BUTTONS
        if not self._openai_api_key_provided(update.effective_user.id, context):
            reply_message += f" {constants.API_KEY_REQUEST_MESSAGE}"
            keyboard = constants.SET_API_KEY_BUTTON
        await update.message.reply_text(reply_message)
        await self._show_menu(update, context, keyboard)

    async def _api_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"_api_key_handler called for User {update.effective_user.id}")

        await update.message.reply_text("Please send me your OpenAI API key. Use Help menu button in order to get info about how to get it.")
        await self._show_menu(update, context, constants.CANCEL_BUTTON)
        self._set_chat_state(ChatState.PROVIDING_API_KEY, context)

    async def _cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_cancel_handler called for User {user_id}")

        self._set_chat_state(ChatState.MAIN, context)
        if self._openai_api_key_provided(user_id, context):
            await self._show_menu(update, context, constants.MAIN_BUTTONS)
        else:
            await self._show_menu(update, context, constants.SET_API_KEY_BUTTON)

    async def _generate_image_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_generate_image_handler called for User {user_id}")

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
        else:
            await update.effective_message.reply_text(constants.IMAGE_DESCRIPTION_REQUEST_MESSAGE)
            self._set_chat_state(ChatState.PROVIDING_IMAGES_DESCRIPTION, context)
    
    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message = update.message.text
        logger.info(f"User's {user_id} message received: " + message)

        chat_state = self._get_chat_state(context)
        if chat_state == ChatState.MAIN:
            if self._openai_api_key_provided(user_id, context):
                await update.message.reply_text(constants.BOT_MENU_HELP_MESSAGE)
                await self._show_menu(update, context, constants.MAIN_BUTTONS)
            else:
                await update.message.reply_text(constants.API_KEY_REQUEST_MESSAGE)
                await self._show_menu(update, context, constants.SET_API_KEY_BUTTON)
    
        elif chat_state == ChatState.PROVIDING_API_KEY:
            api_key = message
            context.user_data[constants.API_KEY_FIELD] = api_key
            self._db_service.store_api_key(user_id, api_key)
            await update.message.reply_text(constants.API_KEY_SET_SUCCESSFULLY_MESSAGE)
            await self._show_menu(update, context, constants.MAIN_BUTTONS)
            self._set_chat_state(ChatState.MAIN, context)

        elif chat_state == ChatState.PROVIDING_IMAGES_DESCRIPTION:
            description = message
            api_key = self._get_openai_api_key(user_id, context)
            dalle_client = DALLEClient(api_key)

            await update.effective_message.reply_text(constants.IMAGE_GENERATION_IN_PROGRESS_MESSAGE)
            images = dalle_client.generate_images(description)
            if images:
                await update.effective_message.reply_photo(images[0])
            else:
                await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE)
            self._set_chat_state(ChatState.MAIN, context)

        elif chat_state == ChatState.PROVIDING_IMAGES_COUNT:
            pass

    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Help currently is not available.")

    async def _show_menu(self, update: Update, context: CallbackContext, keyboard: list):
        # keyboard = [
        #     [InlineKeyboardButton("Provide API Key", callback_data="provide_api_key")],
        # ]

        # if self._openai_api_key_provided(user_id, context):
        #     keyboard.extend([
        #         [InlineKeyboardButton("Begin Chat", callback_data="begin_chat"),
        #             InlineKeyboardButton("End Chat", callback_data="end_chat")],
        #         [InlineKeyboardButton("Generate Image", callback_data="generate_image")],
        #     ])

        # reply_markup = InlineKeyboardMarkup(keyboard)

        # if "keyboard_message" in context.chat_data:
        #     await context.chat_data["keyboard_message"].delete()

        # message = await update.effective_message.reply_text("Choose an option:", reply_markup=reply_markup)
        # context.chat_data["keyboard_message"] = message

        logger.info(f"Showing keyboard to user {update.effective_user.id}")

        keyboard += constants.HELP_BUTTON
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.effective_message.reply_text("Here is the bot menu:", reply_markup=reply_markup)

    async def _hide_menu(self, update: Update):
        reply_markup = ReplyKeyboardRemove()
        await update.effective_message.reply_text("Bot menu temporary hidden.", reply_markup=reply_markup)

    def _set_chat_state(self, state: ChatState, context: ContextTypes.DEFAULT_TYPE):
        context.chat_data[constants.CHAT_STATE_FIELD] = state

    def _get_chat_state(self, context: ContextTypes.DEFAULT_TYPE) -> ChatState:
        if constants.CHAT_STATE_FIELD not in context.chat_data:
            context.chat_data[constants.CHAT_STATE_FIELD] = ChatState.MAIN
        return context.chat_data[constants.CHAT_STATE_FIELD]


def main():
    bot_token = os.getenv(constants.TELEGRAM_BOT_TOKEN_ENV)
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN_ENV was not found in environment variables")
        return
    bot = ChatGPTBot(bot_token)
    bot.run()

if __name__ == "__main__":
    main()
