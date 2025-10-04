# AgentCore Browser Data Collection Guide

## 概要

**AWS Bedrock AgentCore Browser** を使ったニュース・天気データ収集の実装ガイド。

## アーキテクチャ

```
Panel Discussion Request
         ↓
Browser Data Collection Service
         ↓
    ┌─────────┴─────────┐
    │                   │
AgentCore Browser   AgentCore Browser
(News Collector)    (Weather Collector)
    │                   │
    ├─ Navigate to      ├─ Navigate to
    │  news sites       │  weather sites
    ├─ Extract data     ├─ Extract data
    ├─ Parse to JSON    ├─ Parse to JSON
    └─ Return          └─ Return
         │                   │
         └─────────┬─────────┘
                   ↓
         Country Data (news + weather)
                   ↓
         Panel Discussion (Strands Agents)
```

## 主な機能

### 1. AgentCore Browser による自動データ収集
- **ニュース**: 各国の主要ニュースサイトから最新記事を自動収集
- **天気**: Weather.com などから現在の天気情報を取得
- **センチメント分析**: ニュース記事の感情傾向を自動推定
- **ムード影響度**: 天気が人々のムードに与える影響を計算

### 2. フォールバック機能
- Browser収集失敗時は自動的にモックデータにフォールバック
- 開発・テスト環境でも動作保証

---

## ファイル構成

```
hackthon-agents/agents/
├── browser_collectors.py           # AgentCore Browser collectors ✨
│   ├── BrowserNewsCollector       # ニュース収集
│   ├── BrowserWeatherCollector    # 天気収集
│   └── BrowserDataCollectionService
│
├── panel_app.py                    # 統合済み
├── panel_discussion_strands.py     # Panel discussion
└── agent_configs.py                # Agent configurations
```

---

## Step 1: セットアップ

### 1.1 依存関係インストール

```bash
cd hackthon-agents

# 依存関係インストール
pip install -r requirements.txt

# Playwrightブラウザインストール
playwright install
```

### 1.2 AWS認証情報

```bash
export AWS_PROFILE=ai-hackathon
export AWS_REGION=ap-northeast-1

# AgentCore Browser有効化確認
aws bedrock-agentcore list-browsers --region ap-northeast-1
```

---

## Step 2: ローカルテスト

### 2.1 ニュース収集テスト

```python
from browser_collectors import BrowserNewsCollector

collector = BrowserNewsCollector(region='ap-northeast-1')

# 日本のニュース収集
news = collector.get_top_headlines('JP', max_results=5)

for article in news:
    print(f"Title: {article['title']}")
    print(f"Sentiment: {article['sentiment']}")
    print(f"---")
```

期待される出力:
```
🌐 Collecting news for JP using AgentCore Browser...
✅ Collected 5 news articles for JP

Title: Japan's economy shows steady growth in Q4
Sentiment: 0.3
---
Title: New tech startups receive record funding in Tokyo
Sentiment: 0.4
---
```

### 2.2 天気収集テスト

```python
from browser_collectors import BrowserWeatherCollector

collector = BrowserWeatherCollector(region='ap-northeast-1')

# 東京の天気
weather = collector.get_weather('JP', city='Tokyo')

print(f"City: {weather['city']}")
print(f"Temp: {weather['temp']}°C")
print(f"Condition: {weather['description']}")
print(f"Mood Impact: {weather['mood_impact']}")
```

### 2.3 統合テスト

```python
from browser_collectors import BrowserDataCollectionService

service = BrowserDataCollectionService(region='ap-northeast-1')

# 完全なデータ収集
data = service.collect_country_data('JP', max_news=10)

print(f"Country: {data['country_code']}")
print(f"News Count: {data['statistics']['news_count']}")
print(f"Avg Sentiment: {data['statistics']['avg_news_sentiment']}")
print(f"Weather Impact: {data['statistics']['weather_mood_impact']}")
```

---

## Step 3: Panel Discussionとの統合

### 3.1 自動データ収集を使用

```python
from panel_app import run_panel_discussion

# データ自動収集＋パネルディスカッション
response = run_panel_discussion({
    'country_code': 'JP',
    'topic': 'Current mood analysis',
    'auto_collect_data': True  # ← Browser収集を自動実行
})

print(response['data']['final_mood'])
print(response['data']['final_score'])
```

### 3.2 手動データ収集

```python
from browser_collectors import BrowserDataCollectionService
from panel_discussion_strands import create_panel_discussion_strands
from agent_configs import AGENTS

# Step 1: データ収集
service = BrowserDataCollectionService()
country_data = service.collect_country_data('JP')

# Step 2: Panel Discussion
panel = create_panel_discussion_strands(AGENTS)
result = panel.start_discussion(
    country_code='JP',
    topic='Current mood analysis',
    country_data=country_data
)
```

---

## Step 4: Browser動作の仕組み

### 4.1 AgentCore Browserとは

- **マネージド ブラウザ環境**: AWSが管理する安全なブラウザ実行環境
- **Strands統合**: Strands AgentからTool として使用可能
- **自動スケーリング**: 同時実行数に応じて自動拡張

### 4.2 データ収集の流れ

```python
# 1. Browser Agent初期化
agent = Agent(
    tools=[AgentCoreBrowser(region='ap-northeast-1').browser],
    model="us.anthropic.claude-3-7-sonnet-20250219-v1:0"
)

# 2. プロンプトでブラウザ操作指示
prompt = """
Navigate to https://news.site.com
Extract top 5 headlines with titles and descriptions
Return as JSON array
"""

# 3. Agent実行（自動でブラウザ起動→操作→データ抽出）
response = agent(prompt)

# 4. JSON解析
articles = json.loads(response)
```

### 4.3 センチメント分析

ニュース記事のセンチメントは以下の方法で推定:

1. **Browser Agent が記事本文を分析**
2. **ポジティブ/ネガティブワードを検出**
3. **-1（ネガティブ）〜 +1（ポジティブ）のスコア算出**

例:
- "Economic growth" → +0.4
- "Market crash" → -0.5
- "Political debate" → 0.0

### 4.4 天気ムード影響度

天気がムードに与える影響度の計算:

```python
def _estimate_mood_impact(temp, description):
    score = 0.0

    # 温度影響
    if 18 <= temp <= 25:  # 快適
        score += 0.3
    elif temp < 5 or temp > 35:  # 極端
        score -= 0.3

    # 天候影響
    if 'clear' in description:
        score += 0.3
    elif 'rain' in description:
        score -= 0.2

    return score  # -1 to 1
```

---

## Step 5: トラブルシューティング

### エラー: "Browser session failed"

```bash
# AgentCore Browser有効確認
aws bedrock-agentcore list-browsers --region ap-northeast-1

# 出力:
# {
#   "items": [
#     {
#       "browserId": "aws.browser.v1",
#       "status": "AVAILABLE"
#     }
#   ]
# }
```

Browser が利用不可の場合:
```bash
# AgentCore Browserを有効化（初回のみ）
aws bedrock-agentcore create-browser \
  --browser-id aws.browser.v1 \
  --region ap-northeast-1
```

### エラー: "JSON parse failed"

Browser Agent の応答がJSON形式でない場合、プロンプトを改善:

```python
# ❌ 悪い例
prompt = "Get news from website"

# ✅ 良い例
prompt = """Navigate to website and extract news.

Return ONLY a JSON array with this exact format:
[
  {
    "title": "...",
    "description": "...",
    "sentiment": 0.5
  }
]

IMPORTANT: Return ONLY JSON, no additional text."""
```

### パフォーマンス問題

Browser起動は遅い（5-10秒）ため、並列実行推奨:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def collect_parallel():
    with ThreadPoolExecutor(max_workers=2) as executor:
        # ニュースと天気を並列収集
        news_future = executor.submit(
            news_collector.get_top_headlines, 'JP'
        )
        weather_future = executor.submit(
            weather_collector.get_weather, 'JP'
        )

        news = news_future.result()
        weather = weather_future.result()
```

### フォールバックモード

Browser失敗時は自動的にモックデータ使用:

```python
try:
    articles = self.agent(prompt)  # Browser収集
except Exception as e:
    print(f"⚠️  Browser failed, using mock data")
    articles = self._get_mock_news(country_code)  # フォールバック
```

---

## Step 6: 本番環境設定

### 6.1 環境変数

```bash
# .env
AWS_REGION=ap-northeast-1
AWS_PROFILE=ai-hackathon

# Browser設定
BROWSER_TIMEOUT=30000  # 30秒タイムアウト
BROWSER_MAX_RETRIES=3
```

### 6.2 コスト最適化

**AgentCore Browser 料金**:
- **セッション料金**: $0.10/分
- **データ転送**: $0.09/GB

**月額見積もり（小規模）**:
- 100国 × 1回/日 × 30日 = 3,000セッション
- 平均1分/セッション = 3,000分
- **月額: ~$300**

**コスト削減Tips**:
1. **キャッシング**: 同じ国のデータを30分キャッシュ
2. **バッチ処理**: 深夜に一括収集
3. **フォールバック**: Browser失敗時は既存データ使用

### 6.3 パフォーマンス最適化

```python
# キャッシュ実装例
import redis
from datetime import timedelta

cache = redis.Redis()

def get_cached_data(country_code):
    key = f"country_data:{country_code}"
    cached = cache.get(key)

    if cached:
        return json.loads(cached)

    # Browser収集
    data = service.collect_country_data(country_code)

    # 30分キャッシュ
    cache.setex(key, timedelta(minutes=30), json.dumps(data))
    return data
```

---

## 比較: API vs Browser収集

| 項目 | API収集 (旧) | Browser収集 (新) |
|------|-------------|-----------------|
| データソース | NewsAPI, OpenWeatherMap | 任意のWebサイト |
| API制限 | あり（100req/日など） | なし |
| リアルタイム性 | API更新頻度依存 | 常に最新 |
| カスタマイズ | API仕様に制約 | 自由度高い |
| コスト | API料金 | Browser時間課金 |
| セットアップ | APIキー必要 | AWS認証のみ |
| 信頼性 | API依存 | Browser依存 |

**推奨**:
- **開発・テスト**: モックデータ（無料）
- **小規模本番**: Browser収集（柔軟）
- **大規模本番**: Browser + キャッシュ（コスト効率）

---

## 完了チェックリスト

- [ ] AgentCore Browser有効化
- [ ] Playwright インストール
- [ ] ニュース収集テスト成功
- [ ] 天気収集テスト成功
- [ ] Panel Discussion統合テスト
- [ ] フォールバック動作確認
- [ ] 本番環境変数設定
- [ ] キャッシュ実装（オプション）

完了！🎉

---

## 参考リンク

- [AgentCore Browser Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser.html)
- [Strands Browser Tool](https://docs.strandsagents.ai/tools/browser)
- [Playwright Documentation](https://playwright.dev/python/)
