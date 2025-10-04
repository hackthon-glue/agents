"""
RDS PostgreSQL Storage for Panel Discussion Results
"""
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from typing import Dict, List, Optional
from dataclasses import asdict
import os


class RDSPanelStorage:
    """Save panel discussion results to RDS PostgreSQL and S3 (for Knowledge Base)"""

    def __init__(
        self,
        db_host: str,
        db_user: str,
        db_password: str,
        database: str = "glue",
        db_port: int = 5432,
        s3_bucket: str = "team-for-glue-knowledge",
        region: str = "us-west-2"
    ):
        """
        Initialize RDS storage

        Args:
            db_host: RDS endpoint
            db_user: Database user
            db_password: Database password
            database: Database name
            db_port: Database port
            s3_bucket: S3 bucket for Knowledge Base documents
            region: AWS region
        """
        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.database = database
        self.db_port = db_port
        self.s3_bucket = s3_bucket
        self.region = region

        # S3 client for Knowledge Base
        self.s3_client = boto3.client('s3', region_name=region)

    def _get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.database,
            port=self.db_port,
            sslmode='require'
        )

    def save_panel_result(self, result, country_code: str, skip_s3: bool = False) -> int:
        """
        Save complete panel discussion to RDS

        Args:
            result: PanelResult dataclass
            country_code: Country code
            skip_s3: Skip S3 save (default: False)

        Returns:
            discussion_id (int)
        """
        try:
            # Convert to dict
            result_dict = asdict(result)

            # 1. Insert main discussion record
            discussion_id = self._save_discussion(result_dict, country_code)
            print(f"💾 Saved discussion: {discussion_id}")

            # 2. Save expert analyses
            self._save_expert_analyses(discussion_id, result_dict)
            print(f"✅ Saved expert analyses")

            # 3. Save votes
            self._save_votes(discussion_id, result_dict)
            print(f"✅ Saved votes")

            # 4. Save transcript
            self._save_transcript(discussion_id, result_dict)
            print(f"✅ Saved transcript")

            # 5. Save to CountrySentiment (Django table)
            try:
                self._save_country_sentiment(result_dict, country_code)
                print(f"📊 Saved to CountrySentiment")
            except Exception as sentiment_error:
                print(f"⚠️  CountrySentiment save skipped: {sentiment_error}")

            # 6. Save to S3 for Knowledge Base (optional)
            if not skip_s3:
                try:
                    self._save_to_s3_for_kb(result_dict, country_code)
                    print(f"📚 Saved to S3 for Knowledge Base")
                except Exception as s3_error:
                    print(f"⚠️  S3 save skipped: {s3_error}")

            return discussion_id

        except Exception as e:
            print(f"❌ Error saving to RDS: {e}")
            raise

    def _save_discussion(self, result_dict: Dict, country_code: str) -> int:
        """Save main discussion record"""

        sql = """
        INSERT INTO panel_discussions
        (country_code, topic, final_mood, final_score, introduction, conclusion,
         discussion_date, total_turns, debate_rounds)
        VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    country_code,
                    result_dict.get('topic', 'Mood Analysis'),
                    result_dict['final_mood'],
                    float(result_dict['final_score']),
                    result_dict.get('introduction', ''),
                    result_dict.get('conclusion', ''),
                    result_dict.get('discussion_date', date.today().isoformat()),
                    result_dict.get('total_turns', 0),
                    result_dict.get('debate_rounds', 3),
                ))
                discussion_id = cur.fetchone()[0]
                conn.commit()
                return discussion_id
        finally:
            conn.close()

    def _save_expert_analyses(self, discussion_id: int, result_dict: Dict):
        """Save expert analyses from new PanelResult structure"""

        # V2 structure: analyses is a list of ExpertAnalysis objects
        analyses = result_dict.get('analyses', [])
        for analysis in analyses:
            self._insert_analysis(
                discussion_id,
                analysis.get('expert_role', 'Unknown'),
                analysis.get('analysis_text', ''),
                analysis.get('round_number', 1)
            )

    def _insert_analysis(self, discussion_id: int, expert_role: str, analysis_text: str, round_number: int):
        """Insert single expert analysis"""

        sql = """
        INSERT INTO panel_expert_analyses
        (discussion_id, expert_role, analysis_text, round_number)
        VALUES (%s, %s, %s, %s)
        """

        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (discussion_id, expert_role, str(analysis_text), round_number))
                conn.commit()
        finally:
            conn.close()

    def _save_votes(self, discussion_id: int, result_dict: Dict):
        """Save votes from new Vote structure"""

        sql = """
        INSERT INTO panel_votes
        (discussion_id, expert_role, vote_mood, confidence, reasoning)
        VALUES (%s, %s, %s, %s, %s)
        """

        votes = result_dict.get('votes', [])
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for vote in votes:
                    cur.execute(sql, (
                        discussion_id,
                        vote.get('expert_role', 'Unknown'),
                        vote.get('vote_mood', 'neutral'),
                        float(vote.get('confidence', 0.5)),  # Already 0-1 range
                        vote.get('reasoning', ''),
                    ))
                conn.commit()
        finally:
            conn.close()

    def _save_transcript(self, discussion_id: int, result_dict: Dict):
        """Save full transcript from new Transcript structure"""

        sql = """
        INSERT INTO panel_transcripts
        (discussion_id, speaker, content, round_number, turn_order)
        VALUES (%s, %s, %s, %s, %s)
        """

        transcripts = result_dict.get('transcripts', [])
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                for transcript in transcripts:
                    cur.execute(sql, (
                        discussion_id,
                        transcript.get('speaker', 'unknown'),
                        transcript.get('content', ''),
                        transcript.get('round_number'),  # Can be None
                        transcript.get('turn_order', 0),
                    ))
                conn.commit()
        finally:
            conn.close()

    def _save_country_sentiment(self, result_dict: Dict, country_code: str):
        """
        Save sentiment to Django's CountrySentiment table
        
        Args:
            result_dict: Panel result dictionary
            country_code: Country code (e.g., 'JP', 'US')
        """
        # Get Django Country ID
        country_id = self._get_country_id(country_code)
        
        if country_id is None:
            print(f"⚠️  Country '{country_code}' not found in insights_country table. Skipping CountrySentiment save.")
            return
        
        # Extract data from panel result
        label = result_dict.get('final_mood', 'neutral')  # 'happy', 'neutral', 'sad'
        score = int(result_dict.get('final_score', 50))  # 0-100
        recorded_date = result_dict.get('discussion_date', date.today().isoformat())
        
        sql = """
        INSERT INTO insights_countrysentiment
        (country_id, label, score, recorded_date)
        VALUES (%s, %s, %s, %s)
        """
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (
                    country_id,
                    label,
                    score,
                    recorded_date,
                ))
                conn.commit()
                print(f"   ✅ CountrySentiment: {label} ({score}/100) for country_id={country_id}")
        except Exception as e:
            print(f"   ⚠️  Error saving CountrySentiment: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def _get_country_id(self, country_code: str) -> Optional[int]:
        """Get Django Country model ID from country code"""
        sql = """
        SELECT id FROM insights_country
        WHERE code = %s
        LIMIT 1
        """
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (country_code.upper(),))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"⚠️  Error getting country ID: {e}")
            return None
        finally:
            conn.close()

    def _sentiment_to_tone(self, sentiment: float) -> str:
        """Convert sentiment score to tone category"""
        if sentiment >= 0.3:
            return 'optimistic'
        elif sentiment >= 0.1:
            return 'celebratory'
        elif sentiment <= -0.3:
            return 'urgent'
        elif sentiment <= -0.1:
            return 'cautious'
        else:
            return 'cautious'

    def _save_to_s3_for_kb(self, result_dict: Dict, country_code: str):
        """Save summary to S3 for Knowledge Base ingestion"""

        # Create Knowledge Base friendly document
        kb_document = f"""# Country Analysis: {country_code}
Date: {date.today()}
Overall Mood: {result_dict['final_mood'].upper()} ({result_dict['final_score']:.1f}/100)

## Introduction
{result_dict.get('moderator_introduction', {}).get('introduction', 'N/A')}

## Expert Analyses
"""

        expert_analyses = result_dict.get('expert_analyses', {})
        for role, analysis in expert_analyses.items():
            kb_document += f"\n### {role.replace('_', ' ').title()}\n{analysis}\n"

        kb_document += f"\n## Conclusion\n{result_dict.get('moderator_conclusion', {}).get('summary', 'N/A')}\n"

        # Add votes summary
        kb_document += "\n## Voting Results\n"
        for vote in result_dict.get('votes', []):
            kb_document += f"- **{vote.get('expert')}**: {vote.get('mood')} (confidence: {vote.get('score')}%)\n"
            kb_document += f"  Reasoning: {vote.get('reasoning', 'N/A')}\n"

        # Save to S3
        file_key = f"panel-discussions/{country_code}/{date.today()}.md"

        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=file_key,
            Body=kb_document,
            ContentType='text/markdown',
            Metadata={
                'country': country_code,
                'mood': result_dict['final_mood'],
                'score': str(result_dict['final_score']),
                'date': str(date.today()),
                'type': 'panel_discussion'
            }
        )

        print(f"📚 Saved to S3: s3://{self.s3_bucket}/{file_key}")

    def save_news_data(self, country_code: str, news_articles: List[Dict]) -> int:
        """
        Save news articles to Django insights_countrynewsitem table and S3 for Knowledge Base
        
        Args:
            country_code: Country code (e.g., 'JP', 'US')
            news_articles: List of news article dicts from BrowserNewsCollector
            
        Returns:
            Number of articles saved
        """
        if not news_articles:
            print("⚠️  No news articles to save")
            return 0
        
        # Get Django Country ID
        country_id = self._get_country_id(country_code)
        if not country_id:
            print(f"❌ Country {country_code} not found in insights_country table")
            return 0
            
        sql = """
        INSERT INTO insights_countrynewsitem
        (country_id, title, summary, url, category, tone)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        conn = self._get_connection()
        saved_count = 0
        try:
            with conn.cursor() as cur:
                for article in news_articles:
                    try:
                        # Convert sentiment to tone
                        sentiment = float(article.get('sentiment', 0.0))
                        tone = self._sentiment_to_tone(sentiment)
                        
                        # Use description as summary, source as category
                        summary = article.get('description', article.get('title', ''))[:500]
                        category = article.get('source', 'General News')
                        url = article.get('url', 'https://example.com/news')
                        
                        cur.execute(sql, (
                            country_id,
                            article.get('title', 'Untitled'),
                            summary,
                            url,
                            category,
                            tone
                        ))
                        saved_count += 1
                    except Exception as e:
                        print(f"⚠️  Failed to save article: {e}")
                        continue
                        
                conn.commit()
            print(f"💾 Saved {saved_count} news articles to insights_countrynewsitem")
            
            # Save to S3 for Knowledge Base
            try:
                self._save_news_to_s3_for_kb(country_code, news_articles)
            except Exception as s3_error:
                print(f"⚠️  S3 save for news failed: {s3_error}")
                
            return saved_count
            
        except Exception as e:
            print(f"❌ Error saving news data: {e}")
            return saved_count
        finally:
            conn.close()

    def save_weather_data(self, country_code: str, weather: Dict) -> bool:
        """
        Save weather data to Django insights_countryweather table (UPSERT) and S3 for Knowledge Base
        
        Args:
            country_code: Country code (e.g., 'JP', 'US')
            weather: Weather dict from BrowserWeatherCollector
            
        Returns:
            True if saved successfully
        """
        if not weather:
            print("⚠️  No weather data to save")
            return False
        
        # Get Django Country ID
        country_id = self._get_country_id(country_code)
        if not country_id:
            print(f"❌ Country {country_code} not found in insights_country table")
            return False
            
        # UPSERT query (PostgreSQL syntax)
        sql = """
        INSERT INTO insights_countryweather
        (country_id, condition, temperature, feels_like, humidity, wind, precipitation_chance)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (country_id)
        DO UPDATE SET
            condition = EXCLUDED.condition,
            temperature = EXCLUDED.temperature,
            feels_like = EXCLUDED.feels_like,
            humidity = EXCLUDED.humidity,
            wind = EXCLUDED.wind,
            precipitation_chance = EXCLUDED.precipitation_chance
        """
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Format wind string (e.g., "10 km/h NW")
                wind_speed = weather.get('wind_speed', 0.0)
                wind = f"{wind_speed:.1f} km/h"
                
                # Convert to integers for Django model
                temp = int(round(weather.get('temp', 20.0)))
                feels_like = int(round(weather.get('feels_like', temp)))
                humidity = int(weather.get('humidity', 50))
                
                # precipitation_chance not in weather data, default to 0
                precip_chance = 0
                
                cur.execute(sql, (
                    country_id,
                    weather.get('description', 'Unknown'),
                    temp,
                    feels_like,
                    humidity,
                    wind,
                    precip_chance
                ))
                conn.commit()
                
            print(f"💾 Saved weather data to insights_countryweather (UPSERT)")
            
            # Save to S3 for Knowledge Base
            try:
                self._save_weather_to_s3_for_kb(country_code, weather)
            except Exception as s3_error:
                print(f"⚠️  S3 save for weather failed: {s3_error}")
                
            return True
            
        except Exception as e:
            print(f"❌ Error saving weather data: {e}")
            return False
        finally:
            conn.close()

    def save_country_data(self, country_data: Dict) -> Dict:
        """
        Save complete country data (news + weather) to RDS and S3
        
        Args:
            country_data: Dict from BrowserDataCollectionService.collect_country_data()
            
        Returns:
            Dict with save results
        """
        country_code = country_data.get('country_code', 'UNKNOWN')
        news = country_data.get('news', [])
        weather = country_data.get('weather', {})
        
        results = {
            'country_code': country_code,
            'news_saved': 0,
            'weather_saved': False
        }
        
        # Save news
        if news:
            results['news_saved'] = self.save_news_data(country_code, news)
            
        # Save weather
        if weather:
            results['weather_saved'] = self.save_weather_data(country_code, weather)
            
        return results

    def _save_news_to_s3_for_kb(self, country_code: str, news_articles: List[Dict]):
        """Save news articles to S3 for Knowledge Base ingestion"""
        
        # Create Knowledge Base friendly document
        kb_document = f"""# News Articles: {country_code}
Date: {date.today()}
Source: Browser Data Collection

## Articles Summary
Total articles collected: {len(news_articles)}

"""
        
        for i, article in enumerate(news_articles, 1):
            sentiment_label = "Positive" if article.get('sentiment', 0) > 0.2 else \
                            "Negative" if article.get('sentiment', 0) < -0.2 else "Neutral"
            
            kb_document += f"""### Article {i}: {article.get('title', 'Untitled')}
**Source**: {article.get('source', 'Unknown')}
**Sentiment**: {sentiment_label} ({article.get('sentiment', 0):.2f})
**Description**: {article.get('description', 'No description available')}
**URL**: {article.get('url', 'N/A')}

"""
        
        # Save to S3
        file_key = f"news-data/{country_code}/{date.today()}_news.md"
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=file_key,
            Body=kb_document,
            ContentType='text/markdown',
            Metadata={
                'country': country_code,
                'date': str(date.today()),
                'type': 'news_data',
                'article_count': str(len(news_articles))
            }
        )
        
        print(f"📚 Saved news to S3: s3://{self.s3_bucket}/{file_key}")

    def _save_weather_to_s3_for_kb(self, country_code: str, weather: Dict):
        """Save weather data to S3 for Knowledge Base ingestion"""
        
        mood_label = "Positive" if weather.get('mood_impact', 0) > 0.2 else \
                    "Negative" if weather.get('mood_impact', 0) < -0.2 else "Neutral"
        
        # Create Knowledge Base friendly document
        kb_document = f"""# Weather Data: {country_code}
Date: {date.today()}
City: {weather.get('city', 'Unknown')}
Source: Browser Data Collection

## Current Weather Conditions

**Temperature**: {weather.get('temp', 'N/A')}°C (Feels like: {weather.get('feels_like', 'N/A')}°C)
**Conditions**: {weather.get('description', 'Unknown')}
**Humidity**: {weather.get('humidity', 'N/A')}%
**Wind Speed**: {weather.get('wind_speed', 'N/A')} km/h

## Mood Impact Analysis

**Mood Impact Score**: {weather.get('mood_impact', 0):.2f} ({mood_label})

Weather conditions can significantly affect public mood and sentiment. The current conditions 
are assessed as having a {mood_label.lower()} impact on the overall mood in {weather.get('city', country_code)}.

"""
        
        # Save to S3
        file_key = f"weather-data/{country_code}/{date.today()}_weather.md"
        
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=file_key,
            Body=kb_document,
            ContentType='text/markdown',
            Metadata={
                'country': country_code,
                'city': weather.get('city', ''),
                'date': str(date.today()),
                'type': 'weather_data',
                'mood_impact': str(weather.get('mood_impact', 0))
            }
        )
        
        print(f"📚 Saved weather to S3: s3://{self.s3_bucket}/{file_key}")

    def get_latest_discussion(self, country_code: str) -> Optional[Dict]:
        """Get latest discussion for a country"""

        sql = """
        SELECT * FROM panel_discussions
        WHERE country_code = %s
        ORDER BY discussion_date DESC
        LIMIT 1
        """

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (country_code,))
                result = cur.fetchone()
                return dict(result) if result else None
        finally:
            conn.close()

    def list_discussions(self, country_code: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """List recent discussions"""

        if country_code:
            sql = """
            SELECT * FROM panel_discussions
            WHERE country_code = %s
            ORDER BY discussion_date DESC
            LIMIT %s
            """
            params = (country_code, limit)
        else:
            sql = """
            SELECT * FROM panel_discussions
            ORDER BY discussion_date DESC
            LIMIT %s
            """
            params = (limit,)

        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params)
                results = cur.fetchall()
                return [dict(row) for row in results]
        finally:
            conn.close()


# Factory function
def create_rds_storage(**kwargs) -> RDSPanelStorage:
    """
    Create RDS storage instance

    Environment variables:
    - DB_HOST
    - DB_USER
    - DB_PASSWORD
    - DB_NAME (default: glue)
    - DB_PORT (default: 5432)
    - KB_S3_BUCKET (default: hackthon-knowledge-base)
    - AWS_REGION (default: us-west-2)
    """
    return RDSPanelStorage(
        db_host=kwargs.get('db_host') or os.getenv('DB_HOST'),
        db_user=kwargs.get('db_user') or os.getenv('DB_USER'),
        db_password=kwargs.get('db_password') or os.getenv('DB_PASSWORD'),
        database=kwargs.get('database') or os.getenv('DB_NAME', 'glue'),
        db_port=kwargs.get('db_port') or int(os.getenv('DB_PORT', '5432')),
        s3_bucket=kwargs.get('s3_bucket') or os.getenv('KB_S3_BUCKET', 'hackthon-knowledge-base'),
        region=kwargs.get('region') or os.getenv('AWS_REGION', 'us-west-2')
    )
