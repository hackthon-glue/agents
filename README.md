# AI Expert Panel Discussion System

AWS Bedrock を使った AI 専門家パネルディスカッションシステムで、複数のエージェントが議論して国のムード（Happy/Neutral/Sad）を分析・決定します。

## 🎯 主な機能

1. **マルチエージェント パネルディスカッション**
   - モデレーター、ニュース分析家、天気分析家、データサイエンティスト、文化専門家、占い師の6人のエージェント
   - 動的な議論フロー（モデレーターがターン数を調整）
   - 投票システムで最終的なムード（Happy/Neutral/Sad）と信頼スコア（0-100）を決定

2. **自動データ収集（Playwright Browser）**
   - ニュースサイトから最新記事を自動スクレイピング
   - 天気情報をリアルタイム取得
   - センチメント分析と天気ムード影響度計算
   - フォールバック機能（Browser失敗時はモックデータ使用）

3. **RDSデータベース統合**
   - パネルディスカッションの結果をRDS（PostgreSQL）に自動保存
   - Django バックエンドと連携してフロントエンドで表示
   - 専門家の分析、投票結果、議論のトランスクリプトを記録

---

## 📁 プロジェクト構成

```
hackthon-agents/
├── agents/
│   ├── panel_discussion_strands_v2.py  # パネルディスカッション実装（V2）
│   ├── agent_configs.py                 # エージェント設定
│   ├── main.py                          # メインエントリーポイント
│   ├── browser_collectors.py            # データ収集サービス
│   ├── rds_storage.py                   # RDS保存ロジック
│   ├── knowledge_base_sync.py           # Knowledge Base同期
│   ├── schema.sql                       # RDSテーブルスキーマ
│   │
│   ├── tests/                           # テストファイル
│   │   ├── test_panel_v2.py
│   │   ├── test_browser_collectors.py
│   │   └── test_rds_storage.py
│   │
│   ├── .env.example                     # 環境変数サンプル
│   ├── Dockerfile                       # Docker設定
│   └── DEPLOYMENT.md                    # デプロイガイド
│
├── requirements.txt                     # Python依存関係
├── .gitignore
└── README.md                            # このファイル
```

---

## 🚀 クイックスタート

### 1. セットアップ

```bash
# ディレクトリ移動
cd hackthon-agents

# 仮想環境作成
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# Playwrightインストール（ブラウザ自動化用）
playwright install chromium
```

### 2. 環境変数設定

```bash
cd agents
cp .env.example .env

# .envファイルを編集
# AWS_REGION=us-west-2
# DB_HOST=your-rds-host
# DB_USER=postgres
# DB_PASSWORD=your-password
# DB_NAME=glue
# KNOWLEDGE_BASE_ID=your-kb-id
# KB_S3_BUCKET=your-s3-bucket
```

### 3. AWS認証

```bash
# AWS認証情報を設定
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_SESSION_TOKEN=your-session-token  # 一時認証の場合
```

### 4. ローカルテスト

```bash
cd agents

# ブラウザデータ収集テスト
python -m tests.test_browser_collectors

# パネルディスカッションテスト（V2）
python -m tests.test_panel_v2

# RDS保存テスト
python -m tests.test_rds_storage

# 統合テスト（データ収集→パネル→RDS保存）
python test_country_sentiment.py
```

---
## 🏗️ アーキテクチャ

```
User Request
     ↓
Main Entry Point
     ↓
 ┌───┴───────┐
 │           │
Browser     Panel Discussion V2
Collection   (Dynamic Flow)
 │              ↓
 ├─ News    Moderator
 ├─ Weather    ├─ Controls flow
 └─ KB         ├─ Manages turns
               ├─ Facilitates debate
               │
            6 Expert Agents
               ├─ News Analyst
               ├─ Weather Analyst
               ├─ Data Scientist
               ├─ Cultural Expert
               ├─ Fortune Teller
               └─ (Dynamic participation)
               ↓
            Voting Phase
               ├─ Each expert votes
               ├─ Provides reasoning
               └─ Confidence score
               ↓
          Final Aggregation
               ↓
        RDS Storage
         (PostgreSQL)
               ├─ panel_discussions
               ├─ panel_expert_analyses
               ├─ panel_votes
               ├─ panel_transcripts
               └─ countries_sentiment
               ↓
        Django Backend
               ↓
        Frontend Display
```

---

## 🔧 技術スタック

- **AWS Bedrock** - Claude 3 Haiku/Sonnet LLM
- **AWS Bedrock Knowledge Base** - RAG (Retrieval-Augmented Generation)
- **RDS Aurora PostgreSQL** - データストレージ
- **Playwright** - ブラウザ自動化・スクレイピング
- **psycopg3** - PostgreSQL接続
- **Python 3.9+**

---

## 📊 データベーススキーマ

### panel_discussions
パネルディスカッションの基本情報
- country_code, topic, final_mood, final_score
- introduction, conclusion, discussion_date
- total_turns, debate_rounds

### panel_expert_analyses
各専門家の分析結果
- expert_role, analysis_text, round_number

### panel_votes
各専門家の投票
- expert_role, vote_mood, confidence, reasoning

### panel_transcripts
議論の全トランスクリプト
- speaker, content, round_number, turn_order

### countries_sentiment
国のセンチメント（Django統合用）
- country, label, score


## 📝 環境変数

必須の環境変数（`.env`ファイルに設定）:

```bash
# AWS設定
AWS_REGION=us-west-2

# RDS接続
DB_HOST=your-aurora-cluster.rds.amazonaws.com
DB_USER=postgres
DB_PASSWORD=your-password
DB_NAME=glue
DB_PORT=5432

# Knowledge Base
KNOWLEDGE_BASE_ID=XXXXXXXXXX
KB_DATA_SOURCE_ID=YYYYYYYYYY
KB_S3_BUCKET=your-knowledge-bucket

# オプション
BROWSER_HEADLESS=true
```

---

## 🧪 テスト

```bash
# 全テスト実行
cd agents
python -m pytest tests/ -v

# 特定のテスト実行
python -m tests.test_panel_v2          # パネルV2テスト
python -m tests.test_browser_collectors # データ収集テスト
python -m tests.test_rds_storage        # RDS保存テスト

# 統合テスト（実際のAPI呼び出し）
python test_country_sentiment.py
```

---

## 📊 データ収集の仕組み

### Playwright Browserによる自動収集

システムはPlaywright Browserを使って、各国のニュースサイトや天気サイトから自動的にデータを収集します。

#### ニュース収集
- 各国の主要ニュースサイトにアクセス
- トップヘッドラインを抽出（タイトル、要約、URL）
- センチメント分析（-1 ネガティブ ～ +1 ポジティブ）を自動実行

#### 天気収集
- 天気情報をリアルタイム取得
- 気温、天候、湿度などを取得
- 天気がムードに与える影響度を計算（-1 ～ +1）

#### センチメント分析の計算

```python
# ニュース記事のセンチメント
# ポジティブワード検出: +0.4
# ネガティブワード検出: -0.5
# 中立的な記事: 0.0

# 天気ムード影響度
def estimate_mood_impact(temp, description):
    score = 0.0

    # 快適な温度（18-25℃）
    if 18 <= temp <= 25:
        score += 0.3
    # 極端な温度
    elif temp < 5 or temp > 35:
        score -= 0.3

    # 晴天
    if 'clear' in description:
        score += 0.3
    # 雨天
    elif 'rain' in description:
        score -= 0.2

    return score
```

---

## 🚀 デプロイ

### AWS環境へのデプロイ

#### 前提条件

1. **AWS CLIとBedrock AgentCore SDKのインストール**

```bash
# AWS CLI
brew install awscli

# Bedrock AgentCore SDK
pip install bedrock-agentcore
```

2. **AWS認証情報の設定**

```bash
aws configure
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region name: us-west-2
# Default output format: json
```

#### 必要なAWSリソースの作成

**RDS PostgreSQLデータベース**

```bash
# RDS Aurora PostgreSQLクラスター作成（コンソールまたはCLI）
# 接続情報を .env に設定
```

**S3バケット（Knowledge Base用）**

```bash
aws s3 mb s3://hackthon-knowledge-base --region us-west-2
```

**Bedrock Knowledge Base**

Bedrockコンソールから作成:
1. Knowledge bases → Create knowledge base
2. S3データソース: `s3://hackthon-knowledge-base`
3. 埋め込みモデル: `amazon.titan-embed-text-v2:0`
4. Knowledge Base IDとData Source IDをメモ

## 🔍 トラブルシューティング

### デプロイ関連

#### "Module 'strands' not found"

```bash
pip install --upgrade strands-agents strands-agents-tools
```

#### Bedrock モデルアクセス拒否

```bash
# Bedrockモデルアクセスを有効化（AWSコンソール）
# Bedrock → Model access → 使用するモデル（Nova Pro/Haiku）を有効化
```

#### RDS接続エラー

```bash
# セキュリティグループ設定確認
# RDSセキュリティグループのインバウンドルールで、
# ECS/EC2からのPostgreSQL (5432)を許可

# 接続テスト
psql -h your-rds-host.rds.amazonaws.com -U postgres -d glue
```

### データ収集関連

#### Browser収集が失敗する

```bash
# Playwright Chromiumインストール確認
playwright install chromium

# 実行権限確認
chmod +x /path/to/chromium
```

### パフォーマンス問題

#### Browser起動が遅い

並列実行で高速化:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=2) as executor:
    news_future = executor.submit(news_collector.get_top_headlines, 'JP')
    weather_future = executor.submit(weather_collector.get_weather, 'JP')

    news = news_future.result()
    weather = weather_future.result()
```

#### メモリ不足エラー

ECSタスク定義でメモリを増量:

```json
{
  "memory": "2048",  // 1024 → 2048
  "cpu": "1024"      // 512 → 1024
}
```

---

## 📚 参考リンク

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Strands Agents Documentation](https://docs.strandsagents.ai)
- [Playwright Python](https://playwright.dev/python/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🤝 貢献

バグ報告や機能リクエストは Issue からお願いします。

---

## 📄 ライセンス

MIT License

---

Made with ❤️ for AWS Hackathon
