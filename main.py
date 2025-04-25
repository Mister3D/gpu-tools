from flask import Flask, jsonify, request, send_file
from TTS.api import TTS
import time
import whisper
from dotenv import load_dotenv
import os
import uuid
import numpy as np
import wave
import io

# Load environment variables
load_dotenv()

# Accept licence
os.environ["COQUI_TOS_AGREED"] = "1"

# Create voices and tmp folder if not exists
if not os.path.exists("./voices"):
    os.makedirs("./voices")
if not os.path.exists("./tmp"):
    os.makedirs("./tmp")

# Initialize global variables
model = None
tts = None

# Load whisper model
print("Load Whisper model")
model = whisper.load_model("turbo")

# Load TTS model
print("Load XTTS-V2 model")
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")

print("All models are loaded")

UPLOAD_FOLDER = "./tmp"

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Créer le dossier si nécessaire
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def check_token(request):
    auth_header = request.headers.get("Authorization")
    print(f"AUTH HEADER : {auth_header}")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False

    token = auth_header.split(" ")[1]
    print(f"TOKEN USED : {token}")
    api_key = os.getenv("TOKEN")
    print(f"TOKEN API : {api_key}")
    return token == api_key


@app.route("/")
def home():
    if not check_token(request):
        return jsonify({"message": "BAD TOKEN"}), 401

    return jsonify({"message": "GOOD TOKEN"})


@app.route("/voices", methods=["GET"])
def get_voices():
    if not check_token(request):
        return jsonify({"message": "BAD TOKEN"}), 401

    directory = "./voices"
    file_names = [
        os.path.splitext(file)[0]  # Name without extension
        for file in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, file))  # Exlude dir
    ]

    return jsonify({"voices": file_names})


@app.route("/tts", methods=["POST"])
def http_tts():
    if not request.content_type.startswith("multipart/form-data"):
        return jsonify({"error": "Unsupported Media Type"}), 415

    if not check_token(request):
        return jsonify({"message": "BAD TOKEN"}), 401

    data = request.form.get("text")
    data = data.rstrip(".!?")
    data = data.strip()

    if not data:
        return jsonify({"error": "Aucun texte envoyé"}), 400

    speaker_wav = None

    # Vérifier si un échantillon de voix est fourni
    if "voice" in request.files:
        audio_file = request.files["voice"]
        if audio_file.filename != "":
            # Sauvegarder temporairement le fichier
            temp_file = os.path.join(
                app.config["UPLOAD_FOLDER"], f"temp_{uuid.uuid4()}.wav"
            )
            audio_file.save(temp_file)
            speaker_wav = temp_file
    else:
        # Utiliser la voix locale
        speaker_name = request.form.get("speaker")
        if not speaker_name:
            return jsonify({"error": "Aucun speaker ou voice spécifié"}), 400
        speaker_wav = f"./voices/{speaker_name}.wav"

    try:
        wav = tts.tts(text=data, speaker_wav=speaker_wav, language="fr")

        # Remove all 0 at the end of the list
        wav = [x for x in wav if x != 0]

        # Convert list to numpy array
        wav_array = np.array(wav, dtype=np.float32)

        # Create BytesIO object
        wav_io = io.BytesIO()

        # Write WAV file
        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(22050)  # sample rate
            wav_file.writeframes((wav_array * 32767).astype(np.int16).tobytes())

        wav_io.seek(0)

        return send_file(
            wav_io, mimetype="audio/wav", as_attachment=True, download_name="output.wav"
        )
    finally:
        # Nettoyer le fichier temporaire si nécessaire
        if "temp_file" in locals() and os.path.exists(temp_file):
            os.remove(temp_file)


@app.route("/transcribes", methods=["POST"])
def transcribes():
    if not request.content_type.startswith("multipart/form-data"):
        return jsonify({"error": "Unsupported Media Type"}), 415

    if not check_token(request):
        return jsonify({"message": "BAD TOKEN"}), 401

    if "audio" not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400

    # Récupérer le fichier
    file = request.files["audio"]

    # Vérifie si un fichier est présent
    if file.filename == "":
        return jsonify({"error": "Aucun fichier"}), 400

    # ALLOWED_EXTENSIONS = {'mp3', 'wav', 'ogg'}
    ALLOWED_EXTENSIONS = {"wav"}
    if not (
        "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    ):
        return jsonify({"error": "Type de fichier non supporté"}), 400

    unique_filename = f"{uuid.uuid4()}.wav"

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(file_path)

    start_time = time.time()
    result = model.transcribe(file_path)
    end_time = time.time()

    execution_time = end_time - start_time

    return jsonify(
        {
            "message": result["text"],
            "delay": execution_time,
        }
    ), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify(
        {
            "message": "Route not found",
        }
    ), 404


if __name__ == "__main__":
    pass
