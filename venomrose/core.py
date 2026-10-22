"""VENOMROSE // PROXY FOUNDRY. Python standard library only."""
from __future__ import annotations

import argparse
import csv
import dataclasses
from datetime import datetime, timezone
import html
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from .branding import REPOSITORY, embedded_banner
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "0.1.1"
NAME = "VENOMROSE // PROXY FOUNDRY"
PROTOCOLS = ("http", "https", "socks4", "socks5")
# Feed URLs are fixed; the command cannot be used to fetch arbitrary URL targets.
FEEDS = {
    "monosans": ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt", "txt", None, "monosans"),
    "monosans-meta": ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies.json", "json", None, "monosans"),
    "proxyscrape": ("https://cdn.jsdelivr.net/gh/proxyscrape/free-proxy-list@main/proxies/all/data.json", "json", None, "proxyscrape"),
    "proxyscrape-api": ("https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text", "txt", None, "proxyscrape"),
    "speedx-http": ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt", "txt", "http", "speedx"),
    "speedx-socks4": ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt", "txt", "socks4", "speedx"),
    "speedx-socks5": ("https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt", "txt", "socks5", "speedx"),
    "proxyscraper-http": ("https://api.proxyscraper.com/v1/http.json", "json", "http", "proxyscraper"),
    "proxyscraper-socks5": ("https://api.proxyscraper.com/v1/socks5.json", "json", "socks5", "proxyscraper"),
}
DEFAULT_FEEDS = "monosans,proxyscrape,proxyscraper-http"
FIELDS = ["protocol", "host", "port", "country", "asn", "provider_latency_ms", "uptime_pct", "anonymity", "source_count", "sources", "tcp_status", "tcp_latency_ms", "forwarding_status", "forwarding_latency_ms", "rank"]


@dataclasses.dataclass
class Proxy:
    protocol: str
    host: str
    port: int
    sources: set[str] = dataclasses.field(default_factory=set)
    groups: set[str] = dataclasses.field(default_factory=set)
    country: str = ""
    asn: str = ""
    provider_latency_ms: int | None = None
    uptime_pct: float | None = None
    anonymity: str = ""
    last_checked: str = ""
    tcp_status: str = "not_checked"
    tcp_latency_ms: int | None = None
    forwarding_status: str = "not_checked"
    forwarding_latency_ms: int | None = None
    rank: int = 0

    @property
    def key(self) -> tuple[str, str, int]:
        return self.protocol, self.host, self.port

    @property
    def address(self) -> str:
        h = f"[{self.host}]" if ":" in self.host else self.host
        return f"{self.protocol}://{h}:{self.port}"

    def as_record(self) -> dict:
        item = dataclasses.asdict(self)
        item.pop("groups")
        item["sources"] = sorted(self.sources)
        item["source_count"] = len(self.groups)
        return item


def parse_line(value: str, default_protocol: str | None = None, allow_reserved: bool = False) -> Proxy | None:
    """Only literal IP:port (including bracketed IPv6). Reject credentials and hostnames."""
    value = value.strip().strip("\ufeff")
    if not value or value.startswith("#") or any(c.isspace() for c in value):
        return None
    text = value if "://" in value else f"{default_protocol or 'http'}://{value}"
    try:
        url = urllib.parse.urlsplit(text)
        protocol = url.scheme.lower()
        if protocol not in PROTOCOLS or not url.hostname or url.username is not None or url.password is not None:
            return None
        if url.path or url.query or url.fragment:
            return None
        ip = ipaddress.ip_address(url.hostname)
        if not ip.is_global and not allow_reserved:
            return None
        port = url.port
        if port is None or not 1 <= port <= 65535:
            return None
        return Proxy(protocol, str(ip), port)
    except (ValueError, AttributeError):
        return None


def maybe_int(v, *, scale: float = 1) -> int | None:
    try:
        if v is None or v == "" or isinstance(v, bool):
            return None
        n = float(v) * scale
        return int(max(0, min(n, 600000)))
    except (ValueError, TypeError, OverflowError):
        return None


def maybe_percent(v) -> float | None:
    try:
        if v is None or v == "" or isinstance(v, bool):
            return None
        n = float(v)
        if 0 <= n <= 100:
            return round(n, 2)
    except (ValueError, TypeError):
        pass
    return None


def parse_json_record(row: dict, default_protocol: str | None = None) -> Proxy | None:
    if not isinstance(row, dict) or row.get("username") or row.get("password"):
        return None
    proto = str(row.get("protocol") or row.get("type") or default_protocol or "http").lower()
    ip = row.get("ip") or row.get("host") or row.get("address")
    port = row.get("port")
    if not isinstance(ip, str) or port is None:
        return None
    item = parse_line(f"{proto}://[{ip}]:{port}" if ":" in ip else f"{proto}://{ip}:{port}")
    if item is None:
        return None
    country = row.get("country_code") or row.get("country") or ""
    if isinstance(country, dict):
        country = country.get("iso_code") or ""
    if not country and isinstance(row.get("geolocation"), dict):
        country = (row["geolocation"].get("country") or {}).get("iso_code") or ""
    if isinstance(country, str):
        item.country = country.upper()[:32]
    asn = row.get("asn")
    if isinstance(asn, dict):
        asn = asn.get("autonomous_system_number")
    if asn is not None and not isinstance(asn, (list, dict)):
        item.asn = str(asn)[:64]
    item.provider_latency_ms = maybe_int(row.get("latency_ms") or row.get("latency"))
    if item.provider_latency_ms is None and row.get("timeout") is not None:
        item.provider_latency_ms = maybe_int(row.get("timeout"), scale=1000)
    item.uptime_pct = maybe_percent(row.get("uptime_percent") if "uptime_percent" in row else row.get("uptime_24h"))
    item.anonymity = str(row.get("anonymity") or "")[:40]
    item.last_checked = str(row.get("last_checked") or "")[:70]
    return item


def parse_feed(body: bytes | str, fmt: str, default_protocol: str | None = None, cap: int = 50000) -> tuple[list[Proxy], int]:
    text = body.decode("utf-8", errors="replace") if isinstance(body, bytes) else body
    out: list[Proxy] = []
    invalid = 0
    if fmt == "json":
        obj = json.loads(text)
        if isinstance(obj, list):
            rows = obj
        elif isinstance(obj, dict):
            rows = next((obj[k] for k in ("proxies", "data", "results") if isinstance(obj.get(k), list)), [])
        else:
            rows = []
        for row in rows[:cap]:
            item = parse_json_record(row, default_protocol)
            if item: out.append(item)
            else: invalid += 1
    else:
        for line in text.splitlines()[:cap]:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            item = parse_line(line, default_protocol)
            if item: out.append(item)
            else: invalid += 1
    return out, invalid


def fetch_feed(name: str, timeout: float, max_bytes: int = 5 * 1024 * 1024):
    url, fmt, proto, _ = FEEDS[name]
    request = urllib.request.Request(url, headers={"User-Agent": f"VenomRoseProxyFoundry/{VERSION} (public list consumer)", "Accept": "application/json,text/plain;q=0.9,*/*;q=0.3"})
    begin = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError(f"feed exceeds {max_bytes} bytes")
        records, bad = parse_feed(body, fmt, proto)
        return records, {"state": "received", "rows": len(records), "discarded": bad, "elapsed_ms": round((time.monotonic()-begin)*1000)}
    except urllib.error.HTTPError as e:
        code = e.code
        state = "rate_limited" if code == 429 else "no_data" if code == 404 else "http_error"
        return [], {"state": state, "detail": f"HTTP {code}", "elapsed_ms": round((time.monotonic()-begin)*1000)}
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as e:
        return [], {"state": "unavailable", "detail": type(e).__name__, "elapsed_ms": round((time.monotonic()-begin)*1000)}


def merge_proxy(target: dict, proxy: Proxy, name: str, group: str):
    key = proxy.key
    if key not in target:
        target[key] = proxy
    obj = target[key]
    obj.sources.add(name)
    obj.groups.add(group)
    for field in ("country", "asn", "anonymity", "last_checked"):
        if not getattr(obj, field) and getattr(proxy, field):
            setattr(obj, field, getattr(proxy, field))
    if proxy.provider_latency_ms is not None and (obj.provider_latency_ms is None or proxy.provider_latency_ms < obj.provider_latency_ms):
        obj.provider_latency_ms = proxy.provider_latency_ms
    if proxy.uptime_pct is not None and (obj.uptime_pct is None or proxy.uptime_pct > obj.uptime_pct):
        obj.uptime_pct = proxy.uptime_pct


def ranking(item: Proxy) -> int:
    # Heuristic confidence in listing metadata, NOT anonymity or successful proxy forwarding.
    base = 10 + min(len(item.groups), 4) * 12
    if item.provider_latency_ms is not None: base += 10
    if item.last_checked: base += 8
    if item.uptime_pct is not None: base += min(12, int(item.uptime_pct / 10) + 2)
    if item.tcp_status == "reachable": base += 8
    if item.forwarding_status == "verified": base += 16
    return min(100, base)


def probe_tcp(item: Proxy, timeout: float):
    before = time.monotonic()
    try:
        with socket.create_connection((item.host, item.port), timeout=timeout):
            return "reachable", round((time.monotonic() - before) * 1000)
    except (OSError, TimeoutError):
        return "unreachable", None


def verify_http_forward(item: Proxy, timeout: float):
    """For HTTP proxies only, request a fixed neutral page via CONNECT.

    No cookies, authorization, or user-supplied destination are involved.
    A pass is one successful forwarding request, not a broader assurance.
    """
    if item.protocol != "http":
        return "unsupported_protocol", None
    start=time.monotonic()
    try:
        proxy_url = item.address
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http":proxy_url,"https":proxy_url}))
        req = urllib.request.Request("https://example.com/", headers={"User-Agent":"VenomRose-RelayCheck/0.1", "Range":"bytes=0-64"})
        with opener.open(req,timeout=timeout) as response:
            code=response.getcode()
            response.read(64)
        return ("verified" if 200 <= code < 400 else "failed"), round((time.monotonic()-start)*1000)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError, ValueError):
        return "failed", None


def sort_items(records, order: str):
    if order == "latency":
        return sorted(records, key=lambda x: (x.provider_latency_ms is None, x.provider_latency_ms if x.provider_latency_ms is not None else 10**9, -x.rank, x.host))
    if order == "ip":
        return sorted(records, key=lambda x: (int(ipaddress.ip_address(x.host)), x.port, x.protocol))
    return sorted(records, key=lambda x: (-x.rank, -len(x.groups), x.provider_latency_ms if x.provider_latency_ms is not None else 10**9, x.host))


def render_html(report: dict) -> str:
    items = report["proxies"][:250]
    c = lambda v: html.escape(str(v), quote=True)
    rows = "\n".join(
        "<tr>" + "".join(f"<td>{c(item.get(k, ''))}</td>" for k in ("protocol", "host", "port", "country", "source_count", "provider_latency_ms", "tcp_status", "forwarding_status", "rank")) + "</tr>"
        for item in items
    )
    providers = "".join(f"<div class='feed'><b>{c(k)}</b><span class='{c(v.get('state',''))}'>{c(v.get('state',''))}</span><small>{c(v.get('rows', 0))} rows · {c(v.get('elapsed_ms', '?'))} ms</small></div>" for k,v in report["feeds"].items())
    summary=report["summary"]
    banner = embedded_banner()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VENOMROSE | PROXY FOUNDRY</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<style>body{{background:#080b0b;color:#e2ebe8;font:15px system-ui,Arial,sans-serif;margin:0}}main{{max-width:1120px;margin:auto;padding:30px}}h1{{font-size:2.7rem;margin:0;color:#ff4382}}h2{{color:#b6ff00}}.eyebrow{{letter-spacing:.22em;color:#8df4b2}}.hero{{padding:30px;border:1px solid #274937;border-radius:17px;background:radial-gradient(ellipse at 95% 5%,#3e0828,#0b1715 60%)}}.hero p{{color:#b6d2c5}}.metrics{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}.metrics div{{background:#131d1b;min-width:140px;padding:19px;border-radius:12px;border:1px solid #33433d}}.metrics strong{{display:block;font-size:2rem;color:#b6ff00}}.metrics small{{color:#a6b5af}}.feeds{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:9px}}.feed{{background:#0e1715;border:1px solid #284639;padding:12px;border-radius:10px}}.feed b{{display:block;color:#eab1cb}}.feed span{{display:block;margin:6px 0;color:#b6ff00}}.feed span.unavailable,.feed span.rate_limited,.feed span.http_error{{color:#ff8c96}}small{{color:#9bada5}}table{{width:100%;border-collapse:collapse;min-width:740px}}.scroll{{overflow-x:auto}}th,td{{padding:9px;border-bottom:1px solid #254239;text-align:left}}th{{color:#b6ff00}}td{{font-family:ui-monospace,monospace}}footer{{font-size:.85rem;color:#9eb1a8;margin-top:25px}}code{{color:#e2a1c9}}.brand-art{{margin:0 0 18px;border-radius:14px;overflow:hidden;border:1px solid #ff438280;background:#030504}}.brand-art img{{display:block;width:100%;height:auto}}.brand-art figcaption{{font-size:.77rem;padding:10px 14px;color:#c5d5cc;background:#121918}}.repo-link{{display:inline-block;color:#a9ffa1;font-weight:700;overflow-wrap:anywhere}}.repo-link:focus-visible{{outline:3px solid #ff4382}}.hero{{margin-bottom:18px}}</style></head><body><main>
<figure class="brand-art"><img src="{banner}" alt="Original VENOMROSE cyberpunk command-center artwork with a neon green serpent wrapped around a crimson rose"><figcaption>OFFICIAL VENOMROSE ARTWORK · The figures and terminal panels inside the artwork are illustrative, not live scan results. Your actual results begin below.</figcaption></figure>
<div class="hero"><div class="eyebrow">GLITCHBYTE PHANTOM LABS · VENOM SIGNAL</div><h1>🥀 VENOMROSE</h1><p>PROXY FOUNDRY // {c(report['version'])} // {c(report['mode'])}</p><p>Feed data and TCP accessibility are different from verified proxy forwarding.</p><p>PROJECT REPOSITORY: <a class="repo-link" rel="noopener noreferrer" target="_blank" href="{REPOSITORY}">Hellfire13666/venomrose-proxy-foundry-2026</a> (link becomes active after GitHub publication)</p></div>
<div class="metrics"><div><strong>{c(summary['unique'])}</strong><small>Unique listings</small></div><div><strong>{c(summary['multi_source'])}</strong><small>Multi-provider sightings</small></div><div><strong>{c(summary['tcp_reachable'])}</strong><small>TCP reachable (sampled)</small></div><div><strong>{c(summary['forwarding_verified'])}</strong><small>HTTP relay checks passed</small></div><div><strong>{c(len(report['feeds']))}</strong><small>Feeds queried</small></div></div>
<h2>THE FEED WEB</h2><div class="feeds">{providers}</div><h2>THE PROXY VAULT</h2><div class="scroll"><table><thead><tr><th>Protocol</th><th>IP</th><th>Port</th><th>Country</th><th>Sources</th><th>Indexed ms</th><th>TCP</th><th>HTTP Relay</th><th>Rank</th></tr></thead><tbody>{rows}</tbody></table></div><footer>Showing up to 250 records in HTML. Full findings in CSV / TXT / JSON. Generated {c(report['timestamp_utc'])}. Data describes public proxy listings only; never enter credentials into untrusted relays.</footer></main></body></html>'''


def save_report(report: dict, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    try: os.chmod(out, 0o700)
    except OSError: pass
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    stem = f"VENOMROSE-{stamp}"
    paths = {ext: out / f"{stem}.{ext}" for ext in ("json", "csv", "txt", "html")}
    def write_private(path: Path, payload: str):
        # exclusive create avoids overwriting older reports, mode 0600 on Unix.
        flags = os.O_CREAT | os.O_WRONLY | os.O_EXCL
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(payload)
    write_private(paths["json"], json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    import io
    buff = io.StringIO(); w = csv.DictWriter(buff, fieldnames=FIELDS); w.writeheader()
    for item in report["proxies"]:
        w.writerow({k: ";".join(item[k]) if k == "sources" else item.get(k) for k in FIELDS})
    write_private(paths["csv"], buff.getvalue())
    write_private(paths["txt"], "".join(
        f"{row['protocol']}://{('['+row['host']+']') if ':' in row['host'] else row['host']}:{row['port']}\n" for row in report["proxies"]))
    write_private(paths["html"], render_html(report))
    return {ext: str(path) for ext, path in paths.items()}


def build_report(items: list[Proxy], states: dict, mode: str, fetched: int, bad: int, probe_n: int) -> dict:
    for item in items: item.rank = ranking(item)
    records=[i.as_record() for i in items]
    return {"tool": NAME, "version": VERSION, "timestamp_utc": datetime.now(timezone.utc).isoformat(), "mode": mode,
            "summary": {"unique":len(records), "raw_rows":fetched, "discarded_rows":bad,
                "multi_source":sum(1 for i in items if len(i.groups)>1),
                "tcp_reachable":sum(1 for i in items if i.tcp_status=="reachable"),
                "forwarding_verified":sum(1 for i in items if i.forwarding_status=="verified"),
                "forwarding_probed":sum(1 for i in items if i.forwarding_status!="not_checked"),
                "tcp_probed":probe_n,
                "protocols":{p:sum(1 for i in items if i.protocol==p) for p in PROTOCOLS}},
            "feeds":states, "proxies":records,
            "notices":["Listings are not confirmed working relays.", "TCP reachability alone is not a proxy forwarding check.", "Rank is a local sorting heuristic, not a security or anonymity score."]}


def colorize(value, code, enabled=True):
    return f"\033[{code}m{value}\033[0m" if enabled else value


def show_banner(enabled=True):
    v=lambda s,n:colorize(s,n,enabled)
    print(v("╔════════════════════════════════════════════════════════════════════╗", "95"))
    print(v("║  🥀 VENOMROSE // PROXY FOUNDRY // GLITCHBYTE PHANTOM LABS       ║", "92"))
    print(v("╚════════════════════════════════════════════════════════════════════╝", "95"))


def demo_data():
    # RFC 5737 documentary addresses, NEVER network-tested.
    rows=[
        ("http://192.0.2.11:8080", "monosans", "monosans"),
        ("http://192.0.2.11:8080", "proxyscrape", "proxyscrape"),
        ("socks5://198.51.100.42:1080", "monosans", "monosans"),
        ("socks4://203.0.113.18:9050", "speedx-socks4", "speedx"),
        ("http://192.0.2.99:3128", "proxyscraper-http", "proxyscraper"),
        ("socks5://198.51.100.42:1080", "proxyscraper-socks5", "proxyscraper"),
    ]
    db={}
    for raw,src,g in rows:
        item=parse_line(raw,allow_reserved=True)
        assert item
        merge_proxy(db,item,src,g)
    db[("http","192.0.2.11",8080)].country="US"
    db[("http","192.0.2.11",8080)].provider_latency_ms=310
    return db, {"demo": {"state": "synthetic", "rows": len(rows), "elapsed_ms":0}}, len(rows), 0


def doctor():
    show_banner(sys.stdout.isatty())
    print(f"  ◆ VERSION       {VERSION}")
    print(f"  ◆ PYTHON        {sys.version.split()[0]} (3.10+ required)")
    print(f"  ◆ FEEDS         {len(FEEDS)} configured; no authentication required")
    print(f"  ◆ DEFAULT       {DEFAULT_FEEDS}")
    print(f"  ◆ REPORTS       {Path.home()/'VenomRoseReports'}")
    print("  ◆ NETWORK       Not contacted during doctor")
    print("  ◆ DEPENDENCIES  Python standard library only")


def main(argv=None):
    parser = argparse.ArgumentParser(description="VENOMROSE: public proxy list collector and local intelligence dashboard")
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="synthetic preview without network access")
    mode.add_argument("--live", action="store_true", help="fetch public proxy feeds")
    mode.add_argument("--from-file", type=Path, metavar="TXT", help="import local proxy list")
    mode.add_argument("--doctor", action="store_true", help="offline environment check")
    mode.add_argument("--list-feeds", action="store_true", help="show built-in providers")
    parser.add_argument("--feeds", default=DEFAULT_FEEDS, help="comma-separated feed names or 'all'")
    parser.add_argument("--protocol", choices=("all",)+PROTOCOLS, default="all")
    parser.add_argument("--country", help="two-letter country code; entries without country metadata are excluded")
    parser.add_argument("--min-sources", type=int, default=1, help="independent source groups required (1-5)")
    parser.add_argument("--limit", type=int, default=500, help="maximum exported results (1-5000)")
    parser.add_argument("--sort", choices=("rank", "latency", "ip"), default="rank")
    parser.add_argument("--timeout", type=float, default=15, help="per-feed HTTPS timeout in seconds (2-60)")
    parser.add_argument("--probe", type=int, default=0, help="optionally TCP-probe first N listed IP:ports (0-20)")
    parser.add_argument("--probe-timeout", type=float, default=3, help="TCP connect timeout seconds (1-10)")
    parser.add_argument("--verify-http", type=int, default=0, help="HTTP proxy forwarding checks via example.com (0-10)")
    parser.add_argument("--workers", type=int, default=3, help="TCP probe concurrency (1-4)")
    parser.add_argument("--out", type=Path, default=Path.home()/"VenomRoseReports")
    parser.add_argument("--color", choices=("auto","always","never"), default="auto")
    args=parser.parse_args(argv)
    if args.doctor: doctor(); return 0
    if args.list_feeds:
        print("🥀 VENOMROSE // PROVIDER REGISTRY")
        for k,(url,fmt,proto,group) in FEEDS.items():
            print(f"  ◆ {k:22} [{group}] {fmt.upper()} {proto or 'mixed'}\n    {url}")
        return 0
    if not (args.demo or args.live or args.from_file):
        parser.print_help(); return 2
    if not (1 <= args.limit <= 5000 and 1 <= args.min_sources <= 5 and 2<=args.timeout<=60 and 0<=args.probe<=20 and 0<=args.verify_http<=10 and 1<=args.workers<=4 and 1<=args.probe_timeout<=10):
        parser.error("limit, min-sources, timeout, probe and worker settings out of bounds")
    if args.country and not re.fullmatch(r"[A-Za-z]{2}",args.country):
        parser.error("--country expects two-letter country code")
    if args.demo and (args.probe or args.verify_http):
        parser.error("synthetic demo cannot be probed")
    enabled=args.color=="always" or (args.color=="auto" and sys.stdout.isatty())
    show_banner(enabled)
    db={}; states={}; fetched=0; bad=0
    if args.demo:
        db, states, fetched, bad=demo_data()
        label="SYNTHETIC DEMO · NO NETWORK"
    elif args.from_file:
        try:
            data=args.from_file.read_bytes()
            if len(data)>5*1024*1024: raise ValueError("local list exceeds 5 MB")
            rows,bad=parse_feed(data, "txt")
        except (OSError, ValueError) as exc:
            print(f"  ◇ LOCAL INPUT ERROR: {exc}",file=sys.stderr);return 1
        fetched=len(rows)
        for row in rows:merge_proxy(db,row,"local-input","local")
        states["local-input"]={"state":"imported","rows":len(rows),"discarded":bad,"elapsed_ms":0}
        label="LOCAL FILE"
    else:
        names=list(FEEDS) if args.feeds.lower()=="all" else [s.strip() for s in args.feeds.split(",") if s.strip()]
        if not names or any(n not in FEEDS for n in names):
            parser.error("Unknown --feeds name; use --list-feeds")
        names=list(dict.fromkeys(names))
        label="PUBLIC FEED COLLECTION"
        for i,name in enumerate(names):
            rows, state=fetch_feed(name,args.timeout)
            states[name]=state
            fetched+=len(rows);bad+=state.get("discarded",0)
            for row in rows:merge_proxy(db,row,name,FEEDS[name][3])
            tag="RECEIVED" if state["state"]=="received" else state["state"].upper()
            print(f"  ◆ {name:21} {tag:13} {state.get('rows',0):>6} rows   {state.get('elapsed_ms','?')} ms")
            if i<len(names)-1:time.sleep(.4)
    items=list(db.values())
    if args.protocol!="all":items=[i for i in items if i.protocol==args.protocol]
    if args.country:items=[i for i in items if i.country.upper()==args.country.upper()]
    items=[i for i in items if len(i.groups)>=args.min_sources]
    for item in items:item.rank=ranking(item)
    items=sort_items(items,args.sort)[:args.limit]
    probed=0
    if args.probe:
        count=min(args.probe,len(items))
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(probe_tcp,items[i],args.probe_timeout):items[i] for i in range(count)}
            for future in as_completed(futures):
                target=futures[future]
                try: target.tcp_status,target.tcp_latency_ms=future.result()
                except Exception: target.tcp_status="unreachable"
                probed+=1
        items=sort_items(items,args.sort)
    if args.verify_http:
        picked=[i for i in items if i.protocol=="http"][:args.verify_http]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(verify_http_forward,item,args.probe_timeout):item for item in picked}
            for future in as_completed(futures):
                target=futures[future]
                try: target.forwarding_status,target.forwarding_latency_ms=future.result()
                except Exception: target.forwarding_status="failed"
        for item in items:item.rank=ranking(item)
        items=sort_items(items,args.sort)
    report=build_report(items,states,label,fetched,bad,probed)
    saved=save_report(report,args.out)
    s=report["summary"]
    print(f"  ◆ MODE          {label}")
    print(f"  ◆ RAW ENTRIES   {s['raw_rows']}")
    print(f"  ◆ UNIQUE EXPORT {s['unique']}")
    print(f"  ◆ MULTI-SOURCE  {s['multi_source']}")
    print(f"  ◆ TCP TESTS     {s['tcp_probed']} probes · {s['tcp_reachable']} reachable (connect only)")
    print(f"  ◆ HTTP RELAY    {s['forwarding_probed']} checked · {s['forwarding_verified']} passed via example.com")
    if args.demo: print("  ◇ SYNTHETIC VALUES ONLY. NONE ARE REAL PROXY HOSTS.")
    for item in items[:min(8,len(items))]:
        print(f"  ◆ {item.address:44} sources={len(item.groups)} rank={item.rank:02} tcp={item.tcp_status} relay={item.forwarding_status}")
    for fmt,path in saved.items(): print(f"  ◆ SAVED {fmt.upper():4} {path}")
    if args.live and not any(v.get("state")=="received" for v in states.values()):
        print("  ◇ All selected feeds were unavailable. Empty reports were still generated.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
