#!/usr/bin/env python3
import argparse
import json
import os
import socket
import subprocess
import shutil
import sys
import time
import urllib.parse
import urllib.request
from http.cookiejar import MozillaCookieJar

import requests
import websocket
from bs4 import BeautifulSoup

BASE = "https://signv.ice.v.ua"
EMBED_URL = f"{BASE}/embed"
CHECKIN_URL = f"{BASE}/checkin?next=/embed"
RESET_URL = f"{BASE}/reset?next=/embed"
ICE_CUSTOM_URL = "https://ice.v.ua/custom/f8c961a6027f9cb0"
LINUXDO_OAUTH_START = "https://ice.v.ua/api/v1/auth/oauth/linuxdo/start?redirect=/custom/f8c961a6027f9cb0"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
DEFAULT_CDP_CANDIDATES = [
    "http://127.0.0.1:9223",
    "http://127.0.0.1:9222",
    "http://127.0.0.1:9224",
    "http://127.0.0.1:9333",
    "http://127.0.0.1:9444",
]


class CDPClient:
    def __init__(self, ws_url: str, origin: str | None = None):
        self.ws = websocket.create_connection(ws_url, timeout=30, origin=origin or "http://127.0.0.1")
        self.msg_id = 0
        self.contexts = []
        self.network_events = []
        self.page_events = []

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

    def _handle_event(self, data: dict):
        method = data.get("method")
        if method == "Runtime.executionContextCreated":
            self.contexts.append(data["params"]["context"])
        elif method in {"Network.requestWillBeSent", "Network.responseReceived"}:
            self.network_events.append(data)
        elif method and method.startswith("Page."):
            self.page_events.append(data)

    def send(self, method: str, params: dict | None = None, timeout: float = 10):
        self.msg_id += 1
        self.ws.send(json.dumps({"id": self.msg_id, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while True:
            self.ws.settimeout(max(0.1, end - time.time()))
            data = json.loads(self.ws.recv())
            if data.get("id") == self.msg_id:
                return data
            self._handle_event(data)
            if time.time() > end:
                raise TimeoutError(method)

    def collect(self, seconds: float):
        end = time.time() + seconds
        while time.time() < end:
            try:
                self.ws.settimeout(end - time.time())
                data = json.loads(self.ws.recv())
                self._handle_event(data)
            except Exception:
                break

    def context_id_by_origin(self, origin: str) -> int:
        matches = [c for c in self.contexts if c.get("origin") == origin]
        if not matches:
            raise RuntimeError(f"未找到 origin={origin} 的 execution context")
        return matches[-1]["id"]


def build_session(cookie_value: str | None = None, cookie_file: str | None = None) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Origin": BASE,
            "Referer": EMBED_URL,
        }
    )

    if cookie_value:
        s.cookies.set("session", cookie_value, domain="signv.ice.v.ua", path="/")
        return s

    if cookie_file:
        jar = MozillaCookieJar()
        jar.load(cookie_file, ignore_discard=True, ignore_expires=True)
        for c in jar:
            s.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
        return s

    return s


def build_embed_url(user_id: str | int, auth_token: str, theme: str = "light", lang: str = "zh-CN") -> str:
    params = {
        "user_id": str(user_id),
        "token": auth_token,
        "theme": theme,
        "lang": lang,
        "ui_mode": "embedded",
        "src_host": "https://ice.v.ua",
        "src_url": ICE_CUSTOM_URL,
    }
    return EMBED_URL + "?" + urllib.parse.urlencode(params)


def bootstrap_from_ice_token(session: requests.Session, user_id: str | int, auth_token: str, theme: str = "light", lang: str = "zh-CN") -> tuple[requests.Response, str]:
    url = build_embed_url(user_id=user_id, auth_token=auth_token, theme=theme, lang=lang)
    r = session.get(url, timeout=30, allow_redirects=True)
    return r, url


def load_config(config_path: str | None) -> dict:
    if not config_path:
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_value(cli_value, config: dict, key: str, env_name: str):
    if cli_value not in (None, ""):
        return cli_value
    if key in config and config[key] not in (None, ""):
        return config[key]
    return os.environ.get(env_name)


def is_placeholder(value: str | None) -> bool:
    if not value:
        return False
    lower = value.lower()
    return any(m in value for m in ["替换成", "你的"]) or any(m in lower for m in ["example", "dummy", "test"])


def parse_embed(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    title = soup.title.get_text(strip=True) if soup.title else ""
    buttons = [b.get_text(strip=True) for b in soup.select("button")]
    badge = soup.select_one(".badge")
    kpi_values = [x.get_text(strip=True) for x in soup.select(".kpi .v")]
    kpi_labels = [x.get_text(strip=True) for x in soup.select(".kpi .l")]
    kpis = dict(zip(kpi_labels, kpi_values))

    username = ""
    name_node = soup.select_one('.card .title[style*="font-size:18px"]')
    if name_node:
        username = name_node.get_text(strip=True)

    return {
        "title": title,
        "username": username,
        "badge": badge.get_text(strip=True) if badge else "",
        "buttons": buttons,
        "kpis": kpis,
        "text": text,
        "already_checked_in": "今日已签到" in text,
    }


def parse_signv_text(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {
        "text": text,
        "lines": lines,
        "already_checked_in": "今日已签到" in text,
        "can_checkin": "签到领刀" in text,
        "can_reset": "申请重置" in text,
        "need_login": "请先登录" in text or "未识别到主站登录态" in text,
    }


def fetch_status(session: requests.Session) -> tuple[dict, str]:
    r = session.get(EMBED_URL, timeout=30)
    r.raise_for_status()
    return parse_embed(r.text), r.text


def do_action(session: requests.Session, action: str) -> requests.Response:
    url = CHECKIN_URL if action == "checkin" else RESET_URL
    return session.post(
        url,
        timeout=30,
        allow_redirects=False,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def is_tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def cdp_alive(cdp_http_url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(cdp_http_url + "/json/version", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def normalize_cdp_url(cdp_http_url: str) -> str:
    return cdp_http_url.rstrip("/")


def detect_cdp_url(explicit_url: str | None = None) -> str | None:
    candidates = []
    if explicit_url:
        candidates.append(normalize_cdp_url(explicit_url))
    env_url = os.environ.get("CDP_URL")
    if env_url:
        candidates.append(normalize_cdp_url(env_url))
    for item in DEFAULT_CDP_CANDIDATES:
        candidates.append(normalize_cdp_url(item))

    seen = set()
    for item in candidates:
        if item in seen:
            continue
        seen.add(item)
        if cdp_alive(item):
            return item
    return None


def launch_chrome_for_cdp(cdp_http_url: str, start_url: str | None = None) -> dict:
    parsed = urllib.parse.urlparse(cdp_http_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 9223

    if is_tcp_open(host, port):
        subprocess.run(["pkill", "-f", f"remote-debugging-port={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 5
        while time.time() < deadline and is_tcp_open(host, port):
            time.sleep(0.2)
    chrome_bins = [
        os.environ.get("CHROME_BIN"),
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
        "microsoft-edge",
    ]
    chrome_bin = None
    for item in chrome_bins:
        if not item:
            continue
        if os.path.isabs(item) and os.path.exists(item):
            chrome_bin = item
            break
        found = shutil.which(item) if 'shutil' in globals() else None
        if found:
            chrome_bin = found
            break
    if chrome_bin is None:
        raise RuntimeError("未找到 Chrome/Chromium，可设置 CHROME_BIN")

    user_data_dir = os.environ.get("ICE_SIGNIN_CHROME_PROFILE", f"/tmp/ice-signin-chrome-{port}")
    os.makedirs(user_data_dir, exist_ok=True)
    cmd = [
        chrome_bin,
        f"--remote-debugging-address={host}",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--headless=new",
        "--remote-allow-origins=*",
    ]
    if start_url:
        cmd.append(start_url)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    deadline = time.time() + 15
    while time.time() < deadline:
        if cdp_alive(cdp_http_url):
            return {
                "launched": True,
                "cdp_url": cdp_http_url,
                "chrome_bin": chrome_bin,
                "user_data_dir": user_data_dir,
            }
        time.sleep(0.5)
    raise RuntimeError(f"已尝试启动浏览器，但 CDP 仍不可用：{cdp_http_url}")


def browser_get_page(cdp_http_url: str, page_url: str | None) -> dict:
    pages = json.load(urllib.request.urlopen(cdp_http_url + "/json"))
    if page_url:
        for p in pages:
            if p.get("type") == "page" and page_url in p.get("url", ""):
                return p
    for p in pages:
        if p.get("type") == "page" and "ice.v.ua" in p.get("url", ""):
            return p
    req = urllib.request.Request(cdp_http_url + "/json/new?" + urllib.parse.quote(page_url or ICE_CUSTOM_URL, safe=""), method="PUT")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def browser_checkin(cdp_http_url: str | None, page_url: str = ICE_CUSTOM_URL, wait_seconds: float = 5.0) -> dict:
    detected = detect_cdp_url(cdp_http_url)
    launch_info = None
    final_cdp = detected
    if final_cdp is None and cdp_http_url:
        launch_info = launch_chrome_for_cdp(normalize_cdp_url(cdp_http_url), start_url=page_url)
        final_cdp = launch_info["cdp_url"]
    elif final_cdp is None:
        target = normalize_cdp_url(DEFAULT_CDP_CANDIDATES[0])
        launch_info = launch_chrome_for_cdp(target, start_url=page_url)
        final_cdp = launch_info["cdp_url"]
    page = browser_get_page(final_cdp, page_url)
    client = CDPClient(page["webSocketDebuggerUrl"], origin=final_cdp)
    try:
        client.send("Runtime.enable")
        client.send("Page.enable")
        client.send("Network.enable")
        client.send("Page.navigate", {"url": page_url}, timeout=20)
        client.collect(4)
        try:
            signv_context = client.context_id_by_origin("https://signv.ice.v.ua")
        except RuntimeError:
            current_url = client.send("Runtime.evaluate", {"expression": "location.href", "returnByValue": True})["result"]["result"].get("value", "")
            page_text = client.send("Runtime.evaluate", {"expression": "document.body ? document.body.innerText : ''", "returnByValue": True})["result"]["result"].get("value", "")
            return {
                "ok": False,
                "action": "browser-checkin",
                "cdp_url": final_cdp,
                "launch_info": launch_info,
                "page_url": page.get("url"),
                "current_url": current_url,
                "linuxdo_oauth_start": LINUXDO_OAUTH_START,
                "message": "浏览器已自动启动，但当前会话没有现成登录态，未进入 signv iframe。该站应优先使用 Linux.do OAuth 登录；下一步应访问 linuxdo_oauth_start 完成授权。",
                "page_text_excerpt": page_text[:2000],
            }

        before = client.send(
            "Runtime.evaluate",
            {
                "expression": "document.body.innerText",
                "contextId": signv_context,
                "returnByValue": True,
            },
        )
        before_text = before["result"]["result"].get("value", "")
        before_state = parse_signv_text(before_text)

        click_result = client.send(
            "Runtime.evaluate",
            {
                "expression": """
(() => {
  const btn = [...document.querySelectorAll('button')].find(b => (b.innerText || '').includes('签到'));
  if (!btn) return { ok: false, reason: 'button_not_found' };
  btn.click();
  return { ok: true, text: btn.innerText };
})()
""",
                "contextId": signv_context,
                "returnByValue": True,
            },
        )

        client.collect(wait_seconds)

        frame_tree = client.send("Page.getFrameTree")
        signv_frame = frame_tree["result"]["frameTree"].get("childFrames", [{}])[0].get("frame", {})
        current_signv_url = signv_frame.get("url", "")

        try:
            new_context = client.context_id_by_origin("https://signv.ice.v.ua")
            after = client.send(
                "Runtime.evaluate",
                {
                    "expression": "document.body.innerText",
                    "contextId": new_context,
                    "returnByValue": True,
                },
            )
            after_text = after["result"]["result"].get("value", "")
        except Exception:
            after_text = ""
        after_state = parse_signv_text(after_text)

        network = []
        for event in client.network_events:
            method = event.get("method")
            params = event.get("params", {})
            if method == "Network.requestWillBeSent":
                req = params.get("request", {})
                url = req.get("url", "")
                if "signv.ice.v.ua" in url:
                    network.append(
                        {
                            "event": "req",
                            "url": url,
                            "method": req.get("method"),
                            "postData": req.get("postData"),
                            "headers": {k: v for k, v in req.get("headers", {}).items() if k in ["Origin", "Referer", "Content-Type"]},
                        }
                    )
            elif method == "Network.responseReceived":
                resp = params.get("response", {})
                url = resp.get("url", "")
                if "signv.ice.v.ua" in url:
                    network.append(
                        {
                            "event": "resp",
                            "url": url,
                            "status": resp.get("status"),
                            "mime": resp.get("mimeType"),
                        }
                    )

        result = {
            "ok": True,
            "action": "browser-checkin",
            "cdp_url": final_cdp,
            "launch_info": launch_info,
            "page_url": page.get("url"),
            "before": before_state,
            "click": click_result["result"]["result"].get("value"),
            "after": after_state,
            "current_signv_url": current_signv_url,
            "network": network,
        }

        if before_state["already_checked_in"]:
            result["message"] = "浏览器里今天已经签到过了；已验证可自动点击真实签到按钮"
        elif after_state["already_checked_in"]:
            result["message"] = "浏览器自动签到成功"
        else:
            result["ok"] = False
            result["message"] = "已在浏览器里触发签到点击，但结果未完全确认，请查看 network/after"
        return result
    finally:
        client.close()


def main() -> int:
    p = argparse.ArgumentParser(description="ice.v.ua / signv.ice.v.ua 签到器")
    p.add_argument("action", choices=["status", "checkin", "reset", "bootstrap", "auto", "browser-checkin"], help="执行动作")
    p.add_argument("--config", help="JSON 配置文件路径")
    p.add_argument("--session-cookie", help="signv.ice.v.ua 的 session cookie 值")
    p.add_argument("--cookie-file", help="Netscape 格式 cookie 文件路径")
    p.add_argument("--ice-auth-token", help="ice.v.ua localStorage 里的 auth_token")
    p.add_argument("--ice-user-id", help="ice.v.ua 当前用户 id（可从 auth_user 中取）")
    p.add_argument("--theme", default=None, help="嵌入页 theme，默认 light")
    p.add_argument("--lang", default=None, help="嵌入页 lang，默认 zh-CN")
    p.add_argument("--cdp-url", help="Chrome DevTools HTTP 地址，例如 http://127.0.0.1:9223")
    p.add_argument("--page-url", default=ICE_CUSTOM_URL, help="浏览器签到模式打开的页面，默认签到页")
    p.add_argument("--wait-seconds", type=float, default=5.0, help="浏览器点击后等待秒数")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    args = p.parse_args()

    config = load_config(args.config)
    session_cookie = pick_value(args.session_cookie, config, "session_cookie", "ICE_SIGN_SESSION_COOKIE")
    cookie_file = pick_value(args.cookie_file, config, "cookie_file", "ICE_SIGN_COOKIE_FILE")
    ice_auth_token = pick_value(args.ice_auth_token, config, "ice_auth_token", "ICE_AUTH_TOKEN")
    ice_user_id = pick_value(args.ice_user_id, config, "ice_user_id", "ICE_USER_ID")
    theme = pick_value(args.theme, config, "theme", "ICE_THEME") or "light"
    lang = pick_value(args.lang, config, "lang", "ICE_LANG") or "zh-CN"
    cdp_url = pick_value(args.cdp_url, config, "cdp_url", "ICE_CDP_URL")

    if is_placeholder(session_cookie):
        session_cookie = None
    if is_placeholder(cookie_file):
        cookie_file = None
    if is_placeholder(ice_auth_token):
        ice_auth_token = None
    if is_placeholder(ice_user_id):
        ice_user_id = None
    if is_placeholder(cdp_url):
        cdp_url = None

    if args.action == "browser-checkin":
        result = browser_checkin(cdp_url, page_url=args.page_url, wait_seconds=args.wait_seconds)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result.get("message", ""))
            print(f"page: {result.get('page_url')}")
            print(f"signv: {result.get('current_signv_url')}")
        return 0 if result.get("ok") else 1

    session = build_session(session_cookie, cookie_file)

    bootstrap_resp = None
    bootstrap_info = None
    if ice_auth_token and ice_user_id:
        bootstrap_resp, embed_url = bootstrap_from_ice_token(
            session,
            user_id=ice_user_id,
            auth_token=ice_auth_token,
            theme=theme,
            lang=lang,
        )
        bootstrap_info = {
            "embed_url": embed_url,
            "http_status": bootstrap_resp.status_code,
        }

    if args.action == "bootstrap":
        if not (ice_auth_token and ice_user_id):
            raise SystemExit("bootstrap 模式需要同时提供 --ice-auth-token 和 --ice-user-id")
        parsed = parse_embed(bootstrap_resp.text)
        result = {
            "ok": True,
            "action": args.action,
            "bootstrap": bootstrap_info,
            "page": parsed,
        }
        text = parsed.get("text", "")
        if "未识别到主站登录态" in text:
            result["ok"] = False
            result["message"] = "signv 未识别到主站登录态，说明仅构造 URL 还不够，仍需真实主站登录上下文或有效 token"
        elif parsed.get("username"):
            result["message"] = "已通过主站参数进入 signv 页面"
        else:
            result["message"] = "已访问构造的 embed URL，请检查 page 字段"
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result.get("message", ""))
            print(embed_url)
        return 0 if result.get("ok") else 1

    if args.action == "auto":
        if bootstrap_resp is not None:
            parsed = parse_embed(bootstrap_resp.text)
            if parsed.get("username") or parsed.get("already_checked_in") or parsed.get("buttons"):
                before = parsed
                result = {"ok": True, "action": args.action, "mode": "bootstrap", "before": before, "bootstrap": bootstrap_info}
                if before.get("already_checked_in"):
                    result["message"] = "今天已经签到过了"
                else:
                    resp = do_action(session, "checkin")
                    result["http_status"] = resp.status_code
                    result["location"] = resp.headers.get("Location", "")
                    after, _ = fetch_status(session)
                    result["after"] = after
                    if after.get("already_checked_in"):
                        result["message"] = "bootstrap 成功，签到成功"
                    else:
                        result["ok"] = False
                        result["message"] = "bootstrap 已执行，但签到结果未确认"
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(result.get("message", ""))
                return 0 if result.get("ok") else 1
            if "未识别到主站登录态" in parsed.get("text", "") and not (session_cookie or cookie_file):
                result = {
                    "ok": False,
                    "action": args.action,
                    "mode": "bootstrap",
                    "bootstrap": bootstrap_info,
                    "page": parsed,
                    "message": "bootstrap 失败：未识别到主站登录态，且未提供 session fallback",
                }
                print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else result["message"])
                return 1
        if not (session_cookie or cookie_file):
            raise SystemExit("auto 模式下，如果 bootstrap 未打通，则至少需要 session_cookie 或 cookie_file 作为回退")
        args.action = "checkin"

    if not (session_cookie or cookie_file or (ice_auth_token and ice_user_id)):
        raise SystemExit("需要提供 --session-cookie / --cookie-file，或提供 --ice-auth-token + --ice-user-id")

    before, _ = fetch_status(session)

    result = {
        "ok": True,
        "action": args.action,
        "before": before,
    }

    if args.action in {"checkin", "reset"}:
        resp = do_action(session, args.action)
        result["http_status"] = resp.status_code
        result["location"] = resp.headers.get("Location", "")
        after, _ = fetch_status(session)
        result["after"] = after

        if args.action == "checkin":
            if before.get("already_checked_in"):
                result["message"] = "今天已经签到过了"
            elif after.get("already_checked_in"):
                result["message"] = "签到成功"
            else:
                result["ok"] = False
                result["message"] = "签到请求已发出，但页面状态未确认变更"

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"用户: {before.get('username') or '-'}")
        print(f"当前状态: {before.get('badge') or '-'}")
        for k, v in before.get("kpis", {}).items():
            print(f"{k}: {v}")
        if "message" in result:
            print(result["message"])
        if "after" in result:
            print(f"动作后状态: {result['after'].get('badge') or '-'}")

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
