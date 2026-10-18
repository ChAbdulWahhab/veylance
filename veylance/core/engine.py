"""Scan engine — orchestrates modules.

This file performs three tasks:
  1. Crawling (if any module requires crawl data)
  2. Running modules concurrently with a semaphore
  3. Wrapping findings into a ScanResult
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Optional

from veylance.core.findings import Finding, ScanResult, Severity
from veylance.core.session import HttpSession
from veylance.core.crawler import Crawler
from veylance.core.target import Target
from veylance.ui.progress import ScanProgress


class ScanEngine:
    def __init__(
        self,
        target: Target,
        modules: list[str],
        max_pages: int = 40,
        concurrency: int = 10,
        rate_requests: int = 20,
        timeout: int = 10,
        verify_tls: bool = True,
        proxy: Optional[str] = None,
        user_agent: Optional[str] = None,
        cookie: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        interactive: bool = False,
        no_history: bool = False,
        history_dir: Optional[Any] = None,
    ):
        self.target = target
        from veylance.modules import ALL_MODULES
        self.module_names = [m for m in modules if m in ALL_MODULES]
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.rate_requests = rate_requests
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.proxy = proxy
        self.user_agent = user_agent
        self.cookie = cookie
        self.extra_headers = extra_headers or {}
        self.interactive = interactive
        self.no_history = no_history
        self.history_dir = history_dir

    async def run(self, progress: ScanProgress | None = None) -> ScanResult:
        from veylance.modules import ALL_MODULES
        if progress is None:
            progress = ScanProgress(quiet=True)  # no-op

        t0 = time.time()

        async with HttpSession(
            timeout=self.timeout,
            verify_tls=self.verify_tls,
            proxy=self.proxy,
            user_agent=self.user_agent,
            cookie=self.cookie,
            extra_headers=self.extra_headers,
            concurrency=self.concurrency,
        ) as session:

            # Shared context readable by every module
            ctx: dict[str, Any] = {
                "pages": {},
                "scripts": set(),
                "forms": [],
                "js_endpoints": set(),
                "tech": set(),
                "info": {},
                "findings": [],
                "rate_requests": self.rate_requests,
                "no_history": self.no_history,
                "history_dir": self.history_dir,
            }

            # ---- Crawl (if any module requests it) ----
            needs_crawl = any(
                ALL_MODULES[m].requires_crawl for m in self.module_names
            )
            if needs_crawl:
                progress.start("crawl", status="discovering pages...")
                crawler = Crawler(
                    self.target, session,
                    max_pages=self.max_pages,
                    concurrency=self.concurrency,
                )
                await crawler.crawl()
                await crawler.mine_js()   # Also extract JS endpoints
                ctx["pages"] = crawler.pages
                ctx["scripts"] = crawler.scripts
                ctx["forms"] = crawler.forms
                ctx["js_endpoints"] = crawler.js_endpoints
                ctx["tech"] = crawler.tech
                progress.done("crawl", f"{len(crawler.pages)} pages")

            # ---- Run modules (limited by semaphore) ----
            findings: list[Finding] = []
            errors: list[str] = []
            sem = asyncio.Semaphore(self.concurrency)

            import logging
            logger = logging.getLogger("veylance.engine")

            async def run_module(name: str):
                async with sem:
                    progress.start(name, status="scanning...")
                    try:
                        mod_cls = ALL_MODULES[name]
                        mod = mod_cls(self.target, session, ctx)
                        # Ensure one hanging module doesn't stall the rest of the audit
                        mod_timeout = max(15.0, float(self.timeout * 3))
                        res = await asyncio.wait_for(mod.run(), timeout=mod_timeout)
                        findings.extend(res)
                        progress.done(name, f"{len(res)} findings")
                    except asyncio.TimeoutError:
                        skip_msg = f"module skipped: execution timed out after {int(mod_timeout)}s"
                        errors.append(f"{name}: {skip_msg}")
                        logger.debug("Module %s timed out after %ss", name, mod_timeout)
                        progress.fail(name, "timed out")
                    except Exception as e:
                        skip_msg = f"module skipped: {type(e).__name__}: {e}"
                        errors.append(f"{name}: {skip_msg}")
                        logger.debug("Module %s error: %s", name, e, exc_info=True)
                        progress.fail(name, f"{type(e).__name__}")

            from veylance.modules import CORRELATION_MODULES
            phase1_modules = [m for m in self.module_names if m not in CORRELATION_MODULES]
            phase2_modules = [m for m in self.module_names if m in CORRELATION_MODULES]

            # Phase 1: Standard and Advanced Active Scan Modules
            if phase1_modules:
                await asyncio.gather(*(run_module(n) for n in phase1_modules))

            # Populate findings context so correlation and drift modules can analyze them
            ctx["findings"] = list(findings)

            # Phase 2: Post-scan Correlation & Drift Modules (no new HTTP requests)
            if phase2_modules:
                await asyncio.gather(*(run_module(n) for n in phase2_modules))

            if hasattr(progress, "stop"):
                progress.stop()

            return ScanResult(
                target=self.target.base,
                timestamp=datetime.now(),
                findings=findings,
                pages=ctx["pages"],
                tech=ctx["tech"],
                info=ctx["info"],
                forms=ctx["forms"],
                scripts=ctx["scripts"],
                js_endpoints=ctx["js_endpoints"],
                duration=time.time() - t0,
                modules_run=self.module_names,
                errors=errors,
            )