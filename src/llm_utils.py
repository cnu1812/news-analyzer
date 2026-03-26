"""
Unified LLM Utilities for Morning Pulse.
Handles Groq (Llama-3.3-70B) and Gemini (2.0-flash) with automatic fallback.
"""
import os
import json
from groq import Groq
import google.generativeai as genai

# Try loading environment variables from .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def call_llm(system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
    """
    Unified LLM call with Groq-to-Gemini fallback.
    response_format: "text" or "json"
    """
    prefer_gemini = os.getenv("PREFER_GEMINI", "false").lower() == "true"
    
    # Define providers in order of preference
    if prefer_gemini:
        providers = ["gemini", "groq"]
    else:
        providers = ["groq", "gemini"]

    last_error = None
    for provider in providers:
        try:
            if provider == "groq":
                return _call_groq(system_prompt, user_prompt, response_format)
            elif provider == "gemini":
                return _call_gemini(system_prompt, user_prompt, response_format)
        except Exception as e:
            print(f"      [LLM] Warning: {provider.capitalize()} call failed: {e}")
            last_error = e
            continue
            
    raise Exception(f"All LLM providers failed. Last error: {last_error}")


def _call_groq(system_prompt: str, user_prompt: str, response_format: str) -> str:
    """Internal helper for Groq API."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found.")
        
    client = Groq(api_key=api_key)
    
    kwargs = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 6000 if "MASTERCLASS" in user_prompt else 2000,
    }
    
    if response_format == "json":
        kwargs["response_format"] = {"type": "json_object"}
        
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def _call_gemini(system_prompt: str, user_prompt: str, response_format: str) -> str:
    """Internal helper for Gemini API."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found.")
        
    genai.configure(api_key=api_key)
    
    # Use Gemini 3.1 Pro as the latest/most efficient model as requested
    # User can override via GEMINI_MODEL (e.g., gemini-2.0-pro-exp)
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-pro")
    model = genai.GenerativeModel(model_name)
    
    # Gemini uses a single prompt or chat history. 
    # For simplicity, we combine system and user prompts.
    full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"
    
    config = genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=8192 if "MASTERCLASS" in user_prompt else 4096,
    )
    
    if response_format == "json":
        config.response_mime_type = "application/json"
        
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text.strip()

if __name__ == "__main__":
    # Quick test
    try:
        res = call_llm("You are a helpful assistant.", "Say hello!")
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")
