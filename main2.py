from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs, urljoin, quote, unquote
import re

chrome_hedz = { #careful or you'll get shit on by cloudflare
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

def rewrite_html(content: bytes, base_url: str, proxy_prefix: str):
    html = content.decode(errors="ignore")
    pattern = r'(?P<attr>(?:href|src|action))=["\'](?!https?:|data:|//)(?P<url>[^"\']+)'
    html = re.sub(
        pattern,
        lambda m: f'{m.group("attr")}="{proxy_prefix}{quote(urljoin(base_url, m.group("url")), safe=":/?=&")}"',
        html,
        flags=re.IGNORECASE
    )
    html = html.replace("src=\"", f"src=\"{proxy_prefix}")
    html = html.replace("href=\"", f"href=\"{proxy_prefix}")
    return html.encode()

def find_nth_occurrence(text, char, n):
  start_index = 0
  index = 0
  for _ in range(n):
      index = text.find(char, start_index)
      if index == -1:  # Character not found enough times
          return -1
      start_index = index + 1  # Start searching from the next position

  return index
  
history = []
class SimpleProxy(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        print(query)
        target_url = query.get("url", [None])[0]
        history.append(query)
        
        if not target_url:
            
            return

        target_url = unquote(target_url)  # decode URL-encoded characters

        try:
            req = Request(target_url, headers=chrome_hedz)
            with urlopen(req) as response:
                content_type = response.headers.get("Content-Type", "text/html")
                content = response.read()

                if "text/html" in content_type:
                    content = rewrite_html(content, response.geturl(), "?url=")

                self.send_response(200)
                for h, v in chrome_hedz.items():
                    self.send_header(h, v)
                print(response.headers)
                if 'Location' in response.headers:
                    # rewrite relative or absolute Location headers to go through proxy
                    loc = response.headers['Location']
                    loc_full = urljoin(response.geturl(), loc)
                    self.send_header('Location', "?url=" + quote(loc_full, safe=":/?=&"))

                self.send_header("Content-Type", content_type)
                for header, value in response.headers.items():
                    if header.lower() not in ["content-length", "content-type", "location"]:
                        self.send_header(header, value)

                self.end_headers()
                self.wfile.write(content)

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode())

def run(server_class=HTTPServer, handler_class=SimpleProxy, port=8080):
    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()

 
