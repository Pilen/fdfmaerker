#!/usr/bin/env python3


#### WARNING ####
# This is NOT a safe server, and isn't intented for outward facing connections.
# Use it at your own risk!

# If the address is set to "127.0.0.1" the server will only be visible on the local machine.
# If the address is set to "0.0.0.0" the server will be visible to anyone able to connect to the machine!
# Normally you are behind a router, and most routers are set to block outside connections to inside ports.
# But if you are on an open network you will be open for people trying to connect to the machine.
# If you are sure you are protected by the router you can start the server and then connect to it from your browser via your IP
# like visting 192.168.0.10:8080 ar whatever your servers local IP + port is.

import os
import pathlib
import mimetypes
import urllib.parse
import subprocess
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

# address = "127.0.0.1" # Server only visible on local machine
address = "0.0.0.0" # Server visible to anyone able to connect to the machine! WARNING DANGEROUS
port = 8080
rebuild = False

class DevRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        file = pathlib.Path("content/") / urllib.parse.unquote(self.path[1:])
        if file.is_dir():
            file = file / "index.html"
        if rebuild and (file.suffix == ".html" or not file.exists()):
            print("building")
            p = subprocess.run(["python", "maerker/build.py"])
            if p.returncode != 0:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("ERROR".encode("utf-8"))
                return

        file = str(file)
        print(file)


        if not filename_is_secure(file):
            self.send_response(403)
            self.end_headers()
            return

        mimetype, _ = mimetypes.guess_type(file, strict=False)
        # print(file, mimetype)

        try:
            with open(file, "rb") as f:
                self.send_response(200)
                self.send_header("Content-type", mimetype)
                self.end_headers()
                self.wfile.write(f.read())
            return
        except FileNotFoundError:
            self.send_response(404);
            self.end_headers()
            return

def filename_is_secure(filename):
    absolute = os.path.realpath(filename)
    return absolute.startswith(os.getcwd())

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    global rebuild
    args = parser.parse_args()
    rebuild = args.rebuild

    try:
        mimetypes.init()
        # WARNING, do not run this as an outward facing server
        server_address = (address, port)
        httpd = HTTPServer(server_address, DevRequestHandler)
        print("Running server...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print ( "Keyboard Interrupt received, shutting down server")
        httpd.socket.close()
if __name__ == "__main__":
    run();
