"""
AI Expert Panel Discussion System using Strands Agents - V2
Improved format matching the frontend panel display
"""

from strands import Agent
from strands.models import BedrockModel
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, date
import json


@dataclass
class ExpertAnalysis:
    """Expert analysis for a specific round"""
    expert_role: str
    analysis_text: str
    round_number: int


@dataclass
class Vote:
    """Individual expert vote"""
    expert_role: str
    vote_mood: str  # 'happy', 'neutral', 'sad'
    confidence: float  # 0-1 (will be displayed as percentage)
    reasoning: str


@dataclass
class Transcript:
    """Conversation turn"""
    speaker: str
    content: str
    round_number: Optional[int]
    turn_order: int


@dataclass
class PanelResult:
    """Complete panel discussion result"""
    country_code: str
    topic: str
    final_mood: str
    final_score: float
    introduction: str
    conclusion: str
    discussion_date: str
    total_turns: int
    debate_rounds: int
    analyses: List[ExpertAnalysis]
    votes: List[Vote]
    transcripts: List[Transcript]


class ExpertAgent:
    """Wrapper for individual expert agents"""

    def __init__(self, role: str, instruction: str, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        self.role = role
        self.agent = Agent(
            model=BedrockModel(
                model_id=model_id,
                temperature=0.7,
                streaming=False
            ),
            system_prompt=instruction
        )

    def respond(self, prompt: str) -> str:
        """Get agent response"""
        try:
            response = self.agent(prompt)
            return response if isinstance(response, str) else str(response)
        except Exception as e:
            print(f"❌ Error from {self.role}: {e}")
            return f"[Error from {self.role}]"


class PanelDiscussionStrandsV2:
    """Orchestrates AI Expert Panel discussions with improved format"""

    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"):
        """Initialize panel with specific expert roles"""
        self.model_id = model_id
        self.transcripts: List[Transcript] = []
        self.analyses: List[ExpertAnalysis] = []
        self.turn_order = 0

        # Define 3 expert roles that will participate
        self.expert_roles = [
            "Economic Analyst",
            "Social Welfare Specialist",
            "Environmental Scientist"
        ]

        # Initialize agents
        self.agents = {
            'moderator': ExpertAgent(
                role='Moderator',
                instruction="""You are a professional panel discussion moderator. Your role is to:
- Introduce topics clearly and engagingly
- Ask probing questions to experts
- Guide the discussion flow
- Synthesize different viewpoints
- Provide balanced conclusions
Keep your responses concise but insightful.""",
                model_id=model_id
            )
        }

        # Initialize expert agents
        expert_instructions = {
            "Economic Analyst": """You are an Economic Analyst expert. Analyze:
- GDP growth, employment, inflation
- Trade, exports, industrial sectors
- Economic policies and reforms
- Infrastructure development
Provide data-driven insights with specific numbers when possible.""",

            "Social Welfare Specialist": """You are a Social Welfare Specialist. Analyze:
- Quality of life, healthcare, education
- Work-life balance, social programs
- Inequality, social mobility
- Cultural trends and public sentiment
Focus on human well-being and social cohesion.""",

            "Environmental Scientist": """You are an Environmental Scientist. Analyze:
- Climate change impacts and policies
- Pollution levels, renewable energy
- Resource management, sustainability
- Environmental regulations
Assess environmental health and future risks."""
        }

        for role, instruction in expert_instructions.items():
            self.agents[role] = ExpertAgent(role=role, instruction=instruction, model_id=model_id)

        print(f"✅ Initialized panel with {len(self.expert_roles)} experts + moderator")

    def start_discussion(
        self,
        country_code: str,
        topic: str,
        country_data: Optional[Dict] = None,
        max_rounds: int = 5
    ) -> PanelResult:
        """
        Start a panel discussion about a country with dynamic moderator-driven flow

        Args:
            country_code: Country code
            topic: Discussion topic
            country_data: Optional country data for context
            max_rounds: Maximum number of discussion rounds (default: 5)

        Returns:
            PanelResult with complete discussion matching frontend format
        """
        print(f"\n{'=' * 60}")
        print(f"🎭 Starting Panel Discussion: {country_code}")
        print(f"{'=' * 60}\n")

        self.transcripts = []
        self.analyses = []
        self.turn_order = 0

        # Build context
        context = self._build_context(country_code, country_data)

        # Phase 1: Moderator Introduction
        print("🎙️  Phase 1: Introduction")
        introduction = self._moderator_introduce(country_code, topic, context)

        # Phase 2: Initial Expert Analyses (Round 1)
        print(f"\n📊 Phase 2: Expert Analyses - Round 1")
        self._collect_round_analyses(country_code, topic, context, round_number=1, is_first=True)

        # Phase 3: Dynamic Debate Rounds (Moderator-driven)
        round_num = 2
        while round_num <= max_rounds:
            print(f"\n💬 Phase 3: Dynamic Debate Round {round_num}")
            
            # Moderator decides if follow-up is needed and who to ask
            should_continue, target_experts = self._moderator_decide_followup(country_code, topic, round_num)
            
            if not should_continue:
                print(f"   ✅ Moderator: Discussion has converged, moving to voting")
                break
            
            # Conduct targeted follow-up with selected experts
            self._conduct_dynamic_debate_round(country_code, topic, round_num, target_experts)
            round_num += 1

        actual_rounds = round_num - 1

        # Phase 4: Voting
        print(f"\n🗳️  Phase 4: Final Voting")
        votes = self._conduct_voting(country_code)

        # Phase 5: Calculate Final Result
        final_mood, final_score = self._calculate_final_mood(votes)

        # Phase 6: Moderator Conclusion
        print(f"\n🎙️  Phase 5: Conclusion")
        conclusion = self._moderator_conclude(country_code, final_mood, final_score)

        result = PanelResult(
            country_code=country_code,
            topic=topic,
            final_mood=final_mood,
            final_score=final_score,
            introduction=introduction,
            conclusion=conclusion,
            discussion_date=date.today().isoformat(),
            total_turns=len(self.transcripts),
            debate_rounds=actual_rounds,
            analyses=self.analyses,
            votes=votes,
            transcripts=self.transcripts
        )

        print(f"\n{'=' * 60}")
        print(f"✅ Discussion Complete: {final_mood.upper()} ({final_score:.1f}/100)")
        print(f"   Total rounds: {actual_rounds}")
        print(f"   Total turns: {len(self.transcripts)}")
        print(f"   Analyses: {len(self.analyses)}")
        print(f"   Votes: {len(votes)}")
        print(f"{'=' * 60}\n")

        return result

    def _build_context(self, country_code: str, country_data: Optional[Dict]) -> str:
        """Build context string from country data"""
        if not country_data:
            return f"Analyze the current state of {country_code} based on recent developments."

        context_parts = []

        if 'news' in country_data:
            news_items = country_data['news'][:5]
            context_parts.append("Recent News Headlines:")
            for item in news_items:
                context_parts.append(f"- {item.get('title', 'N/A')}")

        if 'weather' in country_data:
            weather = country_data['weather']
            context_parts.append(f"\nCurrent Conditions: {weather.get('description', 'N/A')}, {weather.get('temp', 'N/A')}°C")

        return '\n'.join(context_parts) if context_parts else f"Current analysis of {country_code}"

    def _add_transcript(self, speaker: str, content: str, round_number: Optional[int] = None):
        """Add turn to transcript"""
        self.turn_order += 1
        self.transcripts.append(Transcript(
            speaker=speaker,
            content=content,
            round_number=round_number,
            turn_order=self.turn_order
        ))

    def _moderator_introduce(self, country_code: str, topic: str, context: str) -> str:
        """Moderator introduces the discussion"""
        prompt = f"""Welcome everyone to today's expert panel discussion.

Topic: {topic}
Country: {country_code}

{context}

As moderator, introduce this panel discussion in 2-3 sentences. Explain what we'll be examining and why it matters. Make it engaging and set the stage for expert analysis."""

        introduction = self.agents['moderator'].respond(prompt)
        self._add_transcript('Moderator', introduction, round_number=None)

        print(f"   Introduction: {introduction[:80]}...")
        return introduction

    def _collect_round_analyses(self, country_code: str, topic: str, context: str, round_number: int, is_first: bool = False):
        """Collect expert analyses for a specific round"""

        # Moderator sets up the round
        if is_first:
            moderator_q = f"Let's begin with our expert analyses. {self.expert_roles[0]}, what's your assessment of {country_code}'s situation?"
        else:
            recent_discussion = self._get_recent_discussion(5)
            moderator_q = f"Let's continue our analysis. What are your updated perspectives based on our discussion?"

        self._add_transcript('Moderator', moderator_q, round_number=round_number)
        print(f"   Moderator: {moderator_q[:60]}...")

        # Each expert provides analysis
        for i, role in enumerate(self.expert_roles):
            if is_first:
                prompt = f"""As the {role} on this panel, provide your opening analysis of {country_code}.

Context:
{context}

Topic: {topic}

Give your expert perspective in 2-4 sentences. Be specific with data or examples where possible."""
            else:
                recent_discussion = self._get_recent_discussion(8)
                prompt = f"""Round {round_number} of our discussion about {country_code}.

Previous discussion:
{recent_discussion}

As the {role}, provide your analysis addressing:
- New insights based on what other experts said
- Your perspective on the key issues raised
- Specific evidence or examples

Keep it focused (2-4 sentences)."""

            analysis_text = self.agents[role].respond(prompt)

            # Add to analyses list
            self.analyses.append(ExpertAnalysis(
                expert_role=role,
                analysis_text=analysis_text,
                round_number=round_number
            ))

            # Add to transcript
            self._add_transcript(role, analysis_text, round_number=round_number)
            print(f"   {role}: {analysis_text[:60]}...")

    def _moderator_decide_followup(self, country_code: str, topic: str, round_number: int) -> tuple[bool, List[str]]:
        """
        Moderator decides if follow-up questions are needed and which experts to ask
        
        Returns:
            (should_continue, target_experts): 
            - should_continue: True if more discussion needed
            - target_experts: List of expert roles to follow up with (empty list means all experts)
        """
        recent_discussion = self._get_recent_discussion(12)
        
        prompt = f"""You are the moderator of an expert panel discussing {country_code}.

Recent discussion:
{recent_discussion}

Analyze the discussion and decide:
1. Have the experts provided sufficient diverse perspectives?
2. Are there any unresolved questions or contradictions?
3. Do we need to hear more from specific experts?

Available experts: {', '.join(self.expert_roles)}

Respond in this exact format:
Continue: [Yes/No]
Target Experts: [comma-separated list of expert roles to follow up with, or "All" if everyone should respond, or "None" if discussion is complete]
Reason: [Brief explanation in 1 sentence]"""

        response = self.agents['moderator'].respond(prompt)
        
        # Parse response
        should_continue = False
        target_experts = []
        
        try:
            lines = response.split('\n')
            for line in lines:
                line_lower = line.lower().strip()
                
                if line_lower.startswith('continue:'):
                    continue_text = line.split(':', 1)[1].strip().lower()
                    should_continue = 'yes' in continue_text
                
                elif line_lower.startswith('target experts:'):
                    experts_text = line.split(':', 1)[1].strip()
                    
                    if 'none' in experts_text.lower():
                        should_continue = False
                        target_experts = []
                    elif 'all' in experts_text.lower():
                        target_experts = self.expert_roles.copy()
                    else:
                        # Parse comma-separated expert names
                        mentioned_experts = [e.strip() for e in experts_text.split(',')]
                        # Match with actual expert roles
                        for expert in self.expert_roles:
                            for mentioned in mentioned_experts:
                                if mentioned.lower() in expert.lower() or expert.lower() in mentioned.lower():
                                    if expert not in target_experts:
                                        target_experts.append(expert)
                                    break
                
                elif line_lower.startswith('reason:'):
                    reason = line.split(':', 1)[1].strip()
                    print(f"   🤔 Moderator reasoning: {reason}")
        
        except Exception as e:
            print(f"   ⚠️  Error parsing moderator decision: {e}")
            # Default: continue with all experts
            should_continue = True
            target_experts = self.expert_roles.copy()
        
        if should_continue and len(target_experts) > 0:
            print(f"   📋 Following up with: {', '.join(target_experts)}")
        
        return should_continue, target_experts

    def _conduct_dynamic_debate_round(self, country_code: str, topic: str, round_number: int, target_experts: List[str]):
        """
        Conduct a targeted debate round with specific experts
        
        Args:
            country_code: Country code
            topic: Discussion topic
            round_number: Current round number
            target_experts: List of expert roles to ask (empty = all experts)
        """
        if not target_experts:
            target_experts = self.expert_roles.copy()
        
        # Moderator poses targeted question
        recent = self._get_recent_discussion(10)
        
        if len(target_experts) == len(self.expert_roles):
            # Question to all experts
            moderator_prompt = f"""Based on our discussion about {country_code}:

{recent}

As moderator, pose a follow-up question or raise an important point that needs clarification. Be specific (1-2 sentences)."""
        else:
            # Question to specific experts
            expert_names = ', '.join(target_experts)
            moderator_prompt = f"""Based on our discussion about {country_code}:

{recent}

As moderator, pose a targeted follow-up question specifically for {expert_names}. Focus on their area of expertise and ask for deeper insights (1-2 sentences)."""

        moderator_question = self.agents['moderator'].respond(moderator_prompt)
        self._add_transcript('Moderator', moderator_question, round_number=round_number)
        print(f"   Moderator: {moderator_question[:80]}...")

        # Selected experts respond with analyses
        for role in target_experts:
            recent_context = self._get_recent_discussion(8)
            
            prompt = f"""Round {round_number} - Follow-up question for you as {role}:

Moderator's question: {moderator_question}

Recent discussion context:
{recent_context}

Provide your expert response addressing the moderator's question. Be specific with evidence or examples (2-4 sentences)."""

            analysis_text = self.agents[role].respond(prompt)

            # Add to analyses list
            self.analyses.append(ExpertAnalysis(
                expert_role=role,
                analysis_text=analysis_text,
                round_number=round_number
            ))

            # Add to transcript
            self._add_transcript(role, analysis_text, round_number=round_number)
            print(f"   {role}: {analysis_text[:80]}...")

    def _conduct_voting(self, country_code: str) -> List[Vote]:
        """Conduct final voting among experts"""
        votes = []

        # Moderator calls for votes
        moderator_call = "Let's move to our final assessments. I'd like each expert to cast their vote on the overall outlook."
        self._add_transcript('Moderator', moderator_call, round_number=None)
        print(f"   Moderator: {moderator_call}")

        recent_discussion = self._get_recent_discussion(15)

        for role in self.expert_roles:
            print(f"   {role} voting...")

            prompt = f"""Based on our complete discussion about {country_code}:

{recent_discussion}

Cast your final vote on the overall outlook/mood.

Respond in this exact format:
Vote: [Happy/Neutral/Sad]
Confidence: [0-100]
Reasoning: [Your explanation in 1-2 sentences based on your expertise]"""

            response = self.agents[role].respond(prompt)
            vote = self._parse_vote(role, response)
            votes.append(vote)

            # Add voting reasoning to transcript
            vote_statement = f"I vote {vote.vote_mood} with {int(vote.confidence * 100)}% confidence. {vote.reasoning}"
            self._add_transcript(role, vote_statement, round_number=None)

        return votes

    def _parse_vote(self, role: str, response: str) -> Vote:
        """Parse vote from expert response"""
        mood = 'neutral'
        confidence = 0.50
        reasoning = ""

        try:
            lines = response.split('\n')
            for line in lines:
                line_lower = line.lower().strip()

                if line_lower.startswith('vote:'):
                    mood_text = line.split(':', 1)[1].strip().lower()
                    if 'happy' in mood_text:
                        mood = 'happy'
                    elif 'sad' in mood_text:
                        mood = 'sad'
                    else:
                        mood = 'neutral'

                elif line_lower.startswith('confidence:'):
                    conf_text = line.split(':', 1)[1].strip()
                    # Extract number
                    conf_num = float(''.join(c for c in conf_text if c.isdigit() or c == '.'))
                    confidence = min(100.0, max(0.0, conf_num)) / 100.0  # Convert to 0-1 range

                elif line_lower.startswith('reasoning:'):
                    reasoning = line.split(':', 1)[1].strip()

        except Exception as e:
            print(f"   ⚠️  Parse error for {role}: {e}")
            reasoning = response

        return Vote(
            expert_role=role,
            vote_mood=mood,
            confidence=confidence,
            reasoning=reasoning if reasoning else response
        )

    def _calculate_final_mood(self, votes: List[Vote]) -> tuple[str, float]:
        """Calculate weighted final mood and score"""
        # Equal weight for all experts
        total_score = 0
        total_weight = 0

        mood_values = {'happy': 100, 'neutral': 50, 'sad': 0}

        for vote in votes:
            mood_value = mood_values[vote.vote_mood]
            weighted_score = mood_value * vote.confidence
            total_score += weighted_score
            total_weight += vote.confidence

        if total_weight == 0:
            return 'neutral', 50.0

        final_score = total_score / total_weight

        # Determine mood category
        if final_score >= 67:
            final_mood = 'happy'
        elif final_score >= 34:
            final_mood = 'neutral'
        else:
            final_mood = 'sad'

        return final_mood, final_score

    def _moderator_conclude(self, country_code: str, final_mood: str, final_score: float) -> str:
        """Moderator provides final conclusion"""
        recent_discussion = self._get_recent_discussion(12)

        prompt = f"""Our expert panel has completed their analysis of {country_code}.

Discussion highlights:
{recent_discussion}

Final assessment: {final_mood.upper()} (Score: {final_score:.1f}/100)

As moderator, provide a concluding statement that:
1. Summarizes the key findings from all experts
2. Explains the final verdict and what it means
3. Provides balanced perspective on strengths and challenges
4. Ends with an insightful closing thought

Keep it comprehensive but concise (4-5 sentences)."""

        conclusion = self.agents['moderator'].respond(prompt)
        self._add_transcript('Moderator', conclusion, round_number=None)

        print(f"   Conclusion: {conclusion[:80]}...")
        return conclusion

    def _get_recent_discussion(self, num_turns: int = 5) -> str:
        """Get recent conversation context"""
        recent = self.transcripts[-num_turns:] if len(self.transcripts) > num_turns else self.transcripts

        return '\n\n'.join([
            f"{t.speaker}: {t.content}"
            for t in recent
        ])


def create_panel_discussion_strands_v2(
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
) -> PanelDiscussionStrandsV2:
    """Factory function to create improved panel discussion system"""
    return PanelDiscussionStrandsV2(model_id=model_id)
