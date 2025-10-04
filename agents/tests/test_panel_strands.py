#!/usr/bin/env python3
"""
Local test script for Strands-based Panel Discussion
"""

from panel_discussion_strands import create_panel_discussion_strands
from data_collectors import DataCollectionService
from agent_configs import AGENTS
import json


def test_data_collection():
    """Test data collection"""
    print("=" * 60)
    print("Testing Data Collection")
    print("=" * 60)

    service = DataCollectionService()

    # Test news collection
    print("\n[1/2] Testing news collection...")
    data = service.collect_country_data('JP', max_news=5)

    print(f"\nCollected Data:")
    print(f"  Country: {data['country_code']}")
    print(f"  News articles: {len(data['news'])}")
    print(f"  Weather: {data['weather']['description']} ({data['weather']['temp']}°C)")
    print(f"  Avg sentiment: {data['statistics']['avg_news_sentiment']}")
    print(f"  Weather mood impact: {data['statistics']['weather_mood_impact']}")

    return data


def test_simple_discussion():
    """Test basic panel discussion with manual data"""
    print("\n" + "=" * 60)
    print("Testing Simple Panel Discussion (Manual Data)")
    print("=" * 60)

    # Create panel
    panel = create_panel_discussion_strands(
        agent_configs=AGENTS,
        model_id="us.amazon.nova-pro-v1:0"
    )

    # Test data
    test_request = {
        'country_code': 'JP',
        'topic': 'Current mood analysis',
        'country_data': {
            'news': [
                {'title': 'Economic growth reported at 2.5%', 'sentiment': 0.3},
                {'title': 'New tech startup funding announced', 'sentiment': 0.4},
                {'title': 'Healthcare reforms debated in parliament', 'sentiment': 0.1}
            ],
            'weather': {
                'description': 'Partly cloudy',
                'temp': 18,
                'mood_impact': 0.1
            }
        }
    }

    # Run discussion
    result = panel.start_discussion(
        country_code=test_request['country_code'],
        topic=test_request['topic'],
        country_data=test_request['country_data']
    )

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nCountry: {result.country_code}")
    print(f"Final Mood: {result.final_mood.upper()} ({result.final_score:.1f}/100)")
    print(f"\nIntroduction:\n{result.introduction}")
    print(f"\nConclusion:\n{result.conclusion}")
    print(f"\nMetadata:")
    print(json.dumps(result.metadata, indent=2))

    return result


def test_agentcore_wrapper():
    """Test BedrockAgentCore wrapper"""
    print("\n" + "=" * 60)
    print("Testing BedrockAgentCore Wrapper")
    print("=" * 60)

    # Import the app
    from panel_app import run_panel_discussion

    test_request = {
        'country_code': 'US',
        'topic': 'Current mood analysis',
        'country_data': {
            'news': [
                {'title': 'Stock market reaches new highs'},
                {'title': 'New infrastructure bill passed'}
            ],
            'weather': {
                'description': 'Sunny',
                'temp': 25
            }
        }
    }

    # Test entrypoint
    response = run_panel_discussion(test_request)

    print(f"\nSuccess: {response.get('success')}")
    if response.get('success'):
        data = response.get('data')
        print(f"Final Mood: {data.get('final_mood')} ({data.get('final_score'):.1f}/100)")
    else:
        print(f"Error: {response.get('error')}")

    return response


if __name__ == "__main__":
    import sys

    print("\n🧪 Starting Strands Panel Discussion Tests\n")

    try:
        # Test 1: Basic discussion
        print("\n[Test 1/2] Basic Panel Discussion")
        result1 = test_simple_discussion()

        # Test 2: AgentCore wrapper
        print("\n[Test 2/2] AgentCore Wrapper")
        result2 = test_agentcore_wrapper()

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
