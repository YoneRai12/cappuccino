# Llama 3.1-latest + Stable Diffusion API

Llama 3.1-latest（チャット）とStable Diffusion（画像生成）を統合したAPIです。最新のLlamaモデルとStable Diffusionを組み合わせて、テキスト生成と画像生成の両方をサポートします。

## 🚀 機能

### 基本機能
- **Llama 3.1-latestチャット**: 最新のLlama 3.1-latestモデルを使用したテキスト生成
- **Stable Diffusion画像生成**: Stable Diffusionを使用した高品質画像生成
- **統合生成**: Llama 3.1-latestとStable Diffusionを組み合わせた機能
- **ストリーミング**: リアルタイムレスポンス

### サポートモデル
- **チャット**: Llama 3.1-latest、Llama 3.1-8b-latest、Llama 3.1-70b-latest
- **画像生成**: Stable Diffusion

## 📦 インストール

```bash
pip install fastapi uvicorn aiohttp python-dotenv openai requests pillow
```

## 🔧 設定

### 環境変数
```bash
# .envファイルを作成
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1
STABLE_DIFFUSION_URL=http://localhost:7860
STABLE_DIFFUSION_API_KEY=your_stable_diffusion_api_key_here
```

### Stable Diffusion WebUIの設定
1. Stable Diffusion WebUIを起動
2. `--api`フラグを追加してAPIを有効化
3. 必要に応じてAPIキーを設定

## 🚀 起動

```bash
# APIサーバーを起動
python api.py

# または
uvicorn api:app --host 0.0.0.0 --port 8000
```

## 📚 API エンドポイント

### 基本エンドポイント

#### ヘルスチェック
```bash
GET /health
```

#### モデル一覧
```bash
GET /models
```

### Llama 3.1-latestエンドポイント

#### Llama 3.1-latestチャット
```bash
POST /llm/chat
{
  "prompt": "こんにちは！",
  "model": "llama-3.1-latest",
  "temperature": 0.8,
  "max_tokens": 2048
}
```

#### Llama 3.1-latestシンプルチャット
```bash
POST /chat
{
  "message": "Pythonで計算機を作成してください",
  "model": "llama-3.1-latest"
}
```

### Stable Diffusion画像生成エンドポイント

#### Stable Diffusion画像生成
```bash
POST /image/generate
{
  "prompt": "美しい桜の花",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "steps": 20,
  "cfg_scale": 7.5,
  "seed": -1
}
```

### 統合エンドポイント

#### Llama 3.1-latest+Stable Diffusion画像生成
```bash
POST /llm/generate_with_image
{
  "prompt": "美しい桜の花の画像を生成してください。画像: 桜の花",
  "model": "llama-3.1-latest",
  "temperature": 0.8,
  "max_tokens": 2048
}
```

### WebSocket エンドポイント

#### Llama 3.1-latestストリーミングチャット
```javascript
const ws = new WebSocket('ws://localhost:8000/chat/stream');
ws.send(JSON.stringify({
  "message": "こんにちは！",
  "model": "llama-3.1-latest"
}));
```

## 🧪 テスト

```bash
# テストスクリプトを実行
python test_api.py
```

## 📖 使用例

### Python クライアント

```python
import aiohttp
import asyncio

async def test_api():
    async with aiohttp.ClientSession() as session:
        # Llama 3.1-latestチャット
        async with session.post('http://localhost:8000/llm/chat', json={
            "prompt": "こんにちは！",
            "model": "llama-3.1-latest"
        }) as response:
            result = await response.json()
            print(result)
        
        # Stable Diffusion画像生成
        async with session.post('http://localhost:8000/image/generate', json={
            "prompt": "美しい桜の花",
            "width": 512,
            "height": 512
        }) as response:
            result = await response.json()
            print(result)

# 実行
asyncio.run(test_api())
```

### cURL コマンド

```bash
# ヘルスチェック
curl http://localhost:8000/health

# Llama 3.1-latestチャット
curl -X POST http://localhost:8000/llm/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "こんにちは！", "model": "llama-3.1-latest"}'

# Stable Diffusion画像生成
curl -X POST http://localhost:8000/image/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "美しい桜の花", "width": 512, "height": 512}'

# Llama 3.1-latest+Stable Diffusion画像生成
curl -X POST http://localhost:8000/llm/generate_with_image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "美しい桜の花の画像を生成してください。画像: 桜の花", "model": "llama-3.1-latest"}'
```

## 🦙 Llama 3.1-latestの特徴

### Llama 3.1-latestの設定
- **温度**: 0.8（より創造的な出力）
- **最大トークン**: 2048（より長いレスポンス）
- **モデル**: llama-3.1-latest（最新のLlamaモデル）

### Llama 3.1-latestの利点
- **最新技術**: 最新のLlama 3.1-latestモデルを使用
- **高品質**: 高品質なテキスト生成
- **多言語対応**: 日本語を含む多言語対応
- **創造性**: より創造的なコンテンツ生成

## 🎨 Stable Diffusion画像生成の詳細

### Stable Diffusionパラメータ

- **prompt**: 画像生成のプロンプト
- **negative_prompt**: 除外したい要素
- **width/height**: 画像サイズ（512x512推奨）
- **steps**: 生成ステップ数（20-50推奨）
- **cfg_scale**: プロンプトの強度（7.5推奨）
- **seed**: シード値（-1でランダム）

### 画像生成のキーワード

プロンプトに以下のキーワードが含まれていると自動的に画像生成が実行されます：
- "画像"
- "image"
- "picture"
- "draw"
- "generate image"
- "create image"

## 🔧 カスタマイズ

### 新しいLlamaモデルの追加

`api.py`の`call_llama`関数を修正して新しいLlamaモデルを追加できます。

### Stable Diffusionの設定変更

環境変数でStable Diffusionの設定を変更できます：
```bash
STABLE_DIFFUSION_URL=http://your-sd-server:7860
STABLE_DIFFUSION_API_KEY=your-api-key
```

## 🐛 トラブルシューティング

### よくある問題

1. **Llama 3.1-latest APIキーエラー**
   - `.env`ファイルに正しいOpenAI APIキーが設定されているか確認
   - APIキーが有効か確認

2. **Stable Diffusion接続エラー**
   - Stable Diffusion WebUIが起動しているか確認
   - `--api`フラグが設定されているか確認
   - URLとポートが正しいか確認

3. **画像生成エラー**
   - Stable Diffusionのモデルが読み込まれているか確認
   - VRAMが不足していないか確認

### ログ確認

```bash
# ログレベルをDEBUGに変更
export LOG_LEVEL=DEBUG
python api.py
```

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🤝 貢献

プルリクエストやイシューの報告を歓迎します！

## 📞 サポート

問題が発生した場合は、GitHubのイシューページで報告してください。 