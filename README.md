# Veylance (`veyl`)

[![Build Status](https://img.shields.io/github/actions/workflow/status/ChAbdulWahhab/veylance/release.yml?branch=main&style=flat-square&label=build)](https://github.com/ChAbdulWahhab/veylance/actions)
[![Release](https://img.shields.io/github/v/release/ChAbdulWahhab/veylance?style=flat-square&color=blue)](https://github.com/ChAbdulWahhab/veylance/releases)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen?style=flat-square)](tests/)

**Veylance** is an automated, high-throughput command-line security auditing engine engineered for security engineers, devsecops teams, and infrastructure owners. It delivers comprehensive heuristic vulnerability assessments and configuration audits against web applications, exposing security exposures before malicious exploitation.

---

## Core Capabilities

- **Interactive Terminal Interface:** Executing `veyl` in an interactive terminal session initiates a high-fidelity terminal UI featuring real-time inspection status, concurrency metrics, and categorized findings.
- **35 Specialized Audit Modules:** Automated security heuristics across transport encryption, authentication mechanisms, session management, access control boundaries, injection surfaces, supply-chain exposures, compound risk chains, and temporal scan drift.
- **6 Standardized Report Formats:** Export machine-readable and executive artifacts in `markdown`, `json`, `html`, `sarif` (OASIS standard for GitHub Code Scanning), `csv` (Excel-compatible UTF-8 BOM), and `pdf`.
- **Integrated Compliance & Governance:** Cryptographic audit logging (`~/.veylance/audit.log`), explicit terms consent persistence (`~/.veylance/consent.json`), and granular domain ownership declarations (`--i-own-this`).
- **Zero-Dependency Native Binaries:** Standalone release binaries compiled for Linux (amd64), macOS Apple Silicon (arm64), macOS Intel (amd64), and Windows (amd64).

---

## Installation

### Option 1: Quick Install Scripts

- **Linux & macOS (Bash):**
  Automatically detects operating system, architecture (Apple Silicon vs. Intel), and Rosetta 2 translation:
  ```bash
  curl -sSL https://raw.githubusercontent.com/ChAbdulWahhab/veylance/main/install.sh | bash
  ```

- **Windows (PowerShell):**
  ```powershell
  irm https://raw.githubusercontent.com/ChAbdulWahhab/veylance/main/install.ps1 | iex
  ```

### Option 2: Python Environment (pip)

Install Veylance into an active Python virtual environment:

```bash
# Clone repository
git clone https://github.com/ChAbdulWahhab/veylance.git
cd veylance

# Install package in editable mode with development and PDF dependencies
pip install -e ".[dev,pdf]"
```

### Option 3: Pre-compiled Standalone Binaries

Download self-contained binaries and cryptographic checksums directly from [GitHub Releases](https://github.com/ChAbdulWahhab/veylance/releases):
- **Linux (x86_64):** `veyl-linux-amd64`, `veyl-linux-amd64.tar.gz`
- **macOS (Apple Silicon arm64):** `veyl-darwin-arm64`, `veyl-darwin-arm64.tar.gz`
- **macOS (Intel x86_64):** `veyl-darwin-amd64`, `veyl-darwin-amd64.tar.gz`
- **Windows (x64):** `veyl-windows-amd64.exe`, `veyl-windows-amd64.zip`

### Option 4: Package Managers

- **Homebrew (macOS & Linux):**
  ```bash
  brew tap ChAbdulWahhab/veylance
  brew install veylance
  ```
- **Windows Package Manager (WinGet):**
  ```powershell
  winget install ChAbdulWahhab.Veylance
  ```

---

## Quick Start & Usage

### 1. Interactive Navigation

Executing `veyl` without subcommands in an interactive terminal opens the interactive management console:

```bash
veyl
```

### 2. Direct Automated Audits

```bash
# Execute comprehensive audit against target infrastructure
veyl scan https://example.com

# Target specific modules with custom output paths and report formats
veyl scan https://example.com -m headers,tls_https,cors -f markdown,html,json -o ./reports

# Declare domain ownership to bypass interactive authorization prompts
veyl scan https://example.com --i-own-this example.com

# Non-interactive automated execution (CI/CD pipelines)
veyl scan https://example.com --yes
```

### 3. Module Inventory

Inspect all registered security analysis modules:

```bash
veyl modules-list
```

### 4. Engine Version

```bash
veyl version
# or
veyl --version
```

---

## Security Modules (23)

| Category | Modules | Technical Focus |
| :--- | :--- | :--- |
| **Transport & Infrastructure** | `tls_https`, `dns_recon`, `subdomain`, `waf_detect`, `rate_limit` | Cipher suites, certificate validation, DNS records, subdomains, WAF presence, rate exhaustion |
| **HTTP Configuration** | `headers`, `cookies`, `cors`, `csp_analyzer`, `http_methods` | HSTS, CSP policy analysis, CORS origin handling, cookie flags (Secure/HttpOnly/SameSite), dangerous methods |
| **Information Disclosure** | `sensitive_paths`, `exposed_files`, `directory_list`, `error_leak`, `robots_sitemap`, `tech_fingerprint` | Admin portals, backup files, `.git` leakage, directory traversal, stack traces, version disclosure |
| **Application & API Logic** | `forms_csrf`, `graphql_probe`, `jwt_probe`, `js_analysis` | CSRF token verification, GraphQL introspection, JWT signature flaws, exposed API routes/keys |
| **Injection & Routing** | `xss_reflection`, `sqli_heuristic`, `open_redirect` | Contextual parameter reflection, SQL error signatures, unvalidated redirect parameters |

---

## Report Formats

- **Markdown (`.md`):** Formatted tables and executive breakdowns optimized for GitHub and GitLab pull request annotations and tracking issues.
- **JSON (`.json`):** Strict schema-validated structured objects designed for CI/CD ingestion, SIEM correlation, and automated pipelines.
- **HTML (`.html`):** Dark-mode responsive audit dashboard designed for browser analysis and stakeholder distribution.
- **SARIF (`.sarif`):** OASIS standard format directly compatible with GitHub Code Scanning alerts and security dashboards.
- **CSV (`.csv`):** Tabular data export with UTF-8 BOM encoding for direct Microsoft Excel and enterprise spreadsheet analysis.
- **PDF (`.pdf`):** Formal security audit artifact with executive summaries and finding descriptions (requires `reportlab`).

---

## Legal Compliance & Authorized Testing Policy

> **CRITICAL COMPLIANCE NOTICE:** Veylance is developed exclusively for authorized security auditing, defensive gap analysis, and authorized penetration testing.

- Execution of Veylance against infrastructure without documented, prior written authorization from the system owner violates local and international cybercrime legislation, including the **U.S. Computer Fraud and Abuse Act (CFAA, 18 U.S.C. Section 1030)**, the **UK Computer Misuse Act 1990**, and the **India Information Technology Act 2000**.
- Maintainers and contributors assume zero liability for unauthorized deployment, operational disruption, or damages caused by scanning activities.
- Consult [DISCLAIMER.md](DISCLAIMER.md) and [TERMS.md](TERMS.md) before conducting security audits.

---

## Antivirus False-Positive Advisory

Standalone release executables are packaged using PyInstaller. Due to the packaging mechanism bundling Python runtimes, dependencies, and byte-compiled modules into a single binary that decompresses into runtime memory, heuristic signature analyzers (such as Windows Defender, VirusTotal, or enterprise EDR agents) may generate false-positive alerts (e.g., `Generic.Trojan` or `Heur.Boring.Packed`).

To verify binary integrity:
1. Validate the cryptographic hash against the official `SHA256SUMS.txt` published with the GitHub release.
2. If organizational security policies restrict packed binaries, deploy Veylance directly from source via `pip install -e .`.

---

## Security Disclosure & Contributing

Refer to [SECURITY.md](SECURITY.md) for coordinated vulnerability disclosure procedures. Contributions are managed under the terms of the [MIT License](LICENSE).