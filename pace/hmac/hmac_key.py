__author__ = 'sisi'

import hmac
import hashlib

class HMAC_KEY:
    def __init__(self):
        self.k = bytes('the shared secret key here').encode('utf-8') 
        #for simpliciyt, we always use the same key
    
    def __del__(self):
        self.k = None
    
    def gen_hmac(self,content):
        return hmac.new(self.k, content, hashlib.sha256).digest()
    
    def verify(self,mac,content):
        #return hmac.compare_digest(mac, hmac.new(self.k, content, hashlib.sha256).digest())
        return str(mac)==str(hmac.new(self.k, content, hashlib.sha256).digest())