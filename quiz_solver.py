from playwright.sync_api import sync_playwright
import requests
import re
import json
import base64
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlparse

def fetch_page_text(url: str, wait_ms: int = 2000) -> str:
    """Fetch the rendered text content of a page using Playwright"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        text = page.inner_text("body")
        browser.close()

    return text

def extract_instructions_from_page(page_text: str) -> Dict[str, Any]:
    """Extract quiz instructions and submission details from page text"""
    instructions = {
        'question': '',
        'submit_url': '',
        'data_url': '',
        'answer_format': 'number'  # default
    }
    
    # Look for submission URL pattern
    submit_match = re.search(r'Post your answer to (https?://[^\s]+)', page_text)
    if submit_match:
        instructions['submit_url'] = submit_match.group(1)
    
    # Look for data download URLs
    data_match = re.search(r'Download.*?href="([^"]+)"', page_text)
    if data_match:
        instructions['data_url'] = data_match.group(1)
    
    # Extract the main question
    lines = page_text.split('\n')
    question_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('{'): 
            question_lines.append(line)
    
    instructions['question'] = '\n'.join(question_lines)
    
    # Determine answer format based on question content
    if 'true' in page_text.lower() or 'false' in page_text.lower():
        instructions['answer_format'] = 'boolean'
    elif 'sum' in page_text.lower() or 'count' in page_text.lower() or 'number' in page_text.lower():
        instructions['answer_format'] = 'number'
    elif 'base64' in page_text.lower() or 'image' in page_text.lower():
        instructions['answer_format'] = 'base64'
    else:
        instructions['answer_format'] = 'string'
    
    return instructions

def solve_quiz_with_llm(instructions: Dict[str, Any]) -> Any:
    """Use LLM reasoning to solve the quiz question"""
    # This is a simplified solver - in a real implementation,
    # you'd integrate with OpenAI/Anthropic APIs
    question = instructions['question']
    
    # Simple pattern matching for demo purposes
    # In reality, you'd send this to GPT-4/Claude with proper context
    
    if 'sum' in question.lower():
        # Look for numbers in the question for demo
        numbers = re.findall(r'\d+', question)
        if numbers:
            return sum(int(n) for n in numbers)
    
    if 'count' in question.lower():
        # Simple counting logic
        return len(re.findall(r'\w+', question.split('count')[-1] if 'count' in question else ''))
    
    # For the demo endpoint, return a simple response
    return 42  # Default answer for testing

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
    payload = {
        "email": email,
        "secret": secret, 
        "url": quiz_url,
        "answer": answer
    }
    
    try:
        response = requests.post(submit_url, json=payload, timeout=30)
        return {
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except Exception as e:
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
            
            # Step 3: Download and analyze data if needed
            data_analysis = {}
            if instructions['data_url']:
                data_analysis = download_and_analyze_data(instructions['data_url'])
            
            # Step 4: Solve the quiz
            answer = solve_quiz_with_llm(instructions)
            
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
