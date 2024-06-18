import matplotlib.pyplot as plt
from schema import Chat, User, Needly
import calendar
from datetime import datetime

def create_line_graph(user_id, year, month):
    # Assuming database models and utility functions are properly set
    # Query the daily expenditures for the given user and month
    # Placeholder for database query results
    expenditures = ...  # Query logic goes here

    # Extract days and expenditure amounts
    days = [expenditure.day for expenditure in expenditures]
    amounts = [expenditure.amount for expenditure in expenditures]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(days, amounts, marker='o', linestyle='-', color='b')
    plt.title(f"Daily Expenditures for {calendar.month_name[month]} {year}")
    plt.xlabel('Day')
    plt.ylabel('Expenditure')
    plt.xticks(days)  # Adjust this as needed
    plt.grid(True)

    # Save the plot
    filename = f"Stats/Linegraph/Single Use/linegraph_{user_id}_{month}_{year}.png"
    plt.savefig(filename)
    plt.close()

    return filename
