import csv
import os
from datetime import datetime


# ============================================================
# AI EYES - ACCESS HISTORY MODULE
# ============================================================

HISTORY_FILE = "access_history.csv"


# ============================================================
# CREATE HISTORY FILE
# ============================================================

def initialize_history():

    if not os.path.exists(HISTORY_FILE):

        with open(
            HISTORY_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "Date",
                "Time",
                "Name",
                "Access Status",
                "Confidence"
            ])

        print("✅ Access history file created")


# ============================================================
# SAVE ACCESS EVENT
# ============================================================

def save_access(
    name,
    status,
    confidence
):

    initialize_history()

    now = datetime.now()

    date = now.strftime(
        "%Y-%m-%d"
    )

    time = now.strftime(
        "%H:%M:%S"
    )


    with open(
        HISTORY_FILE,
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            date,
            time,
            name,
            status,
            f"{confidence:.3f}"
        ])


# ============================================================
# READ ALL HISTORY
# ============================================================

def get_all_history():

    initialize_history()

    history = []

    with open(
        HISTORY_FILE,
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        for row in reader:

            history.append(row)

    return history


# ============================================================
# DISPLAY ALL HISTORY
# ============================================================

def show_all_history():

    history = get_all_history()


    if not history:

        print("\n📋 No access history available.")

        return


    print("\n")
    print("=" * 90)
    print("                 AI EYES - ACCESS HISTORY")
    print("=" * 90)


    print(
        f"{'Date':<12}"
        f"{'Time':<10}"
        f"{'Name':<20}"
        f"{'Status':<18}"
        f"{'Confidence':<12}"
    )

    print("-" * 90)


    for row in history:

        print(
            f"{row['Date']:<12}"
            f"{row['Time']:<10}"
            f"{row['Name']:<20}"
            f"{row['Access Status']:<18}"
            f"{row['Confidence']:<12}"
        )


    print("=" * 90)


# ============================================================
# TODAY'S HISTORY
# ============================================================

def show_today_history():

    history = get_all_history()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    today_history = [

        row

        for row in history

        if row["Date"] == today

    ]


    if not today_history:

        print("\n📋 No access activity today.")

        return


    print("\n")
    print("=" * 90)
    print("              TODAY'S ACCESS HISTORY")
    print("=" * 90)


    print(
        f"{'Time':<10}"
        f"{'Name':<20}"
        f"{'Status':<18}"
        f"{'Confidence':<12}"
    )

    print("-" * 90)


    for row in today_history:

        print(
            f"{row['Time']:<10}"
            f"{row['Name']:<20}"
            f"{row['Access Status']:<18}"
            f"{row['Confidence']:<12}"
        )


    print("=" * 90)


# ============================================================
# SEARCH BY PERSON
# ============================================================

def search_person():

    name = input(
        "\nEnter person name: "
    ).strip()


    history = get_all_history()


    results = [

        row

        for row in history

        if row["Name"].lower()
        == name.lower()

    ]


    if not results:

        print(
            f"\n❌ No history found for {name}"
        )

        return


    print("\n")
    print("=" * 90)
    print(
        f"       ACCESS HISTORY - {name}"
    )
    print("=" * 90)


    print(
        f"{'Date':<12}"
        f"{'Time':<10}"
        f"{'Status':<18}"
        f"{'Confidence':<12}"
    )

    print("-" * 90)


    for row in results:

        print(
            f"{row['Date']:<12}"
            f"{row['Time']:<10}"
            f"{row['Access Status']:<18}"
            f"{row['Confidence']:<12}"
        )


    print("=" * 90)


# ============================================================
# SHOW STATISTICS
# ============================================================

def show_statistics():

    history = get_all_history()


    total = len(history)


    granted = sum(
        1
        for row in history
        if row["Access Status"]
        == "GRANTED"
    )


    denied = sum(
        1
        for row in history
        if row["Access Status"]
        == "DENIED"
    )


    unknown = sum(
        1
        for row in history
        if row["Name"].lower()
        == "unknown"
    )


    print("\n")
    print("=" * 50)
    print("          AI EYES - STATISTICS")
    print("=" * 50)


    print(
        f"📊 Total Events       : {total}"
    )

    print(
        f"🟢 Access Granted     : {granted}"
    )

    print(
        f"🔴 Access Denied      : {denied}"
    )

    print(
        f"❓ Unknown Attempts   : {unknown}"
    )


    print("=" * 50)


# ============================================================
# DELETE ALL HISTORY
# ============================================================

def delete_history():

    print("\n⚠️ WARNING")
    print(
        "This will permanently delete "
        "all access history."
    )


    confirmation = input(
        "\nType DELETE to confirm: "
    ).strip()


    if confirmation != "DELETE":

        print(
            "\n❌ Delete cancelled."
        )

        return


    if os.path.exists(HISTORY_FILE):

        os.remove(
            HISTORY_FILE
        )


    initialize_history()


    print(
        "\n🗑️ Access history deleted."
    )


# ============================================================
# MENU
# ============================================================

def menu():

    initialize_history()


    while True:

        print("\n")
        print("=" * 50)
        print("             🤖 AI EYES")
        print("          ACCESS HISTORY")
        print("=" * 50)

        print(
            "1. 📋 View All History"
        )

        print(
            "2. 📅 View Today's History"
        )

        print(
            "3. 👤 Search Person"
        )

        print(
            "4. 📊 View Statistics"
        )

        print(
            "5. 🗑️ Delete History"
        )

        print(
            "6. 🚪 Exit"
        )

        print("=" * 50)


        choice = input(
            "Enter your choice: "
        ).strip()


        if choice == "1":

            show_all_history()


        elif choice == "2":

            show_today_history()


        elif choice == "3":

            search_person()


        elif choice == "4":

            show_statistics()


        elif choice == "5":

            delete_history()


        elif choice == "6":

            print(
                "\n👋 Access History closed."
            )

            break


        else:

            print(
                "\n❌ Invalid choice."
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    menu()