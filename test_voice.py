import pyttsx3

print("🔊 Starting voice test...")

engine = pyttsx3.init()

engine.setProperty("rate", 150)
engine.setProperty("volume", 1.0)

voices = engine.getProperty("voices")

print("Available voices:", len(voices))

for i, voice in enumerate(voices):
    print(i, voice.name)

engine.say("Welcome Muthu selvi, You are a nice girl you are very pretty devi is your nice sister  ")
engine.runAndWait()

print("✅ Voice test completed")