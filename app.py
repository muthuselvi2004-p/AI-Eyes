import os
import cv2
import pickle
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pyttsx3
from PIL import Image, ImageTk


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE_FILE = os.path.join(
    BASE_DIR,
    "face_database.pkl"
)

YU_NET_MODEL = os.path.join(
    BASE_DIR,
    "models",
    "face_detection_yunet_2023mar.onnx"
)

SFACE_MODEL = os.path.join(
    BASE_DIR,
    "models",
    "face_recognition_sface_2021dec.onnx"
)

COSINE_THRESHOLD = 0.40
DUPLICATE_THRESHOLD = 0.45

REQUIRED_FRAMES = 3

CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720

WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700


# ============================================================
# CHECK MODELS
# ============================================================

if not os.path.exists(YU_NET_MODEL):
    raise FileNotFoundError(
        f"YuNet model not found:\n{YU_NET_MODEL}"
    )

if not os.path.exists(SFACE_MODEL):
    raise FileNotFoundError(
        f"SFace model not found:\n{SFACE_MODEL}"
    )


# ============================================================
# LOAD AI MODELS
# ============================================================

try:

    detector = cv2.FaceDetectorYN.create(
        YU_NET_MODEL,
        "",
        (640, 480),
        0.5,
        0.3,
        5000
    )

    recognizer = cv2.FaceRecognizerSF.create(
        SFACE_MODEL,
        ""
    )

    print("✅ AI Models Loaded")

except Exception as e:

    print("❌ Model loading failed")
    print(e)

    raise


# ============================================================
# DATABASE
# ============================================================

def load_database():

    if not os.path.exists(DATABASE_FILE):
        return []

    try:

        with open(
            DATABASE_FILE,
            "rb"
        ) as f:

            data = pickle.load(f)

        if not isinstance(data, list):
            return []

        cleaned = []

        for person in data:

            if not isinstance(
                person,
                dict
            ):
                continue

            if "name" not in person:
                continue

            if "embeddings" not in person:
                person["embeddings"] = []

            if "active" not in person:
                person["active"] = True

            cleaned.append(person)

        return cleaned

    except Exception as e:

        print(
            "❌ Database load error:",
            e
        )

        return []


def save_database():

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

        print(
            "❌ Database save error:",
            e
        )

        return False


database = load_database()


# ============================================================
# VOICE SYSTEM
# ============================================================

# Windows SAPI voice is used through one dedicated worker thread.
# This is more reliable for multiple greetings than repeatedly
# creating/using pyttsx3 from the Tkinter camera loop.

voice_queue = queue.Queue()
voice_running = True

# Prevent the same voice message from being queued repeatedly
# while it is waiting or being spoken.
voice_pending = set()
voice_pending_lock = threading.Lock()


def voice_worker():
    speaker = None
    use_sapi = False

    try:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()

        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        speaker.Rate = 0
        speaker.Volume = 100

        use_sapi = True
        print("🔊 Windows SAPI voice initialized")

    except Exception as e:
        print("⚠️ SAPI voice initialization failed:", e)
        print("🔊 Falling back to pyttsx3...")

        try:
            speaker = pyttsx3.init()
            speaker.setProperty("rate", 165)
            speaker.setProperty("volume", 1.0)
        except Exception as fallback_error:
            print(
                "❌ Voice initialization failed:",
                fallback_error
            )
            return

    while voice_running:

        try:
            text_to_speak = voice_queue.get(
                timeout=0.5
            )

        except queue.Empty:
            continue

        if text_to_speak is None:
            voice_queue.task_done()
            break

        # Keep the message marked as pending while it is actually
        # being spoken too. Otherwise the camera loop could queue the
        # same greeting again during a long SAPI speech call.
        try:
            print("🔊 Speaking:", text_to_speak)

            if use_sapi:
                # SAPI Speak is blocking, so every queued message
                # is completed before the next one starts.
                speaker.Speak(
                    text_to_speak
                )

            else:
                speaker.say(
                    text_to_speak
                )
                speaker.runAndWait()

        except Exception as e:
            print(
                "❌ Voice error:",
                e
            )

            # Try to recreate pyttsx3 if SAPI fails.
            if use_sapi:
                try:
                    speaker = pyttsx3.init()
                    speaker.setProperty(
                        "rate",
                        165
                    )
                    speaker.setProperty(
                        "volume",
                        1.0
                    )
                    use_sapi = False

                except Exception as recovery_error:
                    print(
                        "Voice recovery failed:",
                        recovery_error
                    )

        finally:
            with voice_pending_lock:
                voice_pending.discard(text_to_speak)
            voice_queue.task_done()

    if use_sapi:
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    print("🔊 Voice worker stopped")


voice_thread = threading.Thread(
    target=voice_worker,
    daemon=True
)

voice_thread.start()


def speak(text):
    """
    Queue a voice message only once while the same message is
    waiting to be spoken. This is important because the camera
    loop runs many times per second.
    """
    if not voice_running:
        return

    if not text:
        return

    text = str(text)

    with voice_pending_lock:
        if text in voice_pending:
            return
        voice_pending.add(text)

    try:
        voice_queue.put(text)
        print("🗣️ Voice queued:", text)

    except Exception as e:
        with voice_pending_lock:
            voice_pending.discard(text)
        print("❌ Could not queue voice:", e)


# ============================================================
# CAMERA OPEN
# ============================================================

def open_camera():

    candidates = [

        (0, cv2.CAP_DSHOW),
        (0, cv2.CAP_MSMF),
        (0, cv2.CAP_ANY),

        (1, cv2.CAP_DSHOW),
        (1, cv2.CAP_ANY),

        (2, cv2.CAP_DSHOW),
        (2, cv2.CAP_ANY),

    ]

    for index, backend in candidates:

        print(
            f"📷 Trying camera {index} "
            f"backend={backend}"
        )

        cap = cv2.VideoCapture(
            index,
            backend
        )

        if not cap.isOpened():

            cap.release()
            continue

        try:

            cap.set(
                cv2.CAP_PROP_FRAME_WIDTH,
                CAMERA_WIDTH
            )

            cap.set(
                cv2.CAP_PROP_FRAME_HEIGHT,
                CAMERA_HEIGHT
            )

            time.sleep(0.15)

            success, frame = (
                cap.read()
            )

            if (
                success
                and
                frame is not None
            ):

                print(
                    f"✅ Camera opened: "
                    f"index={index}"
                )

                return cap

        except Exception as e:

            print(
                "Camera test error:",
                e
            )

        cap.release()

    print(
        "❌ No working camera found"
    )

    return None


# ============================================================
# FACE DETECTION
# ============================================================

def detect_faces(frame):

    if frame is None:
        return None

    try:

        height, width = (
            frame.shape[:2]
        )

        detector.setInputSize(
            (width, height)
        )

        _, faces = detector.detect(
            frame
        )

        return faces

    except Exception as e:

        print(
            "Detection error:",
            e
        )

        return None


# ============================================================
# LARGEST FACE
# ============================================================

def get_largest_face(faces):

    if faces is None:
        return None

    try:

        arr = np.asarray(
            faces
        )

        if arr.size == 0:
            return None

        if arr.ndim == 1:

            if arr.shape[0] < 4:
                return None

            arr = arr.reshape(
                1,
                -1
            )

        largest = max(
            arr,
            key=lambda face:
            float(face[2])
            *
            float(face[3])
        )

        return largest

    except Exception as e:

        print(
            "Largest face error:",
            e
        )

        return None


# ============================================================
# EMBEDDING
# ============================================================

def get_embedding(
    frame,
    face
):

    try:

        aligned = (
            recognizer.alignCrop(
                frame,
                face
            )
        )

        feature = (
            recognizer.feature(
                aligned
            )
        )

        return feature

    except Exception as e:

        print(
            "Embedding error:",
            e
        )

        return None


# ============================================================
# COMPARE
# ============================================================

def compare_embedding(
    feature,
    stored_feature
):

    try:

        score = recognizer.match(
            feature,
            stored_feature,
            cv2.FaceRecognizerSF_FR_COSINE
        )

        return float(score)

    except Exception:

        return 0.0


# ============================================================
# RECOGNIZE PERSON
# ============================================================

def recognize_person(
    feature
):

    best_name = None
    best_score = 0.0
    best_active = False

    if feature is None:
        return (
            None,
            0.0,
            False
        )

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

            score = compare_embedding(
                feature,
                stored_feature
            )

            if score > best_score:

                best_score = score
                best_name = name
                best_active = active

    if (
        best_score
        >= COSINE_THRESHOLD
    ):

        return (
            best_name,
            best_score,
            best_active
        )

    return (
        None,
        best_score,
        False
    )


# ============================================================
# IMAGE RESIZE
# ============================================================

def resize_image_for_registration(
    frame
):

    if frame is None:
        return None

    height, width = (
        frame.shape[:2]
    )

    if width < 400:

        new_width = 400

        new_height = int(
            height
            *
            new_width
            /
            width
        )

        frame = cv2.resize(
            frame,
            (
                new_width,
                new_height
            ),
            interpolation=cv2.INTER_CUBIC
        )

    return frame


# ============================================================
# SAFE WIDGET CHECK
# ============================================================

def safe_exists(widget):

    try:

        return (
            widget is not None
            and widget.winfo_exists()
        )

    except Exception:

        return False


# ============================================================
# MAIN APP
# ============================================================

class AIEyesApp:

    def __init__(
        self,
        root
    ):

        self.root = root

        self.root.title(
            "AI EYES - Smart Face Access"
        )

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.root.minsize(
            950,
            620
        )

        self.root.configure(
            bg="#f3f4f6"
        )

        self.closing = False

        # ----------------------------------------------------
        # CAMERAS
        # ----------------------------------------------------

        self.recognition_camera = None
        self.add_camera = None

        self.recognition_running = False
        self.add_camera_running = False

        self.recognition_after_id = None
        self.add_camera_after_id = None

        # ----------------------------------------------------
        # ADD PERSON
        # ----------------------------------------------------

        self.latest_add_frame = None
        self.captured_embedding = None
        self.selected_uploaded_image = None

        # ----------------------------------------------------
        # OLD RECOGNITION VARIABLES
        # ----------------------------------------------------

        self.current_person = None
        self.current_person_active = False

        self.stable_person = None
        self.stable_count = 0

        self.last_seen_time = 0
        self.voice_greeted = False

        # ----------------------------------------------------
        # NEW MULTI-PERSON VOICE TRACKING
        # ----------------------------------------------------

        self.greeted_people = set()

        self.last_detected_people = set()

        # Person must be absent continuously for this many seconds
        # before we consider them to have left. This prevents normal
        # YuNet detection flicker from causing repeated greetings.
        self.person_missing_since = {}
        self.LEAVE_CONFIRM_SECONDS = 2.0

        # ----------------------------------------------------
        # WIDGETS
        # ----------------------------------------------------

        self.content_frame = None

        self.dashboard_camera_label = None
        self.dashboard_status_label = None
        self.dashboard_person_label = None
        self.dashboard_score_label = None

        self.add_camera_label = None
        self.add_name_entry = None
        self.add_status_label = None

        self.setup_style()

        self.build_layout()

        self.show_dashboard()

        self.root.bind(
            "<Escape>",
            lambda event:
            self.on_close()
        )

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        print("=" * 38)
        print(
            "        🤖 AI EYES APPLICATION"
        )
        print("=" * 38)

        print(
            f"👥 Registered people: "
            f"{len(database)}"
        )

        print(
            "✅ Application starting..."
        )

        print("=" * 38)


    # ========================================================
    # STYLE
    # ========================================================

    def setup_style(self):

        style = ttk.Style()

        try:
            style.theme_use(
                "clam"
            )
        except Exception:
            pass

        style.configure(
            "Treeview",
            rowheight=34,
            font=(
                "Segoe UI",
                10
            )
        )

        style.configure(
            "Treeview.Heading",
            font=(
                "Segoe UI",
                10,
                "bold"
            )
        )


    # ========================================================
    # MAIN LAYOUT
    # ========================================================

    def build_layout(self):

        self.header = tk.Frame(
            self.root,
            bg="#111827",
            height=58
        )

        self.header.pack(
            side="top",
            fill="x"
        )

        self.header.pack_propagate(
            False
        )

        tk.Label(
            self.header,
            text="🤖 AI EYES",
            font=(
                "Segoe UI",
                20,
                "bold"
            ),
            fg="white",
            bg="#111827"
        ).pack(
            side="left",
            padx=20
        )

        tk.Label(
            self.header,
            text="Smart Face Access System",
            font=(
                "Segoe UI",
                10
            ),
            fg="#d1d5db",
            bg="#111827"
        ).pack(
            side="left",
            padx=4
        )

        self.main_area = tk.Frame(
            self.root,
            bg="#f3f4f6"
        )

        self.main_area.pack(
            fill="both",
            expand=True
        )

        # Sidebar

        self.sidebar = tk.Frame(
            self.main_area,
            bg="#1f2937",
            width=180
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(
            False
        )

        self.create_sidebar_button(
            "🏠 Dashboard",
            self.show_dashboard
        )

        self.create_sidebar_button(
            "👤 Add Person",
            self.show_add_person
        )

        self.create_sidebar_button(
            "🔐 Manage People",
            self.show_manage_people
        )

        exit_button = tk.Button(
            self.sidebar,
            text="❌ Exit",
            command=self.on_close,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#7f1d1d",
            fg="white",
            activebackground="#991b1b",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        )

        exit_button.pack(
            side="bottom",
            fill="x",
            padx=12,
            pady=12
        )

        self.content_frame = tk.Frame(
            self.main_area,
            bg="#f3f4f6"
        )

        self.content_frame.pack(
            side="left",
            fill="both",
            expand=True
        )


    def create_sidebar_button(
        self,
        text,
        command
    ):

        button = tk.Button(
            self.sidebar,
            text=text,
            command=command,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#374151",
            fg="white",
            activebackground="#4b5563",
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            anchor="w",
            padx=14,
            height=2
        )

        button.pack(
            fill="x",
            padx=10,
            pady=4
        )


    # ========================================================
    # CLEAR CONTENT
    # ========================================================

    def clear_content(self):

        self.stop_recognition_camera()

        self.stop_add_camera()

        if self.content_frame is None:
            return

        for widget in (
            self.content_frame
            .winfo_children()
        ):

            try:
                widget.destroy()
            except Exception:
                pass


    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(self):

        self.clear_content()

        top = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        top.pack(
            fill="x",
            padx=16,
            pady=(12, 6)
        )

        tk.Label(
            top,
            text="Dashboard",
            font=(
                "Segoe UI",
                18,
                "bold"
            ),
            bg="#f3f4f6",
            fg="#111827"
        ).pack(
            side="left"
        )

        tk.Label(
            top,
            text=(
                f"Registered: "
                f"{len(database)}"
            ),
            font=(
                "Segoe UI",
                10
            ),
            bg="#f3f4f6",
            fg="#6b7280"
        ).pack(
            side="right"
        )

        body = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=8
        )

        body.grid_columnconfigure(
            0,
            weight=1
        )

        body.grid_columnconfigure(
            1,
            weight=0,
            minsize=230
        )

        body.grid_rowconfigure(
            0,
            weight=1
        )

        # Camera

        camera_card = tk.Frame(
            body,
            bg="black",
            bd=1,
            relief="solid"
        )

        camera_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        self.dashboard_camera_label = (
            tk.Label(
                camera_card,
                text=(
                    "📷\n\n"
                    "Camera is stopped"
                ),
                font=(
                    "Segoe UI",
                    14
                ),
                fg="white",
                bg="black"
            )
        )

        self.dashboard_camera_label.pack(
            fill="both",
            expand=True
        )

        # Status

        status_card = tk.Frame(
            body,
            bg="white",
            bd=1,
            relief="solid"
        )

        status_card.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        tk.Label(
            status_card,
            text="ACCESS STATUS",
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            bg="white",
            fg="#374151"
        ).pack(
            pady=(20, 10)
        )

        self.dashboard_status_label = (
            tk.Label(
                status_card,
                text="CAMERA OFF",
                font=(
                    "Segoe UI",
                    17,
                    "bold"
                ),
                bg="white",
                fg="#6b7280",
                wraplength=200
            )
        )

        self.dashboard_status_label.pack(
            pady=10
        )

        self.dashboard_person_label = (
            tk.Label(
                status_card,
                text="Person: --",
                font=(
                    "Segoe UI",
                    11
                ),
                bg="white",
                fg="#111827",
                wraplength=210
            )
        )

        self.dashboard_person_label.pack(
            pady=5
        )

        self.dashboard_score_label = (
            tk.Label(
                status_card,
                text="Confidence: --",
                font=(
                    "Segoe UI",
                    10
                ),
                bg="white",
                fg="#6b7280"
            )
        )

        self.dashboard_score_label.pack(
            pady=5
        )

        button_area = tk.Frame(
            status_card,
            bg="white"
        )

        button_area.pack(
            side="bottom",
            fill="x",
            padx=14,
            pady=18
        )

        self.dashboard_start_button = (
            tk.Button(
                button_area,
                text="▶ Start Camera",
                command=(
                    self.start_recognition_camera
                ),
                font=(
                    "Segoe UI",
                    10,
                    "bold"
                ),
                bg="#16a34a",
                fg="white",
                relief="flat",
                bd=0,
                cursor="hand2",
                height=2
            )
        )

        self.dashboard_start_button.pack(
            fill="x",
            pady=4
        )

        tk.Button(
            button_area,
            text="⏹ Stop Camera",
            command=(
                self.stop_recognition_camera
            ),
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#dc2626",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            pady=4
        )

        tk.Button(
            button_area,
            text="👤 Add Person",
            command=self.show_add_person,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#2563eb",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            pady=4
        )


    # ========================================================
    # START RECOGNITION
    # ========================================================

    def start_recognition_camera(self):

        if self.closing:
            return

        if self.recognition_running:
            return

        if self.dashboard_camera_label is None:
            return

        if len(database) == 0:

            messagebox.showwarning(
                "No Registered People",
                "Please add at least one person first."
            )

            return

        self.stop_add_camera()

        cap = open_camera()

        if cap is None:

            messagebox.showerror(
                "Camera Error",
                "Camera could not be opened.\n\n"
                "Close Zoom / Teams / Camera app "
                "and try again."
            )

            return

        self.recognition_camera = cap

        self.recognition_running = True

        self.current_person = None
        self.current_person_active = False

        self.stable_person = None
        self.stable_count = 0

        self.voice_greeted = False

        # IMPORTANT
        self.greeted_people.clear()
        self.last_detected_people.clear()
        self.person_missing_since.clear()

        # Remove any old pending voice messages when a new
        # recognition session starts.
        try:
            while True:
                pending_voice = voice_queue.get_nowait()
                voice_queue.task_done()

        except queue.Empty:
            pass

        if safe_exists(
            self.dashboard_status_label
        ):

            self.dashboard_status_label.config(
                text="SCANNING...",
                fg="#2563eb"
            )

        self.update_camera()


    # ========================================================
    # RECOGNITION LOOP
    # ========================================================

    def update_camera(self):

        if self.closing:
            return

        if not self.recognition_running:
            return

        if self.recognition_camera is None:
            return

        if not safe_exists(
            self.dashboard_camera_label
        ):

            self.stop_recognition_camera()

            return

        try:

            success, frame = (
                self.recognition_camera.read()
            )

            if (
                not success
                or
                frame is None
            ):

                print(
                    "❌ Camera frame "
                    "could not be read"
                )

                self.stop_recognition_camera()

                if safe_exists(
                    self.dashboard_status_label
                ):

                    self.dashboard_status_label.config(
                        text="CAMERA ERROR",
                        fg="#dc2626"
                    )

                return

            # =================================================
            # DETECT ALL FACES
            # =================================================

            faces = detect_faces(
                frame
            )

            current_people = set()

            if faces is not None:

                try:

                    faces_array = np.asarray(
                        faces
                    )

                    if faces_array.size > 0:

                        if (
                            faces_array.ndim
                            == 1
                        ):

                            faces_array = (
                                faces_array.reshape(
                                    1,
                                    -1
                                )
                            )

                        # ==========================================
                        # PROCESS EVERY FACE
                        # ==========================================

                        for face in faces_array:

                            result = (
                                self.process_face(
                                    frame,
                                    face
                                )
                            )

                            if result is None:
                                continue

                            name = result[
                                "name"
                            ]

                            score = result[
                                "score"
                            ]

                            active = result[
                                "active"
                            ]

                            known = result[
                                "known"
                            ]

                            current_people.add(
                                name
                            )

                            # ======================================
                            # FACE BOX
                            # ======================================

                            x = int(
                                face[0]
                            )

                            y = int(
                                face[1]
                            )

                            w = int(
                                face[2]
                            )

                            h = int(
                                face[3]
                            )

                            # Green:
                            # known + active

                            if (
                                known
                                and
                                active
                            ):

                                box_color = (
                                    0,
                                    255,
                                    0
                                )

                                label_color = (
                                    0,
                                    255,
                                    0
                                )

                                access_text = (
                                    "ACCESS GRANTED"
                                )

                            else:

                                box_color = (
                                    0,
                                    0,
                                    255
                                )

                                label_color = (
                                    0,
                                    0,
                                    255
                                )

                                access_text = (
                                    "ACCESS DENIED"
                                )

                            # ======================================
                            # DRAW BOX
                            # ======================================

                            cv2.rectangle(
                                frame,
                                (x, y),
                                (
                                    x + w,
                                    y + h
                                ),
                                box_color,
                                3
                            )

                            # ======================================
                            # NAME
                            # ======================================

                            if (
                                name
                                == "Unknown"
                            ):

                                display_name = (
                                    "Unknown"
                                )

                            else:

                                display_name = (
                                    f"{name} "
                                    f"{score:.2f}"
                                )

                            text_y = max(
                                30,
                                y - 12
                            )

                            cv2.putText(
                                frame,
                                display_name,
                                (
                                    x,
                                    text_y
                                ),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.75,
                                label_color,
                                2,
                                cv2.LINE_AA
                            )

                            # ======================================
                            # ACCESS TEXT
                            # ======================================

                            access_y = (
                                y
                                +
                                h
                                +
                                28
                            )

                            cv2.putText(
                                frame,
                                access_text,
                                (
                                    x,
                                    access_y
                                ),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.60,
                                label_color,
                                2,
                                cv2.LINE_AA
                            )

                except Exception as e:

                    print(
                        "Face processing error:",
                        e
                    )

            # =================================================
            # HANDLE PEOPLE WHO MAY HAVE LEFT
            # =================================================
            # Do NOT immediately forget a person when detection misses
            # one frame. YuNet can occasionally miss a face for a short
            # moment because of movement, lighting or angle.

            now = time.time()

            # People detected in this frame are definitely present.
            for person in current_people:
                self.person_missing_since.pop(
                    person,
                    None
                )

            # People that were previously visible but are missing now
            # start a leave timer.
            missing_people = (
                self.last_detected_people
                -
                current_people
            )

            for person in missing_people:
                if person not in self.person_missing_since:
                    self.person_missing_since[person] = now

            # Only after the full grace period do we allow a future
            # appearance to trigger a fresh greeting.
            for person, missing_since in list(
                self.person_missing_since.items()
            ):
                if (
                    now - missing_since
                    >= self.LEAVE_CONFIRM_SECONDS
                ):
                    self.greeted_people.discard(person)
                    self.person_missing_since.pop(
                        person,
                        None
                    )

            self.last_detected_people = set(
                current_people
            )

            # =================================================
            # DASHBOARD STATUS
            # =================================================

            if len(current_people) == 0:

                if safe_exists(
                    self.dashboard_status_label
                ):

                    self.dashboard_status_label.config(
                        text="NO FACE",
                        fg="#6b7280"
                    )

                if safe_exists(
                    self.dashboard_person_label
                ):

                    self.dashboard_person_label.config(
                        text="Person: --"
                    )

                if safe_exists(
                    self.dashboard_score_label
                ):

                    self.dashboard_score_label.config(
                        text="Confidence: --"
                    )

            else:

                active_people = []

                for person_name in (
                    current_people
                ):

                    for person in database:

                        if (
                            person.get(
                                "name"
                            )
                            ==
                            person_name
                            and
                            person.get(
                                "active",
                                True
                            )
                        ):

                            active_people.append(
                                person_name
                            )

                if len(active_people) > 0:

                    if safe_exists(
                        self.dashboard_status_label
                    ):

                        self.dashboard_status_label.config(
                            text="ACCESS GRANTED",
                            fg="#16a34a"
                        )

                else:

                    if safe_exists(
                        self.dashboard_status_label
                    ):

                        self.dashboard_status_label.config(
                            text="ACCESS DENIED",
                            fg="#dc2626"
                        )

                if safe_exists(
                    self.dashboard_person_label
                ):

                    self.dashboard_person_label.config(
                        text=(
                            "People: "
                            +
                            ", ".join(
                                sorted(
                                    current_people
                                )
                            )
                        )
                    )

                if safe_exists(
                    self.dashboard_score_label
                ):

                    self.dashboard_score_label.config(
                        text=(
                            "Faces detected: "
                            +
                            str(
                                len(
                                    current_people
                                )
                            )
                        )
                    )

            # =================================================
            # SHOW FRAME
            # =================================================

            self.show_camera_frame(
                frame,
                self.dashboard_camera_label,
                max_width=680,
                max_height=500
            )

            # =================================================
            # NEXT FRAME
            # =================================================

            if self.recognition_running:

                self.recognition_after_id = (
                    self.root.after(
                        30,
                        self.update_camera
                    )
                )

        except Exception as e:

            print(
                "❌ Recognition camera error:",
                e
            )

            self.stop_recognition_camera()


    # ========================================================
    # PROCESS ONE FACE
    # ========================================================

    def process_face(
        self,
        frame,
        face
    ):

        feature = get_embedding(
            frame,
            face
        )

        if feature is None:
            return None

        name, score, active = (
            recognize_person(
                feature
            )
        )

        # ====================================================
        # UNKNOWN
        # ====================================================

        if name is None:

            # Speak only once while this
            # unknown face remains detected.

            unknown_key = (
                "Unknown"
            )

            if (
                unknown_key
                not in
                self.greeted_people
            ):

                speak(
                    "Access denied. "
                    "Unknown person."
                )

                self.greeted_people.add(
                    unknown_key
                )

            return {
                "name": "Unknown",
                "score": score,
                "active": False,
                "known": False
            }

        # ====================================================
        # KNOWN + ACTIVE
        # ====================================================

        if active:

            # IMPORTANT:
            # Each person's name is tracked separately.

            if (
                name
                not in
                self.greeted_people
            ):

                speak(
                    f"Hello {name}. "
                    f"Access granted."
                )

                self.greeted_people.add(
                    name
                )

            return {
                "name": name,
                "score": score,
                "active": True,
                "known": True
            }

        # ====================================================
        # KNOWN BUT DISABLED
        # ====================================================

        if (
            name
            not in
            self.greeted_people
        ):

            speak(
                f"Access denied. "
                f"{name} is disabled."
            )

            self.greeted_people.add(
                name
            )

        return {
            "name": name,
            "score": score,
            "active": False,
            "known": True
        }


    # ========================================================
    # STOP RECOGNITION
    # ========================================================

    def stop_recognition_camera(
        self
    ):

        self.recognition_running = False

        if (
            self.recognition_after_id
            is not None
        ):

            try:

                self.root.after_cancel(
                    self.recognition_after_id
                )

            except Exception:
                pass

            self.recognition_after_id = None

        if (
            self.recognition_camera
            is not None
        ):

            try:

                self.recognition_camera.release()

            except Exception:
                pass

            self.recognition_camera = None

        self.stable_person = None
        self.stable_count = 0
        self.voice_greeted = False

        # IMPORTANT:
        # Reset multi-person greeting state.

        self.greeted_people.clear()
        self.last_detected_people.clear()
        self.person_missing_since.clear()

        print(
            "📷 Recognition camera stopped"
        )

        if safe_exists(
            self.dashboard_status_label
        ):

            try:

                self.dashboard_status_label.config(
                    text="CAMERA OFF",
                    fg="#6b7280"
                )

            except Exception:
                pass


    # ========================================================
    # DISPLAY CAMERA
    # ========================================================

    def show_camera_frame(
        self,
        frame,
        label,
        max_width=680,
        max_height=500
    ):

        if frame is None:
            return

        if not safe_exists(label):
            return

        try:

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(
                rgb
            )

            image.thumbnail(
                (
                    max_width,
                    max_height
                ),
                Image.Resampling.LANCZOS
            )

            photo = ImageTk.PhotoImage(
                image=image
            )

            label.config(
                image=photo,
                text=""
            )

            label.image = photo

        except Exception as e:

            print(
                "Display frame error:",
                e
            )


    # ========================================================
    # ADD PERSON PAGE
    # ========================================================

    def show_add_person(self):

        self.clear_content()

        self.latest_add_frame = None
        self.captured_embedding = None
        self.selected_uploaded_image = None

        header = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        header.pack(
            fill="x",
            padx=16,
            pady=(10, 5)
        )

        tk.Label(
            header,
            text="Add New Person",
            font=(
                "Segoe UI",
                18,
                "bold"
            ),
            bg="#f3f4f6",
            fg="#111827"
        ).pack(
            side="left"
        )

        body = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        body.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=8
        )

        body.grid_columnconfigure(
            0,
            weight=1
        )

        body.grid_columnconfigure(
            1,
            weight=0,
            minsize=250
        )

        body.grid_rowconfigure(
            0,
            weight=1
        )

        # Camera

        camera_card = tk.Frame(
            body,
            bg="black",
            bd=1,
            relief="solid"
        )

        camera_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        self.add_camera_label = tk.Label(
            camera_card,
            text=(
                "📷\n\n"
                "Add Person Camera\n\n"
                "Click Start Camera"
            ),
            font=(
                "Segoe UI",
                14
            ),
            fg="white",
            bg="black"
        )

        self.add_camera_label.pack(
            fill="both",
            expand=True
        )

        # Controls

        control = tk.Frame(
            body,
            bg="white",
            bd=1,
            relief="solid"
        )

        control.grid(
            row=0,
            column=1,
            sticky="nsew"
        )

        tk.Label(
            control,
            text="PERSON DETAILS",
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            bg="white",
            fg="#374151"
        ).pack(
            pady=(18, 10)
        )

        tk.Label(
            control,
            text="Person Name",
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="white",
            fg="#374151"
        ).pack(
            anchor="w",
            padx=15
        )

        self.add_name_entry = tk.Entry(
            control,
            font=(
                "Segoe UI",
                11
            ),
            relief="solid",
            bd=1
        )

        self.add_name_entry.pack(
            fill="x",
            padx=15,
            pady=(5, 12)
        )

        tk.Button(
            control,
            text="▶ Start Camera",
            command=self.start_add_camera,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#16a34a",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            padx=15,
            pady=3
        )

        tk.Button(
            control,
            text="📸 Capture Face",
            command=self.capture_from_camera,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#2563eb",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            padx=15,
            pady=3
        )

        tk.Button(
            control,
            text="⏹ Stop Camera",
            command=self.stop_add_camera,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#dc2626",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            padx=15,
            pady=3
        )

        ttk.Separator(
            control,
            orient="horizontal"
        ).pack(
            fill="x",
            padx=15,
            pady=12
        )

        tk.Button(
            control,
            text="📁 Upload Photo",
            command=self.upload_photo,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#7c3aed",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            padx=15,
            pady=3
        )

        tk.Button(
            control,
            text="✅ Register Person",
            command=self.register_person,
            font=(
                "Segoe UI",
                10,
                "bold"
            ),
            bg="#059669",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        ).pack(
            fill="x",
            padx=15,
            pady=3
        )

        self.add_status_label = tk.Label(
            control,
            text="Ready",
            font=(
                "Segoe UI",
                10
            ),
            bg="white",
            fg="#6b7280",
            wraplength=210,
            justify="left"
        )

        self.add_status_label.pack(
            fill="x",
            padx=15,
            pady=15
        )


    # ========================================================
    # START ADD CAMERA
    # ========================================================

    def start_add_camera(self):

        if self.closing:
            return

        if self.add_camera_running:
            return

        self.stop_recognition_camera()

        cap = open_camera()

        if cap is None:

            messagebox.showerror(
                "Camera Error",
                "Camera could not be opened.\n\n"
                "Close other apps using the camera."
            )

            return

        self.add_camera = cap

        self.add_camera_running = True

        self.latest_add_frame = None

        if safe_exists(
            self.add_status_label
        ):

            self.add_status_label.config(
                text=(
                    "Camera running. "
                    "Position your face clearly."
                )
            )

        self.update_add_camera()


    # ========================================================
    # ADD CAMERA LOOP
    # ========================================================

    def update_add_camera(self):

        if self.closing:
            return

        if not self.add_camera_running:
            return

        if self.add_camera is None:
            return

        if not safe_exists(
            self.add_camera_label
        ):

            self.stop_add_camera()
            return

        try:

            success, frame = (
                self.add_camera.read()
            )

            if (
                not success
                or
                frame is None
            ):

                self.stop_add_camera()

                if safe_exists(
                    self.add_status_label
                ):

                    self.add_status_label.config(
                        text="Camera frame error.",
                        fg="#dc2626"
                    )

                return

            # FULL RESOLUTION FRAME

            self.latest_add_frame = (
                frame.copy()
            )

            faces = detect_faces(
                frame
            )

            selected_face = (
                get_largest_face(
                    faces
                )
            )

            display_frame = (
                frame.copy()
            )

            if selected_face is not None:

                x = int(
                    selected_face[0]
                )

                y = int(
                    selected_face[1]
                )

                w = int(
                    selected_face[2]
                )

                h = int(
                    selected_face[3]
                )

                cv2.rectangle(
                    display_frame,
                    (x, y),
                    (
                        x + w,
                        y + h
                    ),
                    (0, 255, 0),
                    3
                )

                cv2.putText(
                    display_frame,
                    "FACE DETECTED",
                    (
                        x,
                        max(
                            30,
                            y - 10
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2
                )

            else:

                cv2.putText(
                    display_frame,
                    "NO FACE DETECTED",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 255),
                    2
                )

            self.show_camera_frame(
                display_frame,
                self.add_camera_label,
                max_width=700,
                max_height=510
            )

            if self.add_camera_running:

                self.add_camera_after_id = (
                    self.root.after(
                        30,
                        self.update_add_camera
                    )
                )

        except Exception as e:

            print(
                "❌ Add camera error:",
                e
            )

            self.stop_add_camera()


    # ========================================================
    # STOP ADD CAMERA
    # ========================================================

    def stop_add_camera(self):

        self.add_camera_running = False

        if (
            self.add_camera_after_id
            is not None
        ):

            try:

                self.root.after_cancel(
                    self.add_camera_after_id
                )

            except Exception:
                pass

            self.add_camera_after_id = None

        if self.add_camera is not None:

            try:

                self.add_camera.release()

            except Exception:
                pass

            self.add_camera = None

        print(
            "📷 Add Person camera stopped"
        )


    # ========================================================
    # CAPTURE FACE
    # ========================================================

    def capture_from_camera(self):

        if self.latest_add_frame is None:

            messagebox.showwarning(
                "No Camera Frame",
                "Start the camera first."
            )

            return

        if not safe_exists(
            self.add_name_entry
        ):

            return

        name = (
            self.add_name_entry
            .get()
            .strip()
        )

        if not name:

            messagebox.showwarning(
                "Name Required",
                "Enter the person's name first."
            )

            return

        frame = (
            self.latest_add_frame.copy()
        )

        frame = (
            resize_image_for_registration(
                frame
            )
        )

        faces = detect_faces(
            frame
        )

        face = get_largest_face(
            faces
        )

        if face is None:

            messagebox.showwarning(
                "No Face",
                "No face detected.\n"
                "Please position your face clearly."
            )

            return

        feature = get_embedding(
            frame,
            face
        )

        if feature is None:

            messagebox.showerror(
                "Face Error",
                "Could not create face embedding."
            )

            return

        self.captured_embedding = (
            feature
        )

        self.selected_uploaded_image = None

        self.stop_add_camera()

        if safe_exists(
            self.add_camera_label
        ):

            self.show_camera_frame(
                frame,
                self.add_camera_label,
                max_width=700,
                max_height=510
            )

        if safe_exists(
            self.add_status_label
        ):

            self.add_status_label.config(
                text=(
                    "✅ Face captured successfully. "
                    "Click Register Person."
                ),
                fg="#059669"
            )


    # ========================================================
    # UPLOAD PHOTO
    # ========================================================

    def upload_photo(self):

        if self.closing:
            return

        if not safe_exists(
            self.add_name_entry
        ):

            return

        name = (
            self.add_name_entry
            .get()
            .strip()
        )

        if not name:

            messagebox.showwarning(
                "Name Required",
                "Enter the person's name first."
            )

            return

        self.stop_add_camera()

        path = filedialog.askopenfilename(
            title="Select Face Image",
            filetypes=[
                (
                    "Image Files",
                    "*.jpg *.jpeg *.png *.bmp"
                )
            ]
        )

        if not path:
            return

        frame = cv2.imread(
            path
        )

        if frame is None:

            messagebox.showerror(
                "Image Error",
                "Could not read the selected image."
            )

            return

        frame = (
            resize_image_for_registration(
                frame
            )
        )

        faces = detect_faces(
            frame
        )

        face = get_largest_face(
            faces
        )

        if face is None:

            messagebox.showwarning(
                "No Face",
                "No face detected in the image."
            )

            return

        feature = get_embedding(
            frame,
            face
        )

        if feature is None:

            messagebox.showerror(
                "Face Error",
                "Could not create face embedding."
            )

            return

        self.captured_embedding = (
            feature
        )

        self.selected_uploaded_image = (
            path
        )

        if safe_exists(
            self.add_camera_label
        ):

            self.show_camera_frame(
                frame,
                self.add_camera_label,
                max_width=700,
                max_height=510
            )

        if safe_exists(
            self.add_status_label
        ):

            self.add_status_label.config(
                text=(
                    "✅ Photo loaded successfully.\n"
                    "Click Register Person."
                ),
                fg="#059669"
            )


    # ========================================================
    # REGISTER PERSON
    # ========================================================

    def register_person(self):

        if self.captured_embedding is None:

            messagebox.showwarning(
                "No Face",
                "Capture a face or upload a photo first."
            )

            return

        if not safe_exists(
            self.add_name_entry
        ):

            return

        name = (
            self.add_name_entry
            .get()
            .strip()
        )

        if not name:

            messagebox.showwarning(
                "Name Required",
                "Enter the person's name."
            )

            return

        # Duplicate check

        for person in database:

            existing_name = person.get(
                "name",
                ""
            )

            embeddings = person.get(
                "embeddings",
                []
            )

            for stored_feature in embeddings:

                score = compare_embedding(
                    self.captured_embedding,
                    stored_feature
                )

                if (
                    score
                    >=
                    DUPLICATE_THRESHOLD
                ):

                    # Same person

                    if (
                        existing_name.lower()
                        ==
                        name.lower()
                    ):

                        person.setdefault(
                            "embeddings",
                            []
                        ).append(
                            self.captured_embedding
                        )

                        person["active"] = (
                            person.get(
                                "active",
                                True
                            )
                        )

                        save_database()

                        messagebox.showinfo(
                            "Updated",
                            f"{name} already exists.\n"
                            "New face image added."
                        )

                        self.reset_add_form()

                        return

                    # Different person

                    else:

                        messagebox.showwarning(
                            "Duplicate Face",
                            "This face already belongs "
                            f"to '{existing_name}'."
                        )

                        return

        # New person

        database.append(
            {
                "name": name,
                "embeddings": [
                    self.captured_embedding
                ],
                "active": True
            }
        )

        if save_database():

            messagebox.showinfo(
                "Success",
                f"✅ {name} registered successfully."
            )

            self.reset_add_form()

        else:

            messagebox.showerror(
                "Database Error",
                "Could not save database."
            )


    # ========================================================
    # RESET ADD FORM
    # ========================================================

    def reset_add_form(self):

        self.stop_add_camera()

        self.captured_embedding = None

        self.selected_uploaded_image = None

        self.latest_add_frame = None

        if safe_exists(
            self.add_name_entry
        ):

            self.add_name_entry.delete(
                0,
                tk.END
            )

        if safe_exists(
            self.add_camera_label
        ):

            self.add_camera_label.config(
                image="",
                text=(
                    "📷\n\n"
                    "Add Person Camera\n\n"
                    "Click Start Camera"
                )
            )

            self.add_camera_label.image = None

        if safe_exists(
            self.add_status_label
        ):

            self.add_status_label.config(
                text="Ready",
                fg="#6b7280"
            )


    # ========================================================
    # MANAGE PEOPLE
    # ========================================================

    def show_manage_people(self):

        self.clear_content()

        header = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        header.pack(
            fill="x",
            padx=16,
            pady=(10, 6)
        )

        tk.Label(
            header,
            text="Manage People",
            font=(
                "Segoe UI",
                18,
                "bold"
            ),
            bg="#f3f4f6",
            fg="#111827"
        ).pack(
            side="left"
        )

        tk.Button(
            header,
            text="➕ Add Person",
            command=self.show_add_person,
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            bg="#2563eb",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(
            side="right",
            padx=3
        )

        tk.Button(
            header,
            text="🔄 Refresh",
            command=self.show_manage_people,
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            bg="#4b5563",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(
            side="right",
            padx=3
        )

        outer = tk.Frame(
            self.content_frame,
            bg="#f3f4f6"
        )

        outer.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=8
        )

        canvas = tk.Canvas(
            outer,
            bg="#f3f4f6",
            highlightthickness=0
        )

        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview
        )

        list_frame = tk.Frame(
            canvas,
            bg="#f3f4f6"
        )

        canvas_window = (
            canvas.create_window(
                (0, 0),
                window=list_frame,
                anchor="nw"
            )
        )

        list_frame.bind(
            "<Configure>",
            lambda event:
            canvas.configure(
                scrollregion=canvas.bbox(
                    "all"
                )
            )
        )

        canvas.bind(
            "<Configure>",
            lambda event:
            canvas.itemconfig(
                canvas_window,
                width=event.width
            )
        )

        canvas.configure(
            yscrollcommand=scrollbar.set
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        if len(database) == 0:

            tk.Label(
                list_frame,
                text=(
                    "No registered people.\n\n"
                    "Click 'Add Person' to register."
                ),
                font=(
                    "Segoe UI",
                    13
                ),
                bg="#f3f4f6",
                fg="#6b7280"
            ).pack(
                pady=80
            )

            return

        for index, person in enumerate(
            database
        ):

            self.create_person_row(
                list_frame,
                index,
                person
            )


    # ========================================================
    # PERSON ROW
    # ========================================================

    def create_person_row(
        self,
        parent,
        index,
        person
    ):

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

        row = tk.Frame(
            parent,
            bg="white",
            bd=1,
            relief="solid"
        )

        row.pack(
            fill="x",
            pady=5
        )

        info = tk.Frame(
            row,
            bg="white"
        )

        info.pack(
            side="left",
            fill="both",
            expand=True,
            padx=12,
            pady=8
        )

        tk.Label(
            info,
            text=name,
            font=(
                "Segoe UI",
                11,
                "bold"
            ),
            bg="white",
            fg="#111827"
        ).pack(
            anchor="w"
        )

        status_text = (
            "🟢 ACTIVE"
            if active
            else
            "🔴 DISABLED"
        )

        status_color = (
            "#16a34a"
            if active
            else
            "#dc2626"
        )

        tk.Label(
            info,
            text=(
                f"{status_text}   •   "
                f"{len(embeddings)} "
                f"face image(s)"
            ),
            font=(
                "Segoe UI",
                9
            ),
            bg="white",
            fg=status_color
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        buttons = tk.Frame(
            row,
            bg="white"
        )

        buttons.pack(
            side="right",
            padx=8,
            pady=8
        )

        if active:

            tk.Button(
                buttons,
                text="🔒 Disable",
                command=lambda n=name:
                self.disable_person(n),
                font=(
                    "Segoe UI",
                    9,
                    "bold"
                ),
                bg="#f59e0b",
                fg="white",
                relief="flat",
                bd=0,
                cursor="hand2"
            ).pack(
                side="left",
                padx=2
            )

        else:

            tk.Button(
                buttons,
                text="🔓 Enable",
                command=lambda n=name:
                self.enable_person(n),
                font=(
                    "Segoe UI",
                    9,
                    "bold"
                ),
                bg="#16a34a",
                fg="white",
                relief="flat",
                bd=0,
                cursor="hand2"
            ).pack(
                side="left",
                padx=2
            )

        tk.Button(
            buttons,
            text="🗑 Delete",
            command=lambda n=name:
            self.delete_person(n),
            font=(
                "Segoe UI",
                9,
                "bold"
            ),
            bg="#dc2626",
            fg="white",
            relief="flat",
            bd=0,
            cursor="hand2"
        ).pack(
            side="left",
            padx=2
        )


    # ========================================================
    # DISABLE
    # ========================================================

    def disable_person(
        self,
        name
    ):

        for person in database:

            if (
                person.get(
                    "name",
                    ""
                ).lower()
                ==
                name.lower()
            ):

                confirm = (
                    messagebox.askyesno(
                        "Disable Person",
                        f"Disable access for {name}?"
                    )
                )

                if not confirm:
                    return

                person["active"] = False

                if save_database():

                    messagebox.showinfo(
                        "Disabled",
                        f"🔒 {name} has been disabled."
                    )

                    self.show_manage_people()

                return


    # ========================================================
    # ENABLE
    # ========================================================

    def enable_person(
        self,
        name
    ):

        for person in database:

            if (
                person.get(
                    "name",
                    ""
                ).lower()
                ==
                name.lower()
            ):

                confirm = (
                    messagebox.askyesno(
                        "Enable Person",
                        f"Enable access for {name}?"
                    )
                )

                if not confirm:
                    return

                person["active"] = True

                if save_database():

                    messagebox.showinfo(
                        "Enabled",
                        f"🔓 {name} is now enabled."
                    )

                    self.show_manage_people()

                return


    # ========================================================
    # DELETE
    # ========================================================

    def delete_person(
        self,
        name
    ):

        confirm = (
            messagebox.askyesno(
                "Delete Person",
                f"Delete '{name}' permanently?"
            )
        )

        if not confirm:
            return

        for index, person in enumerate(
            database
        ):

            if (
                person.get(
                    "name",
                    ""
                ).lower()
                ==
                name.lower()
            ):

                database.pop(
                    index
                )

                self.greeted_people.discard(
                    name
                )

                if save_database():

                    messagebox.showinfo(
                        "Deleted",
                        f"🗑 {name} deleted."
                    )

                    self.show_manage_people()

                return


    # ========================================================
    # CLOSE
    # ========================================================

    def on_close(self):

        if self.closing:
            return

        self.closing = True

        print(
            "🛑 Closing AI EYES..."
        )

        try:
            self.stop_recognition_camera()
        except Exception:
            pass

        try:
            self.stop_add_camera()
        except Exception:
            pass

        global voice_running

        voice_running = False

        try:

            voice_queue.put_nowait(
                None
            )

        except Exception:
            pass

        try:

            self.root.destroy()

        except Exception:
            pass

        print(
            "👋 AI EYES closed"
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = AIEyesApp(
        root
    )

    root.mainloop()