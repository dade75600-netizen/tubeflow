import urllib.request
import re
import webbrowser

req = urllib.request.Request('http://127.0.0.1:8000/', headers={'Host': 'ff4efb86e91933.lhr.life', 'X-Forwarded-Proto': 'https'})
html = urllib.request.urlopen(req).read().decode('utf-8')
match = re.search(r'href=\"(https://www.tiktok.com/v2/auth/authorize/[^\"]+)\"', html)
if match:
    url = match.group(1).replace('&amp;', '&')
    print('Opening:', url)
    webbrowser.open(url)
else:
    print('URL not found in HTML')
