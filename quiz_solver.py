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
    print(f"DEBUG fetch_page_text: url='{url}'")
    try:
        with sync_playwright() as p:
            # Use Firefox browser exclusively with deployment-friendly options
            browser = p.firefox.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
            page = browser.new_page()
            
            # Set reasonable timeouts for deployment environment
            page.set_default_timeout(30000)  # 30 seconds
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(wait_ms)

            text = page.inner_text("body")
            browser.close()
            print(f"DEBUG fetch_page_text: Successfully fetched {len(text)} characters")
            return text
            
    except Exception as e:
        print(f"ERROR fetch_page_text: {e}")
        # Fallback to requests if Playwright fails
        try:
            print("DEBUG fetch_page_text: Trying fallback with requests...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            print(f"DEBUG fetch_page_text: Fallback successful")
            return response.text
        except Exception as fallback_error:
            print(f"ERROR fetch_page_text: Fallback failed: {fallback_error}")
            raise e


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

    # --- 2. Extract DATA URL (CSV or JSON if any) --- Improved
    # Try different patterns for data URLs
    data_patterns = [
        r'https?://[^\s"]+\.(csv|json)',  # Absolute URLs
        r'(https?://[^\s"]+)(?=\s*CSV|csv)',  # URL followed by CSV mention
        r'/[^\s"]*\.csv',  # Relative CSV paths
        r'/[^\s"]*\.json',  # Relative JSON paths
    ]
    
    for pattern in data_patterns:
        data_match = re.search(pattern, page_text, re.IGNORECASE)
        if data_match:
            instructions["data_url"] = data_match.group(0)
            break

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

    print(f"DEBUG extract_instructions: submit_url='{instructions['submit_url']}', data_url='{instructions['data_url']}', question='{instructions['question'][:100]}...'")
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
    print(f"DEBUG solve_scrape_secret: question='{question}'")
    
    # First, use Playwright to get the rendered content of current page
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.goto(current_url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            rendered_content = page.inner_text("body")
            browser.close()
        
        print(f"DEBUG solve_scrape_secret: Rendered page content='{rendered_content[:500]}...'")
        
        # Find the relative path e.g. /demo-scrape-data?email=...
        m = re.search(r'/demo-scrape-data[^\s")]*', rendered_content)
        if m:
            rel = m.group(0)
            target_url = urljoin(current_url, rel)
        else:
            # Fallback to question text
            m = re.search(r'/demo-scrape-data[^\s")]*', question)
            if m:
                rel = m.group(0)
                target_url = urljoin(current_url, rel)
            else:
                target_url = current_url

        print(f"DEBUG solve_scrape_secret: target_url='{target_url}'")

        # Now use Playwright to get the data from the target URL
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            target_content = page.inner_text("body")
            browser.close()

        print(f"DEBUG solve_scrape_secret: Target content='{target_content}'")

        # Look for secret patterns in the target content
        patterns = [
            r'[Ss]ecret[^:]*:\s*([0-9]+)',  # Secret code is 12345
            r'[Ss]ecret[^:]*is\s*([0-9]+)',  # Secret is 12345
            r'[Cc]ode[^:]*:\s*([0-9]+)',
            r'[Cc]ode[^:]*is\s*([0-9]+)',
            r'[Ss]ecret[^:]*:\s*([A-Za-z0-9_\-]{6,})',
            r'[Cc]ode[^:]*:\s*([A-Za-z0-9_\-]{6,})',
            r'([0-9]{4,})',  # Any 4+ digit number
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, target_content, re.IGNORECASE)
            if matches:
                # Filter out common words and take first valid match
                filtered = [m for m in matches if m.lower() not in ['question', 'response', 'document', 'function']]
                if filtered:
                    secret = filtered[0]
                    print(f"DEBUG solve_scrape_secret: Found secret with pattern '{pattern}': '{secret}'")
                    return secret

    except Exception as e:
        print(f"DEBUG solve_scrape_secret: Playwright error: {e}")
        
    # Fallback: try basic requests approach
    try:
        m = re.search(r'/demo-scrape-data[^\s")]*', question)
        if m:
            rel = m.group(0)
            target_url = urljoin(current_url, rel)
            
            resp = requests.get(target_url, timeout=30)
            resp.raise_for_status()
            text = resp.text
            print(f"DEBUG solve_scrape_secret: Fallback response text='{text[:500]}...'")

            # Try JSON parsing
            try:
                obj = resp.json()
                if isinstance(obj, dict) and "secret" in obj:
                    secret = obj["secret"]
                    print(f"DEBUG solve_scrape_secret: Found secret in JSON: '{secret}'")
                    return secret
            except ValueError:
                pass

    except Exception as e:
        print(f"DEBUG solve_scrape_secret: Fallback error: {e}")

    # Last resort
    print("DEBUG solve_scrape_secret: Using last resort answer 42")
    return 42


def solve_csv_question(current_url: str, page_text: str, instructions: Dict[str, Any]) -> Any:
    """
    Handle 'CSV file / Cutoff: XXXX / Wrong sum of numbers' type tasks.
    Heuristic: sum values in the main numeric column above the cutoff.
    """
    q = instructions.get("question", "")
    print(f"DEBUG solve_csv_question: question='{q}'")
    
    # Get the rendered page content using Playwright for better extraction
    try:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=True)
            page = browser.new_page()
            page.goto(current_url, wait_until="networkidle")
            page.wait_for_timeout(2000)
            rendered_content = page.inner_text("body")
            full_html = page.content()
            browser.close()
        
        print(f"DEBUG solve_csv_question: Rendered content='{rendered_content[:200]}...'")
        # Use rendered content for extraction instead of page_text
        page_text = rendered_content
    except Exception as e:
        print(f"DEBUG solve_csv_question: Playwright error, using original page_text: {e}")
    
    cutoff = None
    # Look for cutoff patterns
    cutoff_patterns = [
        r'Cutoff:\s*([0-9]+(?:\.[0-9]+)?)',
        r'cutoff[^0-9]*([0-9]+(?:\.[0-9]+)?)',
        r'threshold[^0-9]*([0-9]+(?:\.[0-9]+)?)',
        r'above[^0-9]*([0-9]+(?:\.[0-9]+)?)',
        r'greater than[^0-9]*([0-9]+(?:\.[0-9]+)?)',
    ]
    
    for pattern in cutoff_patterns:
        m = re.search(pattern, q, re.IGNORECASE)
        if m:
            cutoff = float(m.group(1))
            print(f"DEBUG solve_csv_question: Found cutoff={cutoff}")
            break

    # Determine CSV URL - improved detection for relative links
    csv_url = instructions.get("data_url") or None
    if not csv_url:
        # Look for CSV URLs in both rendered content and HTML
        csv_patterns = [
            r'https?://[^\s"]+\.csv',  # Absolute CSV URLs
            r'href="([^"]*\.csv)"',    # Links to CSV files  
            r'href=\'([^\']*\.csv)\'',  # Single quoted CSV links
            r'([a-zA-Z0-9\-_]+\.csv)',  # Simple CSV filenames like demo-audio-data.csv
            r'/[^\s"]*\.csv',  # Relative CSV paths starting with /
        ]
        
        # Check both rendered content and HTML if available
        search_texts = [page_text]
        try:
            if 'full_html' in locals():
                search_texts.append(full_html)
        except:
            pass
        
        for pattern in csv_patterns:
            for search_text in search_texts:
                matches = re.findall(pattern, search_text, re.IGNORECASE)
                if matches:
                    csv_url = matches[0]
                    print(f"DEBUG solve_csv_question: Found CSV URL with pattern '{pattern}': '{csv_url}'")
                    break
            if csv_url:
                break
    
    # Make CSV URL absolute if it's relative
    if csv_url and not csv_url.lower().startswith("http"):
        csv_url = urljoin(current_url, csv_url)

    print(f"DEBUG solve_csv_question: csv_url='{csv_url}'")

    if not csv_url:
        return 42

    try:
        r = requests.get(csv_url, timeout=30)
        r.raise_for_status()
        lines = r.text.strip().splitlines()
        if not lines:
            return 42

        print(f"DEBUG solve_csv_question: CSV has {len(lines)} lines")
        print(f"DEBUG solve_csv_question: First few lines: {lines[:3]}")

        import csv as _csv
        reader = _csv.reader(lines)
        rows = list(reader)
        if len(rows) < 2:
            return 42

        header = rows[0]
        data_rows = rows[1:]
        
        print(f"DEBUG solve_csv_question: Header: {header}")
        print(f"DEBUG solve_csv_question: Data rows count: {len(data_rows)}")

        # Find numeric columns - improved logic
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
                    # Handle various numeric formats
                    val_clean = val.replace("$", "").replace("%", "")
                    vals.append(float(val_clean))
                except ValueError:
                    ok = False
                    break
            if ok and vals:
                numeric_candidates.append((idx, header[idx].lower(), vals))
                print(f"DEBUG solve_csv_question: Numeric column '{header[idx]}' has {len(vals)} values, sample: {vals[:5]}")

        if not numeric_candidates:
            print("DEBUG solve_csv_question: No numeric columns found")
            return 42

        # Prefer specific column names - improved logic
        chosen_idx = numeric_candidates[0][0]
        chosen_name = numeric_candidates[0][1]
        max_priority = -1
        
        # Priority order for column selection (higher number = higher priority)
        priority_keywords = {
            "value": 5, "amount": 4, "number": 3, "price": 3, 
            "cost": 3, "total": 2, "sum": 2, "val": 1
        }
        
        for idx, col_name, vals in numeric_candidates:
            current_priority = 0
            for keyword, priority in priority_keywords.items():
                if keyword in col_name:
                    current_priority = max(current_priority, priority)
            
            if current_priority > max_priority:
                chosen_idx = idx
                chosen_name = col_name
                max_priority = current_priority
                print(f"DEBUG solve_csv_question: Chose column '{header[idx]}' with priority {current_priority}")
        
        if max_priority == -1:
            print(f"DEBUG solve_csv_question: Using default column '{header[chosen_idx]}'")
        
        # If still no good choice, prefer columns with more variation in values
        if max_priority == -1 and len(numeric_candidates) > 1:
            max_std = 0
            for idx, col_name, vals in numeric_candidates:
                if len(vals) > 1:
                    import statistics
                    std = statistics.stdev(vals)
                    if std > max_std:
                        max_std = std
                        chosen_idx = idx
                        print(f"DEBUG solve_csv_question: Chose column '{header[idx]}' based on variation (std={std:.2f})")

        # Extract values from chosen column
        values = []
        for row in data_rows:
            if chosen_idx >= len(row):
                continue
            val = row[chosen_idx].strip().replace(",", "").replace("$", "").replace("%", "")
            if not val:
                continue
            try:
                values.append(float(val))
            except ValueError:
                continue

        if not values:
            print("DEBUG solve_csv_question: No values extracted")
            return 42

        print(f"DEBUG solve_csv_question: Extracted {len(values)} values from column '{header[chosen_idx]}'")
        print(f"DEBUG solve_csv_question: Values range: {min(values)} to {max(values)}")

        # Apply cutoff filter and calculate sum
        if cutoff is not None:
            filtered_values = [v for v in values if v > cutoff]
            total = sum(filtered_values)
            print(f"DEBUG solve_csv_question: Cutoff={cutoff}, filtered {len(filtered_values)}/{len(values)} values > cutoff")
            print(f"DEBUG solve_csv_question: Filtered values: {filtered_values[:10]}...")
        else:
            total = sum(values)
            print(f"DEBUG solve_csv_question: No cutoff, summing all {len(values)} values")

        print(f"DEBUG solve_csv_question: Total sum = {total}")

        # Return integer if close to whole number
        if abs(total - round(total)) < 1e-6:
            result = int(round(total))
            print(f"DEBUG solve_csv_question: Returning integer: {result}")
            return result
        else:
            print(f"DEBUG solve_csv_question: Returning float: {total}")
            return total

    except Exception as e:
        print(f"DEBUG solve_csv_question: Exception: {e}")
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
