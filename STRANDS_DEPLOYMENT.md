# Strands Agents + Bedrock AgentCore Deployment Guide

## 概要

AI Expert Panel を **Strands Agents** + **Bedrock AgentCore** で実装・デプロイするガイド。

## アーキテクチャの変更点

### Before (旧実装)
- boto3で直接 Bedrock Runtime API 呼び出し
- 手動オーケストレーション
- ~400行のカスタムコード

### After (新実装)
- **Strands Agents SDK** - シンプルなエージェント管理
- **Bedrock AgentCore** - AWS本番環境への自動デプロイ
- ~100行の実装コード

---

## ファイル構成

```
hackthon-agents/agents/
├── agent_configs.py                  # エージェント設定
├── panel_discussion_strands.py       # Panel discussion (Strands) ✨
├── browser_collectors.py             # AgentCore Browser data collection ✨
├── panel_app.py                      # AgentCore deployment wrapper ✨
├── test_panel_strands.py             # ローカルテスト ✨
└── deploy_agents.py                  # デプロイスクリプト
```

---

## Step 1: 環境セットアップ

### 1.1 依存関係インストール

```bash
cd hackthon-agents

# 仮想環境作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt
```

### 1.2 AWS認証情報設定

```bash
export AWS_PROFILE=ai-hackathon
export AWS_REGION=ap-northeast-1

# 認証確認
aws sts get-caller-identity
```

---

## Step 2: ローカルテスト

### 2.1 基本テスト

```bash
cd agents

# テストスクリプト実行
python test_panel_strands.py
```

期待される出力:
```
🧪 Starting Strands Panel Discussion Tests

[Test 1/2] Basic Panel Discussion
============================================================
🎭 Starting Panel Discussion: JP
============================================================

✅ Initialized 6 agents with model: us.amazon.nova-pro-v1:0
🎙️  Moderator: Introducing...
📊 Collecting expert analyses...
   News Analyst...
   Weather Analyst...
   ...

============================================================
✅ Discussion Complete: NEUTRAL (55.0/100)
============================================================

[Test 2/2] AgentCore Wrapper
Success: True
Final Mood: neutral (55.0/100)

============================================================
✅ All tests completed successfully!
============================================================
```

### 2.2 個別エージェントテスト

```python
from strands import Agent
from strands.models import BedrockModel

agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-pro-v1:0"),
    system_prompt="You are a helpful assistant"
)

response = agent("Tell me about Japan")
print(response)
```

---

## Step 3: Bedrock AgentCore へデプロイ

### 3.1 AgentCore プロジェクト作成

```bash
# AgentCore CLIインストール（初回のみ）
pip install bedrock-agentcore-cli

# プロジェクト初期化
cd hackthon-agents/agents
agentcore init --name panel-discussion-app
```

### 3.2 設定ファイル（`agentcore.yaml`）

```yaml
name: panel-discussion-app
description: AI Expert Panel Discussion System
runtime: python3.12
entrypoint: panel_app:app

resources:
  memory: 2048
  timeout: 300

environment:
  MODEL_ID: us.amazon.nova-pro-v1:0
  REGION: ap-northeast-1

iam:
  policies:
    - arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

### 3.3 デプロイ実行

```bash
# デプロイ
agentcore deploy --profile ai-hackathon

# 出力例:
# ✅ Building agent...
# ✅ Uploading to S3...
# ✅ Creating AgentCore resource...
# ✅ Deployed successfully!
# Agent URL: https://xxxxx.agentcore.bedrock.aws.dev
```

---

## Step 4: デプロイ後のテスト

### 4.1 AgentCore API経由でテスト

```bash
# エンドポイント取得
AGENT_URL=$(agentcore get-url --name panel-discussion-app)

# テストリクエスト
curl -X POST "$AGENT_URL/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "country_code": "JP",
    "topic": "Current mood analysis",
    "country_data": {
      "news": [
        {"title": "Economic growth reported at 2.5%"}
      ],
      "weather": {
        "description": "Partly cloudy",
        "temp": 18
      }
    }
  }'
```

期待されるレスポンス:
```json
{
  "success": true,
  "data": {
    "country_code": "JP",
    "final_mood": "neutral",
    "final_score": 55.0,
    "introduction": "...",
    "conclusion": "...",
    "metadata": {
      "timestamp": "2025-10-02T...",
      "total_turns": 25,
      "model_id": "us.amazon.nova-pro-v1:0"
    }
  }
}
```

### 4.2 Health Check

```bash
curl -X POST "$AGENT_URL/invocations" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "health_check"
  }'
```

---

## Step 5: Django Backend統合

### 5.1 環境変数設定

`hackthon-backend/.env`:
```bash
# AgentCore endpoint
AGENTCORE_PANEL_URL=https://xxxxx.agentcore.bedrock.aws.dev

# AWS credentials (IAM role推奨)
AWS_REGION=ap-northeast-1
```

### 5.2 Django Service作成

```python
# hackthon-backend/apps/insights/services/agentcore_panel_service.py

import requests
import os

class AgentCorePanelService:
    def __init__(self):
        self.agent_url = os.getenv('AGENTCORE_PANEL_URL')

    def run_discussion(self, country_code: str, topic: str, country_data: dict):
        """Run panel discussion via AgentCore"""
        response = requests.post(
            f"{self.agent_url}/invocations",
            json={
                'country_code': country_code,
                'topic': topic,
                'country_data': country_data
            },
            timeout=300
        )
        return response.json()
```

---

## トラブルシューティング

### エラー: "Module 'strands' not found"

```bash
pip install --upgrade strands-agents strands-agents-tools
```

### エラー: "Bedrock model access denied"

```bash
# Bedrockモデルアクセスを有効化
aws bedrock put-model-invocation-logging-configuration \
  --model-id us.amazon.nova-pro-v1:0 \
  --region ap-northeast-1
```

### デプロイが遅い

```bash
# ビルド最適化
# agentcore.yaml に追加:
build:
  exclude:
    - "*.pyc"
    - "__pycache__"
    - "tests/"
```

### メモリ不足エラー

```yaml
# agentcore.yaml で増量
resources:
  memory: 4096  # 2048 → 4096
  timeout: 600  # 300 → 600
```

---

## コスト見積もり

### Bedrock AgentCore 料金

- **リクエスト料金**: $0.003/1K tokens
- **実行時間料金**: $0.0001/秒 (2GB memory)
- **ストレージ**: $0.023/GB-month

### 月額見積もり（小規模）

- 1000リクエスト/日 × 30日 = 30,000リクエスト
- 平均2K tokens/リクエスト = 60M tokens
- 平均実行時間: 30秒/リクエスト

**月額: ~$200**

### コスト削減Tips

1. **キャッシング**: 同じ国の結果を30分キャッシュ
2. **バッチ処理**: 複数国を一度に処理
3. **モデル選択**: Nova Micro (~10x安い) で開発/テスト

---

## 比較: 旧実装 vs 新実装

| 項目 | 旧実装 (boto3) | 新実装 (Strands + Browser) |
|------|----------------|---------------------------|
| コード行数 | ~400行 | ~250行 |
| データ収集 | APIキー必要 | Browser自動収集 |
| セットアップ | IAM役割管理必要 | AgentCoreが自動管理 |
| エラーハンドリング | 手動実装 | SDK内蔵 |
| セッション管理 | カスタム実装 | SessionManager自動 |
| ストリーミング | 手動パース | 自動対応 |
| デプロイ | 手動設定 | 1コマンド |
| スケーリング | 手動設定 | 自動スケール |
| モニタリング | CloudWatch手動設定 | AgentCore内蔵 |

---

## Next Steps

1. ✅ ローカルテスト完了
2. ✅ AgentCoreデプロイ完了
3. ⬜ Django Backend統合
4. ⬜ Knowledge Base接続（RAG）
5. ⬜ 本番環境デプロイ

---

## 参考リンク

- [Strands Agents Documentation](https://docs.strandsagents.ai)
- [Bedrock AgentCore SDK](https://github.com/aws/bedrock-agentcore-sdk-python)
- [Bedrock AgentCore User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)

完了！🎉
