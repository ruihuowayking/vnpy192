str = "\u5e73\u6628"
print str.decode("unicode_escape")
from pytdx.exhq import TdxExHq_API
api = TdxExHq_API()
with api.connect("119.23.127.172",7727):
    at = api.get_instrument_quote(47, "IF1709")
    print(at)    
