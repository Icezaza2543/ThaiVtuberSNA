"""Playwright browser lifecycle and session management."""

import os
from pathlib import Path
from typing import Optional


class PlaywrightNotInstalledError(RuntimeError):
    """Raised when Playwright is required but not installed in the environment."""

    pass


def check_playwright():
    """Verify that Playwright is importable or raise a helpful error."""
    try:
        from playwright.async_api import async_playwright

        return async_playwright
    except ImportError as exc:
        raise PlaywrightNotInstalledError(
            'Playwright is not installed. Install with: pip install -e ".[discovery]". '
            "A locally installed Chrome or Edge can be used; a Playwright browser "
            "download is optional."
        ) from exc


def browser_channel_candidates() -> list[Optional[str]]:
    """Return browser launch order, preferring installed browsers."""
    override = os.environ.get("REGISTRY_BROWSER_CHANNEL", "").strip().lower()
    if override:
        if override not in {"chrome", "msedge", "chromium"}:
            raise ValueError(
                "REGISTRY_BROWSER_CHANNEL must be chrome, msedge, or chromium"
            )
        return [None if override == "chromium" else override]
    return ["chrome", "msedge", None]


class BrowserSession:
    """Manages an async Chromium-family browser session and isolated context."""

    def __init__(
        self,
        *,
        headless: bool = False,
        profile_dir: Optional[Path] = None,
        timeout: float = 30.0,
    ):
        self.headless = headless
        self.profile_dir = profile_dir
        self.timeout = timeout
        self._playwright = None
        self._browser = None
        self._context = None
        self.browser_backend: Optional[str] = None

    async def _launch_context(self, chromium, *, user_agent, viewport):
        errors: list[str] = []
        for channel in browser_channel_candidates():
            label = channel or "playwright-chromium"
            launch_kwargs = {"headless": self.headless}
            if channel:
                launch_kwargs["channel"] = channel
            try:
                if self.profile_dir:
                    self.profile_dir.mkdir(parents=True, exist_ok=True)
                    self._context = await chromium.launch_persistent_context(
                        str(self.profile_dir),
                        user_agent=user_agent,
                        viewport=viewport,
                        **launch_kwargs,
                    )
                else:
                    self._browser = await chromium.launch(**launch_kwargs)
                    self._context = await self._browser.new_context(
                        user_agent=user_agent,
                        viewport=viewport,
                    )
                self.browser_backend = label
                return
            except Exception as exc:
                errors.append(f"{label}: {exc}")
                if self._browser:
                    try:
                        await self._browser.close()
                    except Exception:
                        pass
                    self._browser = None
                self._context = None

        joined = "\n  - ".join(errors)
        raise RuntimeError(
            "Could not launch a supported browser. Tried system Chrome, system Edge, "
            "and Playwright Chromium. On Windows, install Chrome or use the built-in "
            "Microsoft Edge; no Playwright browser download is required when either is "
            f"available. Attempts:\n  - {joined}"
        )

    async def __aenter__(self):
        async_playwright = check_playwright()
        self._playwright = await async_playwright().start()

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/128.0.0.0 Safari/537.36"
        )
        viewport = {"width": 1280, "height": 800}

        try:
            await self._launch_context(
                self._playwright.chromium,
                user_agent=user_agent,
                viewport=viewport,
            )
        except Exception:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            raise

        self._context.set_default_timeout(int(self.timeout * 1000))
        return self._context

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._context:
                await self._context.close()
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
