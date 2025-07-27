import sys
import asyncio
import base64
import io
import os
from typing import Dict, List
from dotenv import load_dotenv
from PIL import Image
from config import settings
from cappuccino_agent import CappuccinoAgent

load_dotenv()
agent = CappuccinoAgent()


async def call_local_llm(prompt: str) -> Dict[str, List[str]]:
    """Send a prompt to the Cappuccino agent and return text and images."""
    result = await agent.run(prompt)
    text_output = result.get("text") if isinstance(result, dict) else str(result)
    return {"text": text_output, "images": result.get("files", []) if isinstance(result, dict) else []}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
    query = sys.argv[1] if len(sys.argv) > 1 else input("Query: ")
    result = asyncio.run(call_local_llm(query))

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
