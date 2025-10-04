# AI Expert Panel with Strands Agents & AgentCore Browser

AWS Bedrock AgentCore を使った AI 専門家パネルディスカッションシステム。

## 🎯 主な機能

1. **マルチエージェント パネルディスカッション**
   - モデレーター、ニュース分析家、天気分析家、データサイエンティスト、文化専門家、占い師
   - 6人のエージェントが議論・投票して最終的な国のムード（Happy/Neutral/Sad）を決定

2. **AgentCore Browser による自動データ収集**
   - ニュースサイトから最新記事を自動スクレイピング
   - 天気情報をリアルタイム取得
   - センチメント分析・ムード影響度計算

3. **AWS Bedrock AgentCore デプロイ**
   - Strands Agents SDK による簡潔な実装
   - 1コマンドで本番環境へデプロイ
   - 自動スケーリング・モニタリング

---

## 📁 プロジェクト構成

```
hackthon-agents/
├── agents/
│   ├── agent_configs.py                # エージェント設定
│   ├── panel_discussion_strands.py     # Panel discussion (Strands)
│   ├── browser_collectors.py           # AgentCore Browser data collection
│   ├── panel_app.py                    # AgentCore deployment wrapper
│   ├── test_panel_strands.py           # ローカルテスト
│   └── deploy_agents.py                # Bedrockエージェントデプロイ
│
├── requirements.txt                     # Python依存関係
├── README.md                            # このファイル
├── STRANDS_DEPLOYMENT.md                # Strandsデプロイガイド
└── BROWSER_DATA_COLLECTION.md           # Browser収集ガイド
```

---

## 🚀 クイックスタート

### 1. セットアップ

```bash
# リポジトリクローン
cd hackthon-agents

# 仮想環境作成
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# Playwrightインストール
playwright install

# AWS認証設定
export AWS_PROFILE=ai-hackathon
export AWS_REGION=ap-northeast-1
```

### 2. ローカルテスト

```bash
cd agents

# データ収集テスト
python -c "
from browser_collectors import BrowserDataCollectionService
service = BrowserDataCollectionService()
data = service.collect_country_data('JP', max_news=5)
print(f'✅ Collected {len(data[\"news\"])} articles')
"

# Panel Discussionテスト
python test_panel_strands.py
```

### 3. デプロイ

```bash
# AgentCore にデプロイ
cd agents
agentcore init --name panel-discussion-app
agentcore deploy --profile ai-hackathon
```

---

## 📖 ドキュメント

- **[STRANDS_DEPLOYMENT.md](./STRANDS_DEPLOYMENT.md)** - Strands Agents + AgentCore デプロイガイド
- **[BROWSER_DATA_COLLECTION.md](./BROWSER_DATA_COLLECTION.md)** - AgentCore Browser データ収集ガイド

---

## 💡 使用例

### シンプルな実行

```python
from panel_app import run_panel_discussion

# 日本のムード分析（データ自動収集）
response = run_panel_discussion({
    'country_code': 'JP',
    'topic': 'Current mood analysis',
    'auto_collect_data': True  # Browser収集を自動実行
})

print(f"Final Mood: {response['data']['final_mood']}")
print(f"Score: {response['data']['final_score']}/100")
print(f"Conclusion: {response['data']['conclusion']}")
```

### カスタムデータで実行

```python
from browser_collectors import BrowserDataCollectionService
from panel_discussion_strands import create_panel_discussion_strands
from agent_configs import AGENTS

# データ収集
service = BrowserDataCollectionService()
country_data = service.collect_country_data('US', max_news=10, city='New York')

# Panel Discussion
panel = create_panel_discussion_strands(AGENTS)
result = panel.start_discussion(
    country_code='US',
    topic='Current mood in New York',
    country_data=country_data
)

# 結果表示
print(f"\n🎭 Discussion Complete!")
print(f"Mood: {result.final_mood} ({result.final_score:.1f}/100)")
```

---

## 🏗️ アーキテクチャ

```
User Request
     ↓
Panel App (BedrockAgentCore)
     ↓
 ┌───┴───┐
 │       │
Browser  Panel Discussion
Collection (Strands Agents)
 │             ↓
 ├─ News    6 Expert Agents
 └─ Weather    ↓
            Voting
              ↓
        Final Mood
```

---

## 🔧 技術スタック

- **Strands Agents** - Agent SDK
- **AWS Bedrock AgentCore** - Managed platform
- **AgentCore Browser** - Web scraping
- **Claude 3.7 Sonnet** - LLM
- **Playwright** - Browser automation
- **Python 3.12+**

---

## ✨ 主な改善点

| Before (旧実装) | After (新実装) |
|----------------|---------------|
| boto3（~400行） | Strands（~250行） |
| APIキー管理必要 | Browser自動収集 |
| 手動エラーハンドリング | SDK内蔵 |
| 手動デプロイ | 1コマンド |

---

Made with ❤️ using AWS Bedrock AgentCore & Strands Agents
