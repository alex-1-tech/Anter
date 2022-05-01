from hashlib import md5

from requests import get

print( md5('test@gmail.com'.encode('utf-8')).hexdigest())

#print(get('http://127.0.0.1:8000//api/news').json())
