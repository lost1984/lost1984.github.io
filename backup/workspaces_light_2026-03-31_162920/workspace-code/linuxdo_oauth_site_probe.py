#!/usr/bin/env python3
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket

CDP_BASE = 'http://127.0.0.1:9223'
LOG_URL = 'https://connect.linux.do/oauth2/log'
OUT_PATH = Path('/root/.openclaw/workspace-code/linuxdo_oauth_sites_probe.json')

JS_GET_APPS = r'''(() => {
  const rows = [...document.querySelectorAll('table tr')]
    .slice(1)
    .map(tr => [...tr.querySelectorAll('td')].map(td => (td.innerText || '').trim()))
    .filter(row => row.length >= 4)
    .map(row => ({app_name: row[0], action: row[1], location: row[2], time: row[3]}));
  const deduped = [];
  const seen = new Set();
  for (const row of rows) {
    if (!seen.has(row.app_name)) {
      seen.add(row.app_name);
      deduped.push(row);
    }
  }
  return deduped;
})()'''

JS_OPEN_APP = r'''(appName) => {
  const candidates = [...document.querySelectorAll('a, button, [role="button"]')];
  const el = candidates.find(el => ((el.innerText || el.textContent || '').trim() === appName));
  if (!el) return {ok:false, reason:'app-not-found'};
  el.click();
  return {ok:true};
}'''

JS_SNAPSHOT = r'''(() => {
  const text = document.body ? document.body.innerText : '';
  const anchors = [...document.querySelectorAll('a[href]')].slice(0, 200).map(a => ({
    text: (a.innerText || a.textContent || '').trim().slice(0, 120),
    href: a.href,
  }));
  const inputs = [...document.querySelectorAll('input, textarea')].slice(0, 100).map(i => ({
    tag: i.tagName,
    type: i.type || '',
    name: i.name || '',
    placeholder: i.placeholder || '',
    value: (i.value || '').slice(0, 200),
  }));
  return {
    title: document.title,
    url: location.href,
    text: text.slice(0, 12000),
    anchors,
    inputs,
  };
})()'''


def cdp_get_json(url: str):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def cdp_call(ws, msg_id, method, params=None, timeout=20):
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    end = time.time() + timeout
    while True:
        ws.settimeout(max(0.1, end - time.time()))
        data = json.loads(ws.recv())
        if data.get('id') == msg_id:
            return data


def get_log_page():
    pages = cdp_get_json(CDP_BASE + '/json')
    for p in pages:
        if p.get('type') == 'page' and ('connect.linux.do' in p.get('url', '') or LOG_URL in p.get('url', '')):
            return p
    req = urllib.request.Request(CDP_BASE + '/json/new?' + urllib.parse.quote(LOG_URL, safe=''), method='PUT')
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def eval_value(ws, msg_id, expression, timeout=20):
    res = cdp_call(ws, msg_id, 'Runtime.evaluate', {
        'expression': expression,
        'returnByValue': True,
        'awaitPromise': True,
    }, timeout=timeout)
    return res['result']['result'].get('value')


def call_function(ws, msg_id, function_declaration, argument_value, timeout=20):
    context = cdp_call(ws, msg_id, 'Runtime.evaluate', {
        'expression': 'this',
    }, timeout=timeout)
    obj_id = context['result']['result'].get('objectId')
    res = cdp_call(ws, msg_id + 100000, 'Runtime.callFunctionOn', {
        'objectId': obj_id,
        'functionDeclaration': function_declaration,
        'arguments': [{'value': argument_value}],
        'returnByValue': True,
        'awaitPromise': True,
    }, timeout=timeout)
    if 'result' not in res:
        return {'ok': False, 'raw': res}
    return res['result']['result'].get('value')


def normalize_guess(app_name: str, snap: dict):
    text = (snap.get('text') or '').lower()
    url = snap.get('url') or ''
    title = snap.get('title') or ''
    anchors = snap.get('anchors') or []
    inputs = snap.get('inputs') or []

    domains = []
    for a in anchors:
        href = a.get('href') or ''
        if href.startswith('http'):
            host = urllib.parse.urlparse(href).netloc
            if host and host not in domains:
                domains.append(host)
    same_host = urllib.parse.urlparse(url).netloc

    key_like = []
    for i in inputs:
        joined = ' '.join([i.get('name',''), i.get('placeholder',''), i.get('value','')]).lower()
        if any(k in joined for k in ['key', 'token', 'api', 'sk-', '令牌']):
            key_like.append(i)

    checkin_keywords = ['签到', 'checkin', 'check-in', 'reward', 'bonus', 'claim', '每日', 'daily']
    api_keywords = ['/v1/models', '/models', 'api key', 'apikey', '令牌', 'token', 'openai']

    return {
        'app_name': app_name,
        'page_title': title,
        'page_url': url,
        'host': same_host,
        'linked_domains': domains[:20],
        'has_api_signals': any(k in text for k in api_keywords) or bool(key_like),
        'has_checkin_signals': any(k in text for k in checkin_keywords),
        'key_like_inputs': key_like[:20],
        'anchor_samples': anchors[:30],
        'text_excerpt': (snap.get('text') or '')[:4000],
    }


def main():
    page = get_log_page()
    ws = websocket.create_connection(page['webSocketDebuggerUrl'], timeout=30, origin='http://127.0.0.1:9223')
    try:
        cdp_call(ws, 1, 'Runtime.enable')
        cdp_call(ws, 2, 'Page.enable')
        cdp_call(ws, 3, 'Page.navigate', {'url': LOG_URL})
        time.sleep(4)
        apps = eval_value(ws, 4, JS_GET_APPS)
        results = []
        msg_id = 10
        for row in apps:
            app_name = row['app_name']
            cdp_call(ws, msg_id, 'Page.navigate', {'url': LOG_URL})
            msg_id += 1
            time.sleep(2)
            opened = call_function(ws, msg_id, JS_OPEN_APP, app_name)
            msg_id += 1
            time.sleep(4)
            snap = eval_value(ws, msg_id, JS_SNAPSHOT)
            msg_id += 1
            result = dict(row)
            result.update(normalize_guess(app_name, snap))
            result['open_result'] = opened
            results.append(result)
            print(f"[{len(results)}/{len(apps)}] {app_name} -> {result['page_url']}", file=sys.stderr)
        payload = {
            'source': LOG_URL,
            'probed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'count': len(results),
            'results': results,
        }
        OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    finally:
        ws.close()


if __name__ == '__main__':
    main()
