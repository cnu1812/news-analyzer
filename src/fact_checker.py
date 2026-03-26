"""
Automated Fact-Checker for Morning Pulse.
Uses Groq (Llama-3.3-70B) to cross-reference news sources and filter for consistency.
"""
import os
import json
from groq import Groq

class FactChecker:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
            print("[FactChecker] Warning: GROQ_API_KEY not found. Fact-checking will be skipped.")

    def verify_news(self, all_news: dict) -> dict:
        """
        Runs a "Fact Consistency" pass on the collected news.
        Removes stories that are flagged as high-risk, conflicting, or non-genuine.
        """
        if not self.client:
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
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # The model might return {"approved_titles": [...]} or just [...] 
            data = json.loads(response.choices[0].message.content)
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
