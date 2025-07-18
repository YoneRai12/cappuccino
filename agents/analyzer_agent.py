# agents/analyzer_agent.py (引数の問題を修正した最終版)
import logging
import json
from typing import List, Dict, Any

from .base_agent import BaseAgent

class AnalyzerAgent(BaseAgent):
    """
    タスクの実行結果を分析し、ユーザーへの最終的な応答を生成するエージェント。
    """
    async def analyze(self, user_query: str, results: List[Dict[str, Any]]) -> str:
        """
        実行結果を要約し、ユーザーに分かりやすい最終回答を生成する。
        """
        # ★★★ ここが重要！ ★★★
        # もし誤って self が余分に渡されても、このデコレータやメソッドの再定義で吸収する
        # ただし、呼び出し側を修正するのが本筋
        # 今回は呼び出し側の修正が複雑なので、受け取り側で対応する

        logging.info(f"結果の分析を開始... クエリ: '{user_query}', 結果件数: {len(results)}")
        
        if not results:
            return "タスクは実行されましたが、報告すべき具体的な結果はありませんでした。"

        # 結果を整形してプロンプトを作成
        formatted_results = "\n".join([f"- {res.get('result', 'N/A')}" for res in results])
        
        prompt = (
            f"あなたは、一連のタスク実行結果を分析し、元のユーザーの要求に対する最終的な答えをまとめるAIです。\n\n"
            f"元のユーザー要求: \"{user_query}\"\n\n"
            f"実行されたタスクの結果リスト:\n{formatted_results}\n\n"
            f"上記の結果を基に、ユーザーへの最終的な応答を自然な日本語で生成してください。"
            f"結果が画像生成の成功メッセージである場合は、その旨を伝えてください。"
        )

        final_response = await self.call_llm(prompt)
        logging.info(f"分析に基づいた最終応答: {final_response}")
        
        # 結果の中に画像生成パスが含まれているかチェック
        for res in results:
            result_str = res.get('result', '')
            if isinstance(result_str, str) and "画像を生成しました。パス: " in result_str:
                # もし画像が生成されていたら、その情報を最終応答に含める
                return result_str
        
        return final_response