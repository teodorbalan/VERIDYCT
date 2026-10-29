"""Separate sigmoid contract: a typed value candidate may produce multiple pairs."""
import argparse
import json
import sys
import numpy as np
from grammar import canonical
from runtime import CpuExtractor, numpy_batch


def decode_multilabel(rows, logits, pairs, threshold=.5):
    probabilities=1/(1+np.exp(-np.clip(logits,-80,80)))
    results=[]
    for i,row in enumerate(rows):
        predicted=[];seen=set()
        for j,candidate in enumerate(row['candidates']):
            # Index zero exists for checkpoint compatibility, but NONE is all-zero.
            for label in np.flatnonzero(probabilities[i,j,1:]>=threshold)+1:
                subject,attribute=pairs[label-1]
                atom={'subject':subject,'attribute':attribute,'value':candidate['value']}
                identity=(subject,attribute,canonical(candidate['value']))
                if identity in seen:continue
                seen.add(identity)
                predicted.append({'atom':atom,'model_score':float(probabilities[i,j,label]),
                                  'value_span_chars':[candidate['start'],candidate['end']],
                                  'value_text':row['text'][candidate['start']:candidate['end']]})
        results.append(predicted)
    return results


class MultiLabelCpuExtractor(CpuExtractor):
    def __init__(self,bundle,model='model.onnx',threads=2):
        super().__init__(bundle,model,threads)
        if self.meta.get('decoder')!='multilabel_sigmoid':
            raise ValueError('A multilabel_sigmoid bundle is required; softmax model incompatible')
        self.threshold=self.meta['selected_threshold']

    def predict_encoded(self,rows):
        feed=numpy_batch(rows)
        logits=self.session.run(None,{k:v for k,v in feed.items() if k in self.inputs})[0]
        return decode_multilabel(rows,logits,self.meta['pairs'],self.threshold)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--text');p.add_argument('--previous',default='');a=p.parse_args()
    engine=MultiLabelCpuExtractor(a.bundle)
    if a.text is not None:print(json.dumps(engine.extract(a.text,a.previous),ensure_ascii=False,indent=2))
    else:
        for line in sys.stdin:
            r=json.loads(line);print(json.dumps(engine.extract(r['text'],r.get('previous_text','')),ensure_ascii=False),flush=True)
