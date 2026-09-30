#!/usr/bin/env python3

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rxmed_decoder import (
    _endpoint_manager,
    collapse_medications,
    decode_claim
)


HOST = "0.0.0.0"
PORT = 8080
DECODE_PATH = "/medications/decode"


def decode_medications(records):
    rxnav_url, nppes_url = _endpoint_manager.snapshot()

    decoded_claims = [
        decode_claim(record, rxnav_url, nppes_url)
        for record in records
    ]

    return collapse_medications(decoded_claims)


class RxMedRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, value):
        body = json.dumps(value, indent=4).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != DECODE_PATH:
            self.send_json(404, {"error": "Not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length)
            records = json.loads(body)

            if not isinstance(records, list):
                self.send_json(
                    400,
                    {"error": "Request body must be a JSON array"}
                )
                return

            medications = decode_medications(records)
            self.send_json(200, medications)

        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})

        except Exception as error:
            self.send_json(500, {"error": str(error)})

    def log_message(self, format, *args):
        print(
            f"{self.client_address[0]} - {format % args}",
            file=sys.stderr
        )


def main():
    server = ThreadingHTTPServer(
        (HOST, PORT),
        RxMedRequestHandler
    )

    print(f"RxMed HTTP service listening on {HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
