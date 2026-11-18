"""Apply the explicitly reviewed computing-class batch; no lexical auto-classifier."""
from pathlib import Path
import json,uuid
root=Path(__file__).resolve().parents[1]
def read(name):return [json.loads(l) for l in (root/name).read_text().splitlines()]
def write(name,rows,key):
 p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in sorted(rows,key=lambda r:r[key])))
cs=read('knowledge/concepts.jsonl');ss=read('knowledge/statements.jsonl');by={c['slug']:c for c in cs}
for slug,label in [('numeric-representation','Numeric representation'),('file-operation','File operation')]:
 if slug not in by:
  c={'id':str(uuid.uuid5(uuid.NAMESPACE_URL,'https://curricula.live/concepts/'+slug)),'slug':slug,'label':label};cs.append(c);by[slug]=c
ibm='https://www.ibm.com/docs/en/xl-c-aix/13.1.0?topic=functions-binary-coded-decimal-built-in'
types='https://docs.python.org/3/library/stdtypes.html'
files='https://docs.python.org/3/tutorial/inputoutput.html#methods-of-file-objects'
reviews=[]
def add(a,b,url,reason):
 sid=str(uuid.uuid5(uuid.NAMESPACE_URL,'curricula.live:classification-review:2026-11-18:'+a+':subtype_of:'+b))
 old=next((s for s in ss if s['predicate']=='subtype_of' and s['subject']['id']==by[a]['id'] and s['object']['id']==by[b]['id']),None)
 if old:sid=old['id']
 else:ss.append({'id':sid,'subject':{'kind':'concept','id':by[a]['id']},'predicate':'subtype_of','object':{'kind':'concept','id':by[b]['id']}})
 reviews.append({'statement_id':sid,'subject_slug':a,'object_slug':b,'predicate':'subtype_of','evidence_urls':[url],'review_reason':reason,'review_status':'editorially_reviewed_class_interpretation','independent_expert_review':False,'scope':'Conventional computing meaning; source examples corroborate the classification. Conditional class-inclusion premise, not an equivalence or a prerequisite.','historical_edge_automatically_promoted':False})
add('binary-coded-decimal','encoding',ibm,'BCD encodes decimal digits in binary; the concept denotes an encoding scheme, not a numeral base.')
add('binary-coded-decimal','numeric-representation',ibm,'BCD is a representation of decimal numeric values using separately encoded decimal digits.')
add('numeric-representation','data-representation',ibm,'Numeric representations specialize data representation to numeric values; editorial category definition.')
for x in ['fixed-point-representation','floating-point-representation','integer-encoding']:
 add(x,'numeric-representation',types,'A representation or encoding of numeric values, under the numeric representation category definition.')
for x in ['integer-addition','integer-subtraction','integer-multiplication','integer-division','real-division','binary-addition','binary-subtraction','modulo','exponentiation']:
 add(x,'arithmetic-operation',types,'Numeric arithmetic includes addition, subtraction, multiplication, division, remainder and powers; integer/binary qualifiers restrict the operand domain.')
for parent in ['arithmetic-operation','string-operation','bitwise-operation','file-operation']:
 add(parent,'computational-operation',files if parent=='file-operation' else types,'Operations on numeric values, strings, bits or files are computational operations; editorial category inclusion.')
for x in ['string-concatenation','string-slicing','string-indexing','string-length','string-splitting','string-comparison','substring-search']:
 add(x,'string-operation',types,'String and sequence documentation describes concatenation, slicing, indexing, length, splitting, comparisons and searching as operations on strings.')
for x in ['bitwise-and','bitwise-or','bitwise-xor','bitwise-not']:
 add(x,'bitwise-operation',types+'#bitwise-operations-on-integer-types','The bitwise operation table explicitly enumerates AND, OR, XOR and inversion.')
for x in ['file-open','file-read','file-write','file-append','file-seek','file-close']:
 add(x,'file-operation',files,'Opening and the read, write, append, seek and close file actions operate on files or file streams.')
write('knowledge/concepts.jsonl',cs,'slug');write('knowledge/statements.jsonl',ss,'id')
write('pipeline/classification-review/specific-computing-classes.jsonl',reviews,'statement_id')
print('reviewed classifications',len(reviews),'concepts',len(cs),'statements',len(ss))
