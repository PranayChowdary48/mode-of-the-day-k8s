#!/usr/bin/env python3
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import cycle
from urllib.parse import urlsplit


HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def parse_upstream(url):
    u = urlsplit(url)
    if not u.scheme or not u.hostname:
        raise ValueError(f"Invalid upstream: {url}")
    port = u.port or (443 if u.scheme == "https" else 80)
    return u.scheme, u.hostname, port


class RRProxyHandler(BaseHTTPRequestHandler):
    rr = None

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def do_PUT(self):
        self._proxy()

    def do_DELETE(self):
        self._proxy()

    def do_PATCH(self):
        self._proxy()

    def do_HEAD(self):
        self._proxy()

    def _proxy(self):
        scheme, host, port = next(self.rr)
        conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        conn = conn_cls(host, port, timeout=10)

        body = None
        if "Content-Length" in self.headers:
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)

        headers = {
            k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP
        }

        conn.request(self.command, self.path, body=body, headers=headers)
        resp = conn.getresponse()

        self.send_response(resp.status, resp.reason)
        for k, v in resp.getheaders():
            if k.lower() in HOP_BY_HOP:
                continue
            self.send_header(k, v)
        self.end_headers()

        if self.command != "HEAD":
            data = resp.read()
            if data:
                self.wfile.write(data)

        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Round-robin reverse proxy")
    parser.add_argument("--listen", default="127.0.0.1:8080")
    parser.add_argument("upstreams", nargs="+", help="e.g. http://127.0.0.1:8081")
    args = parser.parse_args()

    parsed = [parse_upstream(u) for u in args.upstreams]
    RRProxyHandler.rr = cycle(parsed)

    host, port = args.listen.split(":")
    server = ThreadingHTTPServer((host, int(port)), RRProxyHandler)
    print(f"listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
