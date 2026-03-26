import os
import json
from llm_utils import call_llm

class FactChecker:
    def __init__(self):
        # We check for keys primarily in call_llm, but we can do a quick check here for reporting
        self.has_keys = os.getenv("GROQ_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.has_keys:
            print("[FactChecker] Warning: No LLM API keys found. Fact-checking will be skipped.")

    def verify_news(self, all_news: dict) -> dict:
        """
        Runs a "Fact Consistency" pass on the collected news.
        Removes stories that are flagged as high-risk, conflicting, or non-genuine.
        """
        if not self.has_keys:
            return all_news

        print("[FactChecker] Performing automated cross-reference analysis...")
        
        # 1. Prepare a compact list of all stories for the LLM to review
        summaries = []
        for cat, stories in all_news.items():
            if isinstance(stories, list):
                for s in stories:
                    summaries.append({"cat": cat, "title": s.get("title"), "summary": s.get("summary", "")[:200]})
            elif cat == "indian_market" and isinstance(stories, dict):
                for s in stories.get("articles", []):
                    summaries.append({"cat": cat, "title": s.get("title"), "summary": s.get("summary", "")[:200]})

        if not summaries:
            return all_news

        # 2. Ask Groq to rank them and identify potential fakes or conflicts
        system_prompt = """You are an elite Fact-Checking Senior Editor.
Your job is to cross-reference news stories and ensure ONLY genuine, verified, and high-impact news reaches the script writer.
Review the list of news provided (category, title, summary).
Discard:
- Blatant PR pieces or corporate "fluff".
- Minor celebrity gossip or low-impact clickbait.
- Stories that seem factually inconsistent or suspicious.
- Redundant stories (keep only the strongest version).

CRITICAL: If two sources report the same event with conflicting core facts, discard both unless one is significantly more authoritative (like NYT or Reuters).

OUTPUT: Return a JSON array of the "Approved" story TITLES only."""

        user_prompt = f"Review these {len(summaries)} news summaries and return a JSON list of the most genuine, high-quality story titles:\n\n"
        user_prompt += json.dumps(summaries, indent=2)

        try:
            response_text = call_llm(system_prompt, user_prompt, response_format="json")
            
            # The model might return {"approved_titles": [...]} or just [...]
            # Standardizing JSON extraction for Gemini/Groq
            start = response_text.find('[') if response_text.strip().startswith('[') else response_text.find('{')
            end = (response_text.rfind(']') if response_text.strip().startswith('[') else response_text.rfind('}')) + 1
            if start != -1 and end != 0:
                response_text = response_text[start:end]

            data = json.loads(response_text)
            approved_titles = data.get("approved_titles", []) if isinstance(data, dict) else data
            
            if not isinstance(approved_titles, list):
                # Fallback if the JSON structure is different
                approved_titles = list(data.values())[0] if isinstance(data, dict) and data else []

            print(f"      -> {len(approved_titles)} stories approved out of {len(summaries)} total.")
            
            # 3. Filter the original news based on approved titles
            filtered_news = {}
            for cat, val in all_news.items():
                if isinstance(val, list):
                    filtered_news[cat] = [s for s in val if s.get("title") in approved_titles]
                elif cat == "indian_market" and isinstance(val, dict):
                    idx = val.get("indices", {})
                    arts = [s for s in val.get("articles", []) if s.get("title") in approved_titles]
                    filtered_news[cat] = {"indices": idx, "articles": arts}
                else:
                    filtered_news[cat] = val
                    
            return filtered_news

        except Exception as e:
            print(f"      [FactChecker] Warning: Analysis failed ({e}). Proceeding with original news set.")
            return all_news

if __name__ == "__main__":
    # Test
    checker = FactChecker()
    test_news = {"nyt": [{"title": "Market Crash in Japan", "summary": "Nikkei down 10%"}], 
                 "tech": [{"title": "New iPhone 16 Leaks", "summary": "Rumors say it has no buttons"}]}
    res = checker.verify_news(test_news)
    print(res)
