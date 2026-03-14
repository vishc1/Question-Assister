"""
Response Generator Module
Uses GPT-4o-mini to generate response suggestions based on personal context
"""

from typing import List, Dict, Optional
import openai
from config import Config


class ResponseGenerator:
    """
    Generates interview response suggestions using GPT-4o-mini
    Acts as the user's "personal twin" based on provided context
    """

    # Identity System Prompt
    IDENTITY_PROMPT = """You are a real-time interview coach whispering talking points to a candidate mid-interview.

Your job: given the interviewer's question and the candidate's background, give 3 punchy bullet points the candidate can say out loud right now.

Rules:
- Write in first person ("I", "My", "I've")
- Sound like a confident human, not an AI or a resume
- Each bullet is ONE specific thing to say — 1-2 sentences max
- Lead with the strongest, most impressive point first
- Use concrete details from the background when available (project names, numbers, outcomes)
- If the background has no direct match, give a confident, relevant talking point a smart candidate would say
- Never start bullets with "I would" — use "I did", "I built", "I led", "I've worked on"
- No filler phrases like "Great question" or "That's a good point"

Format: exactly 3 bullet points, each starting with "• "."""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_bullet_points: int = None
    ):
        """
        Initialize response generator

        Args:
            api_key: OpenAI API key (defaults to config)
            model: GPT model to use (defaults to gpt-4o-mini)
            max_bullet_points: Maximum bullet points to generate
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.model = model or Config.GPT_MODEL
        self.max_bullet_points = max_bullet_points or Config.MAX_BULLET_POINTS

        # Set API key
        if self.api_key:
            openai.api_key = self.api_key

        # Stats
        self.stats = {
            "requests": 0,
            "successes": 0,
            "errors": 0,
            "total_tokens": 0
        }

    def generate_response(
        self,
        query: str,
        context: List[Dict],
        user_style_notes: str = ""
    ) -> Optional[List[str]]:
        """
        Generate response suggestions based on query and context

        Args:
            query: The interviewer's question
            context: List of relevant context from RAG (with 'content' key)
            user_style_notes: Optional notes about user's communication style

        Returns:
            List of bullet point suggestions, or None on error
        """
        if not self.api_key:
            print("✗ OpenAI API key not set")
            return None

        self.stats["requests"] += 1

        try:
            # Format context
            context_text = self._format_context(context)

            # Build user message
            user_message = self._build_user_message(query, context_text, user_style_notes)

            # Call GPT-4o-mini
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.IDENTITY_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=300,
                top_p=0.9
            )

            # Extract bullet points
            content = response.choices[0].message.content
            bullet_points = self._parse_bullet_points(content)

            # Update stats
            self.stats["successes"] += 1
            self.stats["total_tokens"] += response.usage.total_tokens

            return bullet_points

        except Exception as e:
            print(f"✗ Error generating response: {e}")
            self.stats["errors"] += 1
            return None

    def _format_context(self, context: List[Dict]) -> str:
        """Format context items into readable text"""
        if not context:
            return "No relevant history found."

        formatted = []
        for i, item in enumerate(context, 1):
            content = item.get('content', '')
            source = item.get('metadata', {}).get('file_name', 'Unknown')

            formatted.append(f"[Context {i} - from {source}]\n{content}")

        return "\n\n".join(formatted)

    def _build_user_message(
        self,
        query: str,
        context_text: str,
        style_notes: str
    ) -> str:
        """Build the user message for GPT"""
        message = f"""Question from interviewer:
"{query}"

Relevant history from your documents:
{context_text}
"""

        if style_notes:
            message += f"\n\nYour communication style:\n{style_notes}"

        message += f"\n\nProvide exactly {self.max_bullet_points} bullet points for how to respond."

        return message

    def _parse_bullet_points(self, content: str) -> List[str]:
        """Parse bullet points from GPT response"""
        lines = content.strip().split('\n')
        bullet_points = []

        for line in lines:
            line = line.strip()

            # Look for bullet point markers
            if line.startswith('•') or line.startswith('-') or line.startswith('*'):
                # Remove marker and clean
                text = line[1:].strip()
                if text:
                    bullet_points.append(text)

            # Also check for numbered points
            elif len(line) > 2 and line[0].isdigit() and line[1] in '.):':
                text = line[2:].strip()
                if text:
                    bullet_points.append(text)

        # Limit to max bullet points
        return bullet_points[:self.max_bullet_points]

    def get_stats(self) -> Dict:
        """Get generation statistics"""
        return self.stats.copy()

    def print_stats(self):
        """Print statistics"""
        print("\n" + "="*60)
        print("Response Generator Statistics")
        print("="*60)
        print(f"Total requests: {self.stats['requests']}")
        print(f"Successful: {self.stats['successes']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"Total tokens used: {self.stats['total_tokens']}")

        if self.stats['successes'] > 0:
            avg_tokens = self.stats['total_tokens'] / self.stats['successes']
            print(f"Average tokens per request: {avg_tokens:.1f}")

        print("="*60 + "\n")


def test_generator():
    """Test response generator"""
    print("\n" + "="*60)
    print("Testing Response Generator")
    print("="*60 + "\n")

    # Initialize generator
    generator = ResponseGenerator()

    # Test query
    query = "Tell me about a challenging Python project you worked on."

    # Simulated context from RAG
    context = [
        {
            "content": "Built a real-time analytics dashboard using Python, React, and WebSockets. "
                      "The main challenge was handling high-frequency data updates without impacting "
                      "performance. Implemented efficient data buffering and optimized database queries. "
                      "Reduced page load time by 60% through caching strategies.",
            "metadata": {"file_name": "projects.docx"}
        },
        {
            "content": "Led development of microservices architecture using Python and FastAPI. "
                      "Faced challenges with service discovery and inter-service communication. "
                      "Implemented circuit breaker pattern and retry logic. Mentored junior developers "
                      "on distributed systems concepts.",
            "metadata": {"file_name": "resume.pdf"}
        },
        {
            "content": "Developed machine learning recommendation system using TensorFlow and scikit-learn. "
                      "Challenge was dealing with sparse data and cold start problem. Experimented with "
                      "different algorithms and settled on hybrid approach combining collaborative and "
                      "content-based filtering.",
            "metadata": {"file_name": "projects.docx"}
        }
    ]

    # Generate response
    print(f"Query: {query}\n")
    print("Generating response suggestions...\n")

    bullet_points = generator.generate_response(query, context)

    if bullet_points:
        print("="*60)
        print("SUGGESTED RESPONSES")
        print("="*60 + "\n")

        for i, point in enumerate(bullet_points, 1):
            print(f"{i}. {point}\n")

        print("="*60)
    else:
        print("✗ Failed to generate response")

    # Print stats
    generator.print_stats()


if __name__ == "__main__":
    test_generator()
