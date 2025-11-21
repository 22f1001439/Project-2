from playwright.sync_api import sync_playwright
import requests
import re
import json
import base64
import os
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

# --- LLM via AI Pipe ---
AIPIPE_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjEwMDE0MzlAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9._2Fs0MHuqsdVhjPbsyoqFQARU8xdqHPr36clIKwgKHw"
AIPIPE_API_URL = "https://api.aipipe.ai/v1/chat/completions"


def fetch_page_text(url: str, wait_ms: int = 2000) -> str:
    """Fetch the rendered text content of a page using Playwright."""
    with sync_playwright() as p:
        # Use whichever browser you installed on Render: firefox or chromium
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        text = page.inner_text("body")
        browser.close()

    return text


def extract_instructions_from_page(page_text: str) -> Dict[str, Any]:
    """Extract quiz instructions and submission details from page text."""
    instructions = {
        "question": "",
        "submit_url": "",
        "data_url": "",
        "answer_format": "string",
    }

    # --- 1. Extract SUBMIT URL (never leave it empty) ---
    submit_match = re.search(r'https://tds-llm-analysis[^\s"]+/submit', page_text)
    if submit_match:
        instructions["submit_url"] = submit_match.group(0)
    else:
        # Hard fallback – demo always uses this
        instructions["submit_url"] = "https://tds-llm-analysis.s-anand.net/submit"

    # --- 2. Extract DATA URL (CSV or JSON if any) ---
    data_match = re.search(r'https?://[^\s"]+\.(csv|json)', page_text)
    if data_match:
        instructions["data_url"] = data_match.group(0)

    # --- 3. Extract QUESTION ---
    if "POST this JSON" in page_text:
        i = page_text.find("POST this JSON")
        instructions["question"] = page_text[i:].strip()
    else:
        # fallback: first few non-empty lines
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        instructions["question"] = "\n".join(lines[:10])

    # --- 4. Detect answer format ---
    q = instructions["question"].lower()
    if "true" in q or "false" in q:
        instructions["answer_format"] = "boolean"
    elif "sum" in q or "count" in q or "integer" in q or "number" in q:
        instructions["answer_format"] = "number"
    elif "base64" in q or "image" in q:
        instructions["answer_format"] = "base64"
    else:
        instructions["answer_format"] = "string"

    return instructions


# -------------------------
# Special-case solvers
# -------------------------

def solve_scrape_secret(current_url: str, instructions: Dict[str, Any]) -> Any:
    """
    Handle tasks like:
      'Scrape /demo-scrape-data?... Get the secret code from this page...'
    """
    question = instructions.get("question", "")
    # Find the relative path e.g. /demo-scrape-data?email=...
    m = re.search(r'/demo-scrape-data[^\s")]*', question)
    if m:
        rel = m.group(0)
        target_url = urljoin(current_url, rel)
    else:
        # fallback: just use current URL (unlikely)
        target_url = current_url

    try:
        resp = requests.get(target_url, timeout=30)
        resp.raise_for_status()
        text = resp.text

        # 1) Try JSON with "secret"
        try:
            obj = resp.json()
            if isinstance(obj, dict) and "secret" in obj:
                return obj["secret"]
        except ValueError:
            pass

        # 2) Look for "secret code: XYZ"
        m2 = re.search(r'[Ss]ecret[^:]*:\s*([A-Za-z0-9_\-]+)', text)
        if m2:
            return m2.group(1)

        # 3) Fallback: first long token
        tokens = re.findall(r'[A-Za-z0-9_\-]{6,}', text)
        if tokens:
            return tokens[0]

    except Exception:
        pass

    # As last resort
    return 42


def solve_csv_question(current_url: str, page_text: str, instructions: Dict[str, Any]) -> Any:
    """
    Handle 'CSV file / Cutoff: XXXX / Wrong sum of numbers' type tasks.
    Heuristic: sum values in the main numeric column above the cutoff.
    """
    q = instructions.get("question", "")
    cutoff = None
    m = re.search(r'Cutoff:\s*([0-9]+(?:\.[0-9]+)?)', q)
    if m:
        cutoff = float(m.group(1))

    # Determine CSV URL
    csv_url = instructions.get("data_url") or None
    if not csv_url:
        # Look for absolute CSV URL
        m_abs = re.search(r'https?://[^\s"]+\.csv', page_text)
        if m_abs:
            csv_url = m_abs.group(0)
        else:
            # Look for relative CSV path
            m_rel = re.search(r'/[^\s"]+\.csv', page_text)
            if m_rel:
                csv_url = urljoin(current_url, m_rel.group(0))
    elif not csv_url.lower().startswith("http"):
        csv_url = urljoin(current_url, csv_url)

    if not csv_url:
        return 42

    try:
        r = requests.get(csv_url, timeout=30)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if not lines:
            return 42

        import csv as _csv
        reader = _csv.reader(lines)
        rows = list(reader)
        if len(rows) < 2:
            return 42

        header = rows[0]
        data_rows = rows[1:]

        # Find numeric columns
        numeric_candidates = []
        for idx in range(len(header)):
            vals = []
            ok = True
            for row in data_rows:
                if idx >= len(row):
                    continue
                val = row[idx].strip().replace(",", "")
                if not val:
                    continue
                try:
                    vals.append(float(val))
                except ValueError:
                    ok = False
                    break
            if ok and vals:
                numeric_candidates.append((idx, header[idx].lower(), vals))

        if not numeric_candidates:
            return 42

        # Prefer 'value'/'amount' column if present
        chosen_idx = numeric_candidates[0][0]
        for idx, col_name, _vals in numeric_candidates:
            if any(key in col_name for key in ["value", "amount", "number"]):
                chosen_idx = idx
                break

        values = []
        for row in data_rows:
            if chosen_idx >= len(row):
                continue
            val = row[chosen_idx].strip().replace(",", "")
            if not val:
                continue
            try:
                values.append(float(val))
            except ValueError:
                continue

        if not values:
            return 42

        if cutoff is not None:
            total = sum(v for v in values if v > cutoff)
        else:
            total = sum(values)

        if abs(total - round(total)) < 1e-6:
            return int(round(total))
        return total

    except Exception:
        return 42


# -------------------------
# Generic LLM solver
# -------------------------

def solve_quiz_with_llm(
    instructions: Dict[str, Any],
    data_analysis: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Use an LLM via AI Pipe to solve the quiz question.
    Falls back to simple heuristics if the API call fails.
    """
    question = instructions.get("question", "")

    # Simple heuristic first
    q_lower = question.lower()
    if "sum" in q_lower:
        numbers = re.findall(r'\d+', question)
        if numbers:
            try:
                return sum(int(n) for n in numbers)
            except Exception:
                pass

    if "count" in q_lower:
        try:
            return len(re.findall(r'\w+', question.split("count")[-1]))
        except Exception:
            pass

    # LLM call
    if not AIPIPE_TOKEN:
        return 42

    user_parts = [f"Question:\n{question}"]
    if data_analysis:
        preview = json.dumps(data_analysis)[:4000]
        user_parts.append(f"\nHere is some data/context (truncated):\n{preview}")

    user_message = "\n\n".join(user_parts)

    payload = {
        "model": "gpt-4.1-mini",
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

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

        # Coerce types based on answer_format
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

        return content

    except Exception:
        return 42


# -------------------------
# Data download helper
# -------------------------

def download_and_analyze_data(data_url: str) -> Dict[str, Any]:
    """Download and analyze data from URL."""
    try:
        response = requests.get(data_url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        if "json" in content_type:
            data = response.json()
            return {"type": "json", "data": data}
        elif "csv" in content_type or data_url.endswith(".csv"):
            content = response.text
            lines = content.strip().split("\n")
            return {"type": "csv", "rows": len(lines) - 1, "content": content}
        else:
            return {"type": "other", "size": len(response.content)}

    except Exception as e:
        return {"type": "error", "error": str(e)}


# -------------------------
# Submission helper
# -------------------------

def submit_answer(
    submit_url: str,
    email: str,
    secret: str,
    quiz_url: str,
    answer: Any
) -> Dict[str, Any]:
    """Submit answer to the quiz endpoint."""
    print(f"DEBUG submit_answer: submit_url='{submit_url}', quiz_url='{quiz_url}', answer={answer}")

    if not submit_url or not submit_url.strip():
        return {
            "status_code": 0,
            "response": {"error": f'Submit URL is empty or invalid: "{submit_url}"'},
        }

    payload = {
        "email": email,
        "secret": secret,
        "url": quiz_url,
        "answer": answer,
    }

    try:
        response = requests.post(submit_url, json=payload, timeout=30)
        return {
            "status_code": response.status_code,
            "response": response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text,
        }
    except Exception as e:
        print(f"DEBUG: Exception in submit_answer: {e}")
        return {
            "status_code": 0,
            "response": {"error": str(e)},
        }


# -------------------------
# Main quiz workflow
# -------------------------

def solve_full_quiz(quiz_url: str, email: str, secret: str) -> Dict[str, Any]:
    """Complete quiz solving workflow over multiple URLs."""
    results = []
    current_url = quiz_url
    max_iterations = 10
    iteration = 0

    while current_url and iteration < max_iterations:
        iteration += 1

        try:
            # Step 1: Fetch page content
            page_text = fetch_page_text(current_url)

            # Step 2: Extract instructions
            instructions = extract_instructions_from_page(page_text)
            print(f"DEBUG: Iter {iteration}, submit_url='{instructions.get('submit_url')}', url='{current_url}'")

            if not instructions.get("submit_url"):
                instructions["submit_url"] = "https://tds-llm-analysis.s-anand.net/submit"

            # Step 3: Download and analyze data if needed
            data_analysis = {}
            if instructions["data_url"]:
                data_analysis = download_and_analyze_data(instructions["data_url"])

            # Step 4: Choose how to solve
            q_lower = instructions["question"].lower()
            answer: Any

            if "demo-scrape-data" in instructions["question"] or "secret code" in q_lower:
                # Scrape the secret from another page
                answer = solve_scrape_secret(current_url, instructions)
            elif "csv file" in q_lower or ".csv" in q_lower or instructions["data_url"].endswith(".csv"):
                # Handle CSV cutoff / sum task
                answer = solve_csv_question(current_url, page_text, instructions)
            else:
                # Generic LLM-based solving
                answer = solve_quiz_with_llm(instructions, data_analysis=data_analysis)

            # Step 5: Submit answer
            submission_result = submit_answer(
                instructions["submit_url"],
                email,
                secret,
                current_url,
                answer,
            )

            # Record this iteration
            iteration_result = {
                "iteration": iteration,
                "url": current_url,
                "question": (
                    instructions["question"][:200] + "..."
                    if len(instructions["question"]) > 200
                    else instructions["question"]
                ),
                "answer": answer,
                "submission": submission_result,
                "data_analysis": data_analysis,
            }
            results.append(iteration_result)

            # Step 6: Decide whether to continue
            if submission_result["status_code"] == 200:
                response_data = submission_result["response"]
                if isinstance(response_data, dict):
                    next_url = response_data.get("url")
                    if next_url:
                        current_url = next_url
                    else:
                        break
                else:
                    break
            else:
                break

        except Exception as e:
            results.append(
                {"iteration": iteration, "url": current_url, "error": str(e)}
            )
            break

    return {
        "total_iterations": iteration,
        "results": results,
        "status": "completed" if iteration < max_iterations else "timeout",
    }
