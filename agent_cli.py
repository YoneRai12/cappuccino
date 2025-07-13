import sys
import asyncio
import base64
import io
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from PIL import Image

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


async def call_openai(prompt: str) -> dict[str, list[str]]:
    """Send a prompt directly to OpenAI and return text and images."""
    resp = await client.responses.create(
        model="gpt-4.1",
        tools=[
            {"type": "web_search_preview"},
            {"type": "code_interpreter", "container": {"type": "auto"}},
            {"type": "image_generation"},
        ],
        input=[{"role": "user", "content": prompt}],
    )

    text_blocks: list[str] = []
    images: list[str] = []
    for item in resp.output:
        if item.type == "message":
            for block in item.content:
                if getattr(block, "type", "") in {"output_text", "text"}:
                    txt = getattr(block, "text", "").strip()
                    if txt:
                        text_blocks.append(txt)
        elif item.type == "image_generation_call":
            img_data = getattr(item, "result", None)
            if img_data:
                images.append(f"data:image/png;base64,{img_data}")

    return {"text": "\n\n".join(text_blocks), "images": images}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    query = sys.argv[1] if len(sys.argv) > 1 else input("Query: ")
    result = asyncio.run(call_openai(query))

    text_output = result.get("text", "")
    if text_output:
        print(text_output)

    images = result.get("images", [])
    if images:
        for i, img_data_uri in enumerate(images):
            try:
                _, encoded = img_data_uri.split(",", 1)
                binary_data = base64.b64decode(encoded)
                image = Image.open(io.BytesIO(binary_data))
                filename = f"generated_image_{i+1}.png"
                image.save(filename)
                print(f"画像{i+1}: {filename} に保存しました。")
            except Exception as e:  # pragma: no cover - manual use
                print(f"画像{i+1}の保存中にエラーが発生しました: {e}")


if __name__ == "__main__":  # pragma: no cover - manual run
    main()
