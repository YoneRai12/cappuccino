# agents/analyzer_agent.py (修正版)
import logging
from typing import List, Dict, Any

from .base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    async def analyze(self, user_query: str, results: List[Dict[str, Any]]) -> str:
        logging.info(f"結果の分析を開始... クエリ: '{user_query}', 結果件数: {len(results)}")
        
        if not results:
            return "タスクは実行されましたが、報告すべき結果はありませんでした。"

        # 画像生成結果をまず優先チェック
        for res in results:
            result_str = res.get('result', '') or res.get('output', '')
            # function名で画像生成か判定
            func_name = res.get('function', '')
            if func_name == 'generate_image' and isinstance(result_str, str):
                if ("画像を生成しました。パス:" in result_str or "画像生成成功" in result_str):
                    return f"画像の生成が完了しました！ファイルはこちらです：{result_str.split('パス:')[-1].strip()}"
                if "エラー" in result_str or "失敗" in result_str:
                    return "申し訳ありません、画像生成に問題が発生しました。もう一度試していただけますか？"

        # 画像生成に関する結果が無い場合、LLMにより自然な返答を生成
        formatted_results = "\n".join([f"- タスク結果: {res.get('result', res.get('output', 'N/A'))}" for res in results])
        
        prompt = (
            f"あなたは、一連のタスク実行結果を分析し、ユーザーへの最終的な応答を生成するAIです。\n"
            f"### 元のユーザー要求:\n\"{user_query}\"\n\n"
            f"### 実行されたタスクの結果リスト:\n{formatted_results}\n\n"
            f"### 指示:\n"
            f"- 上記の結果を基に、ユーザーへの最終的な応答を、親しみやすく自然な日本語で生成してください。\n"
            f"- 解説や余計な情報は含めず、返信メッセージのみを出力してください。"
        )

        final_response = await self.call_llm(prompt)
        logging.info(f"分析に基づいた最終応答: {final_response}")
        return final_response
