# agents/analyzer_agent.py (自然な日本語生成に特化した最終版)
import logging
import json
from typing import List, Dict, Any

from .base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    async def analyze(self, user_query: str, results: List[Dict[str, Any]]) -> str:
        logging.info(f"結果の分析を開始... クエリ: '{user_query}', 結果件数: {len(results)}")
        
        if not results:
            return "タスクは実行されましたが、報告すべき結果はありませんでした。"

        # 実行結果を分かりやすく整形
        formatted_results = "\n".join([f"- タスク結果: {res.get('result', 'N/A')}" for res in results])
        
        prompt = (
            f"あなたは、一連のタスク実行結果を分析し、ユーザーへの最終的な応答を生成するAIです。\n"
            f"### 元のユーザー要求:\n\"{user_query}\"\n\n"
            f"### 実行されたタスクの結果リスト:\n{formatted_results}\n\n"
            f"### 指示:\n"
            f"- 上記の結果を基に、ユーザーへの最終的な応答を、親しみやすく自然な日本語で生成してください。\n"
            f"- 結果が画像生成の成功メッセージの場合、その成功を伝えてください。\n"
            f"- 失敗の報告がある場合は、それを正直に、しかし丁寧に伝えてください。\n"
            f"- あなた自身の思考プロセスや解説は含めず、ユーザーへの返信メッセージだけを出力してください。"
        )

        final_response = await self.call_llm(prompt)
        logging.info(f"分析に基づいた最終応答: {final_response}")
        
        # Analyzerの応答の中に、もし画像パスが含まれていたら、それを優先して返す
        for res in results:
            result_str = res.get('result', '')
            if isinstance(result_str, str) and "画像を生成しました。パス: " in result_str:
                return result_str
        
        return final_response