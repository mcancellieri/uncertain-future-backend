import io
import os
from flask import Flask, send_file, request
from pydub import AudioSegment

app = Flask(__name__)

# Base directory paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets", "uncertainfutures")

print("Preloading audio assets into RAM...")

# Preload all 85 sentence clips into RAM
MEM_CLIPS = {}
for i in range(1, 86):
    file_path = os.path.join(ASSETS_DIR, "uncertainfutures", f"part_{i}.mp3")
    MEM_CLIPS[i] = AudioSegment.from_mp3(file_path)

# Preload background music at -18dB volume
bg_path = os.path.join(ASSETS_DIR, "bgmusic.mp3")
MEM_BG_MUSIC = AudioSegment.from_mp3(bg_path) - 18

print("All audio assets loaded into RAM successfully!")

# Deterministic PRNG logic matching frontend seed
def seeded_random(seed):
    a = seed & 0xFFFFFFFF
    def rand():
        nonlocal a
        a = (a + 0x6d2b79f5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | a) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rand

def hash_date(digits_str):
    digits = [int(d) for d in digits_str if d.isdigit()]
    acc = 7
    for d in digits:
        acc = (acc * 31 + d) & 0xFFFFFFFF
    return acc

def get_fortune_part_numbers(digits_str):
    rand = seeded_random(hash_date(digits_str))
    pick = lambda count, offset: offset + int(rand() * count) + 1
    return [
        pick(17, 0),    # Opening (1-17)
        pick(17, 17),   # Subject (18-34)
        pick(17, 34),   # Action (35-51)
        pick(17, 51),   # Time (52-68)
        pick(17, 68)    # Advice (69-85)
    ]

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/get-fortune-audio", methods=["GET"])
def get_fortune_audio():
    digits = request.args.get("digits", "00000000")
    part_numbers = get_fortune_part_numbers(digits)

    # 1. Concatenate voice clips from memory
    voice_track = AudioSegment.empty()
    pause = AudioSegment.silent(duration=400)

    for num in part_numbers:
        voice_track += MEM_CLIPS[num] + pause

    # 2. Add 5-second trailing background music fade
    fade_out_ms = 5000
    total_duration = len(voice_track) + fade_out_ms

    # 3. Loop background music to duration & apply trailing fade-out
    bg_track = AudioSegment.empty()
    while len(bg_track) < total_duration:
        bg_track += MEM_BG_MUSIC
    bg_track = bg_track[:total_duration].fade_out(fade_out_ms)

    # 4. Mix voice over background music
    final_mix = bg_track.overlay(voice_track)

    # Stream MP3 in response
    buffer = io.BytesIO()
    final_mix.export(buffer, format="mp3")
    buffer.seek(0)
    return send_file(buffer, mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))