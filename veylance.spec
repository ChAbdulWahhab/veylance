# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building standalone Veylance (veyl) binary."""
import os
import sys
from pathlib import Path

block_cipher = None

repo_root = Path(SPECPATH).resolve()

from PyInstaller.utils.hooks import collect_data_files

# Bundled data files (sensitive paths, subdomains, user agents, pyfiglet fonts, tldextract PSL, etc.)
datas = [
    (str(repo_root / "veylance" / "data"), "veylance/data"),
]
datas += collect_data_files("pyfiglet")
datas += collect_data_files("tldextract")

# Hidden imports for dynamically registered modules and CLI dependencies
hiddenimports = [
    # Core CLI & UI
    "veylance.cli",
    "veylance.config",
    "veylance.ui.banner",
    "veylance.ui.consent",
    "veylance.ui.menu",
    "veylance.ui.progress",
    "veylance.ui.tables",
    "veylance.utils.audit",
    "veylance.utils.drift",
    "veylance.utils.logger",
    "veylance.utils.wordlists",
    # All 35 security modules
    "veylance.modules",
    "veylance.modules.base",
    "veylance.modules.headers",
    "veylance.modules.tls_https",
    "veylance.modules.cookies",
    "veylance.modules.cors",
    "veylance.modules.http_methods",
    "veylance.modules.sensitive_paths",
    "veylance.modules.error_leak",
    "veylance.modules.forms_csrf",
    "veylance.modules.js_analysis",
    "veylance.modules.tech_fingerprint",
    "veylance.modules.rate_limit",
    "veylance.modules.robots_sitemap",
    "veylance.modules.dns_recon",
    "veylance.modules.subdomain",
    "veylance.modules.open_redirect",
    "veylance.modules.xss_reflection",
    "veylance.modules.sqli_heuristic",
    "veylance.modules.directory_list",
    "veylance.modules.exposed_files",
    "veylance.modules.waf_detect",
    "veylance.modules.csp_analyzer",
    "veylance.modules.graphql_probe",
    "veylance.modules.jwt_probe",
    # Advanced / Hidden Exposure Modules
    "veylance.modules.secrets_in_js",
    "veylance.modules.source_map_exposure",
    "veylance.modules.git_exposure",
    "veylance.modules.subdomain_takeover",
    "veylance.modules.dependency_exposure",
    "veylance.modules.ci_cd_exposure",
    "veylance.modules.sri_check",
    "veylance.modules.comment_leak",
    "veylance.modules.cert_transparency_recon",
    "veylance.modules.cache_poisoning_headers",
    # Correlation & Differentiation Modules
    "veylance.modules.combined_risk_scenarios",
    "veylance.modules.scan_drift",
    # All report generators
    "veylance.report",
    "veylance.report.base",
    "veylance.report.markdown",
    "veylance.report.json_report",
    "veylance.report.html_report",
    "veylance.report.sarif",
    "veylance.report.csv_report",
    "veylance.report.pdf_report",
    # External libraries
    "dns.resolver",
    "dns.exception",
    "bs4",
    "yaml",
    "httpx",
    "tldextract",
    "pyfiglet",
    "pyfiglet.fonts",
    "rich",
    "rich.console",
    "rich.table",
    "rich.panel",
    "rich.prompt",
    "rich.progress",
    "typer",
]

a = Analysis(
    [str(repo_root / "veylance" / "__main__.py")],
    pathex=[str(repo_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy", "pandas"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="veyl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
