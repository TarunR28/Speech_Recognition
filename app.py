from datetime import datetime
from fileinput import filename
from urllib import response
import uuid
from google.cloud import speech
from google.protobuf import wrappers_pb2 # type: ignore
from google.cloud import texttospeech_v1


from flask import Flask, flash, render_template, request, redirect, url_for, send_file, send_from_directory
from werkzeug.utils import secure_filename

import os

service_account = "conv-ai-436204-ffd7664da115.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = service_account

client=speech.SpeechClient()
client2 = texttospeech_v1.TextToSpeechClient()

app = Flask(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
TTS_FOLDER = 'tts'
ALLOWED_EXTENSIONS = {'wav'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TTS_FOLDER'] = TTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TTS_FOLDER, exist_ok = True )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_files():
    files = []
    for filename in os.listdir(UPLOAD_FOLDER):
        if allowed_file(filename):
            files.append(filename)
            print(filename)
    files.sort(reverse=True)
    return files

def get_tts_files():
    tts_files = []
    for filename in os.listdir(TTS_FOLDER):
        if allowed_file(filename):
            tts_files.append(filename)
            print(filename)
    tts_files.sort(reverse=True)
    return tts_files
    
def sample_recognize(content):
        audio=speech.RecognitionAudio(content=content)

        config=speech.RecognitionConfig(
  # encoding=speech.RecognitionConfig.AudioEncoding.MP3,
        #sample_rate_hertz=24000,
        language_code="en-US",
        model="latest_long",
        audio_channel_count=1,
        enable_word_confidence=True,
        enable_word_time_offsets=True,
        )

        operation=client.long_running_recognize(config=config, audio=audio)

        response=operation.result(timeout=90)

        txt = ''
        for result in response.results:
            txt = txt + result.alternatives[0].transcript + '\n'
        

        return txt

def sample_synthesize_speech(text=None, ssml=None):
    input = texttospeech_v1.SynthesisInput()
    if ssml:
      input.ssml = ssml
    else:
      input.text = text

    voice = texttospeech_v1.VoiceSelectionParams()
    voice.language_code = "en-US"
    # voice.ssml_gender = "MALE"

    audio_config = texttospeech_v1.AudioConfig()
    audio_config.audio_encoding = "LINEAR16"

    request = texttospeech_v1.SynthesizeSpeechRequest(
        input=input,
        voice=voice,
        audio_config=audio_config,
    )

    response = client2.synthesize_speech(request=request)

    return response.audio_content

@app.route('/')
def index():
    files = get_files()
    tts_files = get_tts_files()
    return render_template('index.html', files=files,tts_files=tts_files)

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'audio_data' not in request.files:
        flash('No audio data')
        return redirect(request.url)
    file = request.files['audio_data']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        # filename = secure_filename(file.filename)
        filename = datetime.now().strftime("%Y%m%d-%I%M%S%p") + '.wav'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        with open(file_path, 'rb') as f:
            content = f.read()
        text = sample_recognize(content)
        text_filename = os.path.join('uploads', filename.replace('.wav', '.txt'))
        os.makedirs('uploads', exist_ok=True)  # Ensure 'texts/' folder exists
        with open(text_filename, 'w') as f:
            f.write(text)


    return redirect('/') #success

@app.route('/upload/<filename>')
def get_file(filename):
    return send_file(filename)



    
@app.route('/upload_text', methods=['POST'])
def upload_text():
    text = request.form['text']
    print(text)

    audio_content = sample_synthesize_speech(text = text)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    unique_filename = f"audio_{timestamp}_{uuid.uuid4().hex[:6]}.wav"
    audio_file_path = os.path.join(app.config['TTS_FOLDER'], unique_filename)

    with open(audio_file_path, 'wb') as out:
        out.write(audio_content)



    #
    #
    # Modify this block to call the stext to speech API
    # Save the output as a audio file in the 'tts' directory 
    # Display the audio files at the bottom and allow the user to listen to them
    #

    return redirect('/') #success

@app.route('/script.js',methods=['GET'])
def scripts_js():
    return send_file('./script.js')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/tts/<filename>')
def uploaded_tts_file(filename):
    return send_from_directory(app.config['TTS_FOLDER'], filename)

@app.route('/texts/<filename>')
def get_text_file(filename):
    return send_from_directory('texts', filename)

if __name__ == '__main__':
    app.run(debug=True)