$ErrorActionPreference = 'Stop'

Write-Host 'Running Jarvis routing smoke tests against LiteLLM...' -ForegroundColor Cyan

$script = @"
import os, json, requests

base_url = 'http://localhost:4000/v1/chat/completions'
api_key = os.environ.get('LITELLM_MASTER_KEY', '')
headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json',
}

results = []

def run_case(name, payload, timeout=180):
    try:
        r = requests.post(base_url, headers=headers, data=json.dumps(payload), timeout=timeout)
        status = r.status_code
        model = None
        preview = ''
        body = r.text[:500]
        try:
            j = r.json()
            model = j.get('model')
            preview = (j.get('choices', [{}])[0].get('message', {}).get('content', '') or '')[:220].replace('\n', ' ')
            body = json.dumps(j)[:500]
        except Exception:
            pass
        return {
            'name': name,
            'status': status,
            'model': model,
            'preview': preview,
            'raw': body,
        }
    except Exception as e:
        return {
            'name': name,
            'status': 'EXCEPTION',
            'model': None,
            'preview': '',
            'raw': str(e),
        }

img = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6pM6kAAAAASUVORK5CYII='

cases = [
    (
        'jarvis-simple',
        {
            'model': 'jarvis',
            'messages': [{'role': 'user', 'content': 'Say hello in one short sentence.'}],
            'temperature': 0,
            'max_tokens': 80,
        },
    ),
    (
        'jarvis-code',
        {
            'model': 'jarvis',
            'messages': [{'role': 'user', 'content': 'Write Python code for factorial using loop. Return code only.'}],
            'temperature': 0,
            'max_tokens': 140,
        },
    ),
    (
        'jarvis-reasoning',
        {
            'model': 'jarvis',
            'messages': [{'role': 'user', 'content': 'Think step by step in 3 bullets: compare two strategies for scaling an API.'}],
            'temperature': 0,
            'max_tokens': 180,
        },
    ),
    (
        'vision-image',
        {
            'model': 'Vision',
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'What is in this image?'},
                        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + img}},
                    ],
                }
            ],
            'temperature': 0,
            'max_tokens': 120,
        },
    ),
    (
        'vision-fallback-direct',
        {
            'model': 'vision-fallback',
            'messages': [{'role': 'user', 'content': 'In one sentence, what tasks are vision models good at?'}],
            'temperature': 0,
            'max_tokens': 80,
        },
    ),
]

for name, payload in cases:
    results.append(run_case(name, payload))

print(json.dumps(results, indent=2))
"@

docker compose exec litellm python -c $script
