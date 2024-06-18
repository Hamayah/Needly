from telegram import *
from telegram.ext import *
from telegram_bot_pagination import InlineKeyboardPaginator
from datetime import datetime, time, timedelta
from needly_utils import *
from constants import *
from piechart import create_pie_chart
from secret import *
import json
import locale
import asyncio
import subprocess
import calendar


## Command Handlers ##
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends welcome message on /start command"""
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    first_name = update.message.from_user.first_name.capitalize()
    created = register_user(chat_id=chat_id, user_id=user_id)

    if created:
        start_msg = f"""Welcome, {first_name}!\nYou have successfully registered on Needly"""
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=start_msg)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f"Hello {first_name}!\nGood to see you again!")

    return ConversationHandler.END


# Help function
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_msg = "*Nick's Seedly -> Needly*\n\n" \
        "_How it works:_\n" \
        "To record Expenses:\n" \
        "Type /record and follow the on-screen instructions to log your expenses\n\n" \
        "To delete Entries:\n" \
        "Type /delete and follow the on-screen instructions to delete your entry\n\n" \
        "To insert Entries:\n" \
        "Type /insert and follow the on-screen instructions to insert your entry\n\n" \
        "To view particular day's expenses in details:\n" \
        "Type /view and follow the on-screen instructions to view your expenses\n\n"\
        "To view this month's expenses in detail:\n" \
        "Type */month* and follow the on-screen instructions to view that month's daily expenses\n\n" \
        "_Commands:_\n" \
        "/start - Start the bot and register's the user\n" \
        "/help - Show help page\n" \
        "/record - Record expenses\n" \
        "/delete - Delete entry\n" \
        "/insert - Insert entry\n" \
        "/view - View any particular day's expenses\n" \
        "/month - View any month's expenses in detail\n" \
        "/monthly - Show total monthly expenses\n" \
        "/stats - Show stats of expenditure\n\n" \
        "_This message will delete automatically in 1 minute!_"

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_msg,
        parse_mode="Markdown"
        )
    
    await schedule_deletion(
        1 * 60,
        update.effective_chat.id,
        message.message_id,
        context.bot
        )

    return ConversationHandler.END


# (Old) Total amount spent by month display function
async def monthly(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    year_dict = dict_months(chat_id=chat_id, user_id=user_id)
    month_dict = year_dict[datetime.now().year]
    money_bag = u"\U0001F4B0"

    text = "*Monthly Totals*\n\n"

    for month, date_dict in month_dict.items():
        monthly_total = 0.0

        for date, log in date_dict.items():
            daily_total = 0.0

            for id, desc, amt, cat in log:
                daily_total += float(amt)

            monthly_total += float(daily_total)

        if monthly_total < 0:
            add_text = f"*-${abs(round(monthly_total, 2)):.2f}*\n\n"
        else:
            add_text = f"*${round(monthly_total, 2):.2f}*\n\n"

        text += f"{money_bag}{parse_month(month)}'s Total: "
        text += add_text

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=text, parse_mode="Markdown")

    return ConversationHandler.END


# Text formatting to show day expenses
def text_format(update: Update, context: ContextTypes.DEFAULT_TYPE, *args) -> str:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    year_dict = dict_months(chat_id=chat_id, user_id=user_id)
    month_dict = year_dict[datetime.now().year]
    month = datetime.now().month
    date_dict = month_dict[month]
    
    money_fly = u"\U0001F4B8"
    daily_total = 0.0
    counter = 1
    
    date = args[0] if args else datetime.now().date()
    if date == datetime.now().date():
        text = "*Today's Expenses*\n"
        
    else: # Insert date handler
        date_string = date.strftime('%d-%m-%Y')
        date_string = date_string.split("-")
        text = f"*{date_string[0]} {parse_month(int(date_string[1]))} Expenses*\n"
        
    # Sort log by ID
    date_dict[date.day].sort(key=lambda x: x[0])
    
    # log tuple
    for id, desc, amt, cat in date_dict[date.day]:
        # daily calculation and text formatting
        daily_total += float(amt)
        text += f"*[ID {id}]* {desc}: {amt:.2f} *({cat})*\n"
        counter += 1
        
    # daily total text formatting
    if daily_total < 0:
        add_text = f"-${abs(round(daily_total, 2)):.2f}"
    else:
        add_text = f"${round(daily_total, 2):.2f}"
        
    text += f"\n{money_fly} *DAILY TOTAL: {add_text}*"
    
    return text    


# Cancels and restarts the bot
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    message = await update.message.reply_text(
        "Request being cancelled...",
        reply_markup=ReplyKeyboardRemove()
    )

    await update.message.delete()

    # Restart the bot using pm2
    try:
        subprocess.run(["pm2", "restart", "bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Error restarting the bot: {e}"
        )

    await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)

    return ConversationHandler.END


# View page week
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    year = datetime.now().year
    month = datetime.now().month

    reply_data = fetch_data(year, month, chat_id=chat_id, user_id=user_id)
    weeks = get_weeks_in_month(year, month)

    for i, week in enumerate(weeks, start=1):
        for _, data in enumerate(week, start=1):
            if datetime.now().day == data[1]:
                curr_week = i
                text = reply_data[curr_week]
        
    paginator = InlineKeyboardPaginator(
        page_count=len(weeks),
        current_page=curr_week,
        data_pattern='page#{page}'
    )

    red_cross = u"\u274C"
    paginator.add_after(
        InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="close_view")
    )

    await update.message.reply_text(
        text=text,
        reply_markup=paginator.markup,
        parse_mode="Markdown"
    )

    return ConversationHandler.END

# Pagination handler
async def view_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.message.from_user.id

    year = datetime.now().year
    month = datetime.now().month

    reply_data = fetch_data(year, month, chat_id=chat_id, user_id=user_id)
    weeks = get_weeks_in_month(year, month)

    if query.data == "close_view":
        await query.delete_message()

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Closed!"
        )

        return ConversationHandler.END

    if query.data.split("#")[0] == "page":
        page_number = int(query.data.split('#')[1])

        context.user_data["Page Number"] = page_number

    page_number = context.user_data.get("Page Number")
    text = reply_data[page_number]

    paginator = InlineKeyboardPaginator(
        page_count=len(weeks),
        current_page=page_number,
        data_pattern='page#{page}'
    )
    
    red_cross = u"\u274C"
    paginator.add_after(
        InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="close_view")
    )

    await query.edit_message_text(
        text=text,
        reply_markup=paginator.markup,
        parse_mode='Markdown'
    )

    return ConversationHandler.END


# Record function
RECORD_ACTION, RECORD_TEXT_REPLY, RECORD_TRAVEL_REPLY = range(3)
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    red_cross = u"\u274C"
    close_button = [InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="record_close")]
    keyboard = [
        [InlineKeyboardButton(data_category, callback_data=f"record_{data_category.lower()}") for data_category in ["FOOD", "DRINK", "GROCERIES"]],
        [InlineKeyboardButton(data_category, callback_data=f"record_{data_category.lower()}") for data_category in ["TRANSPORT", "TRAVEL", "SHOPPING"]],
        [InlineKeyboardButton(data_category, callback_data=f"record_{data_category.lower()}") for data_category in ["SUBSCRIPTION", "BILLS", "LEISURE"]],
        close_button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if context.user_data.get("record_initial_message_id"):
        chat_id = update.effective_chat.id
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=context.user_data.get("record_initial_message_id"),
            text="*RECORD EXPENSES*\n\nSelect the category of your expense",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    else:
        message = await update.message.reply_text(
            text="*RECORD EXPENSES*\n\nSelect the category of your expense",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        context.user_data["record_initial_message_id"] = message.message_id

        await update.message.delete()

    return RECORD_ACTION

# Record button handler
async def record_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Data processing
    data_type, selected = query.data.split('_')[0], query.data.split('_')[1].split(" ")[0]
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # Keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="record_close")
    back_button = InlineKeyboardButton("« Back", callback_data="record_categoryback")
    save_button = InlineKeyboardButton("Save", callback_data="record_save")
    keyboard = [
        [InlineKeyboardButton(data, callback_data="record_" + data.lower()) for data in ["Amount", "Description"]],
        [back_button, close_button, save_button]
    ]
    
    if data_type == "record" and selected in ['food', 'drink', 'groceries', 'transport', 'travel', 'shopping', 'subscription', 'bills', 'leisure']:
        # Store selected category
        context.user_data["record_category"] = selected
        
        # Handle keyboard options - Add 'currency' if selected = travel
        if selected == "travel":
            keyboard = [
                [InlineKeyboardButton(data, callback_data="record_travel" + data.lower()) for data in ["Currency", "Amount", "Description"]],
                [back_button, close_button, save_button]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await query.edit_message_text(
            text="*RECORD EXPENSES*\n\nInformation about the expense\nCategory selected: " + f"*{selected.capitalize()}*",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        context.user_data["record_query_message_id"] = message.message_id

    elif data_type == "record" and selected in ['amount', 'description']: # Add 'currency' if selected = travel
        if selected == 'amount':
            context.user_data['awaiting_amount_reply'] = True

            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="*RECORD EXPENSES*\n\nHow much did you spend?",
                reply_markup=ForceReply(selective=True),
                parse_mode="Markdown"
            )
            context.user_data["record_amount_message_id"] = message.message_id

            return RECORD_TEXT_REPLY

        elif selected == 'description':
            context.user_data['awaiting_description_reply'] = True

            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="*RECORD EXPENSES*\n\nWhat was your expense?",
                reply_markup=ForceReply(selective=True),
                parse_mode="Markdown"
            )
            context.user_data["record_description_message_id"] = message.message_id

            return RECORD_TEXT_REPLY
        
        
    elif data_type == "record" and selected in ['travelcurrency', 'travelamount', 'traveldescription']:
        if selected in ['travelamount', 'traveldescription'] and not context.user_data.get('record_currency'):
            keyboard = [
                [InlineKeyboardButton(data, callback_data="record_travel" + data.lower()) for data in ["Currency", "Amount", "Description"]],
                [back_button, close_button, save_button]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text="*RECORD EXPENSES*\n\nPlease fill out the *Currency* of your expense first!",
                parse_mode="Markdown",
                reply_markup=reply_markup    
            )
            context.user_data["record_query_message_id"] = message.message_id

            return RECORD_TRAVEL_REPLY  # Keep the user in the same state to force them to choose currency first.
        
        elif selected == 'travelamount':
            context.user_data['awaiting_amount_reply'] = True

            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="*RECORD EXPENSES*\n\nHow much did you spend?",
                reply_markup=ForceReply(selective=True),
                parse_mode="Markdown"
            )
            context.user_data["record_amount_message_id"] = message.message_id

            return RECORD_TRAVEL_REPLY

        elif selected == 'traveldescription':
            context.user_data['awaiting_description_reply'] = True

            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="*RECORD EXPENSES*\n\nWhat was your expense?",
                reply_markup=ForceReply(selective=True),
                parse_mode="Markdown"
            )
            context.user_data["record_description_message_id"] = message.message_id

            return RECORD_TRAVEL_REPLY
        
        elif selected == 'travelcurrency':
            context.user_data['awaiting_currency_reply'] = True
            
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="*RECORD EXPENSES*\n\nWhat is the currency of your expense?",
                reply_markup=ForceReply(selective=True),
                parse_mode="Markdown"
            )
            context.user_data["record_currency_message_id"] = message.message_id

            return RECORD_TRAVEL_REPLY

    # Back button handler on month selection
    elif data_type == "record" and selected == "categoryback":
        return await record(update, context)

    # Save button handler
    elif data_type == "record" and selected == "save":
        log_category = context.user_data.get('record_category')

        if log_category == "travel":
            log_amount = format(-float(context.user_data.get('conversion_amount')), ".2f")
        else:
            log_amount = context.user_data.get('record_amount')

        log_description = context.user_data.get('record_description')
        log_date = datetime.now()

        entered_amount = log_amount
        if entered_amount is not None:
            entered_amount = str(entered_amount)
            entered_amount = entered_amount[1:]
            entered_amount = float(entered_amount)
            entered_amount = f"{entered_amount:.2f}" # Ensure 2dp on amount text reply

        money_fly = u'\U0001F4B8'
        emoji_notes = '\U0001F4DD'
        
        emoji_err = " " + '\U0001F6AB' + " "
        emoji_err_4 = emoji_err * 4

        if not log_amount and not log_description:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"*RECORD EXPENSES*\n\n{emoji_err_4}*ERROR*{emoji_err_4}\nPlease ensure both *Amount* and *Description* are filled!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        elif not log_amount:
            keyboard = [
                [InlineKeyboardButton("Amount", callback_data="record_amount"), InlineKeyboardButton(f"{emoji_notes} {log_description}", callback_data="record_description")],
                [back_button, close_button, save_button]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"*RECORD EXPENSES*\n\n{emoji_err_4}*ERROR*{emoji_err_4}\nPlease ensure the *Amount* is filled!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        elif not log_description:
            keyboard = [
                [InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_amount"), InlineKeyboardButton("Description", callback_data="record_description")],
                [back_button, close_button, save_button]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=f"*RECORD EXPENSES*\n\n{emoji_err_4}*ERROR*{emoji_err_4}\nPlease ensure the *Description* is filled!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        else:
            log_entry(
                chat_id=chat_id,
                user_id=user_id,
                log_cat=log_category,
                log_amt=log_amount,
                log_desc=log_description,
                date=log_date
                )
            
            record_query_message_id = context.user_data.get('record_query_message_id')
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=record_query_message_id
                )
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=text_format(update, context),
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

            context.user_data.clear()
            return ConversationHandler.END

    # Close button handler
    elif data_type == "record" and selected == "close":
        # Close the interaction and delete the message
        await query.message.delete()

        # Clear previous user data
        context.user_data.clear()

        return ConversationHandler.END


# Record button reply handlers
async def handle_record_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="record_close")
    back_button = InlineKeyboardButton("« Back", callback_data="record_categoryback")
    save_button = InlineKeyboardButton("Save", callback_data="record_save")
    second_row = [back_button, close_button, save_button]

    # Text formatting resources
    category_selected = context.user_data.get('record_category')
    money_fly = u'\U0001F4B8'
    emoji_notes = '\U0001F4DD'

    text = f"*RECORD EXPENSES*\n\nCategory selected: *{category_selected.capitalize()}*\n"

    # Awaiting replies
    await_amount_reply = context.user_data.get('awaiting_amount_reply')
    await_description_reply = context.user_data.get('awaiting_description_reply')
    # await_currency_reply = context.user_data.get('awaiting_currency_reply')

    # Waiting for amount reply
    if await_amount_reply:
        entered_amount = update.message.text
        log_amount = format(float(entered_amount), ".2f")

        # Format amount to 2dp for database, always expensed as negative
        if float(entered_amount) < 0: # If user input negative amount
            log_amount = float(log_amount)
            entered_amount = entered_amount[1:]
        else: # If user input positive amount
            log_amount = -float(log_amount)

        context.user_data['record_amount'] = log_amount
        context.user_data['awaiting_amount_reply'] = False  # Reset flag

        original_message_id = context.user_data.get('record_query_message_id')
        chat_id = update.effective_chat.id

        # Check if description has been entered
        entered_amount = float(entered_amount) # Convert to float
        entered_amount = f"{entered_amount:.2f}" # Ensure 2dp on amount text reply
        entered_description = context.user_data.get('record_description')

        if entered_description: # Have description input
            text += f"You spent *${entered_amount}* on *{entered_description}*"
            keyboard = [
                [InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_amount"), InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_description")]
            ]
        
        else: # No description input
            text += f"You spent *${entered_amount}*"
            keyboard = [
                [InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_amount"), InlineKeyboardButton("Description", callback_data="record_description")]
            ]

        # Add the second row of buttons
        keyboard.append(second_row)

        if original_message_id:
            # Delete the amount spent message
            amount_spent_message_id = context.user_data.get('record_amount_message_id')
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=amount_spent_message_id
                )

            # Delete input amount message
            await update.message.delete()

            text += "\n\nClick *Save* to record the expense"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=original_message_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    # Waiting for description reply
    elif await_description_reply:
        entered_description = update.message.text

        # Check if amount has been entered
        entered_amount = context.user_data.get('record_amount')

        if entered_amount is not None:
            entered_amount = str(entered_amount)
            entered_amount = entered_amount[1:]
            entered_amount = float(entered_amount)
            entered_amount = f"{entered_amount:.2f}" # Ensure 2dp on amount text reply

        context.user_data['record_description'] = entered_description
        context.user_data['awaiting_description_reply'] = False  # Reset flag

        original_message_id = context.user_data.get('record_query_message_id')
        chat_id = update.effective_chat.id

        if entered_amount: # Have amount input
            text += f"You spent *${entered_amount}* on *{entered_description}*"
            keyboard = [
                [InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_amount"), InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_description")]
            ]
        else: # No amount input
            text += f"You spent on *{entered_description}*"
            keyboard = [
                [InlineKeyboardButton("Amount", callback_data="record_amount"), InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_description")]
            ]
        keyboard.append(second_row)

        if original_message_id:
            # Delete the amount spent message
            description_message_id = context.user_data.get('record_description_message_id')
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=description_message_id
                )

            # Delete input amount message
            await update.message.delete()

            # Update information about the expense message
            category_selected = context.user_data.get('record_category')

            text += "\n\nClick *Save* to record the expense"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=original_message_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def handle_record_travel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="record_close")
    back_button = InlineKeyboardButton("« Back", callback_data="record_categoryback")
    save_button = InlineKeyboardButton("Save", callback_data="record_save")
    second_row = [back_button, close_button, save_button]

    # Text formatting resources
    category_selected = context.user_data.get('record_category')
    money_fly = u'\U0001F4B8'
    emoji_notes = '\U0001F4DD'

    text = f"*RECORD EXPENSES*\n\nCategory selected: *{category_selected.capitalize()}*\n"

    original_message_id = context.user_data.get('record_query_message_id')
    chat_id = update.effective_chat.id

    # Get await status
    await_amount_reply = context.user_data.get('awaiting_amount_reply')
    await_description_reply = context.user_data.get('awaiting_description_reply')
    await_currency_reply = context.user_data.get('awaiting_currency_reply')

    # Button handler
    entered_currency = context.user_data.get('record_currency')

    # Handle user replies for currency, amount and description buttons
    if await_currency_reply:
        # Separate control flow for "TRAVEL" category
        entered_currency = update.message.text.upper()

        # Forex data
        base_currency = "SGD"
        currency_to_sgd = entered_currency + base_currency
        forex_data = get_forex(currency_to_sgd)
        context.user_data['currency_pair'] = currency_to_sgd
        context.user_data['exchange_rate'] = f"*{currency_to_sgd} = {forex_data:.5f}*"

        # Store currency in user data
        context.user_data['record_currency'] = entered_currency.upper()

        currency_button = InlineKeyboardButton(f"Currency: {entered_currency}", callback_data="record_currency")

        keyboard = [
            [
                currency_button,
                InlineKeyboardButton("Amount", callback_data="record_travelamount"),
                InlineKeyboardButton("Description", callback_data="record_traveldescription")
                ]
        ]

    elif await_amount_reply:
        entered_amount = update.message.text
        log_amount = format(float(entered_amount), ".2f")

        # Format amount to 2dp for database, always expensed as negative
        if float(entered_amount) < 0: # If user input negative amount
            log_amount = float(log_amount)
            entered_amount = entered_amount[1:]
        else: # If user input positive amount
            log_amount = -float(log_amount)
        context.user_data['record_amount'] = log_amount

        entered_description = context.user_data.get('record_description')

        # Forex data handler
        currency_to_sgd = context.user_data.get('currency_pair')
        forex_data = context.user_data.get('exchange_rate')
        forex_amount = forex_data.split(" = ")[-1][:-1]
        entered_amount = float(forex_amount) * float(entered_amount)
        entered_amount = f"{entered_amount:.2f}"

        context.user_data['conversion_amount'] = entered_amount

        currency_button = InlineKeyboardButton(f"Currency: {entered_currency}", callback_data="record_currency")

        if entered_description:
            text += f"You spent *${entered_amount}* on *{entered_description}*"
            keyboard = [
                [
                    currency_button,
                    InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_travelamount"),
                    InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_traveldescription")
                    ]
            ]

        else:
            text += f"You spent *${entered_amount}*"
            keyboard = [
                [
                    currency_button,
                    InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_travelamount"),
                    InlineKeyboardButton("Description", callback_data="record_traveldescription")
                    ]
            ]

    elif await_description_reply:
        entered_description = update.message.text
        context.user_data['record_description'] = entered_description
        
        # Get converted amount
        entered_amount = context.user_data.get('conversion_amount')

        # Check if entered_amount is not None and is a valid number
        if entered_amount is not None:
            try:
                entered_amount = float(entered_amount)
                entered_amount = f"{entered_amount:.2f}"
            except ValueError:
                # Handle the case where entered_amount is not a valid float
                print("Entered amount is not a valid number.")
                # Set entered_amount to a default value or handle this error appropriately
                entered_amount = "0.00"
        else:
            # Handle the case where entered_amount is None
            print("No amount entered.")
            # Set entered_amount to a default value or handle this error appropriately
            entered_amount = "0.00"


        currency_button = InlineKeyboardButton(f"Currency: {entered_currency}", callback_data="record_currency")

        if entered_amount:
            text += f"You spent *${entered_amount}* on *{entered_description}*"
            keyboard = [
                [
                    currency_button,
                    InlineKeyboardButton(f"{money_fly} ${entered_amount}", callback_data="record_travelamount"),
                    InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_traveldescription")
                    ]
            ]
        else:
            text += f"You spent on *{entered_description}*"
            keyboard = [
                [
                    currency_button,
                    InlineKeyboardButton("Amount", callback_data="record_travelamount"),
                    InlineKeyboardButton(f"{emoji_notes} {entered_description}", callback_data="record_traveldescription")
                    ]
            ]

    # Add currency to text
    exchange_rate = context.user_data.get('exchange_rate')
    text += f"\n\nExchange Rate: {exchange_rate}"

    # Add the second row of buttons
    keyboard.append(second_row)

    if original_message_id:
        if await_currency_reply:
            message_id = context.user_data.get('record_currency_message_id')
            context.user_data['awaiting_currency_reply'] = False # Reset flag
        
        elif await_amount_reply:
            message_id = context.user_data.get('record_amount_message_id')
            context.user_data['awaiting_amount_reply'] = False # Reset flag

        elif await_description_reply:
            message_id = context.user_data.get('record_description_message_id')
            context.user_data['awaiting_description_reply'] = False # Reset flag

        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )

        # Delete input currency message
        await update.message.delete()

        text += "\n\nClick *Save* to record the expense"
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=original_message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# Stats function
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear() # Clear previous user data

    red_cross = u"\u274C"
    close_button = [InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="stats_close")]
    keyboard = [
        [InlineKeyboardButton(data, callback_data=f"stats_{data.lower()}") for data in ["Pie Chart", "Line Graph", "Bar Chart"]],
        close_button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select a type of chart to display your expenses in:",
        reply_markup=reply_markup
    )

    await update.message.delete()

    return ConversationHandler.END

# Stats button handler
async def stats_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Data processing
    data_type, selected = query.data.split('_')[0], query.data.split('_')[1].split(" ")[0]
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # Keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="stats_close")
    back_button = InlineKeyboardButton("« Back", callback_data="stats_monthback")
    keyboard = [
        [InlineKeyboardButton(month, callback_data="stats_" + month.lower()) for month in ["January", "February", "March"]],
        [InlineKeyboardButton(month, callback_data="stats_" + month.lower()) for month in ["April", "May", "June"]],
        [InlineKeyboardButton(month, callback_data="stats_" + month.lower()) for month in ["July", "August", "September"]],
        [InlineKeyboardButton(month, callback_data="stats_" + month.lower()) for month in ["October", "November", "December"]],
        [back_button, close_button]
    ]

    # Chart type selection handler
    if data_type == "stats" and selected in ['pie', 'line', 'bar']:
        context.user_data["stats_chart_type"] = selected # Store selected chart type

        # Show months after selecting the data type
        # Your existing month selection keyboard logic here
        if selected !=  "pie":
            message = await context.bot.send_message(
                chat_id=chat_id,
                text="Sorry, this feature is not available yet!"
            )
            context.user_data["unavailable_feature_message"] = message.message_id

        else:
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text="Select a month to view your expenses in a chart:",
                reply_markup=reply_markup
            )

    # Month selection handler
    elif data_type == "stats" and selected.lower() in [month.lower() for month in calendar.month_name[1:]]:
        # Process month selection here
        year = datetime.now().year
        month_no = parse_month_no(selected)
        reply_data = fetch_data(year, month_no, chat_id, user_id)

        if reply_data is not None:
            # Call chart generation function
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
            month_name = selected.capitalize()
            get_date_range = get_month_dates(month_name, datetime.now().year)

            start_date = get_date_range[0]
            end_date = get_date_range[1]

            dir_path = create_pie_chart(start_date=start_date, end_date=end_date)

            reply_markup = InlineKeyboardMarkup([
                [close_button]
                ])

            with open (dir_path, "rb") as photo:
                photo = await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=f"Pie chart for {start_date.strftime('%d')} to {end_date.strftime('%d %B')}",
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )

                context.user_data["photo_id"] = photo.message_id

        else:
            # No data for selected month, prompt to select again
            await query.edit_message_text(
                text="_Uh oh.. I don't have any data for that month_\n*Please select again!*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    # Back button handler on month selection
    elif data_type == "stats" and selected == "monthback":
        # Show the initial chart type selection keyboard
        keyboard = [
            [InlineKeyboardButton(data, callback_data=f"stats_{data.lower()}") for data in ["Pie Chart", "Line Graph", "Bar Chart"]],
            [close_button]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="Select a type of chart to display your expenses in:",
            reply_markup=reply_markup
        )

    # Close button handler
    elif data_type == "stats" and selected == "close":
        if 'photo_message_id' in context.user_data:
            photo_message_id = context.user_data.pop('photo_message_id')
            await context.bot.delete_message(chat_id=chat_id, message_id=photo_message_id)

        if 'unavailable_feature_message' in context.user_data:
            unavailable_feature_message = context.user_data.pop('unavailable_feature_message')
            await context.bot.delete_message(chat_id=chat_id, message_id=unavailable_feature_message)

        # Close the interaction and delete the message
        await query.message.delete()

        # Clear previous user data
        context.user_data.clear()

    return ConversationHandler.END
    

# Inline Keyboard Options: Month names
def month_inline_keyboard() -> list:
    reply_keyboard = [[InlineKeyboardButton("January", callback_data="January"), InlineKeyboardButton("February", callback_data="February"), InlineKeyboardButton("March", callback_data="March")],
    [InlineKeyboardButton("April", callback_data="April"), InlineKeyboardButton("May", callback_data="May"), InlineKeyboardButton("June", callback_data="June")],
    [InlineKeyboardButton("July", callback_data="July"), InlineKeyboardButton("August", callback_data="August"), InlineKeyboardButton("September", callback_data="September")],
    [InlineKeyboardButton("October", callback_data="October"), InlineKeyboardButton("November", callback_data="November"), InlineKeyboardButton("December", callback_data="December")]]

    return reply_keyboard

async def month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = month_inline_keyboard()

    await update.message.reply_text(
        text="*Select any month to see how much you spent*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

    return ConversationHandler.END

async def month_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_id = query.message.from_user.id
    keyboard = month_inline_keyboard()

    if query.data == "close_month_view":
        await query.delete_message()

        await context.bot.send_message(
            chat_id=chat_id,
            text="Closed!"
        )

        return ConversationHandler.END
    
    if query.data == "back":
        await query.edit_message_text(
            text="*Select any month to see how much you spent*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    year = datetime.now().year
    if query.data in REGEX_MONTH_PAGE:
        month_name = query.data
        context.user_data["Month Name"] = month_name
    
    month_name = context.user_data.get("Month Name")
    month_no = parse_month_no(month_name)
    reply_data = fetch_data(year, month_no, chat_id, user_id)

    if reply_data == None:
        await query.edit_message_text(
            text="_Uh oh.. I don't have any data for that month_\n*Please select again!*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

        return ConversationHandler.END

    weeks = get_weeks_in_month(year, month_no)
    text = reply_data[1]

    page_number = 1
    if query.data.split("#")[0] == "month_page":
        page_number = int(query.data.split("#")[1])
        context.user_data["Page Number"] = page_number

        text = reply_data[page_number]

        page_number = context.user_data.get("Page Number")


    paginator = InlineKeyboardPaginator(
        page_count=len(weeks),
        current_page=page_number,
        data_pattern='month_page#{page}'
    )

    red_cross = u"\u274C"
    paginator.add_after(
        InlineKeyboardButton("« Back", callback_data="back"),
        InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="close_month_view")
    )

    await query.edit_message_text(
        text=text,
        reply_markup=paginator.markup,
        parse_mode='Markdown'
    )

    return ConversationHandler.END


# Delete function
DELETE_ACTION, DELETE_TEXT_REPLY = range(2)
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="delete_close")
    save_button = InlineKeyboardButton("Save", callback_data="delete_save")

    keyboard = [
        [InlineKeyboardButton("ID", callback_data="delete_ID")],
        [close_button, save_button]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Initial instruction message
    message = await update.message.reply_text(
        text="*DELETE ENTRY*\n\nClick on the ID button and send the ID of the entry you want to delete",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    # Store text message above for deletion later
    context.user_data["delete_initial_message_id"] = message.message_id

    # Delete the command message
    await update.message.delete()

    return DELETE_ACTION


async def delete_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Data processing
    data_type, selected = query.data.split('_')[0], query.data.split('_')[1].split(" ")[0]
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # Inline keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="delete_close")
    save_button = InlineKeyboardButton("Save", callback_data="delete_save")

    keyboard = [
        [InlineKeyboardButton("ID", callback_data="delete_ID")],
        [close_button, save_button]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if data_type == "delete" and selected == "ID":
        context.user_data["awaiting_delete_id_reply"] = True

        # Send request for ID message to user
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="*DELETE ENTRY*\n\nSend the ID of the entry you want to delete",
            reply_markup=ForceReply(selective=True),
            parse_mode="Markdown"
        )

        # Store text message above for deletion later
        context.user_data["delete_id_message_id"] = message.message_id

        return DELETE_TEXT_REPLY
    
    elif data_type == "delete" and selected == "save":
        delete_id = context.user_data.get('delete_id')

        emoji_err = " " + '\U0001F6AB' + " "
        emoji_err_4 = emoji_err * 4

        # No ID entered
        if db_get_by_id(delete_id) == []:

            # Edit the command message to show error
            message = await query.edit_message_text(
                text=f"*DELETE ENTRY*\n\n{emoji_err_4}*ERROR*{emoji_err_4}\nPlease ensure an ID is entered!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )

        # ID entered
        else:
            # Delete entry from database
            delete_entry_db(delete_id)

            # Get the initial message ID
            delete_initial_message_id = context.user_data.get('delete_initial_message_id')

            # Delete the initial message
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=delete_initial_message_id
            )

            # Get log details from user data
            log_desc = context.user_data.get('log_desc')
            log_amt = context.user_data.get('log_amt')
            log_cat = context.user_data.get('log_cat')

            # Send success message
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"*DELETE ENTRY*\n\nYou have successfully deleted\n*[ID {delete_id}]* {log_desc}: {log_amt} *({log_cat})*",
                parse_mode="Markdown",
                reply_markup=ReplyKeyboardRemove()
            )

            # Clear previous user data
            context.user_data.clear()
            return ConversationHandler.END

    # Close button handler
    elif data_type == "delete" and selected == "close":
        # Close the interaction and delete the message
        await query.message.delete()

        # Clear previous user data
        context.user_data.clear()
        return ConversationHandler.END

async def handle_delete_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # Inline keyboard options
    red_cross = u"\u274C"
    close_button = InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="delete_close")
    save_button = InlineKeyboardButton("Save", callback_data="delete_save")
    
    if context.user_data.get('awaiting_delete_id_reply'):
        entered_id = update.message.text

        # Assign entered ID to user data
        context.user_data['delete_id'] = entered_id

        # Get display ID from database
        delete_request = db_get_by_id(int(entered_id))

        # No such ID found
        if delete_request == []:
            # Error message
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"ID *{entered_id}* does not exist! Send the ID again",
                parse_mode="Markdown"
            )

        # ID found
        else:
            log_desc = delete_request[0]
            log_amt = delete_request[1]
            log_cat = delete_request[2]

            # Assign log details to user data
            context.user_data['log_desc'] = log_desc
            context.user_data['log_amt'] = log_amt
            context.user_data['log_cat'] = log_cat
            
            text = f"You are about to delete: \n*[ID {entered_id}]* {log_desc}: {log_amt} *({log_cat})*\n\nClick *Save* to confirm"
            keyboard = [
                [InlineKeyboardButton(entered_id, callback_data="delete_ID")],
                [close_button, save_button]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Get the initial message ID to edit later
            original_message_id = context.user_data.get('delete_initial_message_id')

            # Reset flag
            context.user_data['awaiting_amount_reply'] = False 

            # Edit the command message to show the delete details
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=original_message_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

            # Get delete ID message ID
            delete_id_message_id = context.user_data.get('delete_id_message_id')

            # Delete "Send the ID" message
            await context.bot.delete_message(
                chat_id=chat_id,
                message_id=delete_id_message_id
            )

            # Delete user send ID message
            await update.message.delete()


# Insert Utils
INSERT_DATE, INSERT_CATEGORY, INSERT_AMOUNT, INSERT_DESC = range(4)
insert_instance = []

# Start function for Insert
async def insert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [[KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3"), KeyboardButton("4"), KeyboardButton("5"), KeyboardButton("6"), KeyboardButton("7")],
               [KeyboardButton("8"), KeyboardButton("9"), KeyboardButton("10"), KeyboardButton(
                   "11"), KeyboardButton("12"), KeyboardButton("13"), KeyboardButton("14")],
               [KeyboardButton("15"), KeyboardButton("16"), KeyboardButton("17"), KeyboardButton(
                   "18"), KeyboardButton("19"), KeyboardButton("20"), KeyboardButton("21")],
               [KeyboardButton("22"), KeyboardButton("23"), KeyboardButton("24"), KeyboardButton(
                   "25"), KeyboardButton("26"), KeyboardButton("27"), KeyboardButton("28")],
               [KeyboardButton("29"), KeyboardButton("30"), KeyboardButton("31")]]

    chat_id = update.effective_chat.id

    message = await update.message.reply_text(
        f"Which date in *{parse_month(datetime.now().month)}* would you like to insert an entry?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Choose a date"
        ),
        parse_mode="Markdown"
    )   

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return INSERT_DATE

# Date of insert
async def insert_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['FOOD', 'DRINK', 'GROCERIES'],
                      ['TRANSPORT', 'TRAVEL', 'SHOPPING'],
                      ['SUBSCRIPTIONS', 'BILLS'],
                      ['SALARY', 'LEISURE']]

    chat_id = update.effective_chat.id

    date_text=update.message.text
    insert_instance.append(date_text)

    message = await update.message.reply_text(
        "What is the category of your expense?",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Choose a Category"
        )
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return INSERT_CATEGORY

# Insert category
async def insert_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    category_text=update.message.text
    insert_instance.append(category_text)

    message = await update.message.reply_text(
        "How much did you spend today?",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return INSERT_AMOUNT

# Insert amount spent
async def insert_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    amount_text = update.message.text
    insert_instance.append(float(amount_text))

    message = await update.message.reply_text(
        "What did you spend on?",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return INSERT_DESC

# Insert description of item spent and ends the conversation
async def insert_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    chat_id = update.message.chat.id
    user_id = update.message.from_user.id

    description_text = update.message.text
    insert_instance.append(str(description_text))

    log_category = insert_instance[1]
    log_amount = insert_instance[2]
    log_description = insert_instance[3]
    date_string = f"{insert_instance[0]}-{str(datetime.now().month)}-{str(datetime.now().year)}"
    log_date = datetime.strptime(date_string, '%d-%m-%Y')

    if int(log_amount) > 0:
        log_amount = -log_amount

    log = log_entry(
        chat_id=chat_id,
        user_id=user_id,
        log_cat=log_category,
        log_amt=log_amount,
        log_desc=log_description,
        date=log_date
    )

    insert_instance.clear()

    message = await update.message.reply_text(
        text=text_format(update, context, log_date),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return ConversationHandler.END


# Forex function
async def forex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    message_id = update.message.message_id
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)

    requested_currency = text.split(" ")[-2].upper()
    requested_amount = text.split(" ")[-1]
    base_currency = "SGD"

    # REQUEST + SGD
    currency_to_sgd = requested_currency + base_currency
    # SGD + REQUEST
    sgd_to_currency = base_currency + requested_currency

    forex_data = get_forex(currency_to_sgd)

    price_in_currency = float(forex_data) * float(requested_amount)

    stock_rising = u'\U0001F4C8'
    formatted_text = f"*Today's rate* {stock_rising}\n\n{currency_to_sgd} = {forex_data:.5f}\n{sgd_to_currency} = {1/forex_data:.5f}\n\n*You requested = {requested_currency}{requested_amount}*\n*Your conversion = SGD{price_in_currency:.2f}*"

    await update.message.reply_text(
        text=formatted_text,
        parse_mode="Markdown"
    )

    return ConversationHandler.END


# Schedule deletion of message
async def schedule_deletion(delay_seconds, chat_id, message_id, bot):
    await asyncio.sleep(delay_seconds)
    asyncio.create_task(delete_message(chat_id, message_id, bot))


# Delete message function
async def delete_message(chat_id, message_id, bot):
    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
            )

    except Exception as e:
        await bot.send_message(
            chat_id=chat_id,
            text=f"Error deleting message {e}"
            )


# Crypto function
CRYPTO_ACTION, CRYPTO_TEXT_REPLY = range(2)
def save_crypto_set(crypto_set):
    with open('saved_crypto.txt', 'w') as f:
        for item in crypto_set:
            f.write("%s\n" % item)

def load_crypto_set():
    try:
        with open('saved_crypto.txt', 'r') as f:
            return {line.strip() for line in f}
    except FileNotFoundError:
        return set()  # Return an empty set if the file does not exist

saved_crypto = load_crypto_set()

async def crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global saved_crypto

    chat_id = update.effective_chat.id
    text = "*CRYPTO*\n\nSaved Tokens:\n"

    red_cross = u"\u274C"
    keyboard = [
        [InlineKeyboardButton(crypto_option, callback_data="crypto_" + crypto_option.lower()) for crypto_option in ["Add", "Delete"]],
        [InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="crypto_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if len(saved_crypto) == 0:
        text += "No tokens saved yet, click *Add* to start adding tokens"
    
    else:
        for tokens in saved_crypto:
            text += f"{tokens}\n"

    message = await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    context.user_data["crypto_initial_message_id"] = message.message_id

    await update.message.delete()

    return CRYPTO_ACTION


async def crypto_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Data processing
    data_type, selected = query.data.split('_')[0], query.data.split('_')[1]
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    red_cross = u"\u274C"
    keyboard = [
        [InlineKeyboardButton(crypto_option, callback_data="crypto_" + crypto_option.lower()) for crypto_option in ["Add", "Delete"]],
        [InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="crypto_close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if data_type == "crypto" and selected == "add":
        context.user_data['awaiting_crypto_add_reply'] = True

        message = await context.bot.send_message(
            chat_id=chat_id,
            text="*CRYPTO*\n\nSend the token(s) tickers you want to track\n\nIf you have more than 1 token, separate it with spaces",
            reply_markup=ForceReply(selective=True),
            parse_mode="Markdown"
        )
        context.user_data["crypto_add_message_id"] = message.message_id

        return CRYPTO_TEXT_REPLY
    
    elif data_type == "crypto" and selected == "delete":
        context.user_data['awaiting_crypto_delete_reply'] = True

        message = await context.bot.send_message(
            chat_id=chat_id,
            text="*CRYPTO*\n\nSend the token(s) tickers you want to delete\n\nIf you have more than 1 token, separate it with spaces",
            reply_markup=ForceReply(selective=True),
            parse_mode="Markdown"
        )
        context.user_data["crypto_delete_message_id"] = message.message_id

        return CRYPTO_TEXT_REPLY
    
    elif data_type == "crypto" and selected == "close":
        # Close the interaction and delete the message
        await query.message.delete()

        # Clear previous user data
        context.user_data.clear()
        return ConversationHandler.END
    

async def handle_crypto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global saved_crypto

    chat_id = update.effective_chat.id
    red_cross = u"\u274C"
    keyboard = [
            [InlineKeyboardButton(crypto_option, callback_data="crypto_" + crypto_option.lower()) for crypto_option in ["Add", "Delete"]],
            [InlineKeyboardButton(f"{red_cross} Close {red_cross}", callback_data="crypto_close")]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await_crypto_add_reply = context.user_data.get('awaiting_crypto_add_reply')
    await_crypto_delete_reply = context.user_data.get('awaiting_crypto_delete_reply')

    if await_crypto_add_reply:
        entered_tokens = update.message.text
        entered_tokens = entered_tokens.split(" ")

        # Add tokens to saved_crypto
        for token in entered_tokens:
            saved_crypto.add(token)

        # Display saved tokens
        text = "*CRYPTO*\n\nSaved Tokens:\n"
        if len(saved_crypto) == 0:
            text += "No tokens saved yet, click *Add* to start adding tokens"
        else:
            for tokens in saved_crypto:
                text += f"{tokens}\n"

        # Get the initial message ID to edit later
        original_message_id = context.user_data.get('crypto_initial_message_id')

        # Reset flag
        context.user_data['awaiting_crypto_add_reply'] = False 

        # Delete the Add Crypto message
        crypto_add_message_id = context.user_data.get('crypto_add_message_id')
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=crypto_add_message_id
        )

        await update.message.delete()

        # Edit the command message to show the added crypto
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=original_message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    if await_crypto_delete_reply:
        entered_tokens = update.message.text
        entered_tokens = entered_tokens.split(" ")

        # Add tokens to saved_crypto
        for token in entered_tokens:
            saved_crypto.discard(token)
        
        # Display saved tokens
        text = "*CRYPTO*\n\nSaved Tokens:\n"
        if len(saved_crypto) == 0:
            text += "No tokens saved yet, click *Add* to start adding tokens"
        else:
            for tokens in saved_crypto:
                text += f"{tokens}\n"
        
        # Get the initial message ID to edit later
        original_message_id = context.user_data.get('crypto_initial_message_id')

        # Reset flag
        context.user_data['awaiting_crypto_delete_reply'] = False 

        # Delete the Delete Crypto message
        crypto_delete_message_id = context.user_data.get('crypto_delete_message_id')
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=crypto_delete_message_id
        )

        await update.message.delete()

        # Edit the command message to show the added crypto
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=original_message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    save_crypto_set(saved_crypto)


# Send crypto price updates
crypto_last_message_id = None        
async def schedule_crypto_message(context: ContextTypes.DEFAULT_TYPE):
    global crypto_last_message_id  # To modify the global variable
    global saved_crypto
    chat_id = CHAT_ID

    # If there's a previous message, delete it
    if crypto_last_message_id is not None:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=crypto_last_message_id)
        except Exception as e:
            print(f"Failed to delete the message: {e}")  # Just in case the message doesn't exist

    # Format as "date/month day | HH:MM AM/PM"
    formatted_date = datetime.now().strftime("%d/%m %A | %I:%M%p")

    text = f"*Price as at {formatted_date}*\n\n"

    tickers = []
    for token in saved_crypto:
        token += "USDT"
        tickers.append(token)

    price_data = get_crypto_price(tickers)

    if price_data is None:
        text += "_System under maintenance, it will be back up shortly!_"

        message = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        crypto_last_message_id = message.message_id
        
        return

    if len(tickers) == 0:
        text += "No tokens to display, use /crypto to add tokens!"
    
    elif len(tickers) == 1:
        ticker = price_data["symbol"].replace("USDT", "")
        price_float = float(price_data["price"])
        price_str = "{:,.2f}".format(price_float)
        text += f"{ticker}: *USDT${price_str}*\n"

    else:
        counter = 1
        for data in price_data:
            ticker = data['symbol'].replace("USDT", "")
            price_float = float(data['price'])
            price_str = "{:,.2f}".format(price_float)
            
            text += f"{counter}. {ticker}: *USDT ${price_str}*\n"
            
            counter += 1

    message = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    crypto_last_message_id = message.message_id

############################################################################################################
# Deprecated functions
""" STATS_PIE_CHART = range(1)
async def pie_date_range(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ["January", "February", "March"],
        ["April", "May", "June"],
        ["July", "August", "September"],
        ["October", "November", "December"]
    ]
    
    message = await update.message.reply_text(
        text="Select a month to visualise data",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Choose a Month"
        )
    )

    message_id = message.message_id
    context.user_data["message_id"] = message_id
    await update.message.delete()

    return STATS_PIE_CHART


async def stats_pie_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    chat_id = update.effective_chat.id
    month_name = update.message.text

    get_date_range = get_month_dates(month_name, datetime.now().year)

    start_date = get_date_range[0]
    end_date = get_date_range[1]

    dir_path = create_pie_chart(start_date=start_date, end_date=end_date)

    with open (dir_path, "rb") as photo:
        photo = await context.bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=f"Pie chart for {start_date.strftime('%d')} to {end_date.strftime('%d %B')}\n\n_This image will automatically delete after 2 minutes_",
            parse_mode="Markdown"
        )


    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()
    
    # Delete photo
    await schedule_deletion(2 * 60, chat_id, photo.message_id, context.bot)

    return ConversationHandler.END """

""" # Record Utils
CATEGORY, AMOUNT, DESC = range(3)
record_instance = []
# Start function of recording
async def record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat.id
    reply_keyboard = [['FOOD', 'DRINK', 'GROCERIES'],
                      ['TRANSPORT', 'TRAVEL', 'SHOPPING'],
                      ['SUBSCRIPTIONS', 'BILLS'],
                      ['SALARY', 'LEISURE']]

    message = await update.message.reply_text(
        "Choose the category of your income/expense",
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="Choose a Category"
        )
    )
    
    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return CATEGORY

# Store selected category and ask how much spent
async def category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    category_text=update.message.text
    record_instance.append(category_text)

    message = await update.message.reply_text(
        "How much did you earn/spend today?",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return AMOUNT

# Store amount spent and asks for description on item spent
async def amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    amount_text = update.message.text
    record_instance.append(float(amount_text))

    message = await update.message.reply_text(
        "What did you earn/spend on?",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return DESC

# Store description of item spent and ends the conversation
async def desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user

    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    date = datetime.now()

    description_text = update.message.text
    record_instance.append(str(description_text))
    record_instance.append(date)

    log_category = record_instance[0]
    log_amount = record_instance[1]
    log_description = record_instance[2]
    log_date = record_instance[3]

    log_entry(
        chat_id=chat_id,
        user_id=user_id,
        log_cat=log_category,
        log_amt=log_amount,
        log_desc=log_description,
        date=log_date
    )

    record_instance.clear()

    await update.message.reply_text(
        # text=text,
        text=today_format(update, context),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    return ConversationHandler.END """


""" # Text formatting
def today_format(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    year_dict = dict_months(chat_id=chat_id, user_id=user_id)
    month_dict = year_dict[datetime.now().year]
    month = datetime.now().month
    date_dict = month_dict[month]

    money_fly = u"\U0001F4B8"
    text = "*Today's Expenses*\n"
    daily_total = 0.0
    counter = 1

    for date, log in sorted(date_dict.items(), key=lambda x: x[-1]):
        if date == datetime.now().day:
            # Sort log by ID
            log.sort(key=lambda x: x[0])

            # log tuple
            for id, desc, amt, cat in log:
                # daily calculation and text formatting
                daily_total += float(amt)
                text += f"*[ID {id}]* {desc}: {amt:.2f} *({cat})*\n"
                counter += 1

            # daily total text formatting
            if daily_total < 0:
                add_text = f"-${abs(round(daily_total, 2)):.2f}"
            else:
                add_text = f"${round(daily_total, 2):.2f}"

            text += f"\n{money_fly} *DAILY TOTAL: {add_text}*"

        else:
            continue
    
    return text


# Insert text formatting
def insert_format(update: Update, context: ContextTypes.DEFAULT_TYPE, date: datetime) -> str:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    year_dict = dict_months(chat_id=chat_id, user_id=user_id)
    month_dict = year_dict[datetime.now().year]
    month = datetime.now().month
    date_dict = month_dict[month]

    date_string = date.strftime('%d-%m-%Y')
    date_string = date_string.split("-")

    money_fly = u"\U0001F4B8"
    text = f"*{date_string[0]} {parse_month(int(date_string[1]))} Expenses*\n"
    daily_total = 0.0
    counter = 1

    log = date_dict[int(date_string[0])]
    for id, desc, amt, cat in log:
        # Sort log by ID
        log.sort(key=lambda x: x[0])

        # daily calculation and text formatting
        daily_total += float(amt)
        text += f"*[ID {id}]* {desc}: {amt:.2f} *({cat})*\n"
        counter += 1

    # daily total text formatting
    if daily_total < 0:
        add_text = f"-${abs(round(daily_total, 2)):.2f}"
    else:
        add_text = f"${round(daily_total, 2):.2f}"

    text += f"\n{money_fly} *DAILY TOTAL: {add_text}*"
    
    return text 
    
# Delete Utils
DELETE_FUNC = 0

# Start function for Delete
async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id

    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send the ID of the entry you want deleted",
        )
    
    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return DELETE_FUNC

# Delete entry action
async def delete_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text
    delete = delete_entry_db(int(update.message.text))

    if delete:
        message = await update.message.reply_text(
            text=f"Successfully deleted *ID {text}*!",
            parse_mode="Markdown"
            )
    else:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to delete *ID {text}*!",
            parse_mode="Markdown"
            )
        
    message_id = context.user_data.get("message_id")
    await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    await update.message.delete()

    message_id = message.message_id
    context.user_data["message_id"] = message_id

    return ConversationHandler.END
"""
############################################################################################################