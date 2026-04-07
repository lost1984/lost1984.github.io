#!/usr/bin/env python3
import json
import sys
import time
import urllib.parse
import urllib.request

import websocket

DEFAULT_CDP = "http://127.0.0.1:9223"
TARGET_URL = "https://connect.linux.do/oauth2/log"


def cdp_get_json(url: str):
    with urllib.request.urlopen(url) as r:
        return json.load(r)


def find_or_open_page(cdp_base: str):
    pages = cdp_get_json(cdp_base + "/json")
    for p in pages:
        if p.get("type") == "page" and TARGET_URL in p.get("url", ""):
            return p
    req = urllib.request.Request(cdp_base + "/json/new?" + urllib.parse.quote(TARGET_URL, safe=""), method="PUT")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def cdp_call(ws, msg_id, method, params=None, timeout=20):
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    end = time.time() + timeout
    while True:
        ws.settimeout(max(0.1, end - time.time()))
        data = json.loads(ws.recv())
        if data.get("id") == msg_id:
            return data


def fetch_log(cdp_base: str):
    page = None
    pages = cdp_get_json(cdp_base + "/json")
    for p in pages:
        if p.get("type") == "page" and (TARGET_URL in p.get("url", "") or "connect.linux.do" in p.get("url", "")):
            page = p
            break
    if page is None:
        req = urllib.request.Request(cdp_base + "/json/new?https%3A%2F%2Fconnect.linux.do%2Foauth2%2Flog", method="PUT")
        with urllib.request.urlopen(req) as r:
            page = json.load(r)

    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=30, origin="http://127.0.0.1:9223")
    try:
        cdp_call(ws, 1, "Runtime.enable")
        cdp_call(ws, 2, "Page.enable")
        cdp_call(ws, 3, "Page.navigate", {"url": TARGET_URL})
        time.sleep(5)
        expr = r'''(() => {
  const rows = [...document.querySelectorAll('table tr')]
    .slice(1)
    .map(tr => [...tr.querySelectorAll('td')].map(td => (td.innerText || '').trim()))
    .filter(row => row.length >= 4)
    .map(row => ({app_name: row[0], action: row[1], location: row[2], time: row[3]}));
  const deduped = [];
  const seen = new Set();
  for (const row of rows) {
    const k = row.app_name;
    if (!seen.has(k)) {
      seen.add(k);
      deduped.push(row);
    }
  }
  return {
    title: document.title,
    url: location.href,
    total_rows: rows.length,
    unique_apps: deduped.length,
    rows,
    deduped,
    text: (document.body ? document.body.innerText : '').slice(0, 5000)
  };
})()'''
        res = cdp_call(ws, 4, "Runtime.evaluate", {"expression": expr, "returnByValue": True}, timeout=20)
        return res["result"]["result"]["value"]
    finally:
        ws.close()


if __name__ == "__main__":
    cdp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CDP
    print(json.dumps(fetch_log(cdp), ensure_ascii=False, indent=2))
