from telegram import KeyboardButton

# environment variables
TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_BOT_DB_ENCRYPTION_KEY_ENV = "TELEGRAM_BOT_DB_ENCRYPTION_KEY"

# user and chat data field keys
API_KEY_FIELD = "api_key"
CHAT_STATE_FIELD = "chat_state"

# predefinded messages
SOMETHING_WENT_WRONG_MESSAGE = "Something went wrong."
API_KEY_REQUEST_MESSAGE = "Please set your OpenAI API key via bot menu in order to use bot functionality."
API_KEY_SET_SUCCESSFULLY_MESSAGE = "API key set successfully! Now you can use bot functionality."
WELCOME_USER_MESSAGE = "Welcome to the ChatGPT Telegram bot!"
BOT_MENU_HELP_MESSAGE = "Go to bot menu in order to use bot functionality. For more details see Help section."

# keyboards
SET_API_KEY_BUTTON = [[KeyboardButton("Set API Key")]]
CANCEL_BUTTON = [[KeyboardButton("Cancel")]]
END_CHAT_BUTTON = [[KeyboardButton("End Chat")]]
HELP_BUTTON = [[KeyboardButton("Help")]]
MAIN_BUTTONS = [
    [KeyboardButton("Start Chat")],
    [KeyboardButton("Generate Image")]
] + SET_API_KEY_BUTTON