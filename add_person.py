import cv2
import pickle
import os
import numpy as np
import time


# ==========================================
# AI EYES - ADD NEW PERSON
# ==========================================

print("=" * 45)
print("          AI EYES REGISTRATION")
print("=" * 45)


# ==========================================
# MODEL PATHS
# ==========================================

DETECTOR_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "models/face_recognition_sface_2021dec.onnx"
DATABASE_FILE = "face_database.pkl"


# ==========================================
# SETTINGS
# ==========================================

FACE_DETECTION_CONFIDENCE = 0.5
NMS_THRESHOLD = 0.3
MAX_FACES = 5000

DUPLICATE_THRESHOLD = 0.45

# Camera face must remain stable for this many seconds
STABLE_SECONDS = 2.0


# ==========================================
# CHECK MODEL FILES
# ==========================================

if not os.path.exists(DETECTOR_MODEL):

    print("\n❌ YuNet model not found:")
    print(DETECTOR_MODEL)
    exit()


if not os.path.exists(RECOGNIZER_MODEL):

    print("\n❌ SFace model not found:")
    print(RECOGNIZER_MODEL)
    exit()


# ==========================================
# LOAD MODELS
# ==========================================

print("\n🔄 Loading AI models...")

detector = cv2.FaceDetectorYN.create(
    DETECTOR_MODEL,
    "",
    (640, 480),
    FACE_DETECTION_CONFIDENCE,
    NMS_THRESHOLD,
    MAX_FACES
)

recognizer = cv2.FaceRecognizerSF.create(
    RECOGNIZER_MODEL,
    ""
)

print("✅ YuNet face detector loaded")
print("✅ SFace face recognizer loaded")


# ==========================================
# LOAD DATABASE
# ==========================================

if os.path.exists(DATABASE_FILE):

    try:

        with open(DATABASE_FILE, "rb") as f:
            database = pickle.load(f)

        print(
            f"👥 Existing registered people: "
            f"{len(database)}"
        )

    except Exception as e:

        print("\n❌ Could not load database")
        print(e)
        exit()

else:

    database = []

    print("ℹ️ No existing database found")
    print("🆕 New database will be created")


# ==========================================
# ENTER PERSON NAME
# ==========================================

print("\n============================================")

person_name = input(
    "\nEnter person name:\n> "
).strip()


if not person_name:

    print("\n❌ Name cannot be empty")
    exit()


# ==========================================
# REGISTRATION MENU
# ==========================================

print("\nChoose registration method:\n")

print("1. Upload Photo")
print("2. Capture Photo using Camera")
print("3. Exit")


choice = input(
    "\nEnter choice:\n> "
).strip()


if choice == "3":

    print("\n👋 Registration cancelled")
    exit()


# ==========================================
# FUNCTION
# GET FACE EMBEDDING
# ==========================================

def get_embedding(image):

    if image is None:

        return None


    # --------------------------------------
    # Resize small image
    # --------------------------------------

    height, width = image.shape[:2]

    if width < 400:

        new_width = 400

        new_height = int(
            height * (400 / width)
        )

        image = cv2.resize(
            image,
            (new_width, new_height)
        )


    # --------------------------------------
    # Set detector input size
    # --------------------------------------

    h, w = image.shape[:2]

    detector.setInputSize(
        (w, h)
    )


    # --------------------------------------
    # Detect faces
    # --------------------------------------

    _, faces = detector.detect(image)


    if faces is None or len(faces) == 0:

        return None


    # --------------------------------------
    # Select largest face
    # --------------------------------------

    largest_face = None
    largest_area = 0


    for face in faces:

        x, y, fw, fh = face[:4]

        area = fw * fh

        if area > largest_area:

            largest_area = area
            largest_face = face


    if largest_face is None:

        return None


    # --------------------------------------
    # Align face using SFace
    # --------------------------------------

    try:

        aligned_face = recognizer.alignCrop(
            image,
            largest_face
        )

    except Exception as e:

        print("❌ Face alignment failed")
        print(e)

        return None


    # --------------------------------------
    # Generate embedding
    # --------------------------------------

    try:

        feature = recognizer.feature(
            aligned_face
        )

    except Exception as e:

        print("❌ Feature extraction failed")
        print(e)

        return None


    return feature


# ==========================================
# FUNCTION
# CHECK DUPLICATE
# ==========================================

def check_duplicate(new_feature):

    highest_score = 0.0
    matched_name = None


    if len(database) == 0:

        return None, 0.0


    for person in database:

        name = person["name"]

        embeddings = person["embeddings"]


        for stored_feature in embeddings:

            try:

                score = recognizer.match(
                    new_feature,
                    stored_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

            except Exception:

                continue


            if score > highest_score:

                highest_score = score
                matched_name = name


    return matched_name, highest_score


# ==========================================
# OPTION 1
# UPLOAD PHOTO
# ==========================================

if choice == "1":

    print("\n============================================")
    print("             UPLOAD PHOTO")
    print("============================================")


    image_path = input(
        "\nEnter image path:\n> "
    ).strip().strip('"')


    # --------------------------------------
    # Check file
    # --------------------------------------

    if not os.path.exists(image_path):

        print("\n❌ Image not found")
        print(image_path)

        exit()


    # --------------------------------------
    # Read image
    # --------------------------------------

    image = cv2.imread(image_path)


    if image is None:

        print("\n❌ Could not read image")

        exit()


    print("\n🔍 Detecting face...")


    # --------------------------------------
    # Generate embedding
    # --------------------------------------

    feature = get_embedding(image)


    if feature is None:

        print("\n❌ No usable face detected")

        print(
            "👉 Please use a clear photo "
            "with one visible face."
        )

        exit()


    print("✅ Face detected")
    print("✅ Face embedding generated")


# ==========================================
# OPTION 2
# CAMERA REGISTRATION
# ==========================================

elif choice == "2":

    print("\n============================================")
    print("          CAMERA REGISTRATION")
    print("============================================")


    print("\n📷 Opening camera...")

    print("\nInstructions:")
    print("👉 Look directly at the camera")
    print("👉 Keep only ONE face in the camera")
    print("👉 Keep your face inside the green box")
    print("👉 Hold your face still")
    print("👉 Automatic capture will happen")
    print("👉 Press Q to cancel")


    # --------------------------------------
    # Open camera
    # --------------------------------------

    cap = cv2.VideoCapture(
        0,
        cv2.CAP_DSHOW
    )


    if not cap.isOpened():

        print("\n❌ Camera could not be opened")

        print(
            "Try changing VideoCapture(0) "
            "to VideoCapture(1)"
        )

        exit()


    feature = None

    face_start_time = None


    # ======================================
    # CAMERA LOOP
    # ======================================

    while True:

        success, frame = cap.read()


        if not success:

            print("\n❌ Could not read camera")

            break


        display = frame.copy()


        # ----------------------------------
        # Frame dimensions
        # ----------------------------------

        h, w = frame.shape[:2]


        # ----------------------------------
        # Detector input size
        # ----------------------------------

        detector.setInputSize(
            (w, h)
        )


        # ----------------------------------
        # Detect face
        # ----------------------------------

        _, faces = detector.detect(
            frame
        )


        # ----------------------------------
        # Find largest face
        # ----------------------------------

        largest_face = None
        largest_area = 0


        if faces is not None:

            for face in faces:

                x, y, fw, fh = face[:4]

                area = fw * fh


                if area > largest_area:

                    largest_area = area
                    largest_face = face


        # ==================================
        # FACE DETECTED
        # ==================================

        if largest_face is not None:

            x, y, fw, fh = largest_face[:4]


            x = int(x)
            y = int(y)
            fw = int(fw)
            fh = int(fh)


            # --------------------------------
            # Draw green rectangle
            # --------------------------------

            cv2.rectangle(
                display,
                (x, y),
                (x + fw, y + fh),
                (0, 255, 0),
                3
            )


            # --------------------------------
            # Start timer
            # --------------------------------

            if face_start_time is None:

                face_start_time = time.time()


            elapsed = (
                time.time()
                - face_start_time
            )


            progress = min(
                elapsed / STABLE_SECONDS,
                1.0
            )


            percentage = int(
                progress * 100
            )


            # --------------------------------
            # Display status
            # --------------------------------

            cv2.putText(
                display,
                "FACE DETECTED",
                (x, max(y - 35, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            cv2.putText(
                display,
                f"Hold Still: {percentage}%",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (0, 255, 0),
                2
            )


            # --------------------------------
            # Progress bar
            # --------------------------------

            bar_x = 20
            bar_y = 65

            bar_width = 400
            bar_height = 25


            cv2.rectangle(
                display,
                (bar_x, bar_y),
                (
                    bar_x + bar_width,
                    bar_y + bar_height
                ),
                (255, 255, 255),
                2
            )


            filled_width = int(
                bar_width * progress
            )


            if filled_width > 0:

                cv2.rectangle(
                    display,
                    (bar_x, bar_y),
                    (
                        bar_x + filled_width,
                        bar_y + bar_height
                    ),
                    (0, 255, 0),
                    -1
                )


            # ==================================
            # AUTO CAPTURE
            # ==================================

            if elapsed >= STABLE_SECONDS:

                print("\n📸 AUTO CAPTURE STARTED")

                feature = get_embedding(
                    frame
                )


                if feature is not None:

                    print(
                        "✅ Face captured successfully!"
                    )

                    print(
                        "✅ Face embedding generated"
                    )

                    break


                else:

                    print(
                        "❌ Face processing failed"
                    )

                    print(
                        "👉 Trying again..."
                    )

                    face_start_time = None


        # ==================================
        # NO FACE
        # ==================================

        else:

            face_start_time = None


            cv2.putText(
                display,
                "NO FACE DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )


        # ----------------------------------
        # Bottom instruction
        # ----------------------------------

        cv2.putText(
            display,
            "Hold still - Auto Capture",
            (20, h - 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        cv2.putText(
            display,
            "Press Q to Exit",
            (20, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )


        # ----------------------------------
        # Show camera
        # ----------------------------------

        cv2.imshow(
            "AI EYES - Register Person",
            display
        )


        # ----------------------------------
        # Keyboard
        # Only Q required
        # ----------------------------------

        key = cv2.waitKey(1) & 0xFF


        if key == ord("q") or key == ord("Q"):

            print(
                "\n👋 Registration cancelled"
            )

            break


    # ======================================
    # CAMERA CLEANUP
    # ======================================

    cap.release()

    cv2.destroyAllWindows()


    # --------------------------------------
    # Check result
    # --------------------------------------

    if feature is None:

        print(
            "\n❌ No face was registered"
        )

        exit()


# ==========================================
# INVALID OPTION
# ==========================================

else:

    print("\n❌ Invalid choice")

    print("Please select 1, 2 or 3")

    exit()


# ==========================================
# DUPLICATE FACE CHECK
# ==========================================

print("\n============================================")
print("        CHECKING EXISTING FACES")
print("============================================")


matched_name, score = check_duplicate(
    feature
)


print(
    f"🔎 Highest similarity score: "
    f"{score:.4f}"
)


# ==========================================
# DUPLICATE FOUND
# ==========================================

if (
    matched_name is not None
    and score >= DUPLICATE_THRESHOLD
):

    print("\n⚠️ POSSIBLE DUPLICATE FACE")
    print("--------------------------------------------")

    print(
        f"Existing Person : {matched_name}"
    )

    print(
        f"Similarity Score: {score:.4f}"
    )

    print("--------------------------------------------")

    print(
        "\n❌ Registration cancelled"
    )

    print(
        "This face may already be registered."
    )

    exit()


# ==========================================
# CHECK IF NAME ALREADY EXISTS
# ==========================================

person_found = False


for person in database:

    if (
        person["name"].strip().lower()
        == person_name.lower()
    ):

        person["embeddings"].append(
            feature
        )

        person_found = True

        break


# ==========================================
# CREATE NEW PERSON
# ==========================================

if not person_found:

    database.append(
        {
            "name": person_name,
            "embeddings": [feature]
        }
    )


# ==========================================
# SAVE DATABASE
# ==========================================

try:

    with open(
        DATABASE_FILE,
        "wb"
    ) as f:

        pickle.dump(
            database,
            f
        )

except Exception as e:

    print("\n❌ Database save failed")

    print(e)

    exit()


# ==========================================
# SUCCESS
# ==========================================

print("\n")

print("=" * 45)
print("       REGISTRATION SUCCESS")
print("=" * 45)

print(
    f"👤 Name : {person_name}"
)


if person_found:

    print(
        "📸 Additional face image added"
    )

else:

    print(
        "🆕 New person registered"
    )


print(
    f"👥 Total registered people: "
    f"{len(database)}"
)


print(
    "\n💾 Database updated:"
)

print(
    "   face_database.pkl"
)


print(
    "\n🤖 SFace embedding saved successfully"
)


print(
    "\n✅ AI EYES is ready!"
)

print("=" * 45)