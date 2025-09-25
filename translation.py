import threading
from queue import Queue
import tempfile, os
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import constants
import sounddevice as sd
import numpy as np
import whisper
from googletrans import Translator
from deepmultilingualpunctuation import PunctuationModel

translator = Translator()
stop_flag = threading.Event()
translation_queue = Queue()
tts_queue = Queue()
model = whisper.load_model("small")
punct_model = PunctuationModel()

# ======================================================
# Translation Worker (never dies)
# ======================================================
def translation_worker():
    while True:
        text, src, dest, callback = translation_queue.get()
        try:
            result = translator.translate(text, src=src, dest=dest)
            translated = result.text
            if callback:
                callback(translated, text, src, dest)
            enqueue_tts(translated, dest)
        except Exception as e:
            print("❌ Translation error:", e)

threading.Thread(target=translation_worker, daemon=True).start()

# ======================================================
# TTS Worker (never dies)
# ======================================================
def tts_worker():
    while True:
        text, lang = tts_queue.get()
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                filename = f.name
            gTTS(text=text, lang=lang, slow=False).save(filename)
            audio = AudioSegment.from_file(filename, format="mp3")
            play(audio)
            os.remove(filename)
        except Exception as e:
            print("⚠️ TTS error:", e)

threading.Thread(target=tts_worker, daemon=True).start()

def enqueue_tts(text, lang):
    tts_queue.put((text, lang))

# ======================================================
# Streaming Recognizer for Speech Translation
# ======================================================
class StreamingRecognizer:
    def __init__(self, get_src_lang, get_dest_lang, callback=None, partial_callback=None):
        self.get_src_lang = get_src_lang
        self.get_dest_lang = get_dest_lang
        self.callback = callback
        self.partial_callback = partial_callback
        self.buffer = np.zeros(0, dtype=np.float32)
        self.fs = 16000
        self.lock = threading.Lock()

    def audio_callback(self, indata, frames, time, status):
        if stop_flag.is_set():
            raise sd.CallbackStop()
        with self.lock:
            self.buffer = np.concatenate((self.buffer, indata.flatten()))
        # partial transcription for real-time display
        if self.partial_callback and len(self.buffer) > self.fs * 0.5:
            partial_text = model.transcribe(self.buffer)["text"].strip()
            if len(partial_text) > 3:
                try:
                    partial_text = punct_model.restore_punctuation(partial_text)
                except:
                    pass
            self.partial_callback(partial_text)

    def run(self):
        print("🎤 Listening (streaming)…")
        with sd.InputStream(samplerate=self.fs, channels=1, callback=self.audio_callback, blocksize=1024):
            while not stop_flag.is_set():
                sd.sleep(500)
                with self.lock:
                    if len(self.buffer) < self.fs * 1:
                        continue
                    audio_chunk = self.buffer.copy()
                    self.buffer = np.zeros(0, dtype=np.float32)
                try:
                    result = model.transcribe(audio_chunk, language=self.get_src_lang())
                    text = result["text"].strip()
                    if not text:
                        continue
                    # only punctuate if text is not too short
                    if len(text) > 3:
                        try:
                            text = punct_model.restore_punctuation(text)
                        except:
                            pass
                    translation_queue.put((text, self.get_src_lang(), self.get_dest_lang(), self.callback))
                except Exception as e:
                    print("❌ Recognition error:", e)

# ======================================================
# Public API
# ======================================================
def threadedAndBetter2(get_src_lang, get_dest_lang, callback=None, partial_callback=None):
    stop_flag.clear()
    recognizer = StreamingRecognizer(get_src_lang, get_dest_lang, callback, partial_callback)
    threading.Thread(target=recognizer.run, daemon=True).start()

def stopListening():
    stop_flag.set()
