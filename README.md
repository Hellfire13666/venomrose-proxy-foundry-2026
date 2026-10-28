# 🥀 VENOMROSE // PROXY FOUNDRY

<!-- GLITCHBYTE-VISITOR-BADGE:START -->
[![Page Views](https://hitscounter.dev/api/hit?url=https%3A%2F%2Fgithub.com%2FHellfire13666%2Fvenomrose-proxy-foundry-2026&label=PAGE%20VIEWS&icon=skull&color=%23FF1493&style=flat-square)](https://github.com/Hellfire13666/venomrose-proxy-foundry-2026)
<!-- GLITCHBYTE-VISITOR-BADGE:END -->

![VENOMROSE exact approved command-center artwork](assets/venomrose-command-center-ORIGINAL.png)

**OFFICIAL ARTWORK · VISUAL EDITION:** The image above is the approved original PNG, copied byte-for-byte. Its interface values are illustration, not live feed results. The offline HTML reports also embed this exact artwork and show actual collection metrics separately.

**Official public repository:** [Hellfire13666/venomrose-proxy-foundry-2026](https://github.com/Hellfire13666/venomrose-proxy-foundry-2026).

**GlitchByte Phantom Labs · v0.1.1 · Python 3.10+ · Ubuntu/Linux**

> The web has thorns. VENOMROSE collects public proxy listing feeds, sorts signals, finds overlap, and forges colorful local intelligence reports.

**Independent workshop identity:** black velvet · poison lime `#B6FF00` · deep rose `#FF4382` · gunmetal · chrome thorns. A separate tool, folder, report vault, and GitHub repository from WOLF FANG.

## ⚡ Quick launch: paste into an Ubuntu terminal

Download `VENOMROSE-PROXY-FOUNDRY-v0.1.1-VISUAL.zip` into `~/Downloads`, then:

```bash
cd "$HOME/Downloads" &&
unzip -oq VENOMROSE-PROXY-FOUNDRY-v0.1.1-VISUAL.zip &&
cd venomrose-proxy-foundry-v0.1.1 &&
./RUN_TESTS.sh &&
./OPEN_VENOMROSE.sh --doctor &&
./OPEN_VENOMROSE.sh --demo &&
./OPEN_REPORT.sh
```

Run `./OPEN_LAUNCH_CENTER.sh` for a dedicated graphical start page with the approved artwork and repository link. No pip installs, tokens, databases, Docker, or account setup required. SHA256 file is available separately if desired; only use `sha256sum -c` after downloading that companion file too.

## 🥀 Three go-to commands

**1. Public feed harvest (3 balanced sources):**

```bash
./OPEN_VENOMROSE.sh --live
```

**2. Full feed harvest (9 endpoints, several are mirrors of the same upstream):**

```bash
./OPEN_VENOMROSE.sh --live --feeds all --timeout 20 --limit 1500
```

**3. SOCKS5 only, cross-listed by independent projects:**

```bash
./OPEN_VENOMROSE.sh --live --feeds all --protocol socks5 --min-sources 2 --limit 250
```

The default fetches `monosans`, `proxyscrape`, and `proxyscraper-http`. On a slow connection use `--timeout 20` or `--feeds monosans`.

## 🕷️ Modules

| Module | Action |
|---|---|
| **ROSE HARVEST** | Collects fixed, published HTTP/HTTPS/SOCKS4/SOCKS5 proxy feeds |
| **VENOM SIEVE** | Parses literal IPv4/IPv6 addresses, removes duplicates, merges provider sightings |
| **THORN TRACE** | Keeps source, ASN, country, provider latency, uptime and anonymity fields if present |
| **CROSSBITE** | Counts *independent source groups* and filters by `--min-sources` |
| **PULSE CHECK** | Optional TCP dial to at most 20 listed endpoints (`--probe 10`) |
| **RELAY CHECK** | Optional HTTPS request to fixed `https://example.com/` through at most 10 listed **HTTP** proxies (`--verify-http 5`) |
| **ROSE VAULT** | Writes timestamped JSON / CSV / TXT / styled offline HTML with embedded original artwork |

**Clarifications:** A listing alone is not a working proxy. TCP reachability is only a socket check. Relay verification shows one successful request to the fixed test page and does not prove anonymity or reliability at other destinations. Rank is a sorting heuristic, **not** an anonymity or security score.

## 🧰 Power recipes

```bash
# Show all provider URLs, aliases and source groups
./OPEN_VENOMROSE.sh --list-feeds

# Filter to US-listed proxies (only rows WITH location metadata)
./OPEN_VENOMROSE.sh --live --country US --feeds proxyscrape,proxyscraper-http

# Fastest published latency first, where provider metadata exists
./OPEN_VENOMROSE.sh --live --feeds proxyscrape,proxyscraper-http --sort latency

# Check 10 endpoints for TCP connectivity (bounded, opt-in)
./OPEN_VENOMROSE.sh --live --probe 10 --probe-timeout 3

# Relay-check up to five listed HTTP proxies using a fixed example.com request
./OPEN_VENOMROSE.sh --live --protocol http --verify-http 5 --probe-timeout 5

# Import your own local plain text proxy list (no URL fetching)
./OPEN_VENOMROSE.sh --from-file "$HOME/my-proxies.txt"

# Open latest locally saved report in your browser
./OPEN_REPORT.sh
```

Additional arguments: `--limit 1..5000`, `--workers 1..4`, `--timeout 2..60`, `--color auto|always|never`, `--out /path/to/reports`, `--protocol all|http|https|socks4|socks5`, `--sort rank|latency|ip`.

## 📡 Provider registry

Source groups are *not* blindly counted as separate when the same operator publishes multiple lists.

| Name | Source | Group |
|---|---|---|
| `monosans`, `monosans-meta` | [monosans/proxy-list](https://github.com/monosans/proxy-list) | monosans |
| `proxyscrape`, `proxyscrape-api` | [ProxyScrape/free-proxy-list](https://github.com/proxyscrape/free-proxy-list) and [free API](https://proxyscrape.com/free-proxy-list) | proxyscrape |
| `speedx-http`, `speedx-socks4`, `speedx-socks5` | [TheSpeedX/PROXY-List](https://github.com/TheSpeedX/PROXY-List) | speedx |
| `proxyscraper-http`, `proxyscraper-socks5` | [Proxy Scraper API](https://proxyscraper.com/api) | proxyscraper |

**Third-party datasets:** See each provider's terms and attribution requirements before redistributing their data. The Proxy Scraper API documents CC BY 4.0 dataset attribution. VENOMROSE does not redistribute provider lists in the source ZIP.

## 🗃️ Local report locations

Default directory: `~/VenomRoseReports` (created on first run)

For each execution: `VENOMROSE-<UTC timestamp>.json`, `.csv`, `.txt`, `.html`. The HTML dashboard works offline and has no remote scripts, tracking, or images. First 250 records appear in HTML; the other files include all exported records. The full-res artwork makes portable HTML larger (roughly 3 MB extra per report). Different runs get unique names. Reports are not included in the Git repository and local Unix permissions are restricted.

## 🧪 Tests / release checks

```bash
./RUN_TESTS.sh
./RELEASE_CHECK.sh
```

Tests run offline with mocked provider responses, documentation-range synthetic IPs, parser validation, CSV/HTML output, provider state behavior, and HTTP forwarding simulation. **The release checks do not verify any real proxy hosts.**

## ⚠️ Operational note

Public relays can log requests, alter responses, vanish without warning, or have restrictions imposed by their operators. Do not send passwords, session cookies, account tokens, or private information through unknown relays. This tool does not rotate proxies into third-party automation or circumvent logins, quotas, or anti-bot controls. Fixed external feeds and an optional fixed relay-check destination are used.

## Repository identity

**Public repository:** [Hellfire13666/venomrose-proxy-foundry-2026](https://github.com/Hellfire13666/venomrose-proxy-foundry-2026). The ZIP does not publish or change GitHub. The v0.1.1 release includes an archived tool package and SHA256 verification file; view its publication status on the [Releases page](https://github.com/Hellfire13666/venomrose-proxy-foundry-2026/releases). See `GITHUB_GUIDE.md` for repository maintenance.
