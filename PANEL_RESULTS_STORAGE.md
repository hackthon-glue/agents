# Panel Discussion Results Storage Guide

## 概要

パネルディスカッションの結果をS3に保存し、Djangoバックエンドから参照できるようにする実装。

## アーキテクチャ

```
Panel Discussion
      ↓
   結果生成
      ↓
  Storage Module
      ↓
   S3保存
      ↓
Django Backend
      ↓
  Frontend表示
```

---

## ファイル構成

### hackthon-agents/agents/
```
├── storage.py                          # S3ストレージモジュール ✨
├── panel_app.py                        # 自動保存機能統合 ✨
```

### hackthon-backend/apps/insights/
```
├── services/
│   └── panel_discussion_service.py     # Django service ✨
├── views/
│   └── panel_discussion_views.py       # Django views ✨
└── urls_panel.py                        # URL routing ✨
```

---

## Step 1: S3バケット作成

### 1.1 バケット作成

```bash
export AWS_PROFILE=ai-hackathon
export REGION=ap-northeast-1
export BUCKET_NAME=hackthon-panel-discussions

# バケット作成
aws s3 mb s3://$BUCKET_NAME --region $REGION

# CORS設定（Frontend からアクセスする場合）
cat > cors.json <<EOF
{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
EOF

aws s3api put-bucket-cors \
  --bucket $BUCKET_NAME \
  --cors-configuration file://cors.json
```

### 1.2 ライフサイクルポリシー（オプション）

古いディスカッションを自動削除:

```bash
cat > lifecycle.json <<EOF
{
  "Rules": [
    {
      "Id": "DeleteOldDiscussions",
      "Status": "Enabled",
      "Prefix": "discussions/",
      "Expiration": {
        "Days": 90
      }
    }
  ]
}
EOF

aws s3api put-bucket-lifecycle-configuration \
  --bucket $BUCKET_NAME \
  --lifecycle-configuration file://lifecycle.json
```

---

## Step 2: 環境変数設定

### hackthon-agents

`.env`:
```bash
AWS_REGION=ap-northeast-1
PANEL_RESULTS_BUCKET=hackthon-panel-discussions
```

### hackthon-backend

`hackthon-backend/.env`:
```bash
PANEL_RESULTS_BUCKET=hackthon-panel-discussions
AWS_REGION=ap-northeast-1
```

---

## Step 3: Django URL設定

`hackthon-backend/config/urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... existing patterns
    path('api/insights/panel/', include('apps.insights.urls_panel')),
]
```

---

## Step 4: 使用方法

### 4.1 パネルディスカッション実行（自動保存）

```python
from panel_app import run_panel_discussion

response = run_panel_discussion({
    'country_code': 'JP',
    'topic': 'Current mood analysis',
    'auto_collect_data': True
})

# 自動的にS3に保存される
discussion_id = response['data']['discussion_id']
print(f"Saved as: {discussion_id}")
```

### 4.2 Django APIからディスカッション一覧取得

```bash
# 全ディスカッション
curl http://localhost:8000/api/insights/panel/discussions/

# 日本のディスカッションのみ
curl http://localhost:8000/api/insights/panel/discussions/?country_code=JP&limit=10
```

レスポンス例:
```json
{
  "success": true,
  "data": {
    "discussions": [
      {
        "discussion_id": "JP_20251002_150000",
        "country_code": "JP",
        "timestamp": "2025-10-02T15:00:00",
        "final_mood": "neutral",
        "final_score": 55.3,
        "s3_key": "discussions/JP/2025/10/JP_20251002_150000.json"
      }
    ],
    "count": 1
  }
}
```

### 4.3 特定のディスカッション取得

```bash
curl http://localhost:8000/api/insights/panel/discussions/JP_20251002_150000/
```

レスポンス例:
```json
{
  "success": true,
  "data": {
    "country_code": "JP",
    "topic": "Current mood analysis",
    "introduction": "Welcome to our panel...",
    "expert_analyses": {
      "news_analyst": "Recent headlines show...",
      "weather_analyst": "Current weather conditions...",
      ...
    },
    "debates": [...],
    "votes": [
      {
        "agent_role": "news_analyst",
        "mood": "neutral",
        "confidence": 70,
        "reasoning": "Mixed signals from news..."
      }
    ],
    "final_mood": "neutral",
    "final_score": 55.3,
    "conclusion": "In summary...",
    "full_transcript": [...]
  }
}
```

### 4.4 サマリーのみ取得（軽量）

```bash
curl http://localhost:8000/api/insights/panel/discussions/JP_20251002_150000/summary/
```

### 4.5 国別履歴・トレンド

```bash
curl http://localhost:8000/api/insights/panel/history/JP/?limit=10
```

レスポンス例:
```json
{
  "success": true,
  "data": {
    "country_code": "JP",
    "discussions": [...],
    "trend": {
      "score_change": 2.5,
      "mood_change": "improving",
      "direction": "up"
    },
    "latest": {
      "discussion_id": "JP_20251002_150000",
      "final_mood": "neutral",
      "final_score": 55.3
    }
  }
}
```

---

## Step 5: Frontend統合

### React/Next.js コンポーネント例

```typescript
// components/PanelDiscussionHistory.tsx
'use client';

import { useState, useEffect } from 'react';

interface Discussion {
  discussion_id: string;
  country_code: string;
  timestamp: string;
  final_mood: string;
  final_score: number;
}

export default function PanelDiscussionHistory({ countryCode }: { countryCode: string }) {
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDiscussions() {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/insights/panel/discussions/?country_code=${countryCode}`
      );
      const data = await response.json();
      if (data.success) {
        setDiscussions(data.data.discussions);
      }
      setLoading(false);
    }

    fetchDiscussions();
  }, [countryCode]);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="panel-history">
      <h2>Panel Discussion History - {countryCode}</h2>
      {discussions.map((disc) => (
        <div key={disc.discussion_id} className="discussion-item">
          <div className="mood-badge mood-{disc.final_mood}">
            {disc.final_mood} ({disc.final_score})
          </div>
          <div className="timestamp">
            {new Date(disc.timestamp).toLocaleString()}
          </div>
          <a href={`/discussions/${disc.discussion_id}`}>
            View Details
          </a>
        </div>
      ))}
    </div>
  );
}
```

### ディスカッション詳細ページ

```typescript
// app/discussions/[id]/page.tsx
export default async function DiscussionDetailPage({
  params
}: {
  params: { id: string }
}) {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_API_URL}/api/insights/panel/discussions/${params.id}/`,
    { cache: 'no-store' }
  );

  const data = await res.json();

  if (!data.success) {
    return <div>Discussion not found</div>;
  }

  const discussion = data.data;

  return (
    <div className="discussion-detail">
      <h1>{discussion.country_code} - {discussion.topic}</h1>

      <div className="result">
        <span className={`mood-${discussion.final_mood}`}>
          {discussion.final_mood.toUpperCase()}
        </span>
        <span className="score">{discussion.final_score}/100</span>
      </div>

      <section className="introduction">
        <h2>Introduction</h2>
        <p>{discussion.introduction}</p>
      </section>

      <section className="expert-analyses">
        <h2>Expert Analyses</h2>
        {Object.entries(discussion.expert_analyses).map(([role, analysis]) => (
          <div key={role} className="expert-analysis">
            <h3>{role.replace('_', ' ').toUpperCase()}</h3>
            <p>{analysis as string}</p>
          </div>
        ))}
      </section>

      <section className="votes">
        <h2>Voting Results</h2>
        {discussion.votes.map((vote: any, idx: number) => (
          <div key={idx} className="vote">
            <strong>{vote.agent_role}</strong>: {vote.mood}
            ({vote.confidence}% confident)
            <p>{vote.reasoning}</p>
          </div>
        ))}
      </section>

      <section className="conclusion">
        <h2>Conclusion</h2>
        <p>{discussion.conclusion}</p>
      </section>
    </div>
  );
}
```

---

## データ構造

### S3保存形式

**Path**: `s3://hackthon-panel-discussions/discussions/JP/2025/10/JP_20251002_150000.json`

**Content**:
```json
{
  "country_code": "JP",
  "topic": "Current mood analysis",
  "introduction": "...",
  "expert_analyses": {
    "news_analyst": "...",
    "weather_analyst": "...",
    "data_scientist": "...",
    "cultural_expert": "...",
    "fortune_teller": "..."
  },
  "debates": [
    {
      "news_analyst": "...",
      "weather_analyst": "...",
      ...
    }
  ],
  "votes": [
    {
      "agent_role": "news_analyst",
      "mood": "neutral",
      "confidence": 70,
      "reasoning": "..."
    }
  ],
  "final_mood": "neutral",
  "final_score": 55.3,
  "conclusion": "...",
  "full_transcript": [...],
  "metadata": {
    "timestamp": "2025-10-02T15:00:00",
    "total_turns": 25,
    "debate_rounds": 2,
    "model_id": "us.amazon.nova-pro-v1:0"
  }
}
```

---

## キャッシング戦略

Django側でキャッシュを活用してS3アクセスを削減:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# キャッシュ期間
# - ディスカッション一覧: 5分
# - ディスカッション詳細: 1時間
```

---

## コスト見積もり

### S3ストレージ

- **ストレージ**: $0.023/GB-month
- **平均ディスカッションサイズ**: ~50KB
- **1000ディスカッション/月**: 50MB = $0.001/月

### S3リクエスト

- **GET**: $0.0004/1000リクエスト
- **PUT**: $0.005/1000リクエスト
- **10,000 GET + 100 PUT/月**: ~$0.005/月

### 合計

**月額: ~$0.01** (ほぼ無料)

キャッシュ活用でさらにコスト削減可能。

---

## トラブルシューティング

### S3アクセス権限エラー

```bash
# IAMポリシー確認
aws iam get-user-policy \
  --user-name your-user \
  --policy-name S3Access

# 必要なポリシー
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::hackthon-panel-discussions",
        "arn:aws:s3:::hackthon-panel-discussions/*"
      ]
    }
  ]
}
```

### Django でディスカッションが取得できない

```bash
# Django shell でテスト
python manage.py shell

from apps.insights.services.panel_discussion_service import PanelDiscussionService
service = PanelDiscussionService()
discussions = service.list_discussions()
print(discussions)
```

### キャッシュクリア

```bash
# Redis キャッシュクリア
redis-cli FLUSHDB

# Django キャッシュクリア
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

---

## 完了チェックリスト

- [ ] S3バケット作成
- [ ] 環境変数設定（agents & backend）
- [ ] Django URL設定追加
- [ ] パネルディスカッション実行・保存確認
- [ ] Django APIでディスカッション取得確認
- [ ] Frontend表示確認
- [ ] キャッシング動作確認

完了！🎉

---

## 参考

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [Django Cache Framework](https://docs.djangoproject.com/en/stable/topics/cache/)
- [Next.js Data Fetching](https://nextjs.org/docs/app/building-your-application/data-fetching)
