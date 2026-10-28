import cv2
import os
import numpy as np
import pickle

# ==============================
# PATHS
# ==============================

DETECTOR_MODEL = "models/face_detection_yunet_2023mar.onnx"
RECOGNIZER_MODEL = "models/face_recognition_sface_2021dec.onnx"

KNOWN_FACES_DIR = "known_faces"
DATABASE_FILE = "face_database.pkl"


# ==============================
# LOAD MODELS
# ==============================

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

print("✅ Models loaded")


# ==============================
# DATABASE
# ==============================

face_database = []


# ==============================
# PROCESS PEOPLE
# ==============================

for person_name in os.listdir(KNOWN_FACES_DIR):

    person_folder = os.path.join(
        KNOWN_FACES_DIR,
        person_name
    )

    if not os.path.isdir(person_folder):
        continue

    print(f"\n👤 Processing: {person_name}")

    person_embeddings = []

    for filename in os.listdir(person_folder):

        if not filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        image_path = os.path.join(
            person_folder,
            filename
        )

        image = cv2.imread(image_path)

        if image is None:
            print(f"❌ Cannot read: {filename}")
            continue

        # --------------------------------
        # Resize very small images
        # --------------------------------

        height, width = image.shape[:2]

        if width < 400:

            scale = 400 / width

            image = cv2.resize(
                image,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_CUBIC
            )

            height, width = image.shape[:2]

        # --------------------------------
        # Detect face
        # --------------------------------

        detector.setInputSize(
            (width, height)
        )

        _, faces = detector.detect(image)

        if faces is None or len(faces) == 0:

            print(
                f"⚠️ No face found: {filename}"
            )

            continue

        # --------------------------------
        # Choose largest face
        # --------------------------------

        largest_face = max(
            faces,
            key=lambda face:
                face[2] * face[3]
        )

        # --------------------------------
        # Align face
        # --------------------------------

        aligned_face = recognizer.alignCrop(
            image,
            largest_face
        )

        # --------------------------------
        # Generate embedding
        # --------------------------------

        feature = recognizer.feature(
            aligned_face
        )

        person_embeddings.append(
            feature
        )

        print(
            f"   ✅ {filename}"
        )

    # --------------------------------
    # Save person
    # --------------------------------

    if person_embeddings:

        face_database.append({
            "name": person_name,
            "embeddings": person_embeddings
        })

        print(
            f"✅ Registered {person_name} "
            f"({len(person_embeddings)} images)"
        )

    else:

        print(
            f"❌ No usable face images for "
            f"{person_name}"
        )


# ==============================
# SAVE DATABASE
# ==============================

with open(
    DATABASE_FILE,
    "wb"
) as file:

    pickle.dump(
        face_database,
        file
    )


print("\n" + "=" * 50)
print("🎉 FACE REGISTRATION COMPLETED")
print("=" * 50)

print(
    f"👥 Registered people: "
    f"{len(face_database)}"
)

print(
    f"💾 Database saved as: "
    f"{DATABASE_FILE}"
)