#!/usr/bin/env python3
import argparse
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


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


class HostProxyHandler(BaseHTTPRequestHandler):
    upstream_host = None
    upstream_port = None
    host_header = None

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
        conn = http.client.HTTPConnection(self.upstream_host, self.upstream_port, timeout=10)

        body = None
        if "Content-Length" in self.headers:
            length = int(self.headers["Content-Length"])
            body = self.rfile.read(length)

        headers = {
            k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP
        }
        headers["Host"] = self.host_header

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
    parser = argparse.ArgumentParser(description="Local proxy that forces Host header")
    parser.add_argument("--listen", default="127.0.0.1:8088")
    parser.add_argument("--upstream", default="127.0.0.1:8080")
    parser.add_argument("--host", required=True)
    args = parser.parse_args()

    host, port = args.listen.split(":")
    up_host, up_port = args.upstream.split(":")

    HostProxyHandler.upstream_host = up_host
    HostProxyHandler.upstream_port = int(up_port)
    HostProxyHandler.host_header = args.host

    server = ThreadingHTTPServer((host, int(port)), HostProxyHandler)
    print(f"listening on http://{host}:{port} -> http://{up_host}:{up_port} Host:{args.host}")
    server.serve_forever()


if __name__ == "__main__":
    main()
