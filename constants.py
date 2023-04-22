from telegram import KeyboardButton

# environment variables
TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
TELEGRAM_BOT_DB_ENCRYPTION_KEY_ENV = "TELEGRAM_BOT_DB_ENCRYPTION_KEY"

# User and chat data field keys
API_KEY_FIELD = "api_key"
CHAT_STATE_FIELD = "chat_state"
IMAGES_DESCRIPTION_KEY = "img_description"
IMAGES_COUNT_KEY = "img_count"

# Predefinded messages
BOT_MENU_HELP_MESSAGE = "For more details see Help section."
WELCOME_USER_MESSAGE = "Welcome to the ChatGPT Telegram bot! Ask me something or go to menu in order to use extended list of features. " + BOT_MENU_HELP_MESSAGE
# API Key
API_KEY_REQUEST_MESSAGE = "Please provide me with your OpenAI API key via bot menu in order to use bot functionality."
API_KEY_SET_SUCCESSFULLY_MESSAGE = "API key set successfully! Now you can use bot functionality."
# Conversation with Chat GPT
ASSISTANT_ROLE_REQUEST_MESSAGE = "Please select role of your assistant from the given list or send me your option."
ASSISTANT_IS_ANSWERING_MESSAGE = "Assistant is answering on your message. Please wait..."
CHAT_STARTED_MESSAGE = "Chat with your assistant has been started. Feel free to ask something :)"
CHAT_ENDED_MESSAGE = "Chat with your assistant has been ended. It was a pleasure to communicate with you :)"
# Image Generation
IMAGE_DESCRIPTION_REQUEST_MESSAGE = "Please provide description of image which you want to generate."
IMAGE_COUNT_REQUEST_MESSAGE = "How much images do you want to generate?"
IMAGE_SIZE_REQUEST_MESSAGE = "Please select images size."
IMAGE_GENERATION_IN_PROGRESS_MESSAGE = "Image is generating at the moment. Please wait..."
IMAGE_SIZE_FORMAT_IS_INCORRECT_MESSAGE = "Entered image size format is incorrect."
# Errors
SOMETHING_WENT_WRONG_MESSAGE = "Something went wrong."
TRY_AGAIN_MESSAGE = "An error occurred. Please try again."

# Keyboards
SET_API_KEY_BUTTON = [[KeyboardButton("Set API Key")]]
CANCEL_BUTTON = [[KeyboardButton("Cancel")]]
END_CHAT_BUTTON = [[KeyboardButton("End Chat")]]
HELP_BUTTON = [[KeyboardButton("Help")]]
MAIN_BUTTONS = [
    [KeyboardButton("Start Chat With Assistant")],
    [KeyboardButton("Generate Image")],
    [KeyboardButton("Transcript Audio")]
] + SET_API_KEY_BUTTON
IMAGE_COUNT_BUTTONS = [
    [KeyboardButton("1"), KeyboardButton("2")],
    [KeyboardButton("3"), KeyboardButton("4")]
]
IMAGE_SIZE_BUTTONS = [
    [KeyboardButton("Small")],
    [KeyboardButton("Medium")],
    [KeyboardButton("Large")]
]
ASSISTANT_ROLES_BUTTONS = [
    [KeyboardButton("Chatbot")],
    [KeyboardButton("Cook")],
    [KeyboardButton("Doctor")],
    [KeyboardButton("Professional sportsmen")],
    [KeyboardButton("Scientist")],
    [KeyboardButton("Funny guy")]
]
