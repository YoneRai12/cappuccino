"""FastAPI interface for Llama 3.1-latest + Stable Diffusion integration."""

from typing import Any, AsyncGenerator, Dict, List, Optional
import asyncio
import json
import logging
import base64
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import requests
from PIL import Image
from config import settings
from local_llm import LocalLLM

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI設定（Llama 3.1-latest用）
OPENAI_API_KEY = settings.openai_api_key
OPENAI_API_BASE = settings.openai_api_base or "https://api.openai.com/v1"

# Stable Diffusion設定
STABLE_DIFFUSION_URL = settings.stable_diffusion_url
STABLE_DIFFUSION_API_KEY = settings.stable_diffusion_api_key

# LLMクライアント（OpenAI またはローカル）
if settings.local_model_path:
    openai_client = LocalLLM(settings.local_model_path)
else:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

app = FastAPI(title="Llama 3.1-latest + Stable Diffusion API", version="1.0.0")


class LLMRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama-3.1-latest"  # デフォルトをLlama 3.1-latestに変更
    temperature: Optional[float] = 0.8  # Llama用に調整
    max_tokens: Optional[int] = 2048  # Llama用に調整
    use_tools: Optional[bool] = False


class LLMResponse(BaseModel):
    response: str
    model: str
    usage: Optional[Dict[str, Any]]


class ImageGenerationRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = ""
    width: Optional[int] = 512
    height: Optional[int] = 512
    steps: Optional[int] = 20
    cfg_scale: Optional[float] = 7.5
    seed: Optional[int] = -1


class ImageGenerationResponse(BaseModel):
    image: str  # base64 encoded image
    prompt: str
    parameters: Dict[str, Any]


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "llama-3.1-latest"  # デフォルトをLlama 3.1-latestに変更
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    response: str
    model: str


async def call_llama(prompt: str, model: str = "llama-3.1-latest", temperature: float = 0.8, max_tokens: int = 2048) -> Dict[str, Any]:
    """Llama 3.1-latestを呼び出す"""
    try:
        if isinstance(openai_client, LocalLLM):
            text = await openai_client.chat(prompt, max_new_tokens=max_tokens)
            return {"response": text, "model": model, "usage": None}

        response = await openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "response": response.choices[0].message.content,
            "model": model,
            "usage": response.usage.model_dump() if response.usage else None
        }
    except Exception as e:
        logger.error(f"Llama呼び出しエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Llama呼び出しに失敗しました: {str(e)}")


async def generate_image_stable_diffusion(prompt: str, negative_prompt: str = "", width: int = 512, height: int = 512, 
                                        steps: int = 20, cfg_scale: float = 7.5, seed: int = -1) -> str:
    """Stable Diffusionで画像を生成"""
    try:
        # Stable Diffusion APIのパラメータ
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "sampler_name": "DPM++ 2M Karras"
        }
        
        headers = {}
        if STABLE_DIFFUSION_API_KEY:
            headers["Authorization"] = f"Bearer {STABLE_DIFFUSION_API_KEY}"
        
        # Stable Diffusion APIにリクエスト
        response = requests.post(
            f"{STABLE_DIFFUSION_URL}/sdapi/v1/txt2img",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Stable Diffusion API エラー: {response.status_code}")
        
        result = response.json()
        
        # base64エンコードされた画像データを取得
        if "images" in result and len(result["images"]) > 0:
            image_data = result["images"][0]
            return f"data:image/png;base64,{image_data}"
        else:
            raise Exception("画像生成に失敗しました")
            
    except Exception as e:
        logger.error(f"Stable Diffusion画像生成エラー: {e}")
        raise HTTPException(status_code=500, detail=f"画像生成に失敗しました: {str(e)}")


@app.post("/llm/chat", response_model=LLMResponse)
async def llm_chat(request: LLMRequest) -> Dict[str, Any]:
    """Llama 3.1-latestチャット"""
    try:
        result = await call_llama(
            request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return LLMResponse(
            response=result["response"],
            model=result["model"],
            usage=result["usage"]
        )
        
    except Exception as e:
        logger.error(f"Llamaチャットエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/image/generate", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest) -> Dict[str, Any]:
    """Stable Diffusionで画像生成"""
    try:
        image_data = await generate_image_stable_diffusion(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            steps=request.steps,
            cfg_scale=request.cfg_scale,
            seed=request.seed
        )
        
        return ImageGenerationResponse(
            image=image_data,
            prompt=request.prompt,
            parameters={
                "width": request.width,
                "height": request.height,
                "steps": request.steps,
                "cfg_scale": request.cfg_scale,
                "seed": request.seed,
                "negative_prompt": request.negative_prompt
            }
        )
        
    except Exception as e:
        logger.error(f"画像生成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/generate_with_image")
async def generate_with_image(request: LLMRequest) -> Dict[str, Any]:
    """Llama 3.1-latestでテキスト生成し、必要に応じてStable Diffusionで画像も生成"""
    try:
        # Llama 3.1-latestでテキスト生成
        llm_result = await call_llama(
            request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # プロンプトに画像生成の指示があるかチェック
        prompt_lower = request.prompt.lower()
        image_keywords = ["画像", "image", "picture", "draw", "generate image", "create image"]
        
        images = []
        if any(keyword in prompt_lower for keyword in image_keywords):
            try:
                # 画像生成のプロンプトを抽出
                image_prompt = request.prompt
                if "画像:" in request.prompt:
                    image_prompt = request.prompt.split("画像:")[1].strip()
                elif "image:" in request.prompt:
                    image_prompt = request.prompt.split("image:")[1].strip()
                
                image_data = await generate_image_stable_diffusion(image_prompt)
                images.append(image_data)
            except Exception as e:
                logger.warning(f"画像生成に失敗: {e}")
        
        return {
            "text": llm_result["response"],
            "images": images,
            "model": llm_result["model"],
            "usage": llm_result["usage"]
        }
        
    except Exception as e:
        logger.error(f"Llama+画像生成エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """Llama 3.1-latestシンプルチャット"""
    try:
        result = await call_llama(
            request.message,
            model=request.model
        )
        
        return ChatResponse(
            response=result["response"],
            model=result["model"]
        )
        
    except Exception as e:
        logger.error(f"チャットエラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    """Llama 3.1-latestストリーミングチャット"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            model = data.get("model", "llama-3.1-latest")
            
            if isinstance(openai_client, LocalLLM):
                text = await openai_client.chat(message)
                await websocket.send_text(text)
                continue

            async for chunk in openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": message}],
                stream=True
            ):
                if chunk.choices[0].delta.content:
                    await websocket.send_text(chunk.choices[0].delta.content)
                    
    except WebSocketDisconnect:
        logger.info("WebSocket接続が切断されました")
    except Exception as e:
        logger.error(f"ストリーミングチャットエラー: {e}")
        await websocket.send_text(f"error: {str(e)}")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "llama_available": bool(OPENAI_API_KEY),
        "stable_diffusion_available": bool(STABLE_DIFFUSION_URL),
        "models": {
            "llm": ["llama-3.1-latest", "llama-3.1-8b-latest", "llama-3.1-70b-latest"],
            "image_generation": "stable_diffusion"
        }
    }


@app.get("/models")
async def list_models() -> Dict[str, Any]:
    """利用可能なモデル一覧"""
    try:
        if isinstance(openai_client, LocalLLM):
            raise RuntimeError("local model")

        models = await openai_client.models.list()
        return {
            "llm_models": [model.id for model in models.data],
            "llama_models": ["llama-3.1-latest", "llama-3.1-8b-latest", "llama-3.1-70b-latest"],
            "image_models": ["stable_diffusion"],
            "default_llm": "llama-3.1-latest",
            "default_image": "stable_diffusion"
        }
    except Exception as e:
        logger.error(f"モデル一覧取得エラー: {e}")
        return {
            "llm_models": ["llama-3.1-latest", "llama-3.1-8b-latest", "llama-3.1-70b-latest"],
            "llama_models": ["llama-3.1-latest", "llama-3.1-8b-latest", "llama-3.1-70b-latest"],
            "image_models": ["stable_diffusion"],
            "default_llm": "llama-3.1-latest",
            "default_image": "stable_diffusion",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
