"""Example SPECTRE plugin — response time analyzer."""
from plugin_loader import Plugin


class ResponseTimePlugin(Plugin):
    name = "response_time"
    version = "1.0.0"
    author = "イズミー (IZUMI)"
    description = "Analyze HTTP response times & detect slow endpoints"

    def run(self, target, session, context=None):
        import time
        url = target if target.startswith("http") else f"https://{target}"
        timings = []
        for path in ["", "/robots.txt", "/favicon.ico", "/sitemap.xml"]:
            try:
                t0 = time.time()
                r = session.get(f"{url}{path}", timeout=10, allow_redirects=False)
                dt = int((time.time() - t0) * 1000)
                timings.append({"path": path or "/", "status": r.status_code,
                                "ms": dt, "size": len(r.content)})
            except Exception as e:
                timings.append({"path": path, "error": str(e)})
        slow = [t for t in timings if t.get("ms", 0) > 2000]
        return {"url": url, "timings": timings,
                "slow_endpoints": slow, "count": len(timings)}