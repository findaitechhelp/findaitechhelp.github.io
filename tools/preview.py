"""Local-only preview server with a real 404; never serves source/review files."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
    def end_headers(self):
        self.send_header('X-Robots-Tag','noindex, nofollow')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def send_error(self,code,message=None,explain=None):
        file=ROOT/'dist'/'404.html'
        if code==404 and file.is_file():
            body=file.read_bytes();self.send_response(404);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers()
            if self.command!='HEAD':self.wfile.write(body)
        else:super().send_error(code,message,explain)
    def list_directory(self,path):
        self.send_error(404);return None
    def do_GET(self):
        redirects={'/buffalo-ny/':'/ny/buffalo/','/dallas-tx/':'/tx/dallas/'}
        path=urlsplit(self.path).path
        if path in redirects:
            self.send_response(301);self.send_header('Location',redirects[path]);self.end_headers();return
        super().do_GET()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8765);args=p.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Local preview: http://127.0.0.1:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
