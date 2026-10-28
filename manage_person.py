import pickle
import os


# ==========================================
# AI EYES - ADMIN PANEL
# ==========================================

DATABASE_FILE = "face_database.pkl"


# ==========================================
# LOAD DATABASE
# ==========================================

def load_database():

    if not os.path.exists(DATABASE_FILE):

        print("\n❌ face_database.pkl not found")

        print(
            "👉 First register at least one person."
        )

        return []

    try:

        with open(
            DATABASE_FILE,
            "rb"
        ) as f:

            database = pickle.load(f)

        # ----------------------------------
        # Add active status to old records
        # ----------------------------------

        for person in database:

            if "active" not in person:

                person["active"] = True

        return database

    except Exception as e:

        print("\n❌ Database loading failed")
        print(e)

        return []


# ==========================================
# SAVE DATABASE
# ==========================================

def save_database(database):

    try:

        with open(
            DATABASE_FILE,
            "wb"
        ) as f:

            pickle.dump(
                database,
                f
            )

        return True

    except Exception as e:

        print("\n❌ Database save failed")
        print(e)

        return False


# ==========================================
# VIEW PEOPLE
# ==========================================

def view_people(database):

    print("\n")
    print("=" * 55)
    print("              REGISTERED PEOPLE")
    print("=" * 55)

    if len(database) == 0:

        print("\n❌ No registered people")

        return


    print(
        f"\n{'No.':<6}"
        f"{'Name':<20}"
        f"{'Faces':<10}"
        f"{'Status':<12}"
    )

    print("-" * 55)


    for index, person in enumerate(
        database,
        start=1
    ):

        name = person.get(
            "name",
            "Unknown"
        )

        embeddings = person.get(
            "embeddings",
            []
        )

        active = person.get(
            "active",
            True
        )


        if active:

            status = "ACTIVE"

        else:

            status = "DISABLED"


        print(
            f"{index:<6}"
            f"{name:<20}"
            f"{len(embeddings):<10}"
            f"{status:<12}"
        )


    print("-" * 55)

    print(
        f"Total people: {len(database)}"
    )


# ==========================================
# FIND PERSON
# ==========================================

def find_person(database):

    if len(database) == 0:

        print("\n❌ No registered people")

        return None


    name = input(
        "\nEnter person name:\n> "
    ).strip()


    if not name:

        print("\n❌ Name cannot be empty")

        return None


    for person in database:

        if (
            person.get("name", "")
            .lower()
            == name.lower()
        ):

            return person


    print(
        f"\n❌ Person '{name}' not found."
    )

    return None


# ==========================================
# DISABLE PERSON
# ==========================================

def disable_person(database):

    print("\n")
    print("=" * 55)
    print("              DISABLE PERSON")
    print("=" * 55)


    person = find_person(database)


    if person is None:

        return


    if not person.get(
        "active",
        True
    ):

        print(
            f"\n⚠️ {person['name']} "
            "is already disabled."
        )

        return


    print(
        f"\n👤 Person: {person['name']}"
    )

    print(
        "\nThis person will no longer "
        "receive access."
    )


    confirm = input(
        "\nDisable this person? (yes/no):\n> "
    ).strip().lower()


    if confirm != "yes":

        print(
            "\n❌ Operation cancelled"
        )

        return


    person["active"] = False


    if save_database(database):

        print(
            f"\n🔒 {person['name']} "
            "has been DISABLED."
        )

        print(
            "❌ Access will be denied."
        )


# ==========================================
# ENABLE PERSON
# ==========================================

def enable_person(database):

    print("\n")
    print("=" * 55)
    print("              ENABLE PERSON")
    print("=" * 55)


    person = find_person(database)


    if person is None:

        return


    if person.get(
        "active",
        True
    ):

        print(
            f"\n⚠️ {person['name']} "
            "is already active."
        )

        return


    print(
        f"\n👤 Person: {person['name']}"
    )


    confirm = input(
        "\nEnable this person? (yes/no):\n> "
    ).strip().lower()


    if confirm != "yes":

        print(
            "\n❌ Operation cancelled"
        )

        return


    person["active"] = True


    if save_database(database):

        print(
            f"\n🔓 {person['name']} "
            "has been ENABLED."
        )

        print(
            "✅ Access is now allowed."
        )


# ==========================================
# DELETE PERSON
# ==========================================

def delete_person(database):

    print("\n")
    print("=" * 55)
    print("              DELETE PERSON")
    print("=" * 55)


    person = find_person(database)


    if person is None:

        return


    print(
        f"\n⚠️ Person: {person['name']}"
    )

    print(
        f"📸 Stored face images: "
        f"{len(person.get('embeddings', []))}"
    )

    print(
        "\n⚠️ This will permanently remove "
        "this person's face embeddings."
    )


    confirm = input(
        "\nType DELETE to confirm:\n> "
    ).strip()


    if confirm != "DELETE":

        print(
            "\n❌ Delete cancelled"
        )

        return


    database.remove(person)


    if save_database(database):

        print(
            f"\n🗑️ {person['name']} "
            "has been permanently deleted."
        )


# ==========================================
# MAIN ADMIN MENU
# ==========================================

def main():

    database = load_database()


    # Make sure database records have active
    for person in database:

        if "active" not in person:

            person["active"] = True


    while True:

        print("\n")

        print("=" * 55)
        print("             AI EYES ADMIN PANEL")
        print("=" * 55)

        print("\n1. View Registered People")
        print("2. Disable Person")
        print("3. Enable Person")
        print("4. Delete Person")
        print("5. Exit")


        choice = input(
            "\nEnter choice:\n> "
        ).strip()


        # ----------------------------------
        # VIEW
        # ----------------------------------

        if choice == "1":

            view_people(database)


        # ----------------------------------
        # DISABLE
        # ----------------------------------

        elif choice == "2":

            disable_person(database)


        # ----------------------------------
        # ENABLE
        # ----------------------------------

        elif choice == "3":

            enable_person(database)


        # ----------------------------------
        # DELETE
        # ----------------------------------

        elif choice == "4":

            delete_person(database)


        # ----------------------------------
        # EXIT
        # ----------------------------------

        elif choice == "5":

            print(
                "\n👋 AI EYES Admin Panel closed."
            )

            break


        else:

            print(
                "\n❌ Invalid choice."
            )

            print(
                "👉 Please enter 1, 2, 3, 4 or 5."
            )


# ==========================================
# START PROGRAM
# ==========================================

if __name__ == "__main__":

    main()