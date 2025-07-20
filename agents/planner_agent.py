import asyncio
import logging
import json
import re
from typing import List, Dict, Any
from .base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    async def plan(self, user_query: str, plan_queue: asyncio.Queue, tools_schema: List[Dict[str, Any]]):
        try:
            # 1. 意図推定
            intent_prompt = (
                f"ユーザーの発言: {user_query}\n"
                f"この発言の意図を以下から1つだけ選んでラベルで返してください: "
                f"['news', 'weather', 'image', 'time', 'command', 'chat']\n"
                f"命令や依頼は'command'、雑談や日常会話は'chat'、質問は内容に応じて分類してください。\n"
                f"出力はラベルのみ。"
            )
            intent = (await self.call_llm(intent_prompt)).strip().lower()

            # 2. 意図に応じてタスクを決定
            if intent == "news":
                await plan_queue.put({"function": "show_news"})
                return
            elif intent == "weather":
                await plan_queue.put({"function": "show_weather"})
                return
            elif intent == "time":
                await plan_queue.put({"function": "get_current_time"})
                return
            elif intent == "image":
                enhanced_prompt = await self.get_strict_sd_prompt(user_query)
                await plan_queue.put({
                    "function": "generate_image",
                    "prompt": enhanced_prompt
                })
                return
            elif intent == "command":
                # 命令・依頼は即答（ストレートに）
                prompt_command = (
                    f"ユーザーのリクエスト: {user_query}\n"
                    f"あなたはAIアシスタントです。命令や依頼にはストレートに即答してください。余計な前置きや曖昧な返しは不要です。"
                )
                response = await self.call_llm(prompt_command)
                await plan_queue.put({"function": "respond_to_user", "parameters": {"text": response.strip()}})
                return
            else:
                # 雑談・日常会話はフランクに
                prompt_chat = (
                    f"ユーザーの発言: {user_query}\n"
                    f"あなたは親しみやすいAIアシスタントです。雑談や日常会話にはフランクで柔らかい日本語で返答してください。"
                )
                response = await self.call_llm(prompt_chat)
                await plan_queue.put({"function": "respond_to_user", "parameters": {"text": response.strip()}})
                return
        except Exception as e:
            logging.error(f"計画作成エラー: {e}", exc_info=True)
            await plan_queue.put({
                "function": "respond_to_user", "text": "計画の作成に失敗しました。"
            })

    def extract_positive_negative(self, text: str) -> str:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        pos = next((l for l in lines if l.lower().startswith("positive:")), None)
        neg = next((l for l in lines if l.lower().startswith("negative:")), None)
        if pos and neg:
            return f"{pos}\n{neg}"
        matches = re.findall(r'Positive:.*|Negative:.*', text, re.IGNORECASE)
        if len(matches) >= 2:
            return f"{matches[0]}\n{matches[1]}"
        return text

    async def get_strict_sd_prompt(self, user_query: str) -> str:
        for _ in range(3):
            prompt = (
                "あなたはStable Diffusionのプロンプトエンジニアです。\n"
                "次の日本語を高品質なStable Diffusion用の英語プロンプトに変換してください。\n"
                "出力は必ず以下の2行のみ、英語で：\n"
                "Positive: [詳細な英語プロンプト]\n"
                "Negative: [ネガティブプロンプト]\n"
                "例や説明、指示文、案内文、日本語の補足は絶対に出力しないでください。\n"
                "あなたの返答は次の2行だけです。他の文は一切不要です。\n"
                f"入力: {user_query}\n"
            )
            result = (await self.call_llm(prompt)).strip()
            result = self.extract_positive_negative(result)
            lines = [l for l in result.splitlines() if l.strip()]
            if len(lines) == 2 and lines[0].startswith("Positive:") and lines[1].startswith("Negative:"):
                return result
        return result
