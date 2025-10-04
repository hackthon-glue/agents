"""
Knowledge Base Sync Module
パネルディスカッション結果をBedrock Knowledge Baseに同期してRAG化
"""
import boto3
import json
from datetime import datetime
from typing import Dict, Optional
from dataclasses import asdict
import os


class KnowledgeBaseSync:
    """Sync panel discussion results to Bedrock Knowledge Base"""

    def __init__(
        self,
        knowledge_base_id: str = None,
        data_source_id: str = None,
        s3_bucket: str = None,
        region: str = "ap-northeast-1"
    ):
        """
        Initialize Knowledge Base sync

        Args:
            knowledge_base_id: Bedrock Knowledge Base ID
            data_source_id: Data source ID in the knowledge base
            s3_bucket: S3 bucket for knowledge base documents
            region: AWS region
        """
        self.kb_id = knowledge_base_id or os.getenv('KNOWLEDGE_BASE_ID')
        self.data_source_id = data_source_id or os.getenv('KB_DATA_SOURCE_ID')
        self.s3_bucket = s3_bucket or os.getenv('KB_S3_BUCKET', 'hackthon-knowledge-base')
        self.region = region

        self.s3_client = boto3.client('s3', region_name=region)
        self.bedrock_agent = boto3.client('bedrock-agent', region_name=region)

    def sync_discussion(
        self,
        discussion_id: str,
        result,
        country_code: str
    ) -> Optional[str]:
        """
        パネルディスカッション結果をナレッジベースに同期

        Args:
            discussion_id: Discussion ID
            result: PanelResult dataclass
            country_code: Country code

        Returns:
            Knowledge base document ID or None
        """
        try:
            # Convert to structured document
            kb_document = self._create_kb_document(
                discussion_id=discussion_id,
                result=result,
                country_code=country_code
            )

            # Save to S3 (KB data source location)
            kb_key = f"panel-discussions/{country_code}/{discussion_id}.json"
            self._save_kb_document(kb_key, kb_document)

            # Trigger knowledge base ingestion
            if self.kb_id and self.data_source_id:
                self._trigger_ingestion()

            print(f"📚 Synced to Knowledge Base: {kb_key}")
            return kb_key

        except Exception as e:
            print(f"❌ Knowledge Base sync failed: {e}")
            return None

    def _create_kb_document(
        self,
        discussion_id: str,
        result,
        country_code: str
    ) -> Dict:
        """
        Create structured document for knowledge base

        Format optimized for RAG retrieval
        """
        result_dict = asdict(result)
        timestamp = datetime.now()

        # Extract key information
        expert_analyses = result_dict.get('expert_analyses', {})
        votes = result_dict.get('votes', [])
        final_mood = result_dict.get('final_mood', 'unknown')
        final_score = result_dict.get('final_score', 0)

        # Create RAG-optimized document
        kb_document = {
            # Metadata for filtering
            "metadata": {
                "discussion_id": discussion_id,
                "country_code": country_code,
                "timestamp": timestamp.isoformat(),
                "final_mood": final_mood,
                "final_score": final_score,
                "topic": result_dict.get('topic', 'Mood Analysis'),
                "document_type": "panel_discussion"
            },

            # Main content for RAG
            "content": {
                # Summary section (high priority for RAG)
                "summary": {
                    "country": country_code,
                    "date": timestamp.strftime("%Y-%m-%d"),
                    "final_mood": final_mood,
                    "final_score": final_score,
                    "conclusion": result_dict.get('moderator_conclusion', {}).get('summary', ''),
                    "key_factors": self._extract_key_factors(result_dict)
                },

                # Expert opinions
                "expert_analyses": expert_analyses,

                # Voting results
                "votes": [
                    {
                        "expert": vote.get('expert', 'unknown'),
                        "mood": vote.get('mood', 'unknown'),
                        "score": vote.get('score', 0),
                        "reasoning": vote.get('reasoning', '')
                    }
                    for vote in votes
                ],

                # Full discussion transcript
                "transcript": result_dict.get('full_transcript', [])
            },

            # RAG-optimized text representation
            "text_representation": self._create_text_representation(
                country_code=country_code,
                result_dict=result_dict,
                timestamp=timestamp
            )
        }

        return kb_document

    def _extract_key_factors(self, result_dict: Dict) -> list:
        """Extract key factors from discussion"""
        factors = []

        # From news analysis
        news_data = result_dict.get('metadata', {}).get('country_data', {}).get('news', [])
        if news_data:
            factors.append(f"News sentiment: {news_data[0].get('sentiment', 'N/A')}")

        # From weather analysis
        weather_data = result_dict.get('metadata', {}).get('country_data', {}).get('weather', {})
        if weather_data:
            factors.append(f"Weather impact: {weather_data.get('mood_impact', 'N/A')}")

        return factors

    def _create_text_representation(
        self,
        country_code: str,
        result_dict: Dict,
        timestamp: datetime
    ) -> str:
        """
        Create text representation optimized for RAG retrieval

        This text will be embedded and used for semantic search
        """
        final_mood = result_dict.get('final_mood', 'unknown')
        final_score = result_dict.get('final_score', 0)
        conclusion = result_dict.get('moderator_conclusion', {}).get('summary', '')

        # Build comprehensive text
        text_parts = [
            f"# パネルディスカッション結果: {country_code}",
            f"日付: {timestamp.strftime('%Y年%m月%d日')}",
            f"",
            f"## 最終結論",
            f"気分: {final_mood}",
            f"スコア: {final_score}/100",
            f"",
            f"## 結論の詳細",
            conclusion,
            f"",
            f"## エキスパート分析"
        ]

        # Add expert analyses
        for expert, analysis in result_dict.get('expert_analyses', {}).items():
            text_parts.append(f"")
            text_parts.append(f"### {expert}")
            text_parts.append(str(analysis))

        # Add voting results
        text_parts.append("")
        text_parts.append("## 投票結果")
        for vote in result_dict.get('votes', []):
            text_parts.append(
                f"- {vote.get('expert')}: {vote.get('mood')} "
                f"(スコア: {vote.get('score')}) - {vote.get('reasoning')}"
            )

        return "\n".join(text_parts)

    def _save_kb_document(self, key: str, document: Dict):
        """Save document to S3 for knowledge base ingestion"""
        try:
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json.dumps(document, indent=2, ensure_ascii=False),
                ContentType='application/json',
                Metadata={
                    'document_type': 'panel_discussion',
                    'country_code': document['metadata']['country_code'],
                    'final_mood': document['metadata']['final_mood']
                }
            )
            print(f"✅ KB document saved: s3://{self.s3_bucket}/{key}")
        except Exception as e:
            print(f"❌ Failed to save KB document: {e}")
            raise

    def _trigger_ingestion(self):
        """Trigger knowledge base ingestion job"""
        try:
            response = self.bedrock_agent.start_ingestion_job(
                knowledgeBaseId=self.kb_id,
                dataSourceId=self.data_source_id
            )
            job_id = response.get('ingestionJob', {}).get('ingestionJobId')
            print(f"✅ Ingestion job started: {job_id}")
        except Exception as e:
            print(f"⚠️  Failed to trigger ingestion (continuing anyway): {e}")


# Convenience function
def sync_to_knowledge_base(
    discussion_id: str,
    result,
    country_code: str
) -> Optional[str]:
    """
    Sync panel discussion to knowledge base

    Args:
        discussion_id: Discussion ID
        result: PanelResult dataclass
        country_code: Country code

    Returns:
        Knowledge base document ID or None
    """
    sync = KnowledgeBaseSync()
    return sync.sync_discussion(
        discussion_id=discussion_id,
        result=result,
        country_code=country_code
    )