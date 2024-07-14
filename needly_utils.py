from datetime import datetime, time, timedelta
from peewee import fn
from schema import Chat, User, Needly
from secret import TM_TOKEN
from binance.spot import Spot as Client
import tradermade as tm
import random
import json
import calendar
import requests


def register_user(chat_id: int, user_id: int) -> bool:
    chat, _ = Chat.get_or_create(chat_id=chat_id)
    user, registered = User.get_or_create(user_id=user_id)

    return registered


def reset_needly_display_order():
    chats = Chat.select()
    for chat in chats:
        # Fetch all Needly records for a chat, ordered by the current ID or another relevant field
        needly_records = Needly.select().where(Needly.chat == chat).order_by(Needly.date.asc())

        # Update each record with a new display_id in sequential order
        for index, record in enumerate(needly_records, start=1):
            record.display_id = index
            record.save()  # Save the update to the database


def log_entry(chat_id: int, user_id: int, log_cat: str, log_amt: float, log_desc: str, date: datetime) -> Needly:
    chat, _ = Chat.get_or_create(chat_id=chat_id)
    user, _ = User.get_or_create(user_id=user_id)

    log = Needly.create(chat=chat, user=user, log_cat=log_cat.upper(), log_amt=log_amt,
                        log_desc=log_desc, date=date)
    
    reset_needly_display_order() # Reset the display order after deleting a record

    return log

def record_entry(chat_id: int, user_id: int, log_cat: str, log_amt: float, log_desc: str, date: datetime) -> Needly:
    chat, _ = Chat.get_or_create(chat_id=chat_id)
    user, _ = User.get_or_create(user_id=user_id)

    log = Needly.create(chat=chat, user=user, log_cat=log_cat.upper(), log_amt=log_amt,
                        log_desc=log_desc, date=date)

    reset_needly_display_order() # Reset the display order after deleting a record

    return log

""" # Entries
entries = [
    ("SHOPPING", -314.92, "HYROX", "01 July 2024"),
    ("GROCERIES", -1.40, "Pringle", "01 July 2024"),
    ("SUBSCRIPTIONS", -28.08, "ChatGPT", "02 July 2024"),
    ("TRANSPORT", -12.20, "Gojek", "04 July 2024"),
    ("LEISURE", -89.00, "Golf", "04 July 2024"),
    ("SHOPPING", -55.00, "Golf balls", "04 July 2024"),
    ("TRANSPORT", -17.56, "Ryde", "04 July 2024"),
    ("FOOD", -7.60, "Yew Kee", "06 July 2024"),
    ("SHOPPING", -4.22, "Golf tee", "06 July 2024"),
    ("FOOD", -1.90, "Zi Char", "06 July 2024"),
    ("LEISURE", -5.00, "Shoe rental", "07 July 2024"),
    ("TRANSPORT", -18.80, "Grab", "07 July 2024"),
    ("DRINK", -10.00, "Playmade", "07 July 2024"),
    ("FOOD", -39.45, "Tun Xiang Hokkien Delights", "07 July 2024"),
    ("TRANSPORT", -15.40, "Gojek", "09 July 2024"),
    ("TRANSPORT", -8.80, "Gojek", "09 July 2024"),
    ("SHOPPING", -5.78, "Golf Tees", "10 July 2024"),
    ("FOOD", -11.20, "GYG", "10 July 2024"),
    ("FOOD", -3.75, "Mcflurry", "10 July 2024"),
    ("FOOD", -5.75, "Hom Aroy", "11 July 2024"),
    ("SHOPPING", -12.00, "Steam", "13 July 2024"),
    ("FOOD", -4.75, "Banana", "13 July 2024"),
    ("FOOD", -5.00, "Doritos", "13 July 2024"),
    ("FOOD", -32.40, "TFF", "13 July 2024"),
    ("LEISURE", -50.00, "PC Pro fee", "13 July 2024"),
    ("LEISURE", -10.10, "SG Pools", "14 July 2024"),
    ("SUBSCRIPTION", -5.98, "Spotify", "14 July 2024")
]

# Log each entry
for log_cat, log_amt, log_desc, date_str in entries:
    date = datetime.strptime(date_str, "%d %B %Y")
    print('logging log_desc:', log_desc, 'date:', date)
    log_entry(227383722, 227383722, log_cat, log_amt, log_desc, date) """


def delete_entry_db(del_id: int) -> tuple:
    delete = Needly.delete().where(Needly.display_id==del_id).execute()
    # delete = Needly.delete().where(del_id).execute()

    reset_needly_display_order() # Reset the display order after deleting a record

    return delete


def db_get_by_id(display_id: int):
    requested_entry = Needly.select(Needly.log_cat, Needly.log_amt, Needly.log_desc).where(Needly.display_id == display_id)

    result = []

    #0 = Description, #1 = Amount, #2 = Category
    for entry in requested_entry:
        result.append(entry.log_desc)
        result.append(entry.log_amt)
        result.append(entry.log_cat)

    return result


def dict_months(chat_id: int, user_id: int) -> dict:
    chat, chat_created = Chat.get_or_create(chat_id=chat_id)
    user, _ = User.get_or_create(user_id=user_id)

    if chat_created:
        return []

    chat_month = Needly.select(
        Needly.display_id,
        Needly.log_cat,
        Needly.log_amt,
        Needly.log_desc,
        Needly.date).where(Needly.chat == chat)

    year_dict = {}
    month_dict = {}

    for entry in chat_month:
        date_string = entry.date.strftime('%d-%m-%Y')
        date = date_string.split('-')
        get_date, get_month, get_year = date[0], date[1], date[2]

        get_date, get_month, get_year = int(get_date), int(get_month), int(get_year)

        if get_year not in month_dict:
            month_dict[get_year] = {}

        if get_month not in month_dict[get_year]:
            month_dict[get_year][get_month] = {}

        if get_date not in month_dict[get_year][get_month]:
            month_dict[get_year][get_month][get_date] = []

        month_dict[get_year][get_month][get_date].append(
            (entry.display_id, entry.log_desc, entry.log_amt, entry.log_cat))

    return month_dict


def parse_month(month_no) -> str:
    months = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
              7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}

    for number, month in months.items():
        if month_no == number:
            return month

    return "Incorrect Month Number!"


def parse_month_no(month_str) -> int:
    # Normalize the input string to lowercase to make the function case-insensitive
    month_str = month_str.lower()

    # Define a dictionary mapping both full month names and abbreviations to their month numbers
    months = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }

    # Attempt to get the month number from the dictionary using the normalized month string
    # Return the month number if found, otherwise return a default value or raise an error
    return months.get(month_str, "Incorrect Month!")


def get_month_dates(month_name, year):
    # Convert month name to month number
    month_number = list(calendar.month_name).index(month_name.capitalize())

    # Calculate the number of days in the month
    _, last_day = calendar.monthrange(year, month_number)

    # Create start and end dates
    start_date = datetime(year, month_number, 1)
    end_date = datetime(year, month_number, last_day, 23, 59, 59)

    return start_date, end_date


def get_weeks_in_month(year, month):
    # Get the first day of the month
    first_day = datetime(year, month, 1)
    
    # Get the last day of the month
    if month == 12:
        last_day = datetime(year, month, 31)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    # Initialize a list to store the weeks
    weeks = []

    # Loop through the weeks of the month
    current_week = []
    current_day = first_day
    
    while current_day <= last_day:
        # Add the day and date to the current week
        current_week.append((current_day.strftime('%A'), current_day.day))
        
        # If it's the last day of the week, start a new week
        if current_day.weekday() == 6:
            weeks.append(current_week)
            current_week = []
        
        # Move to the next day
        current_day += timedelta(days=1)
    
    # Add the last week if it's not empty
    if current_week:
        weeks.append(current_week)
    
    return weeks


# Formats a particular month's expense
def fetch_data(year, month, chat_id, user_id) -> dict:
    year_dict = dict_months(chat_id=chat_id, user_id=user_id)
    month_dict = year_dict[year]
    day_dict = month_dict.get(month, False)

    if day_dict == False:
        return None

    month_name = parse_month(month)
    weeks = get_weeks_in_month(year, month)

    money_fly = u"\U0001F4B8"
    money_bag = u"\U0001F4B0"
    thinking_face = u"\U0001F914"
    calendar_emoji = u"\U0001F4C5"
    stock_rising = u'\U0001F4C8'

    fun_replies = ["No expenses logged on this day!", 
                   "Wow that's surprising, you didn't spend any money", 
                   "No way you didn't spend any money...", 
                   "That's cap", 
                   "No money flowed out of your account?!",
                   "Wow that's a first, not a single cent spent"]

    res_dict = {}
    month_total = 0.0
    for i, week in enumerate(weeks, start=1):
        week_total = 0.0
        if i not in res_dict:
            res_dict[i] = f"*Week {i}/{len(weeks)} of {month_name}{calendar_emoji}*\n\n"
        
        for day, date in week:
            day_total = 0.0
            res_dict[i] += f"*{date} {month_name} ({day})*\n"
            entry = day_dict.get(date, False)

            if entry == False:
                if datetime(year, month, date) > datetime.now():
                    res_dict[i] += f"You have yet to log a future expense! {thinking_face}\n\n"

                else: 
                    rng = random.randint(0, len(fun_replies) - 1)
                    res_dict[i] += f"{fun_replies[rng]} {thinking_face}\n\n"

            else:
                # Sort entry by Display ID
                entry.sort(key=lambda x: x[0])
                for data in entry:
                    id = data[0]
                    description = data[1]
                    amount = data[2]
                    cat = data[3]

                    day_total += amount

                    res_dict[i] += f"*[ID. {id}]* {description}: {amount:.2f} *[{cat}]*\n"
                
                res_dict[i] += f"{money_fly}*Daily Total = {day_total:.2f}*\n\n"
            
            week_total += day_total

        res_dict[i] += f"{money_bag}*Weekly Total = {week_total:.2f}*\n"

        month_total += week_total
        res_dict[i] += f"{stock_rising}*Cumulative Total = {month_total:.2f}*"

    return res_dict


def get_forex(ticker):
    tm.set_rest_api_key(TM_TOKEN)

    request_currency = tm.live(currency=ticker, fields = ["mid"]).at[0, "mid"]
    return request_currency


def get_btc_price():
    # Send request to CoinDesk API
    response = requests.get('https://api.coindesk.com/v1/bpi/currentprice.json')
    data = response.json()
    
    # Access the Bitcoin rate in USD
    bitcoin_rate_str = data["bpi"]["USD"]["rate"].replace(',', '')
    bitcoin_rate_float = float(bitcoin_rate_str)

    # Format the float back to a string with commas for visibility
    bitcoin_rate_formatted = "{:,.2f}".format(bitcoin_rate_float)

    return bitcoin_rate_float, bitcoin_rate_formatted


def get_crypto_price(tickers):
    try:
        spot_client = Client(base_url="https://testnet.binance.vision")
        
        if len(tickers) == 1:
            response = spot_client.ticker_price(symbol=tickers[0])
        else:
            response = spot_client.ticker_price(symbols=tickers)

    except Exception as e:
        return None

    return response


############################################################################################################
# Deprecated Functions
""" def filter_week(chat_id: int, user_id: int) -> dict:
    chat, chat_created = Chat.get_or_create(chat_id=chat_id)
    user, _ = User.get_or_create(user_id=user_id)
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    start_of_week = start_of_week.strftime('%d-%m-%Y')
    start_of_week = datetime.strptime(start_of_week, '%d-%m-%Y')

    if chat_created:
        return []

    chat_month = Needly.select(
        Needly.display_id,
        Needly.log_cat,
        Needly.log_amt,
        Needly.log_desc,
        Needly.date).where(
            (Needly.chat == chat) &
            (Needly.date.between(start_of_week, datetime.now()))
        )

    month_dict = {}

    for entry in chat_month:
        date_string = entry.date.strftime('%d-%m-%Y')
        date = date_string.split('-')
        get_date, get_month, get_year = date[0], date[1], date[2]

        get_date, get_month, get_year = int(get_date), int(get_month), int(get_year)

        if get_year not in month_dict:
            month_dict[get_year] = {}

        if get_month not in month_dict[get_year]:
            month_dict[get_year][get_month] = {}

        if get_date not in month_dict[get_year][get_month]:
            month_dict[get_year][get_month][get_date] = []

        month_dict[get_year][get_month][get_date].append(
            (entry.id, entry.log_desc, entry.log_amt, entry.log_cat))

    return month_dict """


""" def within_week(date) -> bool:
    within_week = False
    start_of_week = datetime.now() - timedelta(days=datetime.now().weekday())
    if 0 <= int(date) - start_of_week.day <= 7 or -23 <= int(date) - start_of_week.day <= -26:
        within_week = True
        return within_week

    elif -26 <= int(date) - start_of_week.day <= -23:
        within_week = True
        return within_week

    return within_week """
############################################################################################################