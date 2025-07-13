
# Codexへの指示書：自律型AIエージェントの作成

## 1. Codexの能力と要件の理解

このセクションでは、OpenAI Codexの主要な能力と、エージェント作成における考慮事項をまとめます。Codexは、自然言語をコードに変換し、ソフトウェア開発タスクを自動化するために設計された強力なAIコーディングエージェントです。

### 1.1. Codexの主要な能力

Codexは、以下の広範な機能を提供します。

*   **コードの生成と編集**: 自然言語のプロンプトから、機能するコードを生成し、既存のファイルを編集する能力を持ちます。これは、ユーザーの要求を直接コードに落とし込む上で不可欠な機能です。
*   **コマンド実行とテスト**: テストハーネス、リンター、型チェッカーなどのコマンドを実行できます。これにより、生成されたコードの品質検証や、開発ワークフローの自動化が可能です。
*   **コードベースの理解と分析**: コードを分析し、プルリクエストのレビュー、コミットメッセージの作成、差分の要約、さらには安全な変更の提案や実行を行うことができます。これは、既存のプロジェクトに統合されるエージェントにとって重要です。
*   **ソフトウェア開発タスクの自動化**: バグ修正、リファクタリング、テスト生成など、反復的または複雑な開発タスクを自動化する能力があります。
*   **多言語サポート**: Pythonが最も得意な言語ですが、Go、JavaScript、Perl、PHP、Ruby、Shell、Swift、TypeScriptなど、12以上のプログラミング言語に対応しています。これにより、多様な開発環境でのエージェント作成が可能です。
*   **クラウドおよびローカルエージェントとしての機能**: 強力なクラウドベースのエージェントとして機能するだけでなく、ローカルのコーディングエージェントとしてタスクを委任することもできます。

### 1.2. Codexの制限事項と考慮事項

Codexは強力ですが、いくつかの制限事項と考慮すべき点があります。

*   **インターネットアクセス**: タスク実行中にインターネットアクセスが無効になる場合があります。これは、外部APIへのアクセスやリアルタイムデータの取得が必要なエージェントの場合、設計上の重要な考慮事項となります。
*   **正確性の問題**: Codexは解決策を生成できますが、常に正確または最適なコードを生成するとは限りません。生成されたコードの検証とテストは、エージェントの信頼性を確保するために不可欠です。
*   **フロントエンド作業の制限**: 画像入力が必要なフロントエンド作業は処理できません。これは、視覚的なUI要素を操作するエージェントの設計に影響を与える可能性があります。
*   **タスク途中でのガイダンスの欠如**: タスクの途中で追加のガイダンスを提供することができません。エージェントの指示書は、可能な限り詳細かつ明確である必要があります。
*   **レイテンシ**: AIエージェントの性質上、処理にレイテンシが発生する可能性があります。リアルタイム性が求められるアプリケーションでは、この点を考慮した設計が必要です。
*   **利用制限**: 利用プランによっては、使用量に制限がある場合があります。大規模なエージェントや頻繁に実行されるエージェントを作成する場合、この制限を考慮する必要があります。

これらの能力と制限を理解した上で、Codexに作成させるエージェントの要件を定義し、詳細な指示書を設計していきます。特に、インターネットアクセスの制限は、外部ツールとの連携方法に大きな影響を与えるため、注意が必要です。



## 2. エージェントの要件定義と指示書構造の設計

このセクションでは、Codexに作成を依頼するエージェントの具体的な要件を定義し、その実装をガイドするための指示書の全体構造を設計します。

### 2.1. エージェントの目的とコア機能

Codexに作成させるエージェントは、ユーザーの多様な要求に応えることができる「汎用AIアシスタント」を目指します。これは、現在のManusの能力を包含し、さらに拡張性を持つように設計されるべきです。主な目的とコア機能は以下の通りです。

**目的**: ユーザーの自然言語による指示を理解し、適切なツールを自律的に選択・実行することで、複雑なタスクを効率的に解決する。

**コア機能**:

1.  **タスク理解と計画**: ユーザーの意図を正確に解釈し、タスクを達成するための多段階の計画を立案する能力。
2.  **ツール利用**: シェルコマンド実行、ファイル操作、ウェブブラウジング、情報検索、メディア生成など、多様な外部ツールを適切に呼び出し、その結果を解釈する能力。
3.  **自己修正と学習**: 実行中に発生したエラーや予期せぬ結果から学習し、計画や行動を自己修正する能力。
4.  **ユーザーとの対話**: タスクの進捗状況を報告し、必要に応じてユーザーに質問を投げかけ、フィードバックを統合する能力。
5.  **永続性と状態管理**: タスクの途中で中断されても、状態を保存し、再開できる能力。過去の対話履歴やタスクのコンテキストを維持する。
6.  **拡張性**: 将来的に新しいツールや機能を追加しやすいモジュール化されたアーキテクチャ。

### 2.2. 指示書の全体構造

Codexが効率的にエージェントを構築できるよう、指示書は以下の論理的な構造で構成されます。

1.  **はじめに**: エージェントの概要、目的、およびCodexへの期待事項。
2.  **エージェントの目的とコア機能**: 上記で定義したエージェントの目的と、実装すべき主要な機能の詳細。
3.  **アーキテクチャ設計**: エージェントの全体的なアーキテクチャ（LLM、ツールマネージャー、サンドボックス、エージェントループなど）の概要と、各コンポーネント間の相互作用。
4.  **技術スタック**: Pythonを主要言語とし、利用する可能性のあるライブラリやフレームワーク（例: `subprocess`, `requests`, `BeautifulSoup`, `selenium/playwright`, LLM APIクライアントなど）。
5.  **主要コンポーネントの実装ガイドライン**: 各コア機能（ツール利用、エージェントループ、状態管理など）の具体的な実装に関する指示と、概念的なコードスニペット。
    *   **ツール定義**: 各ツールのPython関数としての定義方法と、LLMが利用するためのスキーマ生成の考え方。
    *   **エージェントループ**: 思考、ツール選択、実行、観測のサイクルを管理するメインループのロジック。
    *   **状態管理**: タスクプラン、履歴、ファイルシステムの状態などを永続化する方法。
    *   **エラーハンドリング**: 堅牢なエージェントのためのエラー処理とリカバリ戦略。
6.  **サンドボックス環境の考慮事項**: Codexが動作する環境の特性（インターネットアクセス制限など）を踏まえた実装の注意点。
7.  **テストと検証**: 生成されたエージェントの機能と信頼性を検証するための基本的なテスト方法。
8.  **今後の拡張性**: 将来的な機能追加や改善のための設計指針。
9.  **結論**: まとめとCodexへの最終的な指示。

この構造に従うことで、Codexは体系的にエージェントを構築し、ユーザーの期待に応える高品質な成果物を生成できると期待されます。特に、各セクションで具体的なコード例や概念的な実装パターンを提供することで、Codexの実装プロセスをよりスムーズにします。



## 0. はじめに

この指示書は、OpenAI Codexを用いて、ユーザーの多様な要求に応えることができる汎用AIアシスタントを構築するための詳細なガイドラインを提供します。構築されるエージェントは、現在のManusの能力を基盤としつつ、より高い拡張性と自律性を持つことを目指します。

Codexの卓越したコード生成、理解、および自動化能力を活用し、自然言語の指示から複雑なタスクを解決できる堅牢なシステムを開発することを期待しています。

### Codexへの期待事項

*   **指示の厳守**: この指示書に記載されているすべての要件とガイドラインを厳密に遵守してください。
*   **高品質なコード**: 可読性が高く、保守が容易で、効率的なPythonコードを生成してください。適切なコメント、型ヒント、およびドキュメンテーションを含めてください。
*   **堅牢性**: エラーハンドリングを適切に行い、予期せぬ入力や状況に対しても安定して動作するエージェントを構築してください。
*   **モジュール性**: 各コンポーネントが独立しており、将来的な機能追加や変更が容易なモジュール化された設計を心がけてください。
*   **テスト可能性**: 生成されたコードがテスト可能であることを確認し、必要に応じて基本的な単体テストや統合テストのフレームワークを提供してください。

この指示書は、エージェントのアーキテクチャ、主要なコンポーネントの実装ガイドライン、およびPythonでの具体的なコード例を網羅しています。Codexの能力を最大限に引き出し、革新的なAIエージェントの実現を目指しましょう。




## 3. アーキテクチャ設計

構築するAIエージェントは、以下の主要なコンポーネントから構成されるモジュール化されたアーキテクチャを採用します。これにより、各コンポーネントの独立性が保たれ、システムの拡張性、保守性、およびテスト容易性が向上します。

### 3.1. 全体アーキテクチャ（概念）

エージェントの全体的なアーキテクチャは、LLM、ツールマネージャー、ツール群、サンドボックス環境、状態マネージャー、そしてエージェントコアが密接に連携して動作するモジュール化されたシステムです。Codexは、この概念を基に具体的な実装を進めてください。

### 3.2. 各コンポーネントの役割

*   **ユーザー (User)**: エージェントに自然言語で指示を与え、エージェントからの応答を受け取ります。
*   **エージェントコア (AgentCore)**: エージェントの主要なロジックを管理し、ユーザーとの対話、タスクの初期化、およびエージェントループの実行を調整します。
*   **大規模言語モデル (LLM)**: エージェントの「脳」として機能します。ユーザーのプロンプトを解釈し、タスクの目標を理解し、実行すべきアクション（ツール呼び出しまたはテキスト応答）を決定します。また、ツールの出力結果を分析し、次のステップを計画する役割も担います。Codexは、OpenAIのAPI（例: GPT-4, GPT-3.5-turbo）を利用してこの機能を実現することを想定しています。
*   **ツールマネージャー (ToolManager)**: LLMからのツール呼び出し要求を受け取り、対応するツールを実行し、その結果をLLMにフィードバックします。利用可能なツールの登録と管理も行います。
*   **ツール群 (Tools)**: エージェントが外部環境とインタラクションするためのインターフェースの集合体です。シェルコマンドの実行、ファイルの読み書き、ウェブブラウジング、情報検索、メディア生成など、特定のタスクを実行するためのAPIとして提供されます。各ツールは、明確な入力と出力を持つPython関数として定義されます。
*   **サンドボックス環境 (Sandbox Environment)**: エージェントが操作を実行する隔離された仮想マシン環境です。これにより、セキュリティが確保され、システムへの不要な影響を防ぎながら、様々な操作を実行できます。Codexは、このサンドボックスの制約（例: インターネットアクセス制限）を考慮してツールを実装する必要があります。
*   **状態マネージャー (StateManager)**: エージェントの現在の状態、過去の対話履歴、タスクプラン、およびその他のコンテキスト情報を永続化し、管理します。これにより、エージェントはタスクの途中で中断されても、状態を復元して作業を再開できます。

### 3.3. エージェントループのフロー

エージェントは、以下のステップを繰り返し実行する「エージェントループ」を通じて自律的に動作します。

1.  **ユーザー入力の受信**: ユーザーからの新しいプロンプトを受け取ります。
2.  **コンテキストの構築**: 過去の対話履歴、現在のタスクプラン、および関連するコンテキスト情報を収集し、LLMへの入力として準備します。
3.  **LLMによる思考と決定**: LLMは、与えられたコンテキストとプロンプトに基づいて、次に実行すべきアクション（ツール呼び出し、テキスト応答、またはタスク終了）を決定します。
4.  **アクションの実行**: LLMがツール呼び出しを決定した場合、ツールマネージャーを通じて対応するツールを実行します。
5.  **観測結果の取得**: ツール実行の結果（標準出力、エラー、ファイル内容、APIレスポンスなど）を取得します。
6.  **観測結果のフィードバック**: 取得した観測結果をLLMへの次の入力として追加し、LLMが次の思考サイクルを開始できるようにします。
7.  **ループの継続または終了**: タスクが完了したか、ユーザーからの明示的な終了指示があった場合、ループを終了します。それ以外の場合は、ステップ2に戻り、次の思考サイクルを開始します。

このアーキテクチャは、エージェントが複雑な問題を解決するために必要な自律性と柔軟性を提供します。Codexは、これらのコンポーネント間の明確なインターフェースと、堅牢なエラーハンドリングを実装することに重点を置いてください。




## 4. 技術スタック

エージェントの実装には、Pythonを主要なプログラミング言語として使用します。以下に、各コンポーネントの実装に推奨されるライブラリと技術を示します。

### 4.1. 主要言語

*   **Python 3.9+**: エージェントのコアロジック、ツール実装、およびLLMとの連携に使用します。その豊富なライブラリエコシステムと読みやすい構文は、迅速な開発とメンテナンスに適しています。

### 4.2. LLMとの連携

*   **OpenAI Python Client Library**: OpenAIのAPI（GPT-4, GPT-3.5-turboなど）と効率的に通信するために使用します。Function Callingの機能を利用して、LLMがツールを呼び出せるように設定します。
    ```python
    # 例: OpenAI APIクライアントの初期化
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    ```

### 4.3. ツール実装の基盤

*   **`subprocess`モジュール**: シェルコマンドの実行（`shell_exec`など）に使用します。これにより、サンドボックス環境内で外部プロセスを安全に起動し、その入出力を制御できます。
    ```python
    # 例: シェルコマンドの実行
    import subprocess
    try:
        result = subprocess.run(['ls', '-l'], capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
    ```
*   **`os`モジュール**: ファイルシステム操作（`file_read`, `file_write_text`など）に使用します。ファイルのパス操作、ディレクトリの作成、ファイルの存在チェックなどを行います。
    ```python
    # 例: ファイルの読み書き
    import os
    with open('example.txt', 'w') as f:
        f.write('Hello, Codex!')
    with open('example.txt', 'r') as f:
        content = f.read()
        print(content)
    ```
*   **`requests`ライブラリ**: ウェブ検索（`info_search_web`など）やAPI呼び出し（`info_search_api`など）に使用します。HTTPリクエストを送信し、レスポンスを処理します。
    ```python
    # 例: ウェブページの取得
    import requests
    try:
        response = requests.get('https://www.example.com')
        response.raise_for_status() # HTTPエラーが発生した場合に例外を発生させる
        print(response.text[:100]) # 最初の100文字を表示
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    ```
*   **`BeautifulSoup4`または`lxml`**: ウェブスクレイピング（`browser_navigate`後のコンテンツ解析など）に使用します。HTML/XMLコンテンツをパースし、必要な情報を抽出します。
    ```python
    # 例: HTMLからのデータ抽出
    from bs4 import BeautifulSoup
    html_doc = """<html><body><p>Hello, <a href=\"#\">World</a>!</p></body></html>"""
    soup = BeautifulSoup(html_doc, 'html.parser')
    print(soup.find('p').get_text())
    ```
*   **`selenium`または`playwright`**: ヘッドレスブラウザ操作（`browser_click`, `browser_input`など）に使用します。実際のブラウザをプログラムで制御し、JavaScriptの実行や動的なコンテンツの操作を可能にします。Codexのサンドボックス環境で利用可能なものを選択してください。
    ```python
    # 例: Seleniumによるブラウザ操作（概念）
    # from selenium import webdriver
    # from selenium.webdriver.common.keys import Keys
    # driver = webdriver.Chrome() # またはFirefox, Edgeなど
    # driver.get("http://www.python.org")
    # assert "Python" in driver.title
    # elem = driver.find_element(By.NAME, "q")
    # elem.clear()
    # elem.send_keys("pycon")
    # elem.send_keys(Keys.RETURN)
    # driver.quit()
    ```

### 4.4. 状態管理と永続化

*   **`json`モジュール**: エージェントの状態、タスクプラン、履歴などをファイルに保存・読み込みするために使用します。シンプルな構造化データを扱うのに適しています。
*   **SQLite3 (Python標準ライブラリ)**: より複雑な構造のデータや、検索・更新が必要なデータを永続化するために使用します。対話履歴、ツール実行ログ、ユーザー設定などを保存するのに適しています。
    ```python
    # 例: SQLite3の利用
    import sqlite3
    conn = sqlite3.connect('agent_state.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, prompt TEXT, response TEXT)''')
    cursor.execute("INSERT INTO history (prompt, response) VALUES (?, ?)", ("Hello", "Hi there!"))
    conn.commit()
    conn.close()
    ```

### 4.5. その他のユーティリティ

*   **`logging`モジュール**: エージェントの動作、エラー、デバッグ情報を記録するために使用します。問題の診断と監視に不可欠です。
*   **`dataclasses`モジュール**: ツール関数の引数や、エージェントの状態を表すデータ構造を定義するために使用します。コードの可読性と保守性を向上させます。

Codexは、これらの技術スタックを参考に、エージェントの機能要件を満たす最適なライブラリと実装パターンを選択してください。特に、サンドボックス環境の制約（利用可能なライブラリ、外部アクセスなど）を考慮し、必要に応じて代替手段を検討してください。




## 2.3. エージェント名: Cappuccino

Codexに作成を依頼するAIエージェントは「**Cappuccino**」と命名します。この名前は、ユーザーに温かく、親しみやすく、そして効率的なサポートを提供するというエージェントの目標を象徴しています。指示書全体を通して、この名前を適切に使用してください。




## 5. 主要コンポーネントの実装ガイドライン

このセクションでは、Cappuccinoエージェントの主要なコンポーネントの実装に関する具体的なガイドラインと、概念的なPythonコード例を提供します。Codexはこれらの例を参考に、堅牢で拡張性の高いコードを生成してください。

### 5.1. ツール定義とToolManager

Cappuccinoが外部環境とインタラクションするための各ツールは、Pythonの関数として定義され、`ToolManager`クラスによって管理されます。LLMは、これらのツールをFunction Callingのメカニズムを通じて呼び出します。

#### 5.1.1. ツールの構造

各ツール関数は、明確な入力引数と、実行結果を返す辞書形式の出力を持つべきです。ツールの説明（docstring）は、LLMがツールの目的と使い方を理解するために非常に重要です。

```python
import os
import subprocess
import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ToolManager:
    def __init__(self):
        self.shell_sessions = {}
        self.db_connection = sqlite3.connect("agent_state.db")
        self._initialize_db()

    def _initialize_db(self):
        cursor = self.db_connection.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT
        )""")
        self.db_connection.commit()

    def shell_exec(self, command: str, session_id: str, working_dir: str = ".") -> Dict[str, Any]:
        """指定されたシェルコマンドをサンドボックス環境で実行します。

        Args:
            command (str): 実行するシェルコマンド。
            session_id (str): シェルセッションを一意に識別するID。
            working_dir (str, optional): コマンドを実行する作業ディレクトリ。デフォルトは現在のディレクトリ。

        Returns:
            Dict[str, Any]: コマンドの標準出力、標準エラー、またはエラーメッセージを含む辞書。
        """
        try:
            # 実際には、より堅牢なセッション管理とプロセス分離が必要
            # ここでは簡易的な例としてsubprocess.runを使用
            logging.info(f"Executing shell command: {command} in session {session_id}")
            result = subprocess.run(
                command, 
                shell=True, 
                cwd=working_dir, 
                capture_output=True, 
                text=True, 
                check=True, # エラー時にCalledProcessErrorを発生させる
                timeout=60 # コマンド実行のタイムアウト
            )
            return {"stdout": result.stdout, "stderr": result.stderr}
        except subprocess.CalledProcessError as e:
            logging.error(f"Shell command failed: {e.cmd}, Stderr: {e.stderr}")
            return {"error": f"Command failed: {e.stderr}"}
        except Exception as e:
            logging.error(f"Error in shell_exec: {e}")
            return {"error": str(e)}

    def file_read(self, abs_path: str, view_type: str = "text", start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """指定されたファイルのコンテンツを読み取ります。

        Args:
            abs_path (str): 読み取るファイルの絶対パス。
            view_type (str, optional): 読み取るコンテンツのタイプ（"text"または"image"）。デフォルトは"text"。
            start_line (Optional[int], optional): テキストファイルの場合、読み取りを開始する行番号（0-based）。
            end_line (Optional[int], optional): テキストファイルの場合、読み取りを終了する行番号（0-based, exclusive）。

        Returns:
            Dict[str, Any]: ファイルの内容、またはエラーメッセージを含む辞書。
        """
        try:
            if not os.path.exists(abs_path):
                logging.warning(f"File not found: {abs_path}")
                return {"error": f"File not found: {abs_path}"}

            if view_type == "text":
                with open(abs_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    content_lines = lines[start_line:end_line] if start_line is not None or end_line is not None else lines
                    content = "".join(content_lines)
                return {"content": content}
            elif view_type == "image":
                # 画像ファイルの場合、実際には画像を読み込み、
                # それを一時的なURLとして提供するなどの処理が必要になります。
                # ここではプレースホルダーとしてエラーを返します。
                logging.warning(f"Image view type not fully implemented for {abs_path}")
                return {"error": "Image view type requires specific handling (e.g., temporary URL generation)."}
            else:
                logging.warning(f"Unsupported view_type: {view_type}")
                return {"error": f"Unsupported view_type: {view_type}"}
        except Exception as e:
            logging.error(f"Error reading file {abs_path}: {e}")
            return {"error": str(e)}

    def info_search_web(self, query: str) -> Dict[str, Any]:
        """指定されたクエリでウェブ検索を実行し、結果を返します。

        Args:
            query (str): 検索クエリ。

        Returns:
            Dict[str, Any]: 検索結果のリスト、またはエラーメッセージを含む辞書。
        """
        try:
            # 実際には、Google Search APIなどの外部APIを使用します。
            # ここでは簡易的なモックとして、固定の結果を返します。
            logging.info(f"Performing web search for: {query}")
            if "OpenAI Codex" in query:
                return {"results": [
                    {"title": "OpenAI Codex - Wikipedia", "url": "https://en.wikipedia.org/wiki/OpenAI_Codex", "snippet": "OpenAI Codex is an AI model developed by OpenAI that translates natural language to code."},
                    {"title": "Introducing Codex - OpenAI", "url": "https://openai.com/blog/introducing-codex", "snippet": "Codex is the AI model that powers GitHub Copilot."}
                ]}
            else:
                return {"results": []}
        except Exception as e:
            logging.error(f"Error in info_search_web: {e}")
            return {"error": str(e)}

    # 他のツール関数も同様にここに定義します。
    # message_notify_user, message_ask_user, file_write_text, file_append_text, file_replace_text, etc.
    # 各ツールは、その機能に応じた適切な引数と戻り値を持つべきです。

    def close(self):
        """データベース接続を閉じます。"""
        self.db_connection.close()

```

#### 5.1.2. LLMへのツール定義の提供

LLMがツールを呼び出せるようにするためには、各ツールの機能と引数のスキーマをLLMに伝える必要があります。OpenAI APIの場合、これは`tools`パラメータとしてJSONスキーマのリストを提供することで行われます。

```python
# 例: LLMに提供するツールのJSONスキーマ（概念）
# 実際には、Pythonの関数定義から自動生成するライブラリを使用することが推奨されます。
# 例: PydanticとOpenAIのtoolsユーティリティ

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": "指定されたシェルコマンドをサンドボックス環境で実行します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "実行するシェルコマンド。"},
                    "session_id": {"type": "string", "description": "シェルセッションを一意に識別するID。"},
                    "working_dir": {"type": "string", "description": "コマンドを実行する作業ディレクトリ。"}
                },
                "required": ["command", "session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "指定されたファイルのコンテンツを読み取ります。",
            "parameters": {
                "type": "object",
                "properties": {
                    "abs_path": {"type": "string", "description": "読み取るファイルの絶対パス。"},
                    "view_type": {"type": "string", "enum": ["text", "image"], "description": "読み取るコンテンツのタイプ。"},
                    "start_line": {"type": "integer", "description": "テキストファイルの場合、読み取りを開始する行番号（0-based）。"},
                    "end_line": {"type": "integer", "description": "テキストファイルの場合、読み取りを終了する行番号（0-based, exclusive）。"}
                },
                "required": ["abs_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "info_search_web",
            "description": "指定されたクエリでウェブ検索を実行し、結果を返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ。"}
                },
                "required": ["query"]
            }
        }
    }
    # 他のツールも同様に追加
]
```

### 5.2. エージェントループの実装

エージェントループは、Cappuccinoの自律的な行動を駆動する中心的なロジックです。これは、LLMとの対話、ツール呼び出しの実行、および結果の処理をオーケストレーションします。

```python
from openai import OpenAI
import json
import time

class CappuccinoAgent:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.tool_manager = ToolManager() # 上記で定義したToolManagerのインスタンス
        self.messages = [] # LLMとの会話履歴
        self.task_plan = [] # タスクプラン（StateManagerで管理されるべき）
        self.current_phase_id = 0

        # システムプロンプトの初期化
        self._initialize_system_prompt()

    def _initialize_system_prompt(self):
        # エージェントの役割、制約、利用可能なツールなどをLLMに伝えるシステムプロンプト
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "ユーザーの指示を理解し、適切なツールを自律的に選択・実行することで、複雑なタスクを効率的に解決してください。\n"
            "利用可能なツールは以下の通りです。これらのツールを適切に利用してタスクを遂行してください。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。\n"
            "タスクが完了したら、`agent_end_task`ツールを呼び出して終了してください。\n"
            "不明な点があれば、ユーザーに質問してください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})

    def _add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None, tool_call_id: Optional[str] = None):
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)
        logging.info(f"Added message: {message}")

    def run(self, user_query: str):
        self._add_message("user", user_query)

        while True:
            logging.info("Entering agent loop...")
            try:
                # LLMを呼び出す
                response = self.client.chat.completions.create(
                    model="gpt-4.1", # または "gpt-4.1 nano" など
                    messages=self.messages,
                    tools=tools_schema, # 上記で定義したツールのスキーマ
                    tool_choice="auto" # LLMにツール使用を自動で判断させる
                )
                response_message = response.choices[0].message
                self._add_message(response_message.role, response_message.content or "", response_message.tool_calls)

                if response_message.tool_calls:
                    # LLMがツール呼び出しを要求した場合
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        logging.info(f"LLM requested tool call: {function_name} with args {function_args}")

                        if hasattr(self.tool_manager, function_name):
                            tool_function = getattr(self.tool_manager, function_name)
                            tool_output = tool_function(**function_args)
                            logging.info(f"Tool {function_name} executed, output: {tool_output}")
                            self._add_message(
                                "tool",
                                content=json.dumps(tool_output),
                                tool_call_id=tool_call.id
                            )
                        else:
                            error_message = f"Error: Tool '{function_name}' not found in ToolManager."
                            logging.error(error_message)
                            self._add_message(
                                "tool",
                                content=json.dumps({"error": error_message}),
                                tool_call_id=tool_call.id
                            )
                    # ツール実行結果をLLMにフィードバックするため、ループを継続
                    continue

                elif response_message.content:
                    # LLMがテキスト応答を返した場合（タスク完了または質問）
                    print(f"Cappuccino: {response_message.content}")
                    # ここでタスク完了を判断し、必要であればループを終了
                    # 例: ユーザーに結果を通知し、終了ツールを呼び出すロジック
                    if "タスクが完了しました" in response_message.content or "終了します" in response_message.content:
                        logging.info("Task likely completed. Ending agent loop.")
                        break
                    # ユーザーからの次の入力を待つ場合は、ここで待機
                    # user_query = input("次の指示をどうぞ: ")
                    # self._add_message("user", user_query)
                    break # この例ではテキスト応答で終了

            except Exception as e:
                logging.error(f"An error occurred in the agent loop: {e}")
                self._add_message("system", f"エージェントループでエラーが発生しました: {e}")
                break # エラー発生時はループを終了

        self.tool_manager.close()

# エージェントの実行例（APIキーは環境変数から取得）
# if __name__ == "__main__":
#     agent = CappuccinoAgent(api_key=os.environ.get("OPENAI_API_KEY"))
#     agent.run("todo.mdの内容を読んで、その要約を教えてください。")
#     # agent.run("現在のディレクトリにあるファイルとフォルダをリストしてください。")
```

### 5.3. 状態管理と永続化

Cappuccinoエージェントは、タスクの進行状況、会話履歴、およびその他の重要な情報を永続化する必要があります。これにより、エージェントは中断後も作業を再開でき、過去のコンテキストを保持できます。

#### 5.3.1. 会話履歴の管理

LLMとの会話履歴は、`messages`リストとして管理され、各ターンでLLMに渡されます。これにより、LLMは過去の対話のコンテキストを保持できます。この履歴は、データベース（例: SQLite）に保存することで永続化できます。

```python
# ToolManagerクラス内に既にSQLiteを使用した履歴管理の初期化と追加の概念が含まれています。
# _add_messageメソッド内で、メッセージをデータベースに保存するロジックを追加できます。

class ToolManager:
    # ... (既存のコード) ...

    def _add_history_entry(self, role: str, content: str):
        cursor = self.db_connection.cursor()
        cursor.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        self.db_connection.commit()
        logging.info(f"History saved: Role={role}, Content={content[:50]}...")

# CappuccinoAgentの_add_messageメソッド内で、ToolManagerの_add_history_entryを呼び出す
# class CappuccinoAgent:
#     def _add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None, tool_call_id: Optional[str] = None):
#         message = {"role": role, "content": content}
#         if tool_calls:
#             message["tool_calls"] = tool_calls
#         if tool_call_id:
#             message["tool_call_id"] = tool_call_id
#         self.messages.append(message)
#         self.tool_manager._add_history_entry(role, content) # ここで履歴を保存
#         logging.info(f"Added message: {message}")
```

#### 5.3.2. タスクプランと状態の永続化

タスクプランやエージェントの現在のフェーズなどのメタデータも、データベースや設定ファイルに保存することで永続化できます。これにより、エージェントは複雑な多段階タスクの途中で再起動しても、中断した場所から正確に再開できます。

```python
# 例: タスクプランと現在のフェーズを保存・読み込む関数（概念）
def save_agent_state(db_connection: sqlite3.Connection, task_plan: List[Dict], current_phase_id: int):
    cursor = db_connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS agent_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    cursor.execute("REPLACE INTO agent_state (key, value) VALUES (?, ?)", ("task_plan", json.dumps(task_plan)))
    cursor.execute("REPLACE INTO agent_state (key, value) VALUES (?, ?)", ("current_phase_id", str(current_phase_id)))
    db_connection.commit()
    logging.info("Agent state saved.")

def load_agent_state(db_connection: sqlite3.Connection) -> Dict[str, Any]:
    cursor = db_connection.cursor()
    cursor.execute("SELECT key, value FROM agent_state")
    state = {row[0]: row[1] for row in cursor.fetchall()}
    
    task_plan = json.loads(state.get("task_plan", "[]"))
    current_phase_id = int(state.get("current_phase_id", "0"))
    logging.info("Agent state loaded.")
    return {"task_plan": task_plan, "current_phase_id": current_phase_id}

# CappuccinoAgentの初期化時に状態をロードし、更新時に保存するロジックを追加
# class CappuccinoAgent:
#     def __init__(self, api_key: str):
#         # ...
#         self.tool_manager = ToolManager()
#         loaded_state = load_agent_state(self.tool_manager.db_connection)
#         self.task_plan = loaded_state["task_plan"]
#         self.current_phase_id = loaded_state["current_phase_id"]
#         # ...

#     def _update_task_plan(self, new_plan: List[Dict], new_phase_id: int):
#         self.task_plan = new_plan
#         self.current_phase_id = new_phase_id
#         save_agent_state(self.tool_manager.db_connection, self.task_plan, self.current_phase_id)
```

### 5.4. エラーハンドリングとリカバリ

堅牢なエージェントを構築するためには、予期せぬエラーが発生した場合でも、適切に処理し、可能な限りタスクを継続できるようなメカニズムが必要です。

#### 5.4.1. ツールレベルのエラーハンドリング

各ツール関数は、自身の内部で発生する可能性のあるエラーを捕捉し、エラーメッセージを返すように設計すべきです。これにより、LLMはツールの失敗を認識し、次の行動を調整できます。

```python
# 各ツール関数（shell_exec, file_readなど）のtry-exceptブロックで既に実装されています。
# 例:
# try:
#     # ツール固有の処理
#     return {"result": "success"}
# except SpecificError as e:
#     logging.error(f"Specific tool error: {e}")
#     return {"error": str(e)}
# except Exception as e:
#     logging.error(f"General tool error: {e}")
#     return {"error": str(e)}
```

#### 5.4.2. エージェントループレベルのエラーハンドリング

エージェントループ全体でエラーを捕捉し、LLMにエラー情報をフィードバックすることで、LLMが自己修正を試みることができます。例えば、LLMが誤ったツール呼び出しを生成した場合や、外部APIとの通信に失敗した場合などです。

```python
# CappuccinoAgentのrunメソッド内のtry-exceptブロックで既に実装されています。
# LLMへのエラーフィードバックは、"tool"ロールのメッセージとして行われます。
# これにより、LLMはエラーメッセージを読み取り、次の思考に活かすことができます。

# 例:
# try:
#     # LLM呼び出しとツール実行ロジック
# except Exception as e:
#     logging.error(f"An error occurred in the agent loop: {e}")
#     self._add_message("system", f"エージェントループでエラーが発生しました: {e}")
#     # ここで、ユーザーにエラーを通知したり、タスクを安全に終了したりするロジックを追加できます。
```

#### 5.4.3. リカバリ戦略

エラーの種類に応じて、異なるリカバリ戦略を適用できます。

*   **再試行**: 一時的なネットワークエラーなどの場合、数秒待ってから操作を再試行します。
*   **代替ツールの使用**: あるツールが失敗した場合、類似の機能を持つ別のツールを試します。
*   **計画の修正**: エラーが現在の計画の根本的な問題を示している場合、LLMは計画全体を見直すように指示されます。
*   **ユーザーへの問い合わせ**: エージェントが自力で解決できない問題に直面した場合、ユーザーに状況を説明し、指示を求めます。

これらのガイドラインとコード例は、CodexがCappuccinoエージェントを堅牢かつ効率的に実装するための出発点となります。各コンポーネントの詳細な実装は、Codexの裁量に委ねられますが、上記の原則を遵守してください。




## 6. サンドボックス環境の考慮事項

Cappuccinoエージェントは、隔離されたサンドボックス環境内で動作することを前提として設計される必要があります。この環境は、セキュリティと安定性を提供しますが、同時にいくつかの制約も伴います。Codexは、これらの制約を理解し、エージェントの実装に適切に反映させる必要があります。

### 6.1. インターネットアクセス制限

Codexが動作するサンドボックス環境では、タスク実行中にインターネットアクセスが制限される場合があります。これは、外部APIへのアクセスやリアルタイムのウェブコンテンツの取得に影響を与えます。この制約に対処するため、以下の点を考慮してください。

*   **オフライン機能の優先**: 可能な限り、インターネットアクセスを必要としない機能を優先して実装してください。例えば、ローカルファイルシステム操作、シェルコマンド実行、内部データ処理などです。
*   **キャッシュとデータ同期**: 頻繁にアクセスする外部データについては、可能な範囲でキャッシュメカニズムを導入し、インターネットアクセスが利用可能な時にデータを同期する戦略を検討してください。
*   **ツール設計への影響**: `info_search_web`や`info_search_image`のようなインターネットアクセスを必要とするツールは、アクセスが制限されている場合に適切にエラーを処理するか、代替手段（例: 既存のローカルデータセットからの検索）を提供するように設計してください。
*   **ユーザーへの通知**: インターネットアクセスが制限されているために特定のタスクを実行できない場合、その旨をユーザーに明確に通知するメカニズムを実装してください。

### 6.2. ファイルシステムと永続性

サンドボックス環境内のファイルシステムは、エージェントの作業領域となります。以下の点に注意してください。

*   **作業ディレクトリの管理**: エージェントは、自身の作業ファイルを特定のディレクトリ（例: `/home/ubuntu/cappuccino_workspace/`）内に整理して保存するようにしてください。これにより、他のシステムファイルとの競合を避け、クリーンアップが容易になります。
*   **永続化の考慮**: サンドボックス環境が一時的である可能性がある場合、重要な状態情報や生成された成果物（レポート、コードなど）は、ユーザーがアクセスできる永続的なストレージに保存するか、タスク完了時にユーザーに提供するメカニズムを実装してください。SQLiteデータベースは、エージェントの状態を永続化するための良い選択肢です。
*   **権限**: ファイル操作は、サンドボックス環境内で許可された権限の範囲内で行われる必要があります。不必要な`sudo`権限の使用は避けてください。

### 6.3. リソース制限

サンドボックス環境には、CPU、メモリ、ディスクスペースなどのリソースに制限がある場合があります。エージェントは、これらのリソースを効率的に使用するように設計されるべきです。

*   **効率的なアルゴリズム**: 大量のデータを処理する場合や、計算コストの高い操作を行う場合は、効率的なアルゴリズムとデータ構造を選択してください。
*   **メモリ管理**: 不要になったオブジェクトは適切に解放し、メモリリークを防ぐように注意してください。
*   **並行処理の最適化**: 複数のタスクを並行して実行する場合、スレッドやプロセスの数を適切に管理し、リソースの枯渇を防いでください。

これらのサンドボックス環境の考慮事項は、Cappuccinoエージェントが安定して効率的に動作するために不可欠です。Codexは、これらの制約を設計段階から考慮し、堅牢な実装を目指してください。




## 7. テストと検証

Cappuccinoエージェントの信頼性と機能性を確保するためには、適切なテストと検証が不可欠です。Codexは、以下のガイドラインに従って、生成されたコードの品質を保証してください。

### 7.1. 単体テスト

各ツール関数（`shell_exec`, `file_read`, `info_search_web`など）は、独立してテストされるべきです。これにより、個々のコンポーネントが期待通りに動作することを確認できます。

*   **テストフレームワーク**: Pythonの標準的なテストフレームワークである`unittest`または`pytest`を使用してください。
*   **モックとスタブ**: 外部サービス（LLM API、ウェブ検索APIなど）や、サンドボックス環境の制約により直接テストが困難なコンポーネントについては、モックやスタブを使用して依存関係を分離し、ツールのロジックのみをテストしてください。
*   **エッジケースのテスト**: 正常系のテストだけでなく、ファイルが見つからない場合、コマンドが失敗する場合、APIがエラーを返す場合などのエッジケースもテストしてください。

```python
# 例: shell_execツールの単体テスト（pytestを使用）
import pytest
from unittest.mock import patch, MagicMock
from your_agent_module import ToolManager # 実際のモジュール名に置き換える

@pytest.fixture
def tool_manager():
    # テスト用のToolManagerインスタンスを作成
    # データベース接続をモックするなど、必要に応じて調整
    return ToolManager()

def test_shell_exec_success(tool_manager):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="hello world\n", stderr="", returncode=0)
        result = tool_manager.shell_exec("echo hello world", "test_session")
        assert "stdout" in result
        assert result["stdout"] == "hello world\n"
        assert "stderr" in result
        assert result["stderr"] == ""
        mock_run.assert_called_once_with(
            "echo hello world", 
            shell=True, 
            cwd=".", 
            capture_output=True, 
            text=True, 
            check=True,
            timeout=60
        )

def test_shell_exec_command_failed(tool_manager):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "ls non_existent_file", stderr="No such file or directory\n")
        result = tool_manager.shell_exec("ls non_existent_file", "test_session")
        assert "error" in result
        assert "Command failed" in result["error"]

def test_file_read_success(tool_manager):
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda s: s, __exit__=lambda s,t,v,tb: False, readlines=lambda: ["line1\n", "line2\n"]))) as mock_open,
         patch("os.path.exists", return_value=True):
        result = tool_manager.file_read("test.txt")
        assert "content" in result
        assert result["content"] == "line1\nline2\n"

def test_file_read_not_found(tool_manager):
    with patch("os.path.exists", return_value=False):
        result = tool_manager.file_read("non_existent.txt")
        assert "error" in result
        assert "File not found" in result["error"]
```

### 7.2. 統合テスト

エージェントループ全体、およびLLMとツールの連携を含む統合テストを実施してください。これにより、各コンポーネントが連携して正しく機能することを確認できます。

*   **シナリオベースのテスト**: ユーザーがエージェントに与える可能性のある典型的なシナリオ（例: 「ファイルを読んで要約する」、「ウェブから情報を検索してレポートを作成する」）を定義し、それらのシナリオが期待通りに実行されることを確認してください。
*   **LLMのモック**: 統合テストでは、実際のLLM APIを呼び出す代わりに、LLMの応答をモックすることで、テストの実行速度を向上させ、APIコストを削減できます。モックされたLLMは、特定の入力に対して特定のツール呼び出しやテキスト応答を返すように設定します。
*   **状態の検証**: テストシナリオの実行後、エージェントの状態（例: 履歴、生成されたファイル、更新されたデータベースエントリ）が期待通りであることを検証してください。

### 7.3. 継続的インテグレーション (CI)

可能であれば、生成されたコードに対して継続的インテグレーション（CI）パイプラインを設定し、コードが変更されるたびに自動的にテストが実行されるようにしてください。これにより、早期に問題を検出し、コードの品質を維持できます。

### 7.4. ユーザーによる検証

最終的には、実際のユーザーがエージェントを試用し、フィードバックを提供することが重要です。ユーザーからのフィードバックは、エージェントの改善と調整に役立ちます。

Codexは、これらのテストと検証のプラクティスを組み込むことで、Cappuccinoエージェントが信頼性が高く、ユーザーの期待に応える品質を持つことを保証してください。




## 8. 今後の拡張性

Cappuccinoエージェントは、将来的な機能追加や改善が容易なように設計されるべきです。モジュール化されたアーキテクチャと明確なインターフェースは、この拡張性を確保するための鍵となります。

### 8.1. 新しいツールの追加

新しいツールを追加するプロセスは、シンプルかつ効率的であるべきです。新しいツールは、`ToolManager`クラスに新しいメソッドとして追加され、その機能と引数のスキーマがLLMに提供される`tools_schema`に反映されるだけで、エージェントのコアロジックを変更することなく組み込めるように設計してください。

*   **ツール関数の定義**: 新しい機能に対応するPython関数を`ToolManager`内に定義します。この関数は、明確な入力と出力、そして詳細なdocstringを持つべきです。
*   **スキーマの更新**: 定義したツール関数のJSONスキーマを生成し、`tools_schema`リストに追加します。これにより、LLMはその新しいツールを認識し、利用できるようになります。
*   **依存関係の管理**: 新しいツールが外部ライブラリに依存する場合、`requirements.txt`ファイルにその依存関係を追加し、サンドボックス環境にインストールできるようにしてください。

### 8.2. LLMモデルの切り替え

将来的に、より高性能なLLMモデルや、異なる特性を持つLLMモデル（例: コスト効率の良いモデル、特定のタスクに特化したモデル）に切り替える可能性を考慮してください。LLMとの連携部分は抽象化され、モデルの変更がエージェントの他の部分に大きな影響を与えないように設計してください。

*   **APIクライアントの抽象化**: `CappuccinoAgent`クラス内で直接OpenAIのクライアントを扱うのではなく、LLMとのインタラクションをラップする抽象レイヤーを導入することを検討してください。これにより、モデルの切り替えが容易になります。
*   **プロンプトの適応性**: 新しいLLMモデルの特性に合わせて、システムプロンプトやツール定義のプロンプトを調整できるように柔軟な設計にしてください。

### 8.3. ユーザーインターフェースの分離

現在の設計では、エージェントのコアロジックとユーザーインターフェース（CLIベースの対話）が密接に結合しています。将来的に、Web UI、デスクトップアプリケーション、チャットボットプラットフォームなど、多様なユーザーインターフェースをサポートできるように、UI層とエージェントのコアロジックを完全に分離してください。

*   **APIインターフェースの提供**: エージェントのコアロジックをHTTP APIとして公開することを検討してください。これにより、任意のフロントエンドからエージェントの機能にアクセスできるようになります。
*   **メッセージキューの利用**: ユーザーからのリクエストとエージェントからの応答を非同期で処理するために、メッセージキューシステム（例: RabbitMQ, Kafka）を導入することを検討してください。これにより、スケーラビリティと応答性が向上します。

### 8.4. パフォーマンスとスケーラビリティの最適化

エージェントの利用が増えるにつれて、パフォーマンスとスケーラビリティが重要になります。以下の点を考慮してください。

*   **非同期処理**: 時間のかかるI/O操作（ネットワークリクエスト、ファイルI/Oなど）には、`asyncio`などの非同期処理フレームワークを積極的に活用してください。
*   **並行処理**: 複数のタスクを同時に処理するために、`multiprocessing`や`threading`モジュール、または分散タスクキュー（例: Celery）を検討してください。
*   **リソース監視**: エージェントのリソース使用量（CPU、メモリ、ディスクI/O）を監視し、ボトルネックを特定して最適化できるようにしてください。

これらの拡張性に関する考慮事項は、Cappuccinoエージェントが長期にわたって進化し、多様なニーズに対応できる柔軟なシステムであり続けるために不可欠です。Codexは、これらの指針を念頭に置いて、将来を見据えた設計と実装を行ってください。




## 9. 結論

この指示書は、OpenAI Codexが「Cappuccino」と名付けられた汎用AIアシスタントを構築するための包括的なガイドラインを提供しました。Cappuccinoは、ユーザーの自然言語による指示を理解し、多様なツールを自律的に利用して複雑なタスクを解決することを目指します。

Codexは、この指示書に記載されたアーキテクチャ設計、技術スタック、主要コンポーネントの実装ガイドライン、エラーハンドリング、サンドボックス環境の考慮事項、テストと検証、そして今後の拡張性に関する指針を厳密に遵守してください。

特に、以下の点に重点を置いてください。

*   **堅牢なツール実装**: 各ツールが独立して機能し、エラーを適切に処理できること。
*   **効率的なエージェントループ**: LLMとツールの間のインタラクションがスムーズで、論理的な思考プロセスが反映されていること。
*   **状態管理と永続化**: エージェントの状態が確実に保存され、中断後もタスクを再開できること。
*   **サンドボックス環境への適応**: 制限された環境下でも最大限のパフォーマンスを発揮できるよう、設計と実装に工夫を凝らすこと。

Cappuccinoの成功は、Codexのコード生成能力と、この指示書に示された設計原則への忠実さにかかっています。ユーザーの期待を超える、革新的で信頼性の高いAIエージェントの実現を期待しています。

--- 

**著者**: Manus AI
**日付**: 2025年7月10日




## 10. 最速応答・並列推論を考慮したアーキテクチャ

Cappuccinoエージェントをヒューマノイドに組み込むという最終目標を達成するためには、単に機能が豊富であるだけでなく、極めて低いレイテンシで応答し、複数のタスクを並列で処理できる能力が不可欠です。これは、リアルタイムのインタラクションや、複雑な環境での迅速な意思決定を可能にするために重要です。Codexは、以下の設計原則と技術を考慮して、Cappuccinoを構築してください。

### 10.1. 非同期処理の徹底

Pythonにおける非同期処理は、I/Oバウンドな操作（ネットワークリクエスト、ファイルI/O、外部API呼び出しなど）において、スレッドやプロセスをブロックすることなく、効率的にリソースを利用するための鍵となります。LLMの推論、ツール呼び出し、データベースアクセスなど、Cappuccinoの多くの操作は本質的にI/Oバウンドです。`asyncio`ライブラリを徹底的に活用し、すべてのI/O操作を非同期で実行するように設計してください。

*   **`async`/`await`構文の利用**: LLM API呼び出し、`requests`ライブラリを使用したウェブアクセス、データベース操作（`aiosqlite`などの非同期ドライバを使用）など、すべての外部通信は`async`/`await`構文を用いて非同期化してください。
*   **非同期ツール関数の設計**: `ToolManager`内の各ツール関数は、可能であれば非同期関数として定義し、`await`を使用して非同期I/Oを待機するようにしてください。これにより、一つのツールがI/O待ちの間も、エージェントループが他の処理を進めることができます。

```python
# 例: 非同期ウェブ検索ツール（概念）
import aiohttp # 非同期HTTPクライアント
import asyncio

class ToolManager:
    # ... (既存のコード) ...

    async def info_search_web_async(self, query: str) -> Dict[str, Any]:
        """指定されたクエリで非同期にウェブ検索を実行し、結果を返します。"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.example.com/search?q={query}") as response:
                    response.raise_for_status()
                    data = await response.json()
                    return {"results": data.get("results", [])}
        except aiohttp.ClientError as e:
            logging.error(f"Async web search failed: {e}")
            return {"error": str(e)}

# CappuccinoAgentのLLM呼び出しも非同期化
# async def run(self, user_query: str):
#     # ...
#     response = await self.client.chat.completions.create(
#         model="gpt-4.1",
#         messages=self.messages,
#         tools=tools_schema,
#         tool_choice="auto"
#     )
#     # ...
#     if hasattr(self.tool_manager, function_name + "_async"):
#         tool_function = getattr(self.tool_manager, function_name + "_async")
#         tool_output = await tool_function(**function_args)
```

### 10.2. 並列推論と並行処理

複数のユーザーリクエストや、エージェント内部で複数の思考パスを同時に探索する必要がある場合、並列処理が不可欠です。特に、LLMの推論は計算コストが高く、複数の推論を同時に実行することでスループットを向上させることができます。

*   **`concurrent.futures`モジュール**: `ThreadPoolExecutor`や`ProcessPoolExecutor`を使用して、LLM推論やCPUバウンドなタスクを並列で実行することを検討してください。特に、複数のLLM呼び出しを同時に行う場合や、重いデータ処理を行う場合に有効です。
    *   **`ThreadPoolExecutor`**: I/Oバウンドなタスク（例: 複数のLLM API呼び出し）の並行処理に適しています。GIL（Global Interpreter Lock）の制約を受けますが、I/O待ちの間は他のスレッドが実行されるため効率的です。
    *   **`ProcessPoolExecutor`**: CPUバウンドなタスク（例: 大規模なデータ解析、複雑なアルゴリズム実行）の並列処理に適しています。GILの制約を受けず、真の並列処理を実現できますが、プロセス間の通信オーバーヘッドが発生します。
*   **分散メッセージキュー**: 複数のCappuccinoエージェントインスタンスをデプロイし、リクエストを分散処理するために、RabbitMQやKafkaのようなメッセージキューシステムを導入することを検討してください。ユーザーからのリクエストをキューに入れ、利用可能なエージェントがそれらを処理することで、高いスケーラビリティと耐障害性を実現できます。
*   **LLMの並列呼び出し**: OpenAI APIは、複数のリクエストを同時に送信することをサポートしています。`asyncio.gather`と`ThreadPoolExecutor`を組み合わせることで、複数のLLM推論を並列で実行し、応答時間を短縮できます。

```python
# 例: 複数のLLM推論の並列実行（概念）
import asyncio
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

async def parallel_llm_calls(api_key: str, prompts: List[str], tools_schema: List[Dict]):
    client = OpenAI(api_key=api_key)
    async def call_llm(prompt):
        messages = [
            {"role": "system", "content": "あなたはAIアシスタントです。"},
            {"role": "user", "content": prompt}
        ]
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        return response.choices[0].message.content

    # ThreadPoolExecutorを使用して、複数のLLM呼び出しを並列で実行
    # OpenAIのPythonクライアントは内部でrequestsを使用しており、requestsは同期I/Oのため、
    # asyncioと組み合わせる場合はThreadPoolExecutorでラップするのが一般的です。
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [loop.run_in_executor(executor, call_llm, prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks)
    return results

# 使用例:
# async def main():
#     prompts = ["今日の天気は？", "Pythonでファイルを読み込む方法は？"]
#     results = await parallel_llm_calls(os.environ.get("OPENAI_API_KEY"), prompts, tools_schema)
#     for r in results:
#         print(r)
# asyncio.run(main())
```

### 10.3. 推論の最適化とキャッシュ

LLMの推論時間を短縮し、APIコストを削減するために、推論の最適化とキャッシュ戦略を導入してください。

*   **プロンプトの最適化**: LLMへの入力プロンプトをできるだけ簡潔かつ明確にすることで、推論時間を短縮し、より的確な応答を引き出すことができます。
*   **出力の構造化**: LLMからの出力にJSONなどの構造化されたフォーマットを要求することで、後続のパース処理を高速化し、エラーを減らすことができます。
*   **キャッシュメカニズム**: 頻繁に繰り返されるLLMの推論結果や、ツールの実行結果をキャッシュすることを検討してください。例えば、特定の検索クエリに対するウェブ検索結果や、ファイルの内容の要約などです。SQLiteデータベースやRedisのようなインメモリデータベースをキャッシュストアとして利用できます。
*   **軽量モデルの活用**: すべてのタスクに高性能なLLMが必要なわけではありません。簡単な質問応答やルーティングには、より軽量で高速なモデル（例: GPT-3.5-turbo）を使用し、複雑なタスクの場合のみ高性能なモデル（例: GPT-4o）にフォールバックするようなハイブリッド戦略を検討してください。

### 10.4. ヒューマノイド統合のためのAPI設計

Cappuccinoをヒューマノイドに組み込むことを想定し、エージェントのコア機能を外部から呼び出しやすいAPIとして設計してください。RESTful APIまたはgRPCのような高性能なRPCフレームワークを検討してください。

*   **FastAPIの利用**: Pythonで高速な非同期APIを構築するために、FastAPIのようなフレームワークが適しています。自動生成されるOpenAPIドキュメントは、ヒューマノイド側の開発者がAPIを理解し、統合するのに役立ちます。
*   **モジュール化されたエンドポイント**: 各エージェント機能（例: `POST /agent/run`, `GET /agent/status`, `POST /agent/tool_call`）を個別のAPIエンドポイントとして公開し、明確な入力と出力スキーマを定義してください。
*   **ストリーミング応答**: ヒューマノイドとのリアルタイムインタラクションのために、LLMの応答やツールの実行結果をストリーミングで提供するメカニズム（例: WebSocket、Server-Sent Events）を検討してください。これにより、応答の最初の部分が利用可能になり次第、ヒューマノイドが動作を開始できます。

これらの設計原則と技術を組み合わせることで、Codexは、ヒューマノイドの要求に応えることができる、高速で応答性の高いCappuccinoエージェントを構築できるでしょう。




### 4.6. 非同期処理と並行処理

*   **`asyncio`**: Pythonの非同期I/Oフレームワーク。ネットワーク通信やファイルI/Oなど、I/Oバウンドな操作をノンブロッキングで実行するために使用します。これにより、エージェントの応答性を高め、複数のタスクを効率的に処理できます。
    ```python
    # 例: asyncioの基本的な使用
    import asyncio

    async def fetch_data(url):
        # 実際にはaiohttpなどの非同期HTTPクライアントを使用
        await asyncio.sleep(1) # ネットワークI/Oのシミュレーション
        return f"Data from {url}"

    async def main():
        results = await asyncio.gather(
            fetch_data("http://example.com/data1"),
            fetch_data("http://example.com/data2")
        )
        print(results)

    # asyncio.run(main())
    ```
*   **`aiohttp`**: 非同期HTTPクライアント/サーバーフレームワーク。ウェブAPIへの非同期リクエスト送信に使用します。
    ```python
    # 例: aiohttpを使用した非同期HTTPリクエスト
    import aiohttp
    import asyncio

    async def get_webpage(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.text()

    # async def main():
    #     content = await get_webpage("https://www.example.com")
    #     print(content[:100])
    # asyncio.run(main())
    ```
*   **`aiosqlite`**: SQLiteデータベースへの非同期アクセスを提供するライブラリ。データベース操作がI/Oバウンドであるため、非同期処理と組み合わせることでエージェントの応答性を維持します。
    ```python
    # 例: aiosqliteを使用した非同期データベース操作
    import aiosqlite
    import asyncio

    async def create_and_insert():
        async with aiosqlite.connect("async_agent_state.db") as db:
            await db.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, message TEXT)")
            await db.execute("INSERT INTO logs (message) VALUES (?)", ("Async operation completed",))
            await db.commit()
            cursor = await db.execute("SELECT * FROM logs")
            rows = await cursor.fetchall()
            print(rows)

    # asyncio.run(create_and_insert())
    ```
*   **`concurrent.futures`**: スレッドプールやプロセスプールを使用して、並行処理や並列処理を抽象化する高レベルインターフェース。特に、同期的な外部ライブラリ（例: `requests`やOpenAIの同期クライアント）を非同期コンテキストで実行する際に役立ちます。

### 4.7. API設計とヒューマノイド統合

*   **`FastAPI`**: 高性能なWeb APIを構築するためのモダンなPythonフレームワーク。非同期処理をネイティブにサポートし、自動的なAPIドキュメント生成（OpenAPI/Swagger UI）を提供します。ヒューマノイドからのリクエストを受け付けるためのインターフェースとして最適です。
    ```python
    # 例: FastAPIの基本的な構造
    # from fastapi import FastAPI
    # from pydantic import BaseModel

    # app = FastAPI()

    # class UserRequest(BaseModel):
    #     query: str

    # @app.post("/agent/run")
    # async def run_agent(request: UserRequest):
    #     # ここにCappuccinoAgentの非同期実行ロジックを呼び出す
    #     return {"response": f"Processing query: {request.query}"}

    # 実行方法: uvicorn main:app --reload
    ```
*   **`WebSockets` (FastAPIの機能)**: リアルタイムな双方向通信を可能にするプロトコル。ヒューマノイドへのLLMのストリーミング応答や、ツールの実行状況のリアルタイムフィードバックに利用できます。

これらの技術スタックを組み合わせることで、Codexは、ヒューマノイドに組み込むための、高速で応答性が高く、並列処理が可能なCappuccinoエージェントを構築できます。


## 5. 主要コンポーネントの実装ガイドライン（更新）

このセクションでは、Cappuccinoエージェントの主要なコンポーネントの実装に関する具体的なガイドラインと、非同期処理および並列推論を考慮したPythonコード例を提供します。Codexはこれらの例を参考に、堅牢で拡張性の高いコードを生成してください。

### 5.1. ツール定義とToolManager（非同期対応）

`ToolManager`内の各ツール関数は、可能であれば非同期関数として定義し、`await`を使用して非同期I/Oを待機するようにしてください。これにより、一つのツールがI/O待ちの間も、エージェントループが他の処理を進めることができます。

#### 5.1.1. ツールの構造（非同期版）

```python
import os
import asyncio
import aiohttp # 非同期HTTPクライアント
import aiosqlite # 非同期SQLiteクライアント
import subprocess
import json
import logging
from typing import Dict, Any, List, Optional

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class ToolManager:
    def __init__(self):
        self.shell_sessions = {}
        self.db_path = "agent_state.db"
        self.db_connection = None # 非同期接続は必要に応じて確立

    async def _get_db_connection(self):
        if self.db_connection is None:
            self.db_connection = await aiosqlite.connect(self.db_path)
            await self._initialize_db()
        return self.db_connection

    async def _initialize_db(self):
        conn = await self._get_db_connection()
        await conn.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT
        )""")
        await conn.commit()

    async def shell_exec_async(self, command: str, session_id: str, working_dir: str = ".") -> Dict[str, Any]:
        """指定されたシェルコマンドをサンドボックス環境で非同期に実行します。

        Args:
            command (str): 実行するシェルコマンド。
            session_id (str): シェルセッションを一意に識別するID。
            working_dir (str, optional): コマンドを実行する作業ディレクトリ。デフォルトは現在のディレクトリ。

        Returns:
            Dict[str, Any]: コマンドの標準出力、標準エラー、またはエラーメッセージを含む辞書。
        """
        try:
            logging.info(f"Executing async shell command: {command} in session {session_id}")
            # asyncio.create_subprocess_shell を使用して非同期にプロセスを実行
            process = await asyncio.create_subprocess_shell(
                command, 
                cwd=working_dir, 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60) # タイムアウト設定
            
            if process.returncode != 0:
                logging.error(f"Shell command failed with exit code {process.returncode}: {command}, Stderr: {stderr.decode()}")
                return {"error": f"Command failed ({process.returncode}): {stderr.decode()}"}
            else:
                return {"stdout": stdout.decode(), "stderr": stderr.decode()}
        except asyncio.TimeoutError:
            process.kill() # タイムアウトしたらプロセスを強制終了
            await process.wait()
            logging.error(f"Shell command timed out: {command}")
            return {"error": f"Command timed out after 60 seconds: {command}"}
        except Exception as e:
            logging.error(f"Error in shell_exec_async: {e}")
            return {"error": str(e)}

    async def file_read_async(self, abs_path: str, view_type: str = "text", start_line: Optional[int] = None, end_line: Optional[int] = None) -> Dict[str, Any]:
        """指定されたファイルのコンテンツを非同期に読み取ります。

        Args:
            abs_path (str): 読み取るファイルの絶対パス。
            view_type (str, optional): 読み取るコンテンツのタイプ（"text"または"image"）。デフォルトは"text"。
            start_line (Optional[int], optional): テキストファイルの場合、読み取りを開始する行番号（0-based）。
            end_line (Optional[int], optional): テキストファイルの場合、読み取りを終了する行番号（0-based, exclusive）。

        Returns:
            Dict[str, Any]: ファイルの内容、またはエラーメッセージを含む辞書。
        """
        try:
            if not os.path.exists(abs_path):
                logging.warning(f"File not found: {abs_path}")
                return {"error": f"File not found: {abs_path}"}

            if view_type == "text":
                # aiofilesなどの非同期ファイルI/Oライブラリを使用することが望ましい
                # ここでは簡単な例として、同期的なopenをThreadPoolExecutorでラップ
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    content = await loop.run_in_executor(pool, self._read_file_sync, abs_path, start_line, end_line)
                return {"content": content}
            elif view_type == "image":
                logging.warning(f"Image view type not fully implemented for {abs_path}")
                return {"error": "Image view type requires specific handling (e.g., temporary URL generation)."}
            else:
                logging.warning(f"Unsupported view_type: {view_type}")
                return {"error": f"Unsupported view_type: {view_type}"}
        except Exception as e:
            logging.error(f"Error reading file {abs_path}: {e}")
            return {"error": str(e)}

    def _read_file_sync(self, abs_path: str, start_line: Optional[int], end_line: Optional[int]) -> str:
        # 同期的なファイル読み込みヘルパー関数
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            content_lines = lines[start_line:end_line] if start_line is not None or end_line is not None else lines
            return "".join(content_lines)

    async def info_search_web_async(self, query: str) -> Dict[str, Any]:
        """指定されたクエリで非同期にウェブ検索を実行し、結果を返します。

        Args:
            query (str): 検索クエリ。

        Returns:
            Dict[str, Any]: 検索結果のリスト、またはエラーメッセージを含む辞書。
        """
        try:
            # 実際のウェブ検索API（例: Google Custom Search API, Bing Web Search APIなど）を使用
            # ここではaiohttpを使用して外部APIを呼び出す例
            api_url = "https://api.example.com/search" # 実際の検索APIのURLに置き換える
            params = {"q": query, "api_key": os.environ.get("SEARCH_API_KEY")}
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    # 検索APIのレスポンス構造に合わせて結果をパース
                    results = data.get("items", []) # 例: Google Custom Search APIの場合
                    formatted_results = []
                    for item in results:
                        formatted_results.append({
                            "title": item.get("title"),
                            "url": item.get("link"),
                            "snippet": item.get("snippet")
                        })
                    return {"results": formatted_results}
        except aiohttp.ClientError as e:
            logging.error(f"Async web search failed: {e}")
            return {"error": f"Web search failed: {e}"}
        except Exception as e:
            logging.error(f"Error in info_search_web_async: {e}")
            return {"error": str(e)}

    async def file_write_text_async(self, abs_path: str, content: str, append_newline: bool = True) -> Dict[str, Any]:
        """テキストファイルを非同期に書き込みます（上書き）。

        Args:
            abs_path (str): 書き込むファイルの絶対パス。
            content (str): 書き込むテキストコンテンツ。
            append_newline (bool): 末尾に改行を追加するかどうか。

        Returns:
            Dict[str, Any]: 成功メッセージ、またはエラーメッセージを含む辞書。
        """
        try:
            # aiofilesなどの非同期ファイルI/Oライブラリを使用することが望ましい
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(pool, self._write_file_sync, abs_path, content, append_newline, "w")
            return {"status": "success", "message": f"File written: {abs_path}"}
        except Exception as e:
            logging.error(f"Error writing file {abs_path}: {e}")
            return {"error": str(e)}

    async def file_append_text_async(self, abs_path: str, content: str, append_newline: bool = True) -> Dict[str, Any]:
        """テキストファイルに非同期にコンテンツを追加します。

        Args:
            abs_path (str): 追加するファイルの絶対パス。
            content (str): 追加するテキストコンテンツ。
            append_newline (bool): 末尾に改行を追加するかどうか。

        Returns:
            Dict[str, Any]: 成功メッセージ、またはエラーメッセージを含む辞書。
        """
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                await loop.run_in_executor(pool, self._write_file_sync, abs_path, content, append_newline, "a")
            return {"status": "success", "message": f"Content appended to file: {abs_path}"}
        except Exception as e:
            logging.error(f"Error appending to file {abs_path}: {e}")
            return {"error": str(e)}

    def _write_file_sync(self, abs_path: str, content: str, append_newline: bool, mode: str):
        # 同期的なファイル書き込みヘルパー関数
        with open(abs_path, mode, encoding="utf-8") as f:
            f.write(content)
            if append_newline:
                f.write("\n")

    async def file_replace_text_async(self, abs_path: str, old_str: str, new_str: str) -> Dict[str, Any]:
        """テキストファイル内の指定された文字列を非同期に置換します。

        Args:
            abs_path (str): 置換を行うファイルの絶対パス。
            old_str (str): 置換される文字列。ファイル内に一度だけ存在する必要があります。
            new_str (str): 置換後の文字列。

        Returns:
            Dict[str, Any]: 成功メッセージ、またはエラーメッセージを含む辞書。
        """
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                content = await loop.run_in_executor(pool, self._read_file_sync, abs_path, None, None)
            
            if content.count(old_str) != 1:
                return {"error": f"Old string '{old_str}' found {content.count(old_str)} times. Must be exactly once."}
            
            new_content = content.replace(old_str, new_str)
            await loop.run_in_executor(pool, self._write_file_sync, abs_path, new_content, False, "w")
            return {"status": "success", "message": f"Text replaced in file: {abs_path}"}
        except Exception as e:
            logging.error(f"Error replacing text in file {abs_path}: {e}")
            return {"error": str(e)}

    async def browser_navigate_async(self, url: str, intent: str, focus: Optional[str] = None) -> Dict[str, Any]:
        """ブラウザを非同期に指定されたURLにナビゲートします。

        Args:
            url (str): ナビゲートするURL。
            intent (str): ナビゲーションの意図（'navigational', 'informational', 'transactional'）。
            focus (Optional[str]): 'informational'の場合、焦点を当てるトピック。

        Returns:
            Dict[str, Any]: 成功メッセージ、またはエラーメッセージを含む辞書。
        """
        try:
            # Playwrightなどの非同期ブラウザ自動化ライブラリを使用
            # ここでは概念的な例
            logging.info(f"Navigating browser to {url} with intent {intent}")
            # await playwright_browser.goto(url)
            # content = await playwright_page.content()
            # return {"status": "success", "content_preview": content[:500]}
            return {"status": "success", "message": f"Navigated to {url}"}
        except Exception as e:
            logging.error(f"Error navigating browser to {url}: {e}")
            return {"error": str(e)}

    async def message_notify_user_async(self, text: str, attachments: Optional[List[str]] = None) -> Dict[str, Any]:
        """ユーザーに非同期に通知メッセージを送信します。

        Args:
            text (str): メッセージテキスト。
            attachments (Optional[List[str]]): 添付ファイルのパスリスト。

        Returns:
            Dict[str, Any]: 成功メッセージ、またはエラーメッセージを含む辞書。
        """
        logging.info(f"Notifying user: {text} (Attachments: {attachments})")
        # 実際のメッセージングシステム（例: WebSocket, HTTP POST）に送信
        return {"status": "success", "message": "User notified"}

    async def message_ask_user_async(self, text: str, options: Optional[List[str]] = None, suggested_user_action: Optional[str] = None) -> Dict[str, Any]:
        """ユーザーに非同期に質問し、応答を待ちます。

        Args:
            text (str): 質問テキスト。
            options (Optional[List[str]]): 選択肢のリスト。
            suggested_user_action (Optional[str]): ユーザーに提案するアクション。

        Returns:
            Dict[str, Any]: ユーザーの応答、またはエラーメッセージを含む辞書。
        """
        logging.info(f"Asking user: {text} (Options: {options}, Action: {suggested_user_action})")
        # 実際のメッセージングシステムを通じてユーザーからの応答を待機
        # 例: WebSocket経由で応答を受け取る
        # user_response = await self._wait_for_user_response()
        # return {"response": user_response}
        return {"status": "success", "message": "User asked, awaiting response"}

    async def close(self):
        """データベース接続を非同期に閉じます。"""
        if self.db_connection:
            await self.db_connection.close()
            self.db_connection = None

```

#### 5.1.2. LLMへのツール定義の提供（非同期ツール対応）

LLMに提供するツールのJSONスキーマは、上記で定義した非同期ツール関数に対応するように更新されます。`async`キーワードはスキーマには影響しませんが、実装が非同期であることを明確にします。

```python
# 例: LLMに提供するツールのJSONスキーマ（概念）
# 各ツールのdescriptionは、LLMがツールの目的と使い方を理解するために非常に重要です。

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "shell_exec_async",
            "description": "指定されたシェルコマンドをサンドボックス環境で非同期に実行します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "実行するシェルコマンド。"},
                    "session_id": {"type": "string", "description": "シェルセッションを一意に識別するID。"},
                    "working_dir": {"type": "string", "description": "コマンドを実行する作業ディレクトリ。"}
                },
                "required": ["command", "session_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_read_async",
            "description": "指定されたファイルのコンテンツを非同期に読み取ります。",
            "parameters": {
                "type": "object",
                "properties": {
                    "abs_path": {"type": "string", "description": "読み取るファイルの絶対パス。"},
                    "view_type": {"type": "string", "enum": ["text", "image"], "description": "読み取るコンテンツのタイプ。"},
                    "start_line": {"type": "integer", "description": "テキストファイルの場合、読み取りを開始する行番号（0-based）。"},
                    "end_line": {"type": "integer", "description": "テキストファイルの場合、読み取りを終了する行番号（0-based, exclusive）。"}
                },
                "required": ["abs_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "info_search_web_async",
            "description": "指定されたクエリで非同期にウェブ検索を実行し、結果を返します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "検索クエリ。"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_write_text_async",
            "description": "テキストファイルを非同期に書き込みます（上書き）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "abs_path": {"type": "string", "description": "書き込むファイルの絶対パス。"},
                    "content": {"type": "string", "description": "書き込むテキストコンテンツ。"},
                    "append_newline": {"type": "boolean", "description": "末尾に改行を追加するかどうか。"}
                },
                "required": ["abs_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_append_text_async",
            "description": "テキストファイルに非同期にコンテンツを追加します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "abs_path": {"type": "string", "description": "追加するファイルの絶対パス。"},
                    "content": {"type": "string", "description": "追加するテキストコンテンツ。"},
                    "append_newline": {"type": "boolean", "description": "末尾に改行を追加するかどうか。"}
                },
                "required": ["abs_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "file_replace_text_async",
            "description": "テキストファイル内の指定された文字列を非同期に置換します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "abs_path": {"type": "string", "description": "置換を行うファイルの絶対パス。"},
                    "old_str": {"type": "string", "description": "置換される文字列。ファイル内に一度だけ存在する必要があります。"},
                    "new_str": {"type": "string", "description": "置換後の文字列。"}
                },
                "required": ["abs_path", "old_str", "new_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate_async",
            "description": "ブラウザを非同期に指定されたURLにナビゲートします。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "ナビゲートするURL。"},
                    "intent": {"type": "string", "enum": ["navigational", "informational", "transactional"], "description": "ナビゲーションの意図。"},
                    "focus": {"type": "string", "description": "'informational'の場合、焦点を当てるトピック。"}
                },
                "required": ["url", "intent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "message_notify_user_async",
            "description": "ユーザーに非同期に通知メッセージを送信します。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "メッセージテキスト。"},
                    "attachments": {"type": "array", "items": {"type": "string"}, "description": "添付ファイルのパスリスト。"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "message_ask_user_async",
            "description": "ユーザーに非同期に質問し、応答を待ちます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "質問テキスト。"},
                    "options": {"type": "array", "items": {"type": "string"}, "description": "選択肢のリスト。"},
                    "suggested_user_action": {"type": "string", "description": "ユーザーに提案するアクション。"}
                },
                "required": ["text"]
            }
        }
    }
    # 他のツールも同様に追加
]
```

### 5.2. エージェントループの実装（非同期版）

エージェントループは、`asyncio`を使用して完全に非同期で動作するように再設計されます。これにより、LLM呼び出しやツール実行中のI/O待ち時間中に、他の処理（例: 別のユーザーリクエストの処理）を並行して実行できるようになります。

```python
from openai import AsyncOpenAI # 非同期クライアントを使用
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

class CappuccinoAgent:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key) # AsyncOpenAIクライアントを使用
        self.tool_manager = ToolManager() # 上記で定義したToolManagerのインスタンス
        self.messages = [] # LLMとの会話履歴
        self.task_plan = [] # タスクプラン（StateManagerで管理されるべき）
        self.current_phase_id = 0
        self.executor = ThreadPoolExecutor() # 同期的な処理を非同期コンテキストで実行するためのExecutor

        # システムプロンプトの初期化
        self._initialize_system_prompt()

    def _initialize_system_prompt(self):
        system_prompt = (
            "あなたはCappuccinoという名前の、ユーザーの多様な要求に応えることができる汎用AIアシスタントです。\n"
            "ユーザーの指示を理解し、適切なツールを自律的に選択・実行することで、複雑なタスクを効率的に解決してください。\n"
            "利用可能なツールは以下の通りです。これらのツールを適切に利用してタスクを遂行してください。\n"
            "思考プロセスは日本語で行い、ユーザーへの応答も日本語で行ってください。\n"
            "タスクが完了したら、`agent_end_task`ツールを呼び出して終了してください。\n"
            "不明な点があれば、ユーザーに質問してください。"
        )
        self.messages.append({"role": "system", "content": system_prompt})

    async def _add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None, tool_call_id: Optional[str] = None):
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        if tool_call_id:
            message["tool_call_id"] = tool_call_id
        self.messages.append(message)
        logging.info(f"Added message: {message}")
        # 非同期で履歴をデータベースに保存
        conn = await self.tool_manager._get_db_connection()
        await conn.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
        await conn.commit()

    async def run(self, user_query: str):
        await self._add_message("user", user_query)

        while True:
            logging.info("Entering async agent loop...")
            try:
                # LLMを非同期で呼び出す
                response = await self.client.chat.completions.create(
                    model="gpt-4.1", 
                    messages=self.messages,
                    tools=tools_schema, 
                    tool_choice="auto" 
                )
                response_message = response.choices[0].message
                await self._add_message(response_message.role, response_message.content or "", response_message.tool_calls)

                if response_message.tool_calls:
                    # LLMがツール呼び出しを要求した場合
                    tool_outputs = []
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        logging.info(f"LLM requested tool call: {function_name} with args {function_args}")

                        if hasattr(self.tool_manager, function_name):
                            tool_function = getattr(self.tool_manager, function_name)
                            # 非同期ツール関数をawaitで実行
                            if asyncio.iscoroutinefunction(tool_function):
                                tool_output = await tool_function(**function_args)
                            else:
                                # 同期ツール関数をThreadPoolExecutorで実行
                                loop = asyncio.get_running_loop()
                                tool_output = await loop.run_in_executor(self.executor, tool_function, **function_args)
                            
                            logging.info(f"Tool {function_name} executed, output: {tool_output}")
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": tool_output
                            })
                        else:
                            error_message = f"Error: Tool \'{function_name}\' not found in ToolManager."
                            logging.error(error_message)
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": {"error": error_message}
                            })
                    
                    # すべてのツール実行結果をLLMにフィードバック
                    for output_entry in tool_outputs:
                        await self._add_message(
                            "tool",
                            content=json.dumps(output_entry["output"]),
                            tool_call_id=output_entry["tool_call_id"]
                        )
                    continue # ツール実行結果をLLMにフィードバックするため、ループを継続

                elif response_message.content:
                    # LLMがテキスト応答を返した場合（タスク完了または質問）
                    print(f"Cappuccino: {response_message.content}")
                    # ここでタスク完了を判断し、必要であればループを終了
                    if "タスクが完了しました" in response_message.content or "終了します" in response_message.content:
                        logging.info("Task likely completed. Ending agent loop.")
                        break
                    break # この例ではテキスト応答で終了

            except Exception as e:
                logging.error(f"An error occurred in the agent loop: {e}")
                await self._add_message("system", f"エージェントループでエラーが発生しました: {e}")
                break # エラー発生時はループを終了

        await self.tool_manager.close()

# エージェントの実行例（APIキーは環境変数から取得）
# async def main():
#     agent = CappuccinoAgent(api_key=os.environ.get("OPENAI_API_KEY"))
#     await agent.run("todo.mdの内容を読んで、その要約を教えてください。")
#     # await agent.run("現在のディレクトリにあるファイルとフォルダをリストしてください。")
# if __name__ == "__main__":
#     asyncio.run(main())
```

### 5.3. 状態管理と永続化（非同期対応）

状態管理も非同期でデータベースと連携するように更新します。`aiosqlite`を使用して、データベース操作が非同期コンテキストをブロックしないようにします。

#### 5.3.1. 会話履歴の管理（非同期版）

`_add_message`メソッド内で、メッセージを非同期でデータベースに保存するロジックを実装します。

```python
# CappuccinoAgentの_add_messageメソッド内で既に実装済み
# class CappuccinoAgent:
#     async def _add_message(self, role: str, content: str, tool_calls: Optional[List[Dict]] = None, tool_call_id: Optional[str] = None):
#         # ...
#         conn = await self.tool_manager._get_db_connection()
#         await conn.execute("INSERT INTO history (role, content) VALUES (?, ?)", (role, content))
#         await conn.commit()
#         # ...
```

#### 5.3.2. タスクプランと状態の永続化（非同期版）

タスクプランやエージェントの現在のフェーズなどのメタデータも、非同期でデータベースに保存・読み込みます。

```python
# 例: タスクプランと現在のフェーズを非同期で保存・読み込む関数
async def save_agent_state_async(db_connection: aiosqlite.Connection, task_plan: List[Dict], current_phase_id: int):
    await db_connection.execute("""CREATE TABLE IF NOT EXISTS agent_state (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    await db_connection.execute("REPLACE INTO agent_state (key, value) VALUES (?, ?)", ("task_plan", json.dumps(task_plan)))
    await db_connection.execute("REPLACE INTO agent_state (key, value) VALUES (?, ?)", ("current_phase_id", str(current_phase_id)))
    await db_connection.commit()
    logging.info("Agent state saved asynchronously.")

async def load_agent_state_async(db_connection: aiosqlite.Connection) -> Dict[str, Any]:
    cursor = await db_connection.execute("SELECT key, value FROM agent_state")
    rows = await cursor.fetchall()
    state = {row[0]: row[1] for row in rows}
    
    task_plan = json.loads(state.get("task_plan", "[]"))
    current_phase_id = int(state.get("current_phase_id", "0"))
    logging.info("Agent state loaded asynchronously.")
    return {"task_plan": task_plan, "current_phase_id": current_phase_id}

# CappuccinoAgentの初期化時に状態を非同期でロードし、更新時に非同期で保存するロジックを追加
# class CappuccinoAgent:
#     async def __init__(self, api_key: str):
#         # ...
#         self.tool_manager = ToolManager()
#         conn = await self.tool_manager._get_db_connection()
#         loaded_state = await load_agent_state_async(conn)
#         self.task_plan = loaded_state["task_plan"]
#         self.current_phase_id = loaded_state["current_phase_id"]
#         # ...

#     async def _update_task_plan(self, new_plan: List[Dict], new_phase_id: int):
#         self.task_plan = new_plan
#         self.current_phase_id = new_phase_id
#         conn = await self.tool_manager._get_db_connection()
#         await save_agent_state_async(conn, self.task_plan, self.current_phase_id)
```

### 5.4. エラーハンドリングとリカバリ（非同期対応）

非同期コンテキストでのエラーハンドリングは、同期的な場合と同様に`try-except`ブロックを使用しますが、`await`呼び出し中に発生する可能性のある`asyncio.TimeoutError`などの非同期特有のエラーも考慮する必要があります。

#### 5.4.1. ツールレベルのエラーハンドリング（非同期版）

各非同期ツール関数は、内部で発生する可能性のあるエラーを捕捉し、エラーメッセージを返すように設計すべきです。

```python
# 各非同期ツール関数（shell_exec_async, file_read_asyncなど）のtry-exceptブロックで既に実装されています。
# 例:
# try:
#     # 非同期ツール固有の処理
#     return {"result": "success"}
# except asyncio.TimeoutError:
#     # タイムアウト処理
#     return {"error": "Operation timed out"}
# except Exception as e:
#     logging.error(f"Specific tool error: {e}")
#     return {"error": str(e)}
```

#### 5.4.2. エージェントループレベルのエラーハンドリング（非同期版）

エージェントループ全体でエラーを捕捉し、LLMにエラー情報をフィードバックすることで、LLMが自己修正を試みることができます。

```python
# CappuccinoAgentのrunメソッド内のtry-exceptブロックで既に実装されています。
# LLMへのエラーフィードバックは、"tool"ロールのメッセージとして行われます。
# これにより、LLMはエラーメッセージを読み取り、次の思考に活かすことができます。

# 例:
# try:
#     # LLM呼び出しとツール実行ロジック
# except Exception as e:
#     logging.error(f"An error occurred in the agent loop: {e}")
#     await self._add_message("system", f"エージェントループでエラーが発生しました: {e}")
#     # ここで、ユーザーにエラーを通知したり、タスクを安全に終了したりするロジックを追加できます。
```

これらの更新されたガイドラインとコード例は、CodexがCappuccinoエージェントを堅牢かつ効率的に、そして非同期・並列処理を考慮して実装するための出発点となります。各コンポーネントの詳細な実装は、Codexの裁量に委ねられますが、上記の原則を遵守してください。


## 8. 今後の拡張性（更新）

Cappuccinoエージェントは、将来的な機能追加や改善が容易なように設計されるべきです。モジュール化されたアーキテクチャと明確なインターフェースは、この拡張性を確保するための鍵となります。特に、ヒューマノイドへの統合を考慮し、パフォーマンスとスケーラビリティを重視した拡張性を提案します。

### 8.1. 新しいツールの追加（非同期対応）

新しいツールを追加するプロセスは、シンプルかつ効率的であるべきです。新しいツールは、`ToolManager`クラスに新しい非同期メソッドとして追加され、その機能と引数のスキーマがLLMに提供される`tools_schema`に反映されるだけで、エージェントのコアロジックを変更することなく組み込めるように設計してください。

*   **ツール関数の定義**: 新しい機能に対応する非同期Python関数を`ToolManager`内に定義します。この関数は、明確な入力と出力、そして詳細なdocstringを持つべきです。
*   **スキーマの更新**: 定義したツール関数のJSONスキーマを生成し、`tools_schema`リストに追加します。これにより、LLMはその新しいツールを認識し、利用できるようになります。
*   **依存関係の管理**: 新しいツールが外部ライブラリに依存する場合、`requirements.txt`ファイルにその依存関係を追加し、サンドボックス環境にインストールできるようにしてください。

### 8.2. LLMモデルの切り替え（非同期対応）

将来的に、より高性能なLLMモデルや、異なる特性を持つLLMモデル（例: コスト効率の良いモデル、特定のタスクに特化したモデル）に切り替える可能性を考慮してください。LLMとの連携部分は抽象化され、モデルの変更がエージェントの他の部分に大きな影響を与えないように設計してください。

*   **APIクライアントの抽象化**: `CappuccinoAgent`クラス内で直接`AsyncOpenAI`クライアントを扱うのではなく、LLMとのインタラクションをラップする抽象レイヤーを導入することを検討してください。これにより、モデルの切り替えが容易になります。
*   **プロンプトの適応性**: 新しいLLMモデルの特性に合わせて、システムプロンプトやツール定義のプロンプトを調整できるように柔軟な設計にしてください。

### 8.3. ユーザーインターフェースの分離とヒューマノイド統合のためのAPI

現在の設計では、エージェントのコアロジックとユーザーインターフェース（CLIベースの対話）が密接に結合しています。ヒューマノイドへの統合を考慮し、UI層とエージェントのコアロジックを完全に分離し、高性能なAPIインターフェースを提供してください。

*   **FastAPIによるAPIインターフェースの提供**: エージェントのコアロジックをHTTP APIとして公開するために、FastAPIを使用してください。これにより、ヒューマノイドの制御システムや他の外部システムから、エージェントの機能に非同期でアクセスできるようになります。
    *   **エンドポイントの設計**: `POST /agent/run`（ユーザーからの指示を受け付け、エージェントを実行）、`GET /agent/status`（エージェントの現在の状態や進捗を取得）、`POST /agent/tool_call_result`（ヒューマノイド側で実行されたツールの結果をエージェントにフィードバック）などのエンドポイントを設計してください。
    *   **非同期処理の徹底**: FastAPIのエンドポイントはすべて`async def`で定義し、内部でCappuccinoAgentの非同期メソッドを`await`で呼び出すようにしてください。
*   **WebSocketsによるストリーミング応答**: ヒューマノイドとのリアルタイムインタラクションのために、LLMの応答やツールの実行状況、エージェントの思考プロセスなどをストリーミングで提供するメカニズムを実装してください。これにより、ヒューマノイドは応答の最初の部分が利用可能になり次第、動作を開始できます。
    *   FastAPIはWebSocketをネイティブにサポートしており、これを利用してエージェントのリアルタイム出力をヒューマノイドにプッシュできます。

### 8.4. パフォーマンスとスケーラビリティの最適化（ヒューマノイド向け）

ヒューマノイドへの組み込みを前提とした場合、極めて低いレイテンシと高いスループットが求められます。以下の点を特に重視してください。

*   **非同期処理の徹底**: すべてのI/Oバウンドな操作（LLM API呼び出し、外部ツール呼び出し、データベースアクセス、ファイルI/O、ネットワーク通信）は、`asyncio`と対応する非同期ライブラリ（`aiohttp`, `aiosqlite`など）を使用して非同期で実行してください。これにより、エージェントはI/O待ち時間中に他の処理を実行でき、応答性を最大化します。
*   **並行処理と並列処理**: 
    *   **I/Oバウンドな並行処理**: 複数のLLM呼び出しや複数のツール呼び出しを同時に行う必要がある場合、`asyncio.gather`を使用して並行して実行してください。これにより、複数の非同期操作が同時に進行し、全体の応答時間を短縮できます。
    *   **CPUバウンドな並列処理**: もしエージェントのロジック内に計算コストの高いCPUバウンドな処理（例: 大規模なデータ解析、複雑なアルゴリズム）が存在する場合、`concurrent.futures.ProcessPoolExecutor`を使用して別プロセスで実行し、PythonのGIL（Global Interpreter Lock）による制約を回避して真の並列処理を実現してください。ただし、プロセス間通信のオーバーヘッドを考慮し、適切な粒度で適用してください。
*   **推論の最適化とキャッシュ**: 
    *   **プロンプトの最適化**: LLMへの入力プロンプトをできるだけ簡潔かつ明確にすることで、推論時間を短縮し、より的確な応答を引き出すことができます。
    *   **出力の構造化**: LLMからの出力にJSONなどの構造化されたフォーマットを要求することで、後続のパース処理を高速化し、エラーを減らすことができます。
    *   **結果のキャッシュ**: 頻繁に繰り返されるLLMの推論結果や、ツールの実行結果をキャッシュすることを検討してください。Redisのようなインメモリデータベースをキャッシュストアとして利用することで、応答時間を大幅に短縮できます。
    *   **軽量モデルの活用**: すべてのタスクに高性能なLLMが必要なわけではありません。簡単な質問応答やルーティングには、より軽量で高速なモデル（例: GPT-3.5-turbo）を使用し、複雑なタスクの場合のみ高性能なモデル（例: GPT-4o）にフォールバックするようなハイブリッド戦略を検討してください。
*   **分散システム**: 複数のCappuccinoエージェントインスタンスをデプロイし、負荷分散を行うことで、高いスケーラビリティと耐障害性を実現できます。RabbitMQやKafkaのようなメッセージキューシステムを導入し、リクエストをキューイングして利用可能なエージェントが処理するように設計してください。複数インスタンスを起動する場合は、それぞれ異なるポートでFastAPIサーバーを立ち上げ、同じキューを監視させます。例: `uvicorn main:app --port 8001` と `uvicorn main:app --port 8002` を実行し、QueueManagerを介してタスクを共有させます。

これらの拡張性に関する考慮事項は、Cappuccinoエージェントが長期にわたって進化し、ヒューマノイドの要求に応えることができる、極めて高速で応答性の高いシステムであり続けるために不可欠です。Codexは、これらの指針を念頭に置いて、将来を見据えた設計と実装を行ってください。


## 11. Manusを超える機能の提案

ユーザーの「Manusを超えるエージェント」という目標を達成するため、Cappuccinoには以下の革新的な機能を追加することを提案します。これらの機能は、現在のManusの能力を凌駕し、より高度な自律性と汎用性を提供します。

### 11.1. 自己進化型ツール学習システム

現在のエージェントは、事前に定義されたツールセットに依存しています。Cappuccinoは、ユーザーのフィードバックやタスクの失敗から、新しいツールを自律的に学習・生成する能力を持つべきです。

*   **失敗からの学習**: エージェントがタスクを完了できなかった場合、その失敗の原因を分析し、不足しているツールや既存ツールの改善点を特定します。
*   **ツール生成モジュール**: LLMを活用し、特定されたニーズに基づいて新しいツール（Python関数）のコードを生成します。このモジュールは、既存のライブラリやAPIのドキュメントを読み込み、それらを活用したツールを生成する能力を持つべきです。
*   **自動テストと統合**: 生成されたツールは、自動的にテストされ、問題がなければ`ToolManager`に統合されます。これにより、エージェントは時間とともに自身の能力を拡張し、より多様なタスクに対応できるようになります。

### 11.2. マルチモーダル推論と行動

現在のエージェントは主にテキストベースの入出力に焦点を当てています。Cappuccinoは、画像、音声、動画などのマルチモーダル情報を理解し、それに基づいて行動する能力を持つべきです。

*   **画像理解**: ユーザーが提供した画像の内容を分析し、それに基づいて推論やツール選択を行います（例: 画像内のオブジェクトを認識し、それに関する情報を検索する）。
*   **音声インタラクション**: 音声入力（Speech-to-Text）と音声出力（Text-to-Speech）を統合し、より自然な会話インタフェースを提供します。ヒューマノイドとの統合において、これは極めて重要です。
*   **動画分析**: 短い動画クリップを分析し、その中のイベントや行動を理解し、それに基づいて次のステップを計画します。
*   **マルチモーダルツール**: 画像生成、動画生成、音声生成などのマルチモーダルツールを統合し、LLMがこれらのツールを適切に呼び出せるようにします。

### 11.3. 感情認識と共感応答

ヒューマノイドとのより人間らしいインタラクションを実現するために、Cappuccinoはユーザーの感情を認識し、それに応じた共感的な応答を生成する能力を持つべきです。

*   **感情分析モジュール**: ユーザーのテキスト入力や音声入力から感情を分析します。
*   **共感応答生成**: 分析された感情に基づいて、LLMがより適切で共感的な応答を生成するようにプロンプトを調整します。
*   **行動の調整**: ユーザーの感情状態に応じて、エージェントの行動（例: 応答のトーン、タスクの優先順位付け）を調整します。

### 11.4. 自律的な目標設定と長期計画

現在のエージェントは、ユーザーから与えられたタスクを解決することに焦点を当てています。Cappuccinoは、より高レベルの目標を自律的に設定し、それを達成するための長期的な計画を立案する能力を持つべきです。

*   **目標設定モジュール**: ユーザーの一般的なニーズや過去のインタラクションから、潜在的な目標を特定し、提案します。
*   **長期計画ジェネレーター**: 設定された目標を達成するための、複数のステップからなる長期的な計画を生成します。この計画は、必要に応じて動的に修正されます。
*   **進捗監視と自己評価**: 計画の進捗を監視し、定期的に自己評価を行い、必要に応じて計画を修正します。

これらの機能は、Cappuccinoを単なるツール実行エージェントから、真に自律的で人間のようなアシスタントへと進化させるためのものです。Codexは、これらの提案を考慮し、可能な限り実装に挑戦してください。


## 12. 結論（更新）

この指示書は、OpenAI Codexが「Cappuccino」と名付けられた汎用AIアシスタントを構築するための、更新された包括的なガイドラインを提供しました。Cappuccinoは、ユーザーの自然言語による指示を理解し、多様なツールを自律的に利用して複雑なタスクを解決することを目指します。特に、ヒューマノイドへの統合を視野に入れ、最速応答、並列推論、そして将来的な自己進化やマルチモーダル対応を可能にする設計を強調しました。

Codexは、この指示書に記載されたアーキテクチャ設計、技術スタック、主要コンポーネントの実装ガイドライン、エラーハンドリング、サンドボックス環境の考慮事項、テストと検証、そして今後の拡張性に関する指針を厳密に遵守してください。

特に、以下の点に重点を置いてください。

*   **堅牢な非同期ツール実装**: 各ツールが非同期で機能し、エラーを適切に処理できること。外部APIとの連携には`aiohttp`、データベース操作には`aiosqlite`など、適切な非同期ライブラリを使用すること。
*   **効率的な非同期エージェントループ**: LLMとツールの間のインタラクションが完全に非同期で動作し、論理的な思考プロセスが反映されていること。`AsyncOpenAI`クライアントと`asyncio.gather`を積極的に活用すること。
*   **状態管理と永続化**: エージェントの状態が確実に非同期で保存され、中断後もタスクを再開できること。
*   **サンドボックス環境への適応**: 制限された環境下でも最大限のパフォーマンスを発揮できるよう、設計と実装に工夫を凝らすこと。
*   **FastAPIによるAPIインターフェース**: ヒューマノイド統合のために、高性能で非同期対応のRESTful APIまたはWebSocketインターフェースを提供すること。
*   **並列推論の考慮**: `ThreadPoolExecutor`や`ProcessPoolExecutor`を適切に利用し、LLM推論やCPUバウンドなタスクの並列処理を可能にすること。
*   **提案された機能拡張への挑戦**: 自己進化型ツール学習、マルチモーダル推論、感情認識、自律的な目標設定といった、Manusを超える革新的な機能の実装に積極的に取り組むこと。

Cappuccinoの成功は、Codexのコード生成能力と、この指示書に示された設計原則への忠実さにかかっています。ユーザーの期待を超える、革新的で信頼性の高いAIエージェントの実現を期待しています。
