"""import cv2
import pickle
import numpy as np
import pyttsx3
import time

# ==========================================
# PATHS
# ==========================================

DETECTOR_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "models/face_recognition_sface_2021dec.onnx"
DATABASE_FILE = "face_database.pkl"


# ==========================================
# LOAD AI MODELS
# ==========================================

print("🔄 Loading AI models...")

detector = cv2.FaceDetectorYN.create(
    DETECTOR_MODEL,
    "",
    (640, 480),
    0.5,
    0.3,
    5000
)

recognizer = cv2.FaceRecognizerSF.create(
    RECOGNIZER_MODEL,
    ""
)

print("✅ AI models loaded")


# ==========================================
# LOAD FACE DATABASE
# ==========================================

with open(DATABASE_FILE, "rb") as file:
    face_database = pickle.load(file)

print("✅ Face database loaded")

for person in face_database:
    print(
        f"👤 {person['name']} "
        f"→ {len(person['embeddings'])} images"
    )


# ==========================================
# TEXT TO SPEECH
# ==========================================

engine = pyttsx3.init()

engine.setProperty(
    "rate",
    150
)


# ==========================================
# CAMERA
# ==========================================

cap = cv2.VideoCapture(0)

if not cap.isOpened():

    print("❌ Camera could not be opened")

    exit()


print("\n🎥 AI EYES started")
print("Press Q to quit")


# ==========================================
# VOICE CONTROL
# ==========================================

last_spoken_name = ""
last_spoken_time = 0

VOICE_DELAY = 5


# ==========================================
# FACE RECOGNITION
# ==========================================

while True:

    success, frame = cap.read()

    if not success:

        print("❌ Failed to read camera")

        break


    # --------------------------------------
    # Flip camera
    # --------------------------------------

    frame = cv2.flip(
        frame,
        1
    )


    # --------------------------------------
    # Get frame size
    # --------------------------------------

    height, width = frame.shape[:2]


    # --------------------------------------
    # Face detection
    # --------------------------------------

    detector.setInputSize(
        (width, height)
    )

    _, faces = detector.detect(frame)


    # --------------------------------------
    # Process detected faces
    # --------------------------------------

    if faces is not None:

        for face in faces:

            # ------------------------------
            # Draw bounding box
            # ------------------------------

            x, y, w, h = face[:4].astype(int)

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )


            # ------------------------------
            # Align face
            # ------------------------------

            aligned_face = recognizer.alignCrop(
                frame,
                face
            )


            # ------------------------------
            # Generate embedding
            # ------------------------------

            feature = recognizer.feature(
                aligned_face
            )


            # ------------------------------
            # Compare with database
            # ------------------------------

            best_name = "Unknown"
            best_score = -1


            for person in face_database:

                person_name = person["name"]

                for stored_feature in person["embeddings"]:

                    score = recognizer.match(
                        feature,
                        stored_feature,
                        cv2.FaceRecognizerSF_FR_COSINE
                    )


                    if score > best_score:

                        best_score = score

                        best_name = person_name


            # ------------------------------
            # Recognition threshold
            # ------------------------------

            THRESHOLD = 0.40


            if best_score >= THRESHOLD:

                status = f"ACCESS GRANTED: {best_name}"

                text_color = (0, 255, 0)


                # --------------------------
                # Voice
                # --------------------------

                current_time = time.time()

                if (
                    best_name != last_spoken_name
                    or
                    current_time - last_spoken_time > VOICE_DELAY
                ):

                    print(
                        f"🔓 Access Granted: "
                        f"{best_name}"
                    )

                    engine.say(
                        f"Welcome {best_name}"
                    )

                    engine.runAndWait()

                    last_spoken_name = best_name

                    last_spoken_time = current_time

            else:

                status = "ACCESS DENIED"

                text_color = (0, 0, 255)


            # ------------------------------
            # Display result
            # ------------------------------

            cv2.putText(
                frame,
                status,
                (x, max(y - 10, 30)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                text_color,
                2
            )


            # ------------------------------
            # Display confidence
            # ------------------------------

            score_text = f"Score: {best_score:.2f}"

            cv2.putText(
                frame,
                score_text,
                (x, y + h + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )


    # ======================================
    # DISPLAY CAMERA
    # ======================================

    cv2.imshow(
        "AI EYES - Smart Face Access",
        frame
    )


    # ======================================
    # QUIT
    # ======================================

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):

        break


# ==========================================
# CLEANUP
# ==========================================

cap.release()

cv2.destroyAllWindows()

engine.stop()

print("👋 AI EYES stopped")"""    


import cv2
import pickle
import os
import pyttsx3
import time
import threading
import queue


# ============================================================
# AI EYES - SMART FACE ACCESS CONTROL
# ============================================================

print("=" * 60)
print("              AI EYES")
print("        SMART FACE ACCESS SYSTEM")
print("=" * 60)


# ============================================================
# CONFIGURATION
# ============================================================

DETECTOR_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "models/face_recognition_sface_2021dec.onnx"
DATABASE_FILE = "face_database.pkl"

THRESHOLD = 0.40

# Number of continuous frames required before confirmation
REQUIRED_FRAMES = 3

# How long a person can disappear before considered "left"
LEAVE_TIMEOUT = 2.0

CAMERA_INDEX = 0


# ============================================================
# CHECK FILES
# ============================================================

if not os.path.exists(DETECTOR_MODEL):
    raise FileNotFoundError(
        f"❌ Detector model not found:\n{DETECTOR_MODEL}"
    )

if not os.path.exists(RECOGNIZER_MODEL):
    raise FileNotFoundError(
        f"❌ Recognizer model not found:\n{RECOGNIZER_MODEL}"
    )

if not os.path.exists(DATABASE_FILE):
    raise FileNotFoundError(
        f"❌ Face database not found:\n{DATABASE_FILE}"
    )


# ============================================================
# LOAD MODELS
# ============================================================

print("\n🔄 Loading AI models...")

detector = cv2.FaceDetectorYN.create(
    DETECTOR_MODEL,
    "",
    (640, 480),
    0.5,
    0.3,
    5000
)

recognizer = cv2.FaceRecognizerSF.create(
    RECOGNIZER_MODEL,
    ""
)

print("✅ Face Detection Model Loaded")
print("✅ Face Recognition Model Loaded")


# ============================================================
# LOAD DATABASE
# ============================================================

print("\n🔄 Loading face database...")

with open(DATABASE_FILE, "rb") as f:
    database = pickle.load(f)


# Make sure every person has active field
database_changed = False

for person in database:

    if "active" not in person:
        person["active"] = True
        database_changed = True


if database_changed:

    with open(DATABASE_FILE, "wb") as f:
        pickle.dump(database, f)

    print("💾 Database updated")


print(f"👥 Registered People: {len(database)}")

for person in database:

    name = person.get("name", "Unknown")
    active = person.get("active", True)

    status = "ACTIVE" if active else "DISABLED"

    print(f"   • {name} → {status}")


# ============================================================
# VOICE SYSTEM
# ============================================================

# IMPORTANT:
# pyttsx3 will run in a separate worker thread.
# Camera loop will NOT wait for voice.

voice_queue = queue.Queue()


def voice_worker():

    voice_engine = pyttsx3.init()

    # Faster speaking
    voice_engine.setProperty("rate", 170)

    # Maximum volume
    voice_engine.setProperty("volume", 1.0)

    print("🔊 Voice system ready")

    while True:

        message = voice_queue.get()

        # Shutdown signal
        if message is None:

            voice_queue.task_done()
            break

        try:

            print(f"🔊 Voice: {message}")

            voice_engine.say(message)

            voice_engine.runAndWait()

        except Exception as e:

            print(f"❌ Voice Error: {e}")

        finally:

            voice_queue.task_done()


# Start voice worker
voice_thread = threading.Thread(
    target=voice_worker,
    daemon=True
)

voice_thread.start()


def speak(message):

    # Add voice message to queue
    voice_queue.put(message)


# ============================================================
# FACE RECOGNITION FUNCTION
# ============================================================

def recognize_face(image, face):

    try:

        # Align face
        aligned_face = recognizer.alignCrop(
            image,
            face
        )

        # Extract face feature
        feature = recognizer.feature(
            aligned_face
        )

    except Exception:

        return "Unknown", 0.0, False


    best_name = "Unknown"
    best_score = 0.0
    best_active = False


    # Compare with every registered person
    for person in database:

        name = person.get(
            "name",
            "Unknown"
        )

        active = person.get(
            "active",
            True
        )


        embeddings = person.get(
            "embeddings",
            []
        )


        for stored_feature in embeddings:

            try:

                score = recognizer.match(
                    feature,
                    stored_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

            except Exception:

                continue


            if score > best_score:

                best_score = score

                best_name = name

                best_active = active


    # --------------------------------------------------------
    # UNKNOWN PERSON
    # --------------------------------------------------------

    if best_score < THRESHOLD:

        return (
            "Unknown",
            best_score,
            False
        )


    # --------------------------------------------------------
    # REGISTERED PERSON
    # --------------------------------------------------------

    return (
        best_name,
        best_score,
        best_active
    )


# ============================================================
# CAMERA
# ============================================================

print("\n🎥 Starting camera...")

cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_DSHOW
)


if not cap.isOpened():

    raise RuntimeError(
        "❌ Camera could not be opened.\n"
        "Try changing CAMERA_INDEX = 1"
    )


# Camera resolution
cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    640
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    480
)


print("✅ Camera started")
print("👁️ AI EYES is watching...")
print("⌨️ Press Q to exit")


# ============================================================
# MULTI-PERSON TRACKING VARIABLES
# ============================================================

# Example:
#
# candidate_counts:
# {
#     "Muthu": 3,
#     "Subha": 2
# }

candidate_counts = {}


# Confirmed people currently visible
#
# Example:
# {"Muthu", "Subha"}

confirmed_people = set()


# Last time a confirmed person was seen
#
# Example:
# {
#     "Muthu": 12345.22
# }

last_seen = {}


# People detected in current frame
current_people = set()


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        success, frame = cap.read()


        if not success:

            print("❌ Camera frame could not be read")

            break


        # ----------------------------------------------------
        # DETECTOR INPUT SIZE
        # ----------------------------------------------------

        height, width = frame.shape[:2]

        detector.setInputSize(
            (width, height)
        )


        # ----------------------------------------------------
        # DETECT FACES
        # ----------------------------------------------------

        _, faces = detector.detect(frame)


        # Current frame people
        current_people = set()


        # ----------------------------------------------------
        # PROCESS EACH FACE
        # ----------------------------------------------------

        if faces is not None:

            for face in faces:

                # Face coordinates
                x = int(face[0])
                y = int(face[1])
                w = int(face[2])
                h = int(face[3])


                # Make sure coordinates are valid
                x = max(0, x)
                y = max(0, y)

                x2 = min(
                    width,
                    x + w
                )

                y2 = min(
                    height,
                    y + h
                )


                # ------------------------------------------------
                # RECOGNIZE
                # ------------------------------------------------

                name, score, active = recognize_face(
                    frame,
                    face
                )


                # ------------------------------------------------
                # IDENTITY KEY
                # ------------------------------------------------

                if name == "Unknown":

                    identity = "Unknown"

                elif active:

                    identity = f"Active:{name}"

                else:

                    identity = f"Disabled:{name}"


                # Add to current people
                current_people.add(identity)


                # ------------------------------------------------
                # STABILITY CHECK
                # ------------------------------------------------

                if identity not in candidate_counts:

                    candidate_counts[identity] = 0


                candidate_counts[identity] += 1


                # ------------------------------------------------
                # LIMIT COUNTER
                # ------------------------------------------------

                if candidate_counts[identity] > REQUIRED_FRAMES:

                    candidate_counts[identity] = REQUIRED_FRAMES


                # ------------------------------------------------
                # CONFIRM PERSON
                # ------------------------------------------------

                if (
                    candidate_counts[identity]
                    >= REQUIRED_FRAMES
                ):

                    # Update last seen
                    last_seen[identity] = time.time()


                    # --------------------------------------------
                    # FIRST TIME DETECTED
                    # --------------------------------------------

                    if identity not in confirmed_people:

                        confirmed_people.add(
                            identity
                        )


                        # ========================================
                        # ACTIVE PERSON
                        # ========================================

                        if identity.startswith(
                            "Active:"
                        ):

                            person_name = identity.replace(
                                "Active:",
                                ""
                            )


                            print(
                                f"\n🟢 ACCESS GRANTED: "
                                f"{person_name}"
                            )

                            print(
                                f"📊 Confidence: "
                                f"{score:.3f}"
                            )


                            speak(
                                f"Hello {person_name}"
                            )


                        # ========================================
                        # DISABLED PERSON
                        # ========================================

                        elif identity.startswith(
                            "Disabled:"
                        ):

                            person_name = identity.replace(
                                "Disabled:",
                                ""
                            )


                            print(
                                f"\n🔴 ACCESS DENIED: "
                                f"{person_name} is disabled"
                            )


                            print(
                                f"📊 Confidence: "
                                f"{score:.3f}"
                            )


                            speak(
                                f"Access denied. "
                                f"{person_name} is disabled."
                            )


                        # ========================================
                        # UNKNOWN PERSON
                        # ========================================

                        elif identity == "Unknown":

                            print(
                                "\n🔴 ACCESS DENIED: "
                                "Unknown Person"
                            )


                            print(
                                f"📊 Confidence: "
                                f"{score:.3f}"
                            )


                            speak(
                                "Access denied. "
                                "Unknown person."
                            )


                # ------------------------------------------------
                # DRAW FACE BOX
                # ------------------------------------------------

                if identity == "Unknown":

                    label = "UNKNOWN"

                    box_color = (
                        0,
                        0,
                        255
                    )

                elif identity.startswith(
                    "Disabled:"
                ):

                    person_name = identity.replace(
                        "Disabled:",
                        ""
                    )

                    label = (
                        f"{person_name} - DISABLED"
                    )

                    box_color = (
                        0,
                        0,
                        255
                    )

                else:

                    person_name = identity.replace(
                        "Active:",
                        ""
                    )

                    label = (
                        f"{person_name} - ACCESS GRANTED"
                    )

                    box_color = (
                        0,
                        255,
                        0
                    )


                # Rectangle
                cv2.rectangle(
                    frame,
                    (x, y),
                    (x2, y2),
                    box_color,
                    2
                )


                # Confidence
                confidence_text = (
                    f"{score:.2f}"
                )


                # Label background
                cv2.rectangle(
                    frame,
                    (x, max(0, y - 35)),
                    (x + 260, y),
                    box_color,
                    -1
                )


                # Name
                cv2.putText(
                    frame,
                    label,
                    (x + 5, y - 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (255, 255, 255),
                    2
                )


                # Confidence below face
                cv2.putText(
                    frame,
                    f"Confidence: {confidence_text}",
                    (x, y2 + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    box_color,
                    2
                )


        # ====================================================
        # REMOVE PEOPLE WHO LEFT
        # ====================================================

        now = time.time()


        people_to_remove = []


        for identity in confirmed_people:

            if identity not in current_people:

                if identity in last_seen:

                    elapsed = (
                        now - last_seen[identity]
                    )


                    if elapsed > LEAVE_TIMEOUT:

                        people_to_remove.append(
                            identity
                        )


        # Remove disappeared people
        for identity in people_to_remove:

            confirmed_people.discard(
                identity
            )

            last_seen.pop(
                identity,
                None
            )

            candidate_counts.pop(
                identity,
                None
            )


        # ====================================================
        # CLEAN OLD CANDIDATE COUNTERS
        # ====================================================

        for identity in list(
            candidate_counts.keys()
        ):

            if identity not in current_people:

                candidate_counts[identity] = 0


        # ====================================================
        # DISPLAY PEOPLE COUNT
        # ====================================================

        visible_count = len(
            confirmed_people
        )


        cv2.rectangle(
            frame,
            (10, 10),
            (300, 55),
            (0, 0, 0),
            -1
        )


        cv2.putText(
            frame,
            f"People Detected: {visible_count}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )


        # ====================================================
        # DISPLAY SYSTEM STATUS
        # ====================================================

        cv2.putText(
            frame,
            "AI EYES - LIVE ACCESS CONTROL",
            (10, height - 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2
        )


        cv2.putText(
            frame,
            "Press Q to Exit",
            (10, height - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )


        # ====================================================
        # SHOW CAMERA
        # ====================================================

        cv2.imshow(
            "AI EYES - Smart Face Access",
            frame
        )


        # ====================================================
        # EXIT
        # ====================================================

        key = cv2.waitKey(1) & 0xFF


        if key == ord("q"):

            print("\n🛑 Stopping AI EYES...")

            break


# ============================================================
# CLEAN SHUTDOWN
# ============================================================

except KeyboardInterrupt:

    print("\n🛑 Program interrupted")


finally:

    print("\n🔄 Closing camera...")

    cap.release()

    cv2.destroyAllWindows()


    # Stop voice worker
    voice_queue.put(None)

    voice_thread.join(
        timeout=2
    )


    print("🔊 Voice system stopped")
    print("📷 Camera stopped")
    print("✅ AI EYES closed successfully")

    print("=" * 60)