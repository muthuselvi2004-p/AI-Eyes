import cv2

# Model paths
detector_model = "models/face_detection_yunet_2023mar.onnx"
recognizer_model = "models/face_recognition_sface_2021dec.onnx"

print("Loading YuNet Face Detector...")

detector = cv2.FaceDetectorYN.create(
    detector_model,
    "",
    (320, 320)
)

print("✅ YuNet loaded successfully")

print("Loading SFace Face Recognizer...")

recognizer = cv2.FaceRecognizerSF.create(
    recognizer_model,
    ""
)

print("✅ SFace loaded successfully")

print("\n🎉 AI EYES Face AI Models Ready!")