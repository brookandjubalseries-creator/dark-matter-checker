# Dark Matter — ai.com Botname Checker

Animated dark-themed GUI for checking ai.com botname availability in bulk.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![License](https://img.shields.io/badge/License-MIT-green)

## Features

- Animated dark matter particle header
- Bulk botname checking with multi-threading (up to 100 threads)
- Proxy support with round-robin rotation (HTTP & SOCKS5)
- Auto dead-proxy detection and removal
- Real-time progress bar, stats, and color-coded results
- Rate-limit handling with auto-retry
- Export results to `checked.txt`

## Install

```bash
pip install customtkinter requests
```

For SOCKS5 proxy support:
```bash
pip install requests[socks]
```

## Usage

```bash
python dark_matter_checker.py
```

1. Paste your ai.com token
2. Add botnames (one per line) or load from a `.txt` file
3. Optionally add proxies (`ip:port` or `user:pass@ip:port`) and select HTTP/SOCKS5
4. Set thread count and hit Start

## Credits

@crysiox
