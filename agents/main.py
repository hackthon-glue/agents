"""
Panel Discussion Agent - Bedrock AgentCore Implementation
複数のエキスパートエージェントが議論を行い、国の気分を分析します
結果はDBに保存し、ナレッジベースにRAG化します
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from panel_discussion_strands_v2 import create_panel_discussion_strands_v2
from browser_collectors import BrowserDataCollectionService
from rds_storage import create_rds_storage
from agent_configs import AGENTS
import os
import json
from dataclasses import asdict


# アプリケーションを初期化
app = BedrockAgentCoreApp()

# パネルディスカッションシステムを初期化（V2 - improved format）
panel = create_panel_discussion_strands_v2(
    model_id="amazon.nova-pro-v1:0"
)

# ブラウザベースのデータ収集サービスを初期化
data_service = BrowserDataCollectionService(
    region=os.getenv('AWS_REGION', 'us-west-2')
)

# RDSストレージを初期化
storage = create_rds_storage(
    db_host=os.getenv('DB_HOST'),
    db_user=os.getenv('DB_USER'),
    db_password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'glue'),
    db_port=int(os.getenv('DB_PORT', '5432')),
    s3_bucket=os.getenv('KB_S3_BUCKET', 'hackthon-knowledge-base'),
    region=os.getenv('AWS_REGION', 'us-west-2')
)


@app.entrypoint
def run_panel_discussion(request: dict):
    """
    パネルディスカッションを実行し、結果をDBとナレッジベースに保存

    Expected request:
    {
        "country_code": "JP",
        "topic": "Current mood analysis",
        "country_data": {...},  # Optional
        "auto_collect_data": true,
        "sync_to_kb": true  # ナレッジベースに同期するか
    }
    """
    try:
        # パラメータ抽出
        country_code = request.get('country_code', 'US')
        topic = request.get('topic', 'Current mood analysis')
        country_data = request.get('country_data')
        auto_collect = request.get('auto_collect_data', True)
        sync_to_kb = request.get('sync_to_kb', True)

        # データ自動収集
        if not country_data and auto_collect:
            print(f"📊 データ収集中: {country_code}...")
            country_data = data_service.collect_country_data(
                country_code=country_code,
                max_news=10
            )
            
            # Save raw news and weather data to RDS and S3
            print(f"💾 保存中: ニュースと天気データ...")
            data_save_result = storage.save_country_data(country_data)
            print(f"✅ データ保存完了: News={data_save_result['news_saved']}, Weather={data_save_result['weather_saved']}")

        # パネルディスカッション実行
        print(f"🎭 パネルディスカッション開始: {country_code}")
        result = panel.start_discussion(
            country_code=country_code,
            topic=topic,
            country_data=country_data
        )

        # RDSに保存（S3 Knowledge Base用ファイルも自動生成）
        discussion_id = storage.save_panel_result(result, country_code)
        print(f"💾 RDSに保存: {discussion_id}")
        print(f"📚 S3 (Knowledge Base)にも保存完了")

        # 結果を返す
        result_data = asdict(result)
        result_data['discussion_id'] = discussion_id

        return {
            'success': True,
            'data': result_data,
            'message': f'パネルディスカッション完了: {discussion_id}'
        }

    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@app.entrypoint
def collect_data_only(request: dict):
    """
    データ収集のみ実行 (RDS + S3に保存)

    Expected request:
    {
        "country_code": "JP",
        "max_news": 10,
        "city": "Tokyo",
        "save_to_storage": true  # Optional, default: true
    }
    """
    try:
        country_code = request.get('country_code', 'US')
        max_news = request.get('max_news', 10)
        city = request.get('city')
        save_to_storage = request.get('save_to_storage', True)

        data = data_service.collect_country_data(
            country_code=country_code,
            max_news=max_news,
            city=city
        )
        
        # Save raw news and weather data to RDS and S3
        save_result = None
        if save_to_storage:
            print(f"💾 保存中: ニュースと天気データ...")
            save_result = storage.save_country_data(data)
            print(f"✅ データ保存完了: News={save_result['news_saved']}, Weather={save_result['weather_saved']}")

        return {
            'success': True,
            'data': data,
            'save_result': save_result
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.entrypoint
def list_discussions(request: dict):
    """
    パネルディスカッション一覧を取得

    Expected request:
    {
        "country_code": "JP",  # Optional
        "limit": 20
    }
    """
    try:
        country_code = request.get('country_code')
        limit = request.get('limit', 20)

        discussions = storage.list_discussions(country_code)[:limit]

        return {
            'success': True,
            'data': {
                'discussions': discussions,
                'count': len(discussions)
            }
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.entrypoint
def get_discussion(request: dict):
    """
    特定のディスカッションを取得

    Expected request:
    {
        "discussion_id": "JP_20251002_150000"
    }
    """
    try:
        discussion_id = request.get('discussion_id')

        if not discussion_id:
            return {
                'success': False,
                'error': 'discussion_id is required'
            }

        result = storage.get_panel_result(discussion_id)

        if not result:
            return {
                'success': False,
                'error': 'Discussion not found'
            }

        return {
            'success': True,
            'data': result
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.entrypoint
def rag_chat(request: dict):
    """
    RAGチャットエージェント - ナレッジベースから情報を検索して回答

    Expected request:
    {
        "query": "What's the current mood in Japan?",
        "country_code": "JP",  # Optional - filter by country
        "max_results": 5       # Optional - number of KB results
    }
    """
    try:
        import boto3
        from strands import Agent

        query = request.get('query', '')
        country_code = request.get('country_code')
        max_results = request.get('max_results', 5)

        if not query:
            return {
                'success': False,
                'error': 'query is required'
            }

        # Knowledge Base設定
        kb_id = os.getenv('KNOWLEDGE_BASE_ID')
        if not kb_id:
            return {
                'success': False,
                'error': 'KNOWLEDGE_BASE_ID not configured'
            }

        # Bedrock Agent Runtimeクライアント
        bedrock_agent = boto3.client(
            'bedrock-agent-runtime',
            region_name=os.getenv('AWS_REGION', 'us-west-2')
        )

        # Knowledge Baseから検索
        retrieval_config = {
            'vectorSearchConfiguration': {
                'numberOfResults': max_results
            }
        }

        # 国コードでフィルタリング
        if country_code:
            retrieval_config['vectorSearchConfiguration']['filter'] = {
                'equals': {
                    'key': 'country_code',
                    'value': country_code
                }
            }

        kb_response = bedrock_agent.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration=retrieval_config
        )

        # 検索結果を整形
        retrieved_docs = []
        for result in kb_response.get('retrievalResults', []):
            retrieved_docs.append({
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0),
                'metadata': result.get('metadata', {})
            })

        # RAGエージェントに渡して回答生成
        rag_agent = Agent(
            model="amazon.nova-pro-v1:0",
            system_prompt=AGENTS['rag_chat_agent']['instruction']
        )

        # コンテキストを構築
        context = "\n\n".join([
            f"【関連情報 {i+1}】(スコア: {doc['score']:.2f})\n{doc['content']}"
            for i, doc in enumerate(retrieved_docs)
        ])

        # プロンプト構築
        prompt = f"""以下の情報を参考にユーザーの質問に答えてください。

関連情報:
{context}

ユーザーの質問: {query}

上記の情報を基に、明確で役立つ回答を提供してください。情報が不足している場合は、その旨を伝えてください。"""

        # エージェント実行
        response = rag_agent(prompt)

        return {
            'success': True,
            'data': {
                'answer': response,
                'sources': retrieved_docs,
                'query': query
            }
        }

    except Exception as e:
        print(f"❌ RAGチャットエラー: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@app.entrypoint
def health_check(request: dict):
    """ヘルスチェック"""
    kb_configured = os.getenv('KNOWLEDGE_BASE_ID') is not None

    return {
        'status': 'healthy',
        'panel_initialized': panel is not None,
        'agents': list(panel.agents.keys()) if panel else [],
        'storage_enabled': storage is not None,
        'knowledge_base_enabled': kb_configured
    }


if __name__ == "__main__":
    print("🚀 Panel Discussion Agent 起動中")
    print(f"✅ エージェント数: {len(panel.agents)}")
    app.run()