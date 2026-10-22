# Operational and data handling notes

This repository contains a public proxy feed collector and a bounded connectivity checker. Public lists are third-party material with independent licensing, updates, and reliability. The collector only downloads from fixed, documented HTTPS URLs; local file mode accepts only literal IP:port entries with no embedded credentials. All imported private, loopback, reserved, and multicast addresses are skipped.

Default mode does not contact listed proxy endpoints. The `--probe` switch makes a TCP connection to at most 20 public listed endpoints; `--verify-http` makes a request to the fixed `https://example.com/` page through at most 10 HTTP listings. Results are only observations at check time, not proxies for production traffic or guarantees of anonymity. Keep passwords, cookies, access tokens, and personal traffic away from unknown public relays. No login automation, account bypass, or proxy-rotation engine is included.
