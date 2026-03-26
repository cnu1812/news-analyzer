"""
Researcher Agent for Morning Pulse.
Performs deep-dive searches on trending headlines to provide more context.
"""
import os
import random
from tavily import TavilyClient

class ResearchAgent:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if self.api_key and "tvly-" in self.api_key:
            self.client = TavilyClient(api_key=self.api_key)
        else:
            self.client = None
            print("[Researcher] Warning: TAVILY_API_KEY not found. Deep-dive research will be skipped.")

    def research_all(self, all_news: dict, max_stories: int = 3) -> dict:
        """
        Identify top stories across all categories and perform deep research.
        Returns a dictionary of {headline: research_context}.
        """
        if not self.client:
            return {}

        # 1. Collect all headlines
        candidates = []
        for category, stories in all_news.items():
            if isinstance(stories, list):
                for s in stories:
                    if isinstance(s, dict) and s.get("title"):
                        candidates.append(s["title"])
            elif category == "indian_market" and isinstance(stories, dict):
                for s in stories.get("articles", []):
                    if s.get("title"):
                        candidates.append(s["title"])

        if not candidates:
            return {}

        # 2. Pick top stories (for now, just pick 3 random ones or the first ones from distinct categories)
        # Optimization: preferentially pick from NYT, Tech, and World
        priority_categories = ["nyt", "tech_news", "world_news"]
        selected_headlines = []
        
        for cat in priority_categories:
            cat_stories = all_news.get(cat, [])
            if cat_stories and len(selected_headlines) < max_stories:
                selected_headlines.append(cat_stories[0]["title"])
        
        # Fill remaining if needed
        while len(selected_headlines) < max_stories and candidates:
            h = random.choice(candidates)
            if h not in selected_headlines:
                selected_headlines.append(h)
            candidates.remove(h)

        print(f"[Researcher] Performing deep-dives for {len(selected_headlines)} trending stories...")
        research_data = {}
        for headline in selected_headlines:
            try:
                print(f"      -> Researching: {headline[:60]}...")
                response = self.client.search(query=headline, search_depth="advanced", max_results=2)
                
                context = ""
                for result in response.get('results', []):
                    context += f"Source: {result.get('url')}\nContext: {result.get('content')}\n\n"
                
                research_data[headline] = context
            except Exception as e:
                print(f"      [Researcher] Warning: Failed to research '{headline}': {e}")

        return research_data

if __name__ == "__main__":
    # Test
    agent = ResearchAgent()
    test_news = {"nyt": [{"title": "Nvidia launches new Blackwell AI chips"}]}
    res = agent.research_all(test_news)
    print(res)
