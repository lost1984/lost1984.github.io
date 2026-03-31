#!/usr/bin/env python3
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path('/root/ai-site')

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            d = dict(attrs)
            href = d.get('href')
            if href:
                self.links.append(href)

bad = []
for html_file in ROOT.rglob('*.html'):
    parser = LinkParser()
    parser.feed(html_file.read_text(encoding='utf-8', errors='replace'))
    for href in parser.links:
        if href.startswith('http://') or href.startswith('https://') or href.startswith('#'):
            continue
        parsed = urlparse(href)
        rel = parsed.path
        target = (html_file.parent / rel).resolve()
        if not target.exists():
            bad.append((str(html_file.relative_to(ROOT)), href, str(target.relative_to(ROOT.parent)) if target.exists() else str(target)))

if not bad:
    print('OK: no broken local links')
else:
    print('BROKEN LINKS:')
    for page, href, target in bad:
        print(f'- page={page} href={href} target={target}')
    raise SystemExit(1)
