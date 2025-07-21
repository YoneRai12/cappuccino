import subprocess
import sys

# メインBOT（run_server_bot.pyで起動）
main_proc = subprocess.Popen([sys.executable, "run_server_bot.py"])

# TTS BOT
tts_proc = subprocess.Popen([sys.executable, "ttsbot.py"])

try:
    main_proc.wait()
    tts_proc.wait()
except KeyboardInterrupt:
    print("終了処理中...")
    main_proc.terminate()
    tts_proc.terminate()
    main_proc.wait()
    tts_proc.wait() 