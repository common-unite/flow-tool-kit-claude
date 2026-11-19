"""Polite fetching for the brand kit scripts: one request every `delay` seconds to the site, and a 429 or 503 waits for
Retry-After (or backs off) and tries again, slowing the rest of the run. Hosted site builders refuse fast crawls; a slow
crawl finishes, a fast one gets refused.

Python 3 standard library only. Tests replace `POLITE.opener` with a fake, so nothing here needs the network to be tested.
"""
import threading
import time
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (compatible; flow-tool-kit brand-kit)"


class NetworkUnavailable(Exception):
    """The site could not be reached at all (no network in this sandbox, a refused domain, DNS)."""


class Polite:
    def __init__(self, delay=0.3, opener=None):
        self.delay, self.lock, self.next = delay, threading.Lock(), 0.0
        self.opener = opener or (lambda request, timeout: urllib.request.urlopen(request, timeout=timeout))

    def wait(self):
        with self.lock:
            now = time.monotonic()
            pause = max(0.0, self.next - now)
            self.next = max(now, self.next) + self.delay
        if pause:
            time.sleep(pause)

    def open(self, url, headers=None, tries=5, timeout=30):
        backoff = 2.0
        for attempt in range(tries):
            self.wait()
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
            try:
                return self.opener(request, timeout)
            except urllib.error.HTTPError as error:
                if error.code in (429, 503) and attempt < tries - 1:
                    retry = error.headers.get("Retry-After") if error.headers else None
                    time.sleep(float(retry) if retry and retry.isdigit() else backoff)
                    backoff *= 2
                    with self.lock:
                        self.delay = min(self.delay * 1.5 + 0.2, 5.0)
                    continue
                raise
            except urllib.error.URLError as error:
                raise NetworkUnavailable(f"{url}: {error.reason}") from error

    def text(self, url):
        """The page's text and the URL it ended at after redirects."""
        with self.open(url) as response:
            return response.read().decode("utf-8", "replace"), response.geturl()

    def body(self, url, limit=None):
        """The file's bytes and its content type."""
        with self.open(url) as response:
            data = response.read(limit) if limit else response.read()
            content_type = response.headers.get_content_type() if response.headers else ""
            return data, content_type


POLITE = Polite()
