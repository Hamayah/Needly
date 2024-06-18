from peewee import JOIN, fn
import matplotlib.pyplot as plt
from datetime import datetime
from schema import Chat, User, Needly
import locale

# Assuming you have the necessary imports and the database is properly initialized

def create_pie_chart(start_date, end_date):
    # Set the locale to use the user's default locale for currency formatting
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')

    # Query data within the date range
    query = (
        Needly
        .select(Needly.log_cat, fn.SUM(Needly.log_amt).alias('total_amt'))
        .join(User, on=(Needly.user == User.id))
        .where((Needly.date >= start_date) & (Needly.date <= end_date))
        .group_by(Needly.log_cat)
    )

    # Calculate total log_amt
    total_amt = sum(entry.total_amt for entry in query)

    # Extract data for the pie chart
    labels = []
    sizes = []
    for entry in query:
        labels.append(entry.log_cat)
        sizes.append(entry.total_amt / total_amt * 100)

    # Set a larger figure size
    fig = plt.figure(figsize=(10, 9))

    # Plotting the pie chart
    ax = plt.gca()
    ax.pie(
        sizes, 
        labels=labels, 
        autopct=lambda p: f'{p:.2f}%\n{locale.currency(total_amt * p / 100, grouping=True)[1:]}',
        pctdistance=0.85,
        startangle=160
    )

    # Set background color using hex code
    fig.patch.set_facecolor("#F6F8FA")

    # plt.axis('equal')  # Equal aspect ratio ensures the pie chart is circular
    plt.title(f"Spending breakdown from {start_date.strftime('%d')} to {end_date.strftime('%d %B')}")
    
    # Display the total amount outside the pie chart
    plt.text(0, 0, f'Total Amount Spent: {locale.currency(total_amt, grouping=True)[1:]}', bbox=dict(facecolor='white', alpha=0.65), ha='center')

    # Automatically adjust subplot parameters for better spacing
    plt.tight_layout()

    # Save the figure with an extended bounding box for better spacing
    plt.savefig('Stats/Pie/Single use/pie_chart.png', bbox_inches='tight')

    # plt.show()

    dir_path = "Stats/Pie/Single use/pie_chart.png"

    return dir_path
