# 👁️ AI EYES – Smart Face Access System

**An AI-powered face recognition system for intelligent access control.**

AI EYES is a Python-based application that uses computer vision and face recognition to identify registered individuals and manage access. It provides a smart way to distinguish authorized users from unrecognized individuals.

## 🚀 Features

- **Face Detection:** Detects faces using OpenCV and the YuNet model.
- **Face Recognition:** Uses the SFace model to recognize registered individuals.
- **Access Control:** Identifies recognized and unrecognized faces.
- **Voice Greeting:** Provides voice greetings for recognized users.
- **Person Management:** Supports registering and managing individuals.
- **Access History:** Maintains access records for tracking recognition activity.
- **Live Recognition:** Supports real-time face recognition through a webcam.

## 🛠️ Technologies Used

- Python
- OpenCV
- YuNet – Face Detection
- SFace – Face Recognition
- Tkinter – Graphical User Interface
- pyttsx3 – Text-to-Speech
- Pickle – Local face-data storage

## 📂 Project Structure

```text
smart_face_access/
│
├── models/
│   ├── face_detection_yunet_2023mar.onnx
│   └── face_recognition_sface_2021dec.onnx
│
├── app.py
├── main.py
├── live_recognition.py
├── register_faces.py
├── add_person.py
├── manage_person.py
├── access_history.py
├── test_models.py
├── test_voice.py
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/muthuselvi2004-p/AI-Eyes.git
cd AI-Eyes
```

### 2. Create a virtual environment

```bash
python -m venv ai_eyes_env
```

Activate it on Windows PowerShell:

```powershell
.\ai_eyes_env\Scripts\Activate.ps1
```

### 3. Install dependencies

Install the required Python libraries used by the project. If a `requirements.txt` file is available, run:

```bash
python -m pip install -r requirements.txt
```

### 4. Run the application

Choose the appropriate entry point for your application:

```bash
python app.py
```

If `app.py` is not the main application entry point, run the appropriate script, such as `main.py`.

## 🔍 How It Works

1. The webcam captures a person's face.
2. The YuNet model detects the face.
3. The SFace model extracts face features for recognition.
4. The system compares the detected face with registered face data.
5. The application identifies the person and determines whether they are recognized.
6. Voice greetings and access-history recording support the user experience.

## 🎯 Project Objective

The objective of AI EYES is to explore how artificial intelligence and computer vision can be used to develop a practical face recognition and access-control application.

## 🔮 Future Improvements

- Improve recognition accuracy under different lighting conditions.
- Add administrator authentication and enhanced security.
- Integrate notifications for unrecognized access attempts.
- Add a database for user profiles and access records.
- Develop a web-based dashboard for monitoring access activity.

## 👩‍💻 Developer

**Muthu Selvi**  
B.Tech – Artificial Intelligence and Data Science

GitHub: [muthuselvi2004-p](https://github.com/muthuselvi2004-p)

---

⭐ If you find this project interesting, feel free to explore the repository and share feedback.

