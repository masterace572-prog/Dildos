import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters
)
import pyfiglet
from io import StringIO

# Store user data temporarily
user_data = {}

# Define conversation states
(
    WAITING_INPUT_FILE,
    WAITING_OUTPUT_NAME,
    SELECTING_LIBRARY,
    WAITING_CUSTOM_LIB,
    SELECTING_PATCH_SEQUENCE,
    WAITING_CUSTOM_SEQ,
) = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    banner = pyfiglet.figlet_format("Patch Processor")
    welcome_message = f"```\n{banner}\n```Welcome to Patch Processor Bot!\n\nSend /process to start creating patch commands."
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the patch processing conversation."""
    chat_id = update.effective_chat.id
    user_data[chat_id] = {}
    
    await update.message.reply_text("Please send me your input file (text file with memory addresses):")
    return WAITING_INPUT_FILE

async def handle_input_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the input file sent by the user."""
    chat_id = update.effective_chat.id
    
    if not update.message.document:
        await update.message.reply_text("Please send a text file as a document.")
        return WAITING_INPUT_FILE
    
    # Store file info temporarily
    file = await update.message.document.get_file()
    user_data[chat_id]['input_file'] = file
    
    # Ask for output file name
    await update.message.reply_text("Great! Now please enter the name for the output file (e.g., output.txt):")
    return WAITING_OUTPUT_NAME

async def handle_output_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the output file name entered by the user."""
    chat_id = update.effective_chat.id
    output_name = update.message.text.strip()
    
    if not output_name.endswith('.txt'):
        output_name += '.txt'
    
    user_data[chat_id]['output_file'] = output_name
    
    # Ask to select library
    keyboard = [
        [InlineKeyboardButton("libanogs.so", callback_data='libanogs.so')],
        [InlineKeyboardButton("libUE4.so", callback_data='libUE4.so')],
        [InlineKeyboardButton("Custom library", callback_data='custom_lib')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text('Select the library name:', reply_markup=reply_markup)
    return SELECTING_LIBRARY

async def select_library(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle library selection."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    
    if query.data == 'custom_lib':
        await query.edit_message_text("Please enter your custom library name (e.g., libcustom.so):")
        return WAITING_CUSTOM_LIB
    else:
        user_data[chat_id]['lib_name'] = query.data
        # Proceed to patch sequence selection
        return await select_patch_sequence_menu(query.message)

async def handle_custom_lib(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom library name input."""
    chat_id = update.effective_chat.id
    lib_name = update.message.text.strip()
    
    if not lib_name.endswith('.so'):
        lib_name += '.so'
    
    user_data[chat_id]['lib_name'] = lib_name
    return await select_patch_sequence_menu(update.message)

async def select_patch_sequence_menu(message) -> int:
    """Show patch sequence selection menu."""
    keyboard = [
        [InlineKeyboardButton("C0 03 5F D6", callback_data='C0 03 5F D6')],
        [InlineKeyboardButton("00 00 80 D2 C0 03 5F D6", callback_data='00 00 80 D2 C0 03 5F D6')],
        [InlineKeyboardButton("Custom sequence", callback_data='custom_seq')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text('Select the patch sequence:', reply_markup=reply_markup)
    return SELECTING_PATCH_SEQUENCE

async def select_patch_sequence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle patch sequence selection."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat.id
    
    if query.data == 'custom_seq':
        await query.edit_message_text("Please enter your custom patch sequence:")
        return WAITING_CUSTOM_SEQ
    else:
        user_data[chat_id]['patch_sequence'] = query.data
        # Proceed to process the file
        return await process_file_final(query.message, chat_id)

async def handle_custom_seq(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom patch sequence input."""
    chat_id = update.effective_chat.id
    patch_sequence = update.message.text.strip()
    
    user_data[chat_id]['patch_sequence'] = patch_sequence
    return await process_file_final(update.message, chat_id)

async def process_file_final(message, chat_id) -> int:
    """Process the file with the selected parameters."""
    try:
        # Download the input file
        input_file = user_data[chat_id]['input_file']
        file_content = (await input_file.download_as_bytearray()).decode('utf-8')
        
        # Process the content
        output_content = StringIO()
        for line in file_content.split('\n'):
            line = line.strip()
            if line.startswith("0x"):
                output_content.write(f'PATCH_LIB("{user_data[chat_id]["lib_name"]}","{line}","{user_data[chat_id]["patch_sequence"]}");\n')
        
        # Send the output file
        output_filename = user_data[chat_id]['output_file']
        await message.reply_document(
            document=output_content.getvalue().encode('utf-8'),
            filename=output_filename,
            caption="Here's your processed file!"
        )
        
        # Clean up
        del user_data[chat_id]
        
    except Exception as e:
        await message.reply_text(f"An error occurred: {str(e)}")
        if chat_id in user_data:
            del user_data[chat_id]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation."""
    chat_id = update.effective_chat.id
    if chat_id in user_data:
        del user_data[chat_id]
    
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Replace with your actual bot token
    application = Application.builder().token("7704220520:AAEI_ouYgKUdt52-ec9JJDjdo44pme781Ls").build()
    
    # Conversation handler for the processing flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('process', process_command)],
        states={
            WAITING_INPUT_FILE: [MessageHandler(filters.Document.TEXT, handle_input_file)],
            WAITING_OUTPUT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_output_name)],
            SELECTING_LIBRARY: [CallbackQueryHandler(select_library)],
            WAITING_CUSTOM_LIB: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_lib)],
            SELECTING_PATCH_SEQUENCE: [CallbackQueryHandler(select_patch_sequence)],
            WAITING_CUSTOM_SEQ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_seq)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=True  # Add this to handle callback queries properly
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
