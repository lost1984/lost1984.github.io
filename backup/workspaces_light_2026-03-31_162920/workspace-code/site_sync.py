#!/usr/bin/env python3
import argparse
import html
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

EXCLUDE_NAMES = {'.git', '.github', '.DS_Store'}
TEXT_EXTS = {
    '.md', '.txt', '.py', '.js', '.ts', '.json', '.yml', '.yaml', '.toml', '.ini',
    '.sh', '.bash', '.zsh', '.css', '.html', '.csv', '.log'
}


def should_exclude(path: Path) -> bool:
    return path.name in EXCLUDE_NAMES


def rendered_href(rel: Path) -> str:
    path = str(rel).replace(os.sep, '/')
    if rel.suffix.lower() == '.md':
        return path[:-3] + '.html'
    return path


def fix_markdown_links(text: str) -> str:
    def repl(match):
        label = match.group(1)
        target = match.group(2)
        if target.startswith('/root/ai/'):
            target = target[len('/root/ai/'):]
        if target.lower().endswith('.md') and ('/' in target or target.startswith('.') or target.startswith('..')):
            target = target[:-3] + '.html'
        return f'[{label}]({target})'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', repl, text)


def parse_attrs(attr_text: str) -> dict:
    return dict(re.findall(r'([\w-]+)="([^"]*)"', attr_text))


def render_callout(attrs: str, inner: str) -> str:
    kv = parse_attrs(attrs)
    emoji = html.escape(kv.get('emoji', '💡'))
    bg = kv.get('background-color', 'light-yellow')
    border = kv.get('border-color', 'yellow')
    bg_map = {
        'light-blue': '#eef6ff',
        'light-yellow': '#fff8db',
        'light-green': '#eefbf0',
        'light-red': '#fff1f0',
        'light-gray': '#f5f5f5',
    }
    border_map = {
        'blue': '#91caff',
        'yellow': '#fadb14',
        'green': '#95de64',
        'red': '#ff7875',
        'gray': '#d9d9d9',
    }
    style = f'background:{bg_map.get(bg, "#f5f5f5")};border-left:4px solid {border_map.get(border, "#d9d9d9")};padding:12px 14px;border-radius:8px;margin:12px 0;'
    inner_html = markdown_to_html(inner, wrap_paragraphs=False)
    return f'<div class="callout" style="{style}"><div><strong>{emoji}</strong></div>{inner_html}</div>'


def render_quote_container(inner: str) -> str:
    inner_html = markdown_to_html(inner, wrap_paragraphs=False)
    return f'<blockquote class="quote-container">{inner_html}</blockquote>'


def render_lark_table(attrs: str, inner: str) -> str:
    rows = re.findall(r'<table-row>(.*?)</table-row>', inner, flags=re.S)
    if not rows:
        return f'<pre>{html.escape(inner.strip())}</pre>'
    kv = parse_attrs(attrs)
    header_row = kv.get('header-row', 'false').lower() == 'true'
    out = ['<table class="lark-table">']
    for idx, row in enumerate(rows):
        cells = re.findall(r'<table-cell>(.*?)</table-cell>', row, flags=re.S)
        tag = 'th' if header_row and idx == 0 else 'td'
        out.append('<tr>')
        for cell in cells:
            cell_md = fix_markdown_links(cell.strip())
            cell_html = markdown_to_html(cell_md, wrap_paragraphs=False).strip()
            out.append(f'<{tag}>{cell_html}</{tag}>')
        out.append('</tr>')
    out.append('</table>')
    return ''.join(out)


def preprocess_blocks(md: str) -> str:
    md = fix_markdown_links(md)

    md = re.sub(
        r'<callout\s+([^>]*)>(.*?)</callout>',
        lambda m: render_callout(m.group(1), m.group(2).strip()),
        md,
        flags=re.S,
    )
    md = re.sub(
        r'<quote-container>(.*?)</quote-container>',
        lambda m: render_quote_container(m.group(1).strip()),
        md,
        flags=re.S,
    )
    md = re.sub(
        r'<lark-table\s*([^>]*)>(.*?)</lark-table>',
        lambda m: render_lark_table(m.group(1), m.group(2).strip()),
        md,
        flags=re.S,
    )
    return md


def markdown_to_html(md: str, wrap_paragraphs: bool = True, current_dir: Path | None = None) -> str:
    md = preprocess_blocks(md)
    md = re.sub(r'(?<![\("\'])/root/ai/([^\s`<>")]+)', r'`\1`', md)
    lines = md.splitlines()
    out = []
    in_list = False
    list_tag = 'ul'
    in_code = False
    code_lang = ''
    code_buf = []
    table_mode = False
    table_rows = []

    def close_list():
        nonlocal in_list, list_tag
        if in_list:
            out.append(f'</{list_tag}>')
            in_list = False
            list_tag = 'ul'

    def close_code():
        nonlocal in_code, code_buf, code_lang
        if in_code:
            code_html = html.escape('\n'.join(code_buf))
            if code_lang == 'mermaid':
                out.append(f'<pre><code class="language-mermaid">{code_html}</code></pre>')
            else:
                cls = f' class="language-{html.escape(code_lang)}"' if code_lang else ''
                out.append(f'<pre><code{cls}>{code_html}</code></pre>')
            in_code = False
            code_buf = []
            code_lang = ''

    def flush_table():
        nonlocal table_mode, table_rows
        if not table_rows:
            table_mode = False
            return
        header = table_rows[0]
        body = table_rows[1:]
        out.append('<table class="md-table">')
        out.append('<thead><tr>' + ''.join(f'<th>{inline(c.strip())}</th>' for c in header) + '</tr></thead>')
        if body:
            out.append('<tbody>')
            for row in body:
                out.append('<tr>' + ''.join(f'<td>{inline(c.strip())}</td>' for c in row) + '</tr>')
            out.append('</tbody>')
        out.append('</table>')
        table_rows = []
        table_mode = False

    def inline(text: str) -> str:
        if '<' in text and '>' in text and any(tag in text for tag in ('<a ', '<div ', '<table', '<blockquote', '<pre', '<code', '<strong>', '<em>')):
            return text
        escaped = html.escape(text)
        escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
        escaped = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', escaped)
        escaped = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', escaped)
        escaped = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', escaped)
        if current_dir is not None:
            escaped = re.sub(
                r'<code>([^<]+\.md)</code>',
                lambda m: f'<a href="{html.escape(m.group(1)[:-3] + ".html")}"><code>{html.escape(m.group(1))}</code></a>' if (current_dir / m.group(1)).exists() else m.group(0),
                escaped,
            )
        return escaped

    for line in lines:
        if line.startswith('```'):
            flush_table()
            if in_code:
                close_code()
            else:
                close_list()
                in_code = True
                code_lang = line[3:].strip()
            continue
        if in_code:
            code_buf.append(line)
            continue

        stripped = line.strip()

        if stripped.startswith('<table ') or stripped.startswith('<div ') or stripped.startswith('<blockquote') or stripped.startswith('<pre>'):
            flush_table()
            close_list()
            out.append(stripped)
            continue
        if stripped in ('</table>', '</div>', '</blockquote>', '</pre>') or stripped.startswith('<thead') or stripped.startswith('</thead') or stripped.startswith('<tbody') or stripped.startswith('</tbody') or stripped.startswith('<tr>') or stripped.startswith('</tr>') or stripped.startswith('<th>') or stripped.startswith('</th>') or stripped.startswith('<td>') or stripped.startswith('</td>'):
            out.append(stripped)
            continue

        if stripped.startswith('|') and stripped.endswith('|'):
            close_list()
            row = [c for c in stripped.strip('|').split('|')]
            if re.fullmatch(r'\s*:?-+:?\s*(\|\s*:?-+:?\s*)*', stripped.strip('|')):
                table_mode = True
                continue
            table_mode = True
            table_rows.append(row)
            continue
        elif table_mode:
            flush_table()

        if not stripped:
            close_list()
            out.append('')
            continue

        if stripped == '---':
            close_list()
            out.append('<hr>')
            continue

        if stripped.startswith('#'):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip('#')), 6)
            content = stripped[level:].strip()
            out.append(f'<h{level}>{inline(content)}</h{level}>')
            continue

        if stripped.startswith('> '):
            close_list()
            quote_text = stripped[2:].strip()
            out.append(f'<blockquote><p>{inline(quote_text)}</p></blockquote>')
            continue

        ordered_match = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if ordered_match:
            if not in_list or list_tag != 'ol':
                close_list()
                out.append('<ol>')
                in_list = True
                list_tag = 'ol'
            out.append(f'<li>{inline(ordered_match.group(2).strip())}</li>')
            continue

        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list or list_tag != 'ul':
                close_list()
                out.append('<ul>')
                in_list = True
                list_tag = 'ul'
            out.append(f'<li>{inline(stripped[2:].strip())}</li>')
            continue

        close_list()
        if wrap_paragraphs:
            out.append(f'<p>{inline(stripped)}</p>')
        else:
            out.append(inline(stripped))

    flush_table()
    close_list()
    close_code()
    return '\n'.join(x for x in out if x is not None)


def wrap_html(title: str, body: str, back_href: str = 'index.html', dir_href: str = '', prev_link: str = '', next_link: str = '') -> str:
    nav_html = '<div class="topbar">'
    nav_html += f'<a href="{html.escape(back_href)}">← 首页</a>'
    if dir_href:
        nav_html += f' <span class="sep">·</span> <a href="{html.escape(dir_href)}">所在目录</a>'
    if prev_link:
        nav_html += f' <span class="sep">·</span> {prev_link}'
    if next_link:
        nav_html += f' <span class="sep">·</span> {next_link}'
    nav_html += '</div>'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; margin: 2rem auto; max-width: 960px; padding: 0 1rem; line-height: 1.8; color: #222; }}
    h1,h2,h3,h4 {{ line-height: 1.3; margin-top: 1.4em; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f6f8fa; padding: 1rem; border-radius: 8px; overflow: auto; }}
    code {{ background: #f6f8fa; padding: 0.1rem 0.3rem; border-radius: 4px; }}
    .topbar {{ margin-bottom: 1.5rem; color: #666; padding: 10px 14px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 12px; }}
    .sep {{ color: #98a2b3; margin: 0 4px; }}
    ul, ol {{ padding-left: 1.5rem; }}
    .doc {{ margin-top: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f7f7f7; }}
    blockquote {{ margin: 1rem 0; padding: 0.75rem 1rem; border-left: 4px solid #d9d9d9; background: #fafafa; }}
    hr {{ border: none; border-top: 1px solid #e5e7eb; margin: 1.5rem 0; }}
    .bottom-nav {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e5e7eb; display: flex; gap: 12px; flex-wrap: wrap; }}
  </style>
</head>
<body>
  {nav_html}
  <article class="doc">
  {body}
  </article>
  <div class="bottom-nav">{nav_html}</div>
</body>
</html>
'''


def file_sort_key(rel_root: Path, name: str):
    priority = 0
    if str(rel_root) == '2.情报跟踪' and name == '情报汇总.md':
        priority = -100
    return (priority, name)


def collect_sections(src: Path):
    sections = []
    for child in sorted(src.iterdir(), key=lambda p: p.name):
        if should_exclude(child):
            continue
        if child.is_dir():
            files = sorted([p for p in child.iterdir() if p.is_file() and not should_exclude(p)], key=lambda p: file_sort_key(Path(child.name), p.name))
            sections.append((child.name, files))
    return sections


def write_directory_indexes(src: Path, dst: Path):
    for section_name, files in collect_sections(src):
        dir_links = []
        for f in files:
            href = f.with_suffix('.html').name if f.suffix.lower() == '.md' else f.name
            label = html.escape(f.name.replace('.md', ''))
            dir_links.append(f'<li><a href="{html.escape(href)}">{label}</a></li>')
        if not dir_links:
            dir_links.append('<li class="empty">暂无文件</li>')
        rel_dir = Path(section_name)
        dir_index = dst / rel_dir / 'index.html'
        dir_index.parent.mkdir(parents=True, exist_ok=True)
        back_href = '../index.html'
        body = f'<h1>{html.escape(section_name)}</h1><ul>{"".join(dir_links)}</ul>'
        dir_index.write_text(wrap_html(section_name, body, back_href), encoding='utf-8')


def write_index(src: Path, dst: Path, site_title: str):
    generated = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cards = []
    for section_name, files in collect_sections(src):
        links = []
        for f in files[:8]:
            rel = f.relative_to(src)
            href = html.escape(rendered_href(rel))
            label = html.escape(f.name.replace('.md', ''))
            links.append(f'<li><a href="{href}">{label}</a></li>')
        if not links:
            links.append('<li class="empty">暂无文件</li>')
        section_href = html.escape(f'{section_name}/index.html')
        cards.append(f'''
        <section class="card">
          <div class="card-head">
            <div class="card-title"><a href="{section_href}">{html.escape(section_name)}</a></div>
          </div>
          <ul class="card-links">
            {''.join(links)}
          </ul>
        </section>
        ''')
    index = f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(site_title)}工作台</title>
  <style>
    :root {{
      --bg: #f6f8fb;
      --card: #ffffff;
      --text: #1f2328;
      --muted: #667085;
      --line: #e6eaf0;
      --brand: #2563eb;
      --brand-soft: #eff6ff;
      --shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px 64px; }}
    .hero {{ background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%); color: #fff; border-radius: 20px; padding: 28px 28px; box-shadow: var(--shadow); }}
    .hero-head {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 2rem; line-height: 1.2; }}
    .hero p {{ margin: 0; opacity: 0.92; }}
    .meta {{ margin-top: 10px; font-size: 0.92rem; opacity: 0.9; }}
    .agent-badge {{ display: inline-flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 999px; background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.24); backdrop-filter: blur(8px); flex-shrink: 0; }}
    .agent-avatar {{ width: 36px; height: 36px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: rgba(255,255,255,.2); font-size: 20px; }}
    .agent-text {{ font-size: .92rem; line-height: 1.2; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-top: 24px; }}
     .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 18px 14px; box-shadow: var(--shadow); }}
    .card-title {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 12px; }}
    .card-links {{ list-style: none; margin: 0; padding: 0; }}
    .card-links li {{ margin: 8px 0; }}
    .card-links a {{ display: block; text-decoration: none; color: var(--text); background: #fafbfc; border: 1px solid #eef1f4; border-radius: 12px; padding: 10px 12px; transition: all .15s ease; }}
    .card-links a:hover {{ border-color: #cfe0ff; background: var(--brand-soft); color: var(--brand); transform: translateY(-1px); }}
    .empty {{ color: var(--muted); padding: 10px 0; }}
    .footer {{ margin-top: 22px; color: var(--muted); font-size: 0.92rem; }}
    @media (max-width: 720px) {{
      .wrap {{ padding: 16px 12px 36px; }}
      .hero {{ padding: 18px 16px; border-radius: 16px; }}
      .hero-head {{ flex-direction: column; align-items: flex-start; }}
      .hero h1 {{ font-size: 1.55rem; }}
      .hero p {{ font-size: 0.95rem; }}
      .meta {{ font-size: 0.84rem; }}
      .agent-badge {{ width: 100%; justify-content: flex-start; border-radius: 14px; }}
      .grid {{ grid-template-columns: 1fr; gap: 12px; margin-top: 16px; }}
      .card {{ padding: 14px 14px 10px; border-radius: 14px; }}
      .card-title {{ font-size: 1rem; margin-bottom: 10px; }}
      .card-links li {{ margin: 6px 0; }}
      .card-links a {{ padding: 10px; border-radius: 10px; font-size: 0.95rem; }}
    }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 18px 14px; box-shadow: var(--shadow); }}
    .card-title {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 12px; }}
    .card-links {{ list-style: none; margin: 0; padding: 0; }}
    .card-links li {{ margin: 8px 0; }}
    .card-links a {{ display: block; text-decoration: none; color: var(--text); background: #fafbfc; border: 1px solid #eef1f4; border-radius: 12px; padding: 10px 12px; transition: all .15s ease; }}
    .card-links a:hover {{ border-color: #cfe0ff; background: var(--brand-soft); color: var(--brand); transform: translateY(-1px); }}
    .empty {{ color: var(--muted); padding: 10px 0; }}
    .footer {{ margin-top: 22px; color: var(--muted); font-size: 0.92rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div class="hero-head">
        <div>
          <h1>{html.escape(site_title)}工作台</h1>
          <p>轻量静态站 · 由智能助手 Code 维护</p>
          <div class="meta">最近生成：{generated}</div>
        </div>
        <div class="agent-badge">
          <div class="agent-avatar">🐭</div>
          <div class="agent-text">
            <div><strong>Code</strong></div>
            <div>天才程序员</div>
          </div>
        </div>
      </div>
    </section>

    <div class="grid">
      {''.join(cards)}
    </div>

    <div class="footer">首页只展示目录入口，正文内容进入具体页面查看。</div>
  </div>
</body>
</html>
'''
    (dst / 'index.html').write_text(index, encoding='utf-8')


def write_markdown_html(src: Path, dst: Path):
    md_files = [p for p in src.rglob('*.md') if not should_exclude(p)]
    groups = {}
    for p in md_files:
        groups.setdefault(p.parent.relative_to(src), []).append(p)
    for rel_dir, files in groups.items():
        files.sort(key=lambda p: file_sort_key(rel_dir, p.name))
        for i, path in enumerate(files):
            rel = path.relative_to(src)
            html_rel = rel.with_suffix('.html')
            out_path = dst / html_rel
            out_path.parent.mkdir(parents=True, exist_ok=True)
            content = path.read_text(encoding='utf-8', errors='replace')
            body = markdown_to_html(content, current_dir=path.parent)
            depth = len(html_rel.parts) - 1
            back_href = '../' * depth + 'index.html' if depth > 0 else 'index.html'
            dir_href = 'index.html'
            prev_link = ''
            next_link = ''
            if i > 0:
                prev_rel = files[i-1].relative_to(src).with_suffix('.html').name
                prev_label = html.escape(files[i-1].name.replace('.md', ''))
                prev_link = f'<a href="{html.escape(prev_rel)}">← {prev_label}</a>'
            if i < len(files) - 1:
                next_rel = files[i+1].relative_to(src).with_suffix('.html').name
                next_label = html.escape(files[i+1].name.replace('.md', ''))
                next_link = f'<a href="{html.escape(next_rel)}">{next_label} →</a>'
            out_path.write_text(wrap_html(str(rel), body, back_href, dir_href, prev_link, next_link), encoding='utf-8')


def copy_tree(src: Path, dst: Path):
    dst.mkdir(parents=True, exist_ok=True)
    keep = set()
    for root, dirs, files in os.walk(src):
        root_path = Path(root)
        dirs[:] = sorted([d for d in dirs if not should_exclude(root_path / d)])
        rel_root = root_path.relative_to(src)
        target_root = dst / rel_root
        target_root.mkdir(parents=True, exist_ok=True)
        keep.add(target_root.resolve())
        for file in sorted(files):
            src_file = root_path / file
            if should_exclude(src_file):
                continue
            dst_file = target_root / file
            shutil.copy2(src_file, dst_file)
            keep.add(dst_file.resolve())
    write_markdown_html(src, dst)
    for p in dst.rglob('*.html'):
        keep.add(p.resolve())
    keep.add((dst / 'index.html').resolve())

    for root, dirs, files in os.walk(dst, topdown=False):
        root_path = Path(root)
        for file in files:
            p = root_path / file
            if p.resolve() not in keep:
                p.unlink()
        for d in dirs:
            p = root_path / d
            if p.resolve() not in keep and p.exists():
                shutil.rmtree(p)


def main():
    parser = argparse.ArgumentParser(description='Mirror a local folder to a GitHub Pages repo.')
    parser.add_argument('--src', required=True)
    parser.add_argument('--dst', required=True)
    parser.add_argument('--title', default='AI Workspace Mirror')
    args = parser.parse_args()

    src = Path(args.src).resolve()
    dst = Path(args.dst).resolve()
    if not src.exists() or not src.is_dir():
        raise SystemExit(f'source directory not found: {src}')

    copy_tree(src, dst)
    write_directory_indexes(src, dst)
    write_index(src, dst, args.title)


if __name__ == '__main__':
    main()
