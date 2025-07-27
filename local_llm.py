import asyncio
from concurrent.futures import ThreadPoolExecutor
from transformers import AutoModelForCausalLM, AutoTokenizer

class LocalLLM:
    """Simple wrapper around a local Hugging Face model."""

    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(model_path)
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def chat(self, prompt: str, max_new_tokens: int = 256) -> str:
        loop = asyncio.get_running_loop()

        def _run() -> str:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return await loop.run_in_executor(self.executor, _run)
