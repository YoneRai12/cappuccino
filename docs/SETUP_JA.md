# セットアップ手順 (日本語)

このドキュメントでは Cappuccino をダウンロードしてから起動するまでの手順を説明します。

## 0. リポジトリの取得

```bash
git clone <repo-url>
cd cappuccino
```

## 1. Python 仮想環境の作成

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows 環境の場合は `Scripts\activate` を実行してください。

## 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

依存パッケージが不足していると言われた場合は、最新の `requirements.txt` を再度
実行してインストールしてください。特に `pycountry` などの追加パッケージをインス
トールし忘れると、Bot 起動時にモジュールが見つからないエラーになります。

## 3. `.env` の作成と編集

```bash
cp .env.example .env
```

`.env` ファイル内に API キーやトークンを入力します。
`OPENAI_API_KEY` を空欄のままにした場合、`LOCAL_MODEL_PATH` に指定した LLaMA などのローカルモデルが使われます。

- `OPENAI_API_KEY`: OpenAI API を利用する際のキー
- `LOCAL_MODEL_PATH`: ローカル LLM モデルのディレクトリ (任意)
- `DISCORD_BOT_TOKEN`: Discord ボット用トークン

## 4. サーバの起動

FastAPI サーバを起動するには次のコマンドを実行します。

```bash
uvicorn api:app --reload
```

API と Discord ボットを同時に動かしたい場合は以下を使います。

```bash
python run_server_bot.py
```

## 5. テストの実行

```bash
pytest -q
```

`DISCORD_BOT_TOKEN` などが設定されていない場合、いくつかのテストはスキップされます。
