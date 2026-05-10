import urllib.request; from urllib.error import HTTPError
try:
    print(urllib.request.urlopen('http://localhost:5000/api/incidents').read().decode())
except HTTPError as e:
    print(e.read().decode())
