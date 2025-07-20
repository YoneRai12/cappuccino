import os
import tempfile
import time
import yt_dlp
import logging
import uuid
import subprocess
from yt_dlp.utils import sanitize_filename

YOUTUBE_AVAILABLE = True
try:
    import yt_dlp
except ImportError:
    YOUTUBE_AVAILABLE = False
    print("yt-dlp not available. YouTube functionality will be disabled.")

logger = logging.getLogger(__name__)

def convert_to_mp3(input_path, output_path):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn", "-acodec", "libmp3lame", "-ab", "96k", output_path
    ]
    subprocess.run(cmd, check=True)

def download_youtube_audio(url: str):
    """YouTubeから音声をダウンロードし、(mp3ファイルパス, タイトル, 再生時間)を返す"""
    if not YOUTUBE_AVAILABLE:
        print("YOUTUBE_AVAILABLE=False")
        return None, None, None
    try:
        unique_id = uuid.uuid4().hex
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'tmp_{unique_id}_%(title)s.%(ext)s',
            'keepvideo': True,  # 変換前ファイルを残す
            'preferredquality': '96',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)  # download=Trueで実際にダウンロード
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            input_file = ydl.prepare_filename(info)
            print(f"実際のダウンロードファイル: {input_file} 存在: {os.path.exists(input_file)}")
            if input_file and os.path.exists(input_file):
                base, _ = os.path.splitext(input_file)
                mp3_file = f"{base}.mp3"
                try:
                    convert_to_mp3(input_file, mp3_file)
                except Exception as e:
                    logger.error(f"ffmpeg変換エラー: {e}")
                    print(f"ffmpeg変換エラー: {e}")
                    return None, None, None
                # 変換後のmp3ファイルが使えるまで待つ
                for _ in range(30):
                    try:
                        with open(mp3_file, "rb") as f:
                            break
                    except PermissionError:
                        time.sleep(0.2)
                print(f"mp3_file: {mp3_file} 存在: {os.path.exists(mp3_file)}")
                if not os.path.exists(mp3_file):
                    print(f"mp3ファイルが見つかりません: {mp3_file}")
                    return None, None, None
                return mp3_file, title, duration
            else:
                print("input_fileが見つかりません")
                return None, None, None
    except Exception as e:
        logger.error(f"YouTube音声ダウンロードエラー: {e}")
        print(f"YouTube音声ダウンロードエラー: {e}")
        return None, None, None

def get_youtube_audio_stream_url(url: str):
    """YouTube音声のストリーミング再生用URL・タイトル・再生時間を返す"""
    if not YOUTUBE_AVAILABLE:
        return None, None, None
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info['url']
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            return stream_url, title, duration
    except Exception as e:
        logger.error(f"YouTubeストリーミングURL取得エラー: {e}")
        return None, None, None

def save_streaming_bgm_segment(stream_url: str, duration: float, output_path: str) -> bool:
    """
    ストリーミングBGMの指定秒数分をffmpegでキャプチャし、output_pathにwavで保存する。
    duration: 保存したい秒数（例: TTS音声の長さ）
    output_path: 保存先ファイルパス
    戻り値: 成功ならTrue, 失敗ならFalse
    """
    try:
        cmd = [
            "ffmpeg", "-y", "-i", stream_url,
            "-t", str(duration),
            "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2", "-b:a", "96k", output_path
        ]
        subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        logger.error(f"ストリーミングBGMキャプチャ失敗: {e}")
        return False 