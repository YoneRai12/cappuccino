from typing import List, Dict

TOOLS_SCHEMA: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "media_generate_speech",
            "description": "Generate speech audio from text and save as an MP3 file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "output_path": {"type": "string"}
                },
                "required": ["text", "output_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_analyze_image",
            "description": "Extract text from an image using OCR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_path": {"type": "string"}
                },
                "required": ["image_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_recognize_speech",
            "description": "Transcribe speech from an audio file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_path": {"type": "string"}
                },
                "required": ["audio_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_describe_video",
            "description": "Return the average color of the first frame of a video.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"}
                },
                "required": ["video_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "info_search_image",
            "description": "Search images using the Unsplash API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "media_analyze_video",
            "description": "Return basic metadata for a video file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_path": {"type": "string"}
                },
                "required": ["video_path"]
            }
        }
    },
]

AGENT_SCHEMA: Dict = {
    "name": "CappuccinoAgent",
    "version": "1.0",
    "description": "General purpose asynchronous agent",
}
