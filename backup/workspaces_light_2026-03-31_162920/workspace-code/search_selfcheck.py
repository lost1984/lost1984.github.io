#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

try:
    import requests
    from requests.auth import HTTPBasicAuth
except Exception:
    print('ERROR: missing requests package')
    sys.exit(2)

QUERY = 'OpenClaw selfcheck'
TIMEOUT = 20

GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
BLUE='\033[34m'
RESET='\033[0m'
BOLD='\033[1m'

def c(color, text):
    return f'{color}{text}{RESET}'

def print_header(title):
    print(f'\n{BOLD}=== {title} ==={RESET}')

def ok(msg):
    print(c(GREEN, f'OK   {msg}'))

def warn(msg):
    print(c(YELLOW, f'WARN {msg}'))

def err(msg):
    print(c(RED, f'FAIL {msg}'))

def info(msg):
    print(c(BLUE, f'INFO {msg}'))

def load_tavily_key():
    candidates = [
        Path('/root/.openclaw/openclaw.json'),
        Path('/root/.openclaw/workspace/memory/2026-03-27.md'),
        Path('/root/.openclaw/workspace/memory/2026-03-28.md'),
        Path('/root/.openclaw/workspace-code/memory/2026-03-27.md'),
        Path('/root/.openclaw/workspace-code/memory/2026-03-28.md'),
    ]
    for p in candidates:
        if p.exists():
            text = p.read_text(encoding='utf-8', errors='ignore')
            m = re.search(r'(tvly-[A-Za-z0-9\-_]+)', text)
            if m:
                return m.group(1), str(p)
    return None, None

def check_searxng():
    print_header('SearXNG')
    cfg_path = Path('/root/.openclaw/secrets/searxng.json')
    if not cfg_path.exists():
        err('config not found: /root/.openclaw/secrets/searxng.json')
        return False
    try:
        cfg = json.loads(cfg_path.read_text())
    except Exception as e:
        err(f'config parse error: {e}')
        return False

    base = cfg.get('baseUrl')
    user = cfg.get('user')
    pwd = cfg.get('pass')
    if not all([base, user, pwd]):
        err('config missing baseUrl/user/pass')
        return False

    info(f'baseUrl={base}')
    try:
        r = requests.get(
            base.rstrip('/') + '/search',
            params={'q': QUERY, 'format': 'json', 'engines': 'google,bing,duckduckgo'},
            auth=HTTPBasicAuth(user, pwd),
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            err(f'HTTP {r.status_code}')
            print(r.text[:500])
            return False
        data = r.json()
        results = data.get('results', [])
        ok(f'HTTP 200, results={len(results)}')
        for i, x in enumerate(results[:3], 1):
            title = (x.get('title') or '').replace('\n', ' ')[:100]
            url = x.get('url') or ''
            print(f'  [{i}] {title} | {url}')
        return True
    except Exception as e:
        err(repr(e))
        return False

def check_tavily():
    print_header('Tavily')
    key, source = load_tavily_key()
    if not key:
        err('API key not found in known locations')
        return False
    info(f'key source={source}')
    info(f'key prefix={key[:12]}...')
    try:
        r = requests.post(
            'https://api.tavily.com/search',
            json={
                'api_key': key,
                'query': QUERY,
                'search_depth': 'basic',
                'max_results': 5,
                'include_answer': False,
            },
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            err(f'HTTP {r.status_code}')
            print(r.text[:500])
            return False
        data = r.json()
        results = data.get('results', [])
        ok(f'HTTP 200, results={len(results)}')
        for i, x in enumerate(results[:3], 1):
            title = (x.get('title') or '').replace('\n', ' ')[:100]
            url = x.get('url') or ''
            print(f'  [{i}] {title} | {url}')
        return True
    except Exception as e:
        err(repr(e))
        return False

def main():
    print(f'{BOLD}Search Self-Check{RESET}')
    print(f'query={QUERY}')
    s1 = check_searxng()
    s2 = check_tavily()
    print_header('Summary')
    print(('SearXNG: ' + ('OK' if s1 else 'FAIL')))
    print(('Tavily : ' + ('OK' if s2 else 'FAIL')))
    sys.exit(0 if (s1 and s2) else 1)

if __name__ == '__main__':
    main()
