# Panel Discussion Agent - デプロイメントガイド

## 概要

このエージェントは、6人のエキスパートが国の気分を分析するパネルディスカッションを実行します。
結果はDynamoDBに保存され、Bedrock Knowledge Baseに自動同期してRAG化されます。

## アーキテクチャ

- **Bedrock AgentCore**: エージェントのホスティング環境
- **Strands Agents**: エージェントフレームワーク
- **DynamoDB**: メタデータストレージ
- **S3**: フルトランスクリプトストレージ
- **Bedrock Knowledge Base**: RAG検索用ナレッジベース
- **Playwright Browser**: ニュース・天気データ収集

## 前提条件

### 1. AWS CLIとBedrock AgentCore SDKのインストール

```bash
# AWS CLI
brew install awscli

# Bedrock AgentCore SDK
pip install bedrock-agentcore
```

### 2. AWS認証情報の設定

```bash
aws configure
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region name: us-west-2
# Default output format: json
```

### 3. 必要なAWSリソースの作成

#### DynamoDBテーブル

```bash
aws dynamodb create-table \
  --table-name PanelDiscussions \
  --attribute-definitions \
    AttributeName=discussion_id,AttributeType=S \
    AttributeName=country_code,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=discussion_id,KeyType=HASH \
  --global-secondary-indexes \
    IndexName=CountryTimestampIndex,KeySchema=[{AttributeName=country_code,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5} \
  --billing-mode PAY_PER_REQUEST \
  --region us-west-2
```

#### S3バケット

```bash
# 討論結果用バケット
aws s3 mb s3://hackthon-panel-discussions --region us-west-2

# ナレッジベース用バケット
aws s3 mb s3://hackthon-knowledge-base --region us-west-2
```

#### Bedrock Knowledge Base

```bash
# Knowledge Base作成（コンソールから実行を推奨）
# 1. Bedrock コンソールへアクセス
# 2. Knowledge bases -> Create knowledge base
# 3. S3データソースとして s3://hackthon-knowledge-base を設定
# 4. 埋め込みモデル: amazon.titan-embed-text-v2:0
# 5. Knowledge Base IDとData Source IDをメモ
```

## デプロイ手順

### 1. 環境変数の設定

```bash
cd hackthon-agents/agents

# .envファイルを作成
cat > .env << EOF
AWS_REGION=us-west-2
PANEL_RESULTS_BUCKET=hackthon-panel-discussions
PANEL_RESULTS_TABLE=PanelDiscussions
KB_S3_BUCKET=hackthon-knowledge-base
KNOWLEDGE_BASE_ID=your-kb-id-here
KB_DATA_SOURCE_ID=your-data-source-id-here
EOF
```

### 2. Bedrock AgentCoreへデプロイ

```bash
# 初期化（初回のみ）
bedrock-agentcore init

# ビルドとデプロイ
bedrock-agentcore deploy
```

### 3. デプロイ後の確認

```bash
# エージェント情報を確認
bedrock-agentcore info

# ログを確認
bedrock-agentcore logs
```

## エージェントの使い方

### 1. パネルディスカッションを実行

```bash
bedrock-agentcore invoke run_panel_discussion \
  --payload '{
    "country_code": "JP",
    "topic": "Current mood analysis",
    "auto_collect_data": true,
    "sync_to_kb": true
  }'
```

### 2. データ収集のみ実行

```bash
bedrock-agentcore invoke collect_data_only \
  --payload '{
    "country_code": "US",
    "max_news": 10
  }'
```

### 3. ディスカッション一覧を取得

```bash
bedrock-agentcore invoke list_discussions \
  --payload '{
    "country_code": "JP",
    "limit": 10
  }'
```

### 4. 特定のディスカッションを取得

```bash
bedrock-agentcore invoke get_discussion \
  --payload '{
    "discussion_id": "JP_20251003_150000_abc123"
  }'
```

## Pythonから呼び出す

```python
import boto3
from bedrock_agentcore import BedrockAgentCoreClient

# クライアント初期化
client = BedrockAgentCoreClient(
    agent_arn="arn:aws:bedrock-agentcore:us-west-2:023487747239:runtime/panel_discussion_agent-xxx"
)

# パネルディスカッション実行
response = client.invoke(
    entrypoint="run_panel_discussion",
    payload={
        "country_code": "JP",
        "topic": "Current mood analysis",
        "auto_collect_data": True,
        "sync_to_kb": True
    }
)

print(response['data'])
```

## ナレッジベースからRAG検索

```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

# RAG検索
response = bedrock_agent.retrieve(
    knowledgeBaseId='your-kb-id',
    retrievalQuery={
        'text': 'What was Japan\'s mood on October 3rd, 2025?'
    }
)

for result in response['retrievalResults']:
    print(result['content']['text'])
```

## トラブルシューティング

### デプロイエラー

```bash
# ログを確認
bedrock-agentcore logs --tail 100

# ロールバック
bedrock-agentcore rollback
```

### DynamoDBアクセスエラー

```bash
# IAMロールに以下のポリシーを追加
aws iam attach-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-xxx \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess
```

### S3アクセスエラー

```bash
# IAMロールに以下のポリシーを追加
aws iam attach-role-policy \
  --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-xxx \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

## モニタリング

### CloudWatchログ

```bash
# ログストリームを確認
aws logs describe-log-streams \
  --log-group-name /aws/bedrock-agentcore/panel_discussion_agent \
  --region us-west-2
```

### CloudWatchメトリクス

```bash
# 起動回数を確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/BedrockAgentCore \
  --metric-name Invocations \
  --dimensions Name=AgentName,Value=panel_discussion_agent \
  --start-time 2025-10-01T00:00:00Z \
  --end-time 2025-10-03T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region us-west-2
```

## コスト最適化

### 1. DynamoDBをオンデマンドに設定済み
- 使用した分だけ課金

### 2. S3ライフサイクルポリシー設定

```bash
# 90日後にGlacierに移動
aws s3api put-bucket-lifecycle-configuration \
  --bucket hackthon-panel-discussions \
  --lifecycle-configuration file://lifecycle.json
```

lifecycle.json:
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldDiscussions",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### 3. Knowledge Base自動更新を手動トリガーに変更

環境変数で制御:
```bash
# ナレッジベース同期を無効化（手動で実行）
export SYNC_TO_KB=false
```

## アップデート

```bash
# コード変更後、再デプロイ
bedrock-agentcore deploy

# 環境変数の更新
bedrock-agentcore update-env \
  --env-file .env
```

## アンデプロイ

```bash
# エージェントを削除
bedrock-agentcore destroy

# AWSリソースを削除
aws dynamodb delete-table --table-name PanelDiscussions --region us-west-2
aws s3 rb s3://hackthon-panel-discussions --force --region us-west-2
aws s3 rb s3://hackthon-knowledge-base --force --region us-west-2
```

## 参考リンク

- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents Documentation](https://github.com/anthropics/strands)
- [Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
