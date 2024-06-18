import logging
from secret import BOT_TOKEN
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ApplicationBuilder, ContextTypes, ConversationHandler
from constants import *
from handlers import *

############################ Logging ############################
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    ############################ Automatic messages ############################
    job_queue = application.job_queue
    job_queue.run_repeating(schedule_crypto_message, interval=300, first=0) # 5 minute intervals

    ############################ Non Conversation Handlers ############################
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("monthly", monthly))
    application.add_handler(CommandHandler("cancel", cancel))

    ############################ Callback Query Handlers ############################
    application.add_handler(CommandHandler("view", view))
    application.add_handler(CallbackQueryHandler(view_page_callback, pattern=REGEX_VIEW))

    application.add_handler(CommandHandler("month", month))
    application.add_handler(CallbackQueryHandler(month_page, pattern=REGEX_MONTH_PAGE))

    application.add_handler(CommandHandler('stats', stats))
    application.add_handler(CallbackQueryHandler(stats_button, pattern='^stats_'))

    ############################ Open Message Handlers ############################
    application.add_handler(MessageHandler(filters.Regex(REGEX_CHECK_FOREX), forex))

    ############################ Conversation Handlers ############################
    """RECORDING EXPENSES"""
    RECORD_ACTION, RECORD_TEXT_REPLY, RECORD_TRAVEL_REPLY = range(3)
    conv_handler_record = ConversationHandler(
        entry_points=[CommandHandler('record', record)],
        states={
            RECORD_ACTION: [CallbackQueryHandler(record_button, pattern='^record_')],
            RECORD_TEXT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_record_reply)],
            RECORD_TRAVEL_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_record_travel_reply)]
        },
        fallbacks=[CallbackQueryHandler(record_button, pattern='^record_')],
        per_chat=True
    )
    application.add_handler(conv_handler_record)

    """DELETING EXPENSES"""
    DELETE_ACTION, DELETE_TEXT_REPLY = range(2)
    conv_handler_delete = ConversationHandler(
        entry_points=[CommandHandler('delete', delete)],
        states={
            DELETE_ACTION: [CallbackQueryHandler(delete_button, pattern='^delete_')],
            DELETE_TEXT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_reply)]
        },
        fallbacks=[CallbackQueryHandler(delete_button, pattern='^delete_')],
        per_chat=True
    )
    application.add_handler(conv_handler_delete)

    """INSERTING EXPENSES"""
    INSERT_DATE, INSERT_CATEGORY, INSERT_AMOUNT, INSERT_DESC = range(4)
    conv_handler_insert = ConversationHandler(
        entry_points=[CommandHandler('insert', insert)],
        states={
            INSERT_DATE: [MessageHandler(filters.Regex(REGEX_DATE), insert_date)],
            INSERT_CATEGORY: [MessageHandler(filters.Regex(REGEX_CAT), insert_category)],
            INSERT_AMOUNT: [MessageHandler(filters.TEXT, insert_amount)],
            INSERT_DESC: [MessageHandler(filters.TEXT, insert_desc)]    
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler_insert)

    """CRYPTO"""
    CRYPTO_ACTION, CRYPTO_TEXT_REPLY = range(2)
    conv_handler_crypto = ConversationHandler(
        entry_points=[CommandHandler('crypto', crypto)],
        states={
            CRYPTO_ACTION: [CallbackQueryHandler(crypto_button, pattern='^crypto_')],
            CRYPTO_TEXT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_crypto_reply)]
        },
        fallbacks=[CallbackQueryHandler(crypto_button, pattern='^crypto_')]
    )
    application.add_handler(conv_handler_crypto)

    ############################ Polling ############################
    application.run_polling()


if __name__ == '__main__':
    main()
