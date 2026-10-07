"""Stdlib parse of the actual site markup for JS event-regression harness. No generated form."""
import json, sys
from html.parser import HTMLParser
from pathlib import Path
VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.root={'tag':'document','attrs':{},'children':[]};self.stack=[self.root]
 def handle_starttag(self,tag,attrs):
  node={'tag':tag,'attrs':dict(attrs),'children':[]};self.stack[-1]['children'].append(node)
  if tag not in VOID:self.stack.append(node)
 def handle_startendtag(self,tag,attrs):
  self.stack[-1]['children'].append({'tag':tag,'attrs':dict(attrs),'children':[]})
 def handle_endtag(self,tag):
  for i in range(len(self.stack)-1,0,-1):
   if self.stack[i]['tag']==tag:self.stack=self.stack[:i];break
 def handle_data(self,data):self.stack[-1]['children'].append({'text':data})
if __name__=='__main__':
 p=Parser();p.feed((Path(__file__).parent/'site/index.html').read_text(encoding='utf-8'));sys.stdout.buffer.write(json.dumps(p.root,ensure_ascii=False).encode('utf-8'))
