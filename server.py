"""Local test server: serves the game and saves scores to leaderboard.json.
Run:  python server.py          (this computer only)
      python server.py --lan    (phones and other computers on your Wi-Fi can play too)"""
import argparse, json, os, socket, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self):
        for stream in self.streams:
            stream.flush()


if __name__ == "__main__":
    log_file = open(os.path.join(ROOT, "run.log"), "a", encoding="utf-8", buffering=1)
    sys.stdout = Tee(sys.stdout, log_file)
    sys.stderr = Tee(sys.stderr, log_file)

sys.path.insert(0, os.path.join(ROOT, "scripts"))
from common import load, save, add_score

LOCK = threading.Lock()
SEEN = set()          # other devices that have reached this server (for the "Connected:" message)


def lan_addresses():
    """IPv4 addresses a phone could use to reach this computer, best guess first.
    The first one is the interface the OS would use to reach the network (normally Wi-Fi).
    Nothing is sent over the network: a UDP 'connect' only asks the OS to pick a route."""
    found = []
    for target in ("8.8.8.8", "10.255.255.255", "192.168.255.255"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect((target, 9))
                found.append(s.getsockname()[0])
            break
        except OSError:
            continue
    try:
        found += [i[4][0] for i in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    out = []
    for ip in found:
        if not ip.startswith(("127.", "169.254.", "0.")) and ip not in out:
            out.append(ip)
    return out


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/ping":
            return self.reply(200, {"ok": True})
        super().do_GET()

    def do_POST(self):
        if self.path != "/api/score":
            return self.reply(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n < 2000:
                raise ValueError("bad request size")
            payload = json.loads(self.rfile.read(n))
            with LOCK:
                data = load()
                entry = add_score(data, payload)
                save(data)
            self.reply(200, {"ok": True, "entry": entry})
        except ValueError as e:
            self.reply(400, {"error": str(e)})

    def log_message(self, fmt, *args):
        ip = self.client_address[0]
        if not ip.startswith("127.") and ip not in SEEN:
            SEEN.add(ip)
            print(f"  Connected: {ip}  ({(self.headers.get('User-Agent') or 'unknown device')[:70]})", flush=True)
        if self.path.split("?", 1)[0] == "/api/score":
            super().log_message(fmt, *args)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--lan", action="store_true", help="allow other devices on your network")
    a = ap.parse_args()
    try:
        server = ThreadingHTTPServer(("0.0.0.0" if a.lan else "127.0.0.1", a.port), Handler)
    except OSError as e:
        sys.exit(f"Cannot start on port {a.port}: {e}\nIs another copy running? Try: python server.py --port {a.port + 1}")
    print(f"\nOn this computer:  http://localhost:{a.port}")
    if a.lan:
        ips = lan_addresses()
        if ips:
            print("On your phone (same Wi-Fi, type http:// at the start):")
            for n, ip in enumerate(ips):
                print(f"    http://{ip}:{a.port}" + ("    <-- try this first" if n == 0 else "    (other adapter)"))
        else:
            print("Could not find a network address. Are you connected to Wi-Fi? Check with ipconfig / ifconfig.")
        print("\nWhen your phone reaches this computer, a line starting 'Connected:' appears below.")
        print("Nothing appears? The firewall or the Wi-Fi is blocking it (see README, B5).")
    else:
        print("Only this computer can open the game. For a phone, stop (Ctrl+C) and run: python server.py --lan")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
