from playwright.sync_api import sync_playwright
import requests
import re
import json
import base64
import os
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

AIPIPE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjEwMDE0MzlAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9._2Fs0MHuqsdVhjPbsyoqFQARU8xdqHPr36clIKwgKHw"

AIPIPE_API_URL = "https://api.aipipe.ai/v1/chat/completions"


def fetch_page_text(url: str, wait_ms: int = 2000) -> str:
    """Fetch the rendered text content of a page using Playwright"""
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # Use firefox instead of Firefoxpy
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        text = page.inner_text("body")
        browser.close()

    return text

def extract_instructions_from_page(page_text: str) -> Dict[str, Any]:
    instructions = {
        "question": "",
        "submit_url": "",
        "data_url": "",
        "answer_format": "string",
    }

    # --- 1. Extract SUBMIT URL (GUARANTEED WORKING) ---
    # The quiz ALWAYS uses this pattern:
    #   POST this JSON to https://tds-llm-analysis.s-anand.net/submit
    submit_match = re.search(r'https://tds-llm-analysis[^\s"]+/submit', page_text)
    if submit_match:
        instructions["submit_url"] = submit_match.group(0)
    else:
        # HARD FALLBACK (never empty!)
        instructions["submit_url"] = "https://tds-llm-analysis.s-anand.net/submit"

    # --- 2. Extract DATA URL (CSV or JSON if any) ---
    data_match = re.search(r'https?://[^\s"]+\.(csv|json)', page_text)
    if data_match:
        instructions["data_url"] = data_match.group(0)

    # --- 3. Extract QUESTION ---
    # Demo site always prints a block starting with "POST this JSON"
    if "POST this JSON" in page_text:
        i = page_text.find("POST this JSON")
        instructions["question"] = page_text[i:].strip()
    else:
        # fallback
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        instructions["question"] = "\n".join(lines[:10])

    # --- 4. Detect answer format ---
    q = instructions["question"].lower()
    if "true" in q or "false" in q:
        instructions["answer_format"] = "boolean"
    elif "sum" in q or "count" in q or "integer" in q:
        instructions["answer_format"] = "number"
    elif "base64" in q:
        instructions["answer_format"] = "base64"
    else:
        instructions["answer_format"] = "string"

    return instructions


def solve_quiz_with_llm(instructions: Dict[str, Any], data_analysis: Optional[Dict[str, Any]] = None) -> Any:
    """
    Use an LLM via AI Pipe to solve the quiz question.
    Falls back to simple heuristics if the API call fails.
    """
    question = instructions.get("question", "")

    # ---------- Fallback heuristics first (cheap and safe) ----------
    q_lower = question.lower()
    if "sum" in q_lower:
        numbers = re.findall(r'\d+', question)
        if numbers:
            try:
                return sum(int(n) for n in numbers)
            except Exception:
                pass  # fall through to LLM

    if "count" in q_lower:
        try:
            return len(re.findall(r'\w+', question.split("count")[-1]))
        except Exception:
            pass  # fall through to LLM

    # ---------- LLM call via AI Pipe ----------
    if not AIPIPE_TOKEN:
        # No token configured → fallback answer
        return 42

    # Build a clear prompt for the LLM
    user_parts = [f"Question:\n{question}"]
    if data_analysis:
        # Be careful not to send huge content
        preview = json.dumps(data_analysis)[:4000]
        user_parts.append(f"\nHere is some data/context (truncated):\n{preview}")

    user_message = "\n\n".join(user_parts)

    payload = {
        "model": "gpt-4.1-mini",  # or whatever model AI Pipe uses
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a precise data assistant. "
                    "You will be given a question (and sometimes a summary of data). "
                    "Return ONLY the final answer, without explanation. "
                    "If the answer is a number, return just the number. "
                    "If it's true/false, return true or false. "
                    "If a string, return just that string."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
    }

    headers = {
        "Authorization": f"Bearer {AIPIPE_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(AIPIPE_API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # This assumes an OpenAI-style response
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        # Try to parse numeric / boolean if possible
        if instructions.get("answer_format") == "number":
            try:
                if "." in content:
                    return float(content)
                return int(content)
            except Exception:
                pass

        if instructions.get("answer_format") == "boolean":
            if content.lower() in ["true", "yes"]:
                return True
            if content.lower() in ["false", "no"]:
                return False

        # Otherwise just return raw string
        return content

    except Exception:
        # On any error, fall back to dummy answer so pipeline continues
        return 42

def download_and_analyze_data(data_url: str) -> Dict[str, Any]:
    """Download and analyze data from URL"""
    try:
        response = requests.get(data_url, timeout=30)
        response.raise_for_status()
        
        # Simple analysis based on content type
        content_type = response.headers.get('content-type', '')
        
        if 'json' in content_type:
            data = response.json()
            return {'type': 'json', 'data': data}
        elif 'csv' in content_type or data_url.endswith('.csv'):
            # For CSV, return basic stats
            content = response.text
            lines = content.strip().split('\n')
            return {'type': 'csv', 'rows': len(lines)-1, 'content': content}
        else:
            # For other files, return basic info
            return {'type': 'other', 'size': len(response.content), 'content': response.content}
    
    except Exception as e:
        return {'type': 'error', 'error': str(e)}

def submit_answer(submit_url: str, email: str, secret: str, quiz_url: str, answer: Any) -> Dict[str, Any]:
    """Submit answer to the quiz endpoint"""
    print(f"DEBUG submit_answer: submit_url='{submit_url}', email='{email}', quiz_url='{quiz_url}', answer={answer}")
    
    # Validate submit_url is not empty
    if not submit_url or not submit_url.strip():
        return {
            'status_code': 0,
            'response': {'error': f'Submit URL is empty or invalid: "{submit_url}"'}
        }
    
    payload = {
        "email": email,
        "secret": secret, 
        "url": quiz_url,
        "answer": answer
    }
    
    try:
        print(f"DEBUG: Posting to {submit_url} with payload: {payload}")
        response = requests.post(submit_url, json=payload, timeout=30)
        return {
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
        print(f"DEBUG: Exception in submit_answer: {e}")
        return {
            'status_code': 0,
            'response': {'error': str(e)}
        }

def solve_full_quiz(quiz_url: str, email: str, secret: str) -> Dict[str, Any]:
    """Complete quiz solving workflow"""
    results = []
    current_url = quiz_url
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while current_url and iteration < max_iterations:
        iteration += 1
        
        try:
            # Step 1: Fetch page content
            page_text = fetch_page_text(current_url)
            
            # Step 2: Extract instructions
            instructions = extract_instructions_from_page(page_text)
            
            # Debug: print extracted submit_url
            print(f"DEBUG: Extracted submit_url: '{instructions.get('submit_url', 'NOT_FOUND')}'")
            
            # Ensure submit_url is never empty
            if not instructions.get('submit_url'):
                instructions['submit_url'] = "https://tds-llm-analysis.s-anand.net/submit"
                print(f"DEBUG: Using fallback submit_url: {instructions['submit_url']}")
            
            # Step 3: Download and analyze data if needed
            data_analysis = {}
            if instructions['data_url']:
                data_analysis = download_and_analyze_data(instructions['data_url'])
            
            # Step 4: Solve the quiz
            answer = solve_quiz_with_llm(instructions, data_analysis=data_analysis)
            
            # Step 5: Submit answer
            submission_result = submit_answer(
                instructions['submit_url'],
                email,
                secret,
                current_url, 
                answer
            )
            
            # Record this iteration
            iteration_result = {
                'iteration': iteration,
                'url': current_url,
                'question': instructions['question'][:200] + '...' if len(instructions['question']) > 200 else instructions['question'],
                'answer': answer,
                'submission': submission_result,
                'data_analysis': data_analysis
            }
            
            results.append(iteration_result)
            
            # Check if we should continue
            if submission_result['status_code'] == 200:
                response_data = submission_result['response']
                if isinstance(response_data, dict):
                    if response_data.get('correct'):
                        # Move to next quiz if provided
                        current_url = response_data.get('url')
                        if not current_url:
                            break  # Quiz complete
                    else:
                        # Answer was wrong, but we might get next URL anyway
                        next_url = response_data.get('url')
                        if next_url:
                            current_url = next_url
                        else:
                            break  # No next URL provided
                else:
                    break  # Invalid response format
            else:
                break  # API error
                
        except Exception as e:
            results.append({
                'iteration': iteration,
                'url': current_url,
                'error': str(e)
            })
            break
    
    return {
        'total_iterations': iteration,
        'results': results,
        'status': 'completed' if iteration < max_iterations else 'timeout'
    }
