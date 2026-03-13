import subprocess, requests, websocket, json, time, base64, sys, os

CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
BASE_URL = "http://localhost:4278"
OUT_DIR  = r"C:/Users/黃以謙/Desktop/@College/Class/Resume"

PAGES = [
    ("motivation",  f"{BASE_URL}/motivation.html"),
    ("lor_chi",     f"{BASE_URL}/lor_chi.html"),
    ("index",       f"{BASE_URL}/index.html"),
]

def cdp_call(ws_url, method, params=None):
    ws = websocket.create_connection(ws_url, timeout=30)
    msg_id = 1
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        raw = ws.recv()
        obj = json.loads(raw)
        if obj.get("id") == msg_id:
            ws.close()
            return obj.get("result", {})

def get_ws_url(chrome_proc):
    for _ in range(20):
        time.sleep(0.5)
        try:
            tabs = requests.get("http://localhost:9222/json", timeout=2).json()
            for tab in tabs:
                if tab.get("type") == "page":
                    return tab["webSocketDebuggerUrl"]
        except Exception:
            pass
    raise RuntimeError("Could not connect to Chrome DevTools")

def navigate_and_print(ws_url, page_url, out_path):
    ws = websocket.create_connection(ws_url, timeout=60)
    call_id = [0]
    
    def send(method, params=None):
        call_id[0] += 1
        ws.send(json.dumps({"id": call_id[0], "method": method, "params": params or {}}))
        return call_id[0]
    
    def wait_for(expected_id=None, event_name=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = ws.recv()
            obj = json.loads(raw)
            if expected_id and obj.get("id") == expected_id:
                return obj.get("result", {})
            if event_name and obj.get("method") == event_name:
                return obj.get("params", {})
        raise TimeoutError(f"Timed out waiting for {expected_id or event_name}")
    
    # Enable Page domain
    send("Page.enable")
    time.sleep(0.2)
    
    # Enable Runtime domain for JS evaluation
    send("Runtime.enable")
    time.sleep(0.1)

    # Navigate
    nav_id = send("Page.navigate", {"url": page_url})
    wait_for(event_name="Page.loadEventFired", timeout=20)

    # Wait for all web fonts to finish loading
    font_id = send("Runtime.evaluate", {
        "expression": "document.fonts.ready",
        "awaitPromise": True,
        "timeout": 8000,
    })
    wait_for(expected_id=font_id, timeout=15)

    # Extra settle time for layout/render
    time.sleep(1.5)
    
    # Print to PDF — A4: 8.27 × 11.69 inches, margins 0.5 inch each side
    pdf_id = send("Page.printToPDF", {
        "paperWidth":     8.27,
        "paperHeight":    11.69,
        "marginTop":      0.5,
        "marginBottom":   0.5,
        "marginLeft":     0.5,
        "marginRight":    0.5,
        "printBackground": True,
        "preferCSSPageSize": False,
    })
    result = wait_for(expected_id=pdf_id, timeout=30)
    ws.close()
    
    data = base64.b64decode(result["data"])
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"  Saved {out_path} ({len(data):,} bytes)")

# Launch Chrome with remote debugging, headless
proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
])
print("Chrome launched, waiting for DevTools...")
time.sleep(2)

try:
    ws_url = get_ws_url(proc)
    print(f"Connected: {ws_url}")
    
    for name, url in PAGES:
        out = os.path.join(OUT_DIR, f"{name}.pdf")
        print(f"Exporting {name} ...")
        # Each page needs a fresh connection since we navigate in the same tab
        navigate_and_print(ws_url, url, out)
        time.sleep(1)
        
        # Refresh ws_url for next tab (same tab reused)
        tabs = requests.get("http://localhost:9222/json", timeout=5).json()
        for tab in tabs:
            if tab.get("type") == "page":
                ws_url = tab["webSocketDebuggerUrl"]
                break

    print("\nAll done!")
finally:
    proc.terminate()
