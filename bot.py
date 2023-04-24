import logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("telegram_bot.log"),
    ]
)
logger = logging.getLogger(__name__)

import os
import constants
from OpenAIClients.ChatGPT.chat_gpt_client import ChatGPTClient, TextDavinciClient
from OpenAIClients.DALLE.dalle_client import DALLEClient, ImageRequestData, ImageSize
from OpenAIClients.WhisperClient.whisper_client import WhisperClient
from Database.user_db_service import UserDatabaseService
from chat_state import ChatState
from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup, InputMediaPhoto
from telegram.ext import filters, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler

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

        # Media handlers
        self._application.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE, self._media_message_handler))

        # Menu hendlers
        self._application.add_handler(MessageHandler(filters.Regex(r'^Set API Key$'), self._api_key_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Cancel$'), self._cancel_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Help$'), self._help_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Start Chat With Assistant$'), self._start_chat_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^\w* (👨‍⚕️|👨‍🍳|🤖|🏆|👨‍🔬|😂)$'), self._assistant_role_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^End Chat$'), self._end_chat_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Generate Image$'), self._generate_image_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^(1|2|3|4)$'), self._image_count_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^(Small|Medium|Large)$'), self._image_size_handler))
        self._application.add_handler(MessageHandler(filters.Regex(r'^Transcript Media$'), self._transcript_media_handler))

        # Message handlers
        self._application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self._message_handler))

        # Error handlers
        self._application.add_error_handler(self._error_handler)

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
        await self._show_menu(update, keyboard)

    async def _api_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"_api_key_handler called for User {update.effective_user.id}")

        await update.message.reply_text("Please send me your OpenAI API key. Use Help menu button in order to get info about how to get it.")
        await self._show_menu(update, constants.CANCEL_BUTTON)
        self._set_chat_state(ChatState.PROVIDING_API_KEY, context)

    async def _cancel_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_cancel_handler called for User {user_id}")

        self._set_chat_state(ChatState.MAIN, context)
        if self._openai_api_key_provided(user_id, context):
            await self._show_menu(update, constants.MAIN_BUTTONS)
        else:
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)

    async def _start_chat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_start_chat_handler called for User {user_id}")

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)
        else:
            await update.effective_message.reply_text(constants.ASSISTANT_ROLE_REQUEST_MESSAGE)
            await self._show_menu(update, constants.ASSISTANT_ROLES_BUTTONS + constants.CANCEL_BUTTON)
            self._set_chat_state(ChatState.SELECTING_ASSISTANT_ROLE, context)

    async def _assistant_role_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_assistant_role_handler called for User {user_id}")

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)
        else:
            api_key = self._get_openai_api_key(user_id, context)
            chat_gpt_client = ChatGPTClient(api_key, update.effective_message.text)
            context.chat_data[constants.CHAT_CLIENT] = chat_gpt_client
            await update.effective_message.reply_text(constants.CHAT_STARTED_MESSAGE)
            await self._show_menu(update, constants.END_CHAT_BUTTON)
            self._set_chat_state(ChatState.HAVING_CONVERSATION_WITH_ASSISTANT, context)

    async def _end_chat_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"_end_chat_handler called for User {update.effective_user.id}")

        if self._get_chat_state(context) == ChatState.HAVING_CONVERSATION_WITH_ASSISTANT:
            del context.chat_data[constants.CHAT_CLIENT]
            await update.effective_message.reply_text(constants.CHAT_ENDED_MESSAGE)
            await self._show_menu(update, constants.MAIN_BUTTONS)
            self._set_chat_state(ChatState.MAIN, context)
        else:
            await self._message_handler(update, context)

    async def _generate_image_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_generate_image_handler called for User {user_id}")

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)
        else:
            await update.effective_message.reply_text(constants.IMAGE_DESCRIPTION_REQUEST_MESSAGE)
            await self._show_menu(update, constants.CANCEL_BUTTON)
            self._set_chat_state(ChatState.PROVIDING_IMAGES_DESCRIPTION, context)

    async def _image_count_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_image_count_handler called for User {user_id}")

        if self._get_chat_state(context) == ChatState.SELECTING_IMAGES_COUNT:
            count = int(update.effective_message.text)
            context.chat_data[constants.IMAGES_COUNT_KEY] = count

            await update.effective_message.reply_text(constants.IMAGE_SIZE_REQUEST_MESSAGE)
            await self._show_menu(update, constants.IMAGE_SIZE_BUTTONS + constants.CANCEL_BUTTON)
            self._set_chat_state(ChatState.SELECTING_IMAGES_SIZE, context)
        else:
            await self._message_handler(update, context)

    async def _image_size_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_image_size_handler called for User {user_id}")

        if self._get_chat_state(context) == ChatState.SELECTING_IMAGES_SIZE:
            size = update.effective_message.text
            api_key = self._get_openai_api_key(user_id, context)
            description, count = context.chat_data[constants.IMAGES_DESCRIPTION_KEY], context.chat_data[constants.IMAGES_COUNT_KEY]
            images_data = ImageRequestData(description, count, ImageSize[size.upper()])

            await update.effective_message.reply_text(constants.IMAGE_GENERATION_IN_PROGRESS_MESSAGE)
            await self._hide_menu(update)
            image_urls = DALLEClient.generate_images(api_key, images_data)
            if image_urls:
                input_media_photos = [InputMediaPhoto(url) for url in image_urls]
                await context.bot.send_media_group(chat_id=update.effective_chat.id, media=input_media_photos)
                await self._show_menu(update, constants.MAIN_BUTTONS)
                self._set_chat_state(ChatState.MAIN, context)
            else:
                await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE)
                await self._show_menu(update, constants.IMAGE_SIZE_BUTTONS + constants.CANCEL_BUTTON)
        else:
            await self._message_handler(update, context)

    async def _transcript_media_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_transcript_media_handler called for User {user_id}") 

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)
        else:
            await update.effective_message.reply_text(constants.MEDIA_FILE_REQUEST_MESSAGE)
            await self._show_menu(update, constants.CANCEL_BUTTON)
            self._set_chat_state(ChatState.PROVIDING_MEDIA_FILE, context)

    async def _media_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        logger.info(f"_handle_audio_video_message called for User {user_id}")

        if not self._openai_api_key_provided(user_id, context):
            await update.effective_message.reply_text(constants.SOMETHING_WENT_WRONG_MESSAGE + constants.API_KEY_REQUEST_MESSAGE)
            await self._show_menu(update, constants.SET_API_KEY_BUTTON)
        elif self._get_chat_state(context) == ChatState.PROVIDING_MEDIA_FILE:
            # Check if the message contains a voice message, audio, or video file
            if update.effective_message.voice:
                file_id = update.message.voice.file_id
                extension = 'ogg'
            elif update.effective_message.audio:
                file_id = update.message.audio.file_id
                extension = 'mp3'
            elif update.effective_message.video:
                file_id = update.message.video.file_id
                extension = 'mp4'
            elif update.effective_message.video_note:
                file_id = update.message.video_note.file_id
                extension = 'mp4'
            else:
                await update.effective_message.reply_text(constants.MEDIA_FILE_REQUEST_MESSAGE)
                return

            # Download the file
            file = await context.bot.get_file(file_id)
            media_filename = f"user_media_{user_id}.{extension}"
            await file.download_to_drive(media_filename)
            api_key = self._get_openai_api_key(user_id, context)
            await update.effective_message.reply_text(constants.TRANSCRIPTION_IN_PROGRESS_MESSAGE)
            transcription = WhisperClient.transcript_media_file(api_key, f"{media_filename}")
            await update.effective_message.reply_text(transcription)
            self._show_menu(update, constants.MAIN_BUTTONS)

            # Remove temporary files
            os.remove(media_filename)
        else:
            await update.effective_message.reply_text(constants.TRANSCRIPT_MEDIA_HELP)

    async def _message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message = update.message.text
        logger.info(f"User's {user_id} message received: " + message)

        chat_state = self._get_chat_state(context)
        if chat_state == ChatState.MAIN:
            if self._openai_api_key_provided(user_id, context):
                await update.effective_message.reply_text(constants.ASSISTANT_IS_ANSWERING_MESSAGE)
                await self._hide_menu(update)
                api_key = self._get_openai_api_key(user_id, context)
                answer = TextDavinciClient.ask_question(api_key, message)
                await update.effective_message.reply_text(answer)
                await self._show_menu(update, constants.MAIN_BUTTONS)
            else:
                await update.message.reply_text(constants.API_KEY_REQUEST_MESSAGE)
                await self._show_menu(update, constants.SET_API_KEY_BUTTON)

        elif chat_state == ChatState.PROVIDING_API_KEY:
            api_key = message
            context.user_data[constants.API_KEY_FIELD] = api_key
            self._db_service.store_api_key(user_id, api_key)
            await update.message.reply_text(constants.API_KEY_SET_SUCCESSFULLY_MESSAGE)
            await self._show_menu(update, constants.MAIN_BUTTONS)
            self._set_chat_state(ChatState.MAIN, context)

        elif chat_state == ChatState.PROVIDING_IMAGES_DESCRIPTION:
            context.chat_data[constants.IMAGES_DESCRIPTION_KEY] = message
            await update.effective_message.reply_text(constants.IMAGE_COUNT_REQUEST_MESSAGE)
            await self._show_menu(update, constants.IMAGE_COUNT_BUTTONS + constants.CANCEL_BUTTON)
            self._set_chat_state(ChatState.SELECTING_IMAGES_COUNT, context)

        elif chat_state == ChatState.SELECTING_ASSISTANT_ROLE:
            await self._assistant_role_handler(update, context)

        elif chat_state == ChatState.HAVING_CONVERSATION_WITH_ASSISTANT:
            chat_gpt_client = context.chat_data[constants.CHAT_CLIENT]
            await update.effective_message.reply_text(constants.ASSISTANT_IS_ANSWERING_MESSAGE)
            response = chat_gpt_client.ask_chat(update.effective_message.text)
            await update.effective_message.reply_text(response)

        else:
            await update.effective_message.reply_text(constants.BOT_MENU_HELP_MESSAGE)

    async def _help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"_help_handler called for User {update.effective_user.id}")

        await update.message.reply_text(constants.HELP_MESSAGE, parse_mode="HTML")

    async def _error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error("Update '%s' caused error '%s'", update, context.error)

        if update and update.effective_message:
            await update.effective_message.reply_text(constants.TRY_AGAIN_MESSAGE)

    async def _show_menu(self, update: Update, keyboard: list):
        logger.info(f"Showing keyboard to user {update.effective_user.id}")

        reply_markup = ReplyKeyboardMarkup(keyboard + constants.HELP_BUTTON, resize_keyboard=True)
        await update.effective_message.reply_text("Bot menu has been updated.", reply_markup=reply_markup)

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
