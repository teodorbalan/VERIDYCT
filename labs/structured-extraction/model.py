"""Small discriminative structured extractor; no autoregressive/LLM decoder."""
import torch
from torch import nn

CONFIGS={
 '01-cnn':dict(encoder='cnn',hidden=128,layers=3,char=False),
 '02-bilstm-word':dict(encoder='lstm',hidden=128,layers=1,char=False),
 '03-char-bilstm':dict(encoder='lstm',hidden=128,layers=1,char=True),
 '04-char-bilstm-large':dict(encoder='lstm',hidden=192,layers=2,char=True),
 '05-char-bigru':dict(encoder='gru',hidden=160,layers=2,char=True),
 '06-char-transformer':dict(encoder='transformer',hidden=192,layers=3,char=True),
}

class Extractor(nn.Module):
    def __init__(self,vocab_size,char_size,n_pairs,config):
        super().__init__();self.config=config
        h=config['hidden'];self.word=nn.Embedding(vocab_size,128,padding_idx=0)
        self.use_char=config['char'];inp=128
        if self.use_char:
            self.char=nn.Embedding(char_size,24,padding_idx=0)
            self.char_conv=nn.Conv1d(24,48,3,padding=1);inp+=48
        self.input_drop=nn.Dropout(.15)
        if config['encoder'] in ['lstm','gru']:
            cls=nn.LSTM if config['encoder']=='lstm' else nn.GRU
            self.encoder=cls(inp,h,num_layers=config['layers'],batch_first=True,bidirectional=True,dropout=.15 if config['layers']>1 else 0);out=h*2
        elif config['encoder']=='cnn':
            layers=[]
            for i in range(config['layers']):layers += [nn.Conv1d(inp if i==0 else h,h,5,padding=2),nn.GELU()]
            self.encoder=nn.Sequential(*layers);out=h
        else:
            self.project=nn.Linear(inp,h);self.position=nn.Embedding(384,h)
            layer=nn.TransformerEncoderLayer(h,4,h*3,dropout=.1,batch_first=True,norm_first=False)
            self.encoder=nn.TransformerEncoder(layer,config['layers'],enable_nested_tensor=False);out=h
        self.kind=nn.Embedding(10,32)
        self.query=nn.Linear(out+32,out)
        self.head=nn.Sequential(nn.Linear(out*3+32,256),nn.GELU(),nn.Dropout(.15),nn.Linear(256,n_pairs+1))

    def forward(self,words,chars,spans,clauses,kinds):
        mask=words.ne(0);x=self.word(words)
        if self.use_char:
            b,t,c=chars.shape
            ce=self.char(chars).reshape(b*t,c,24).transpose(1,2)
            ce=self.char_conv(ce).relu().amax(-1).reshape(b,t,48)
            x=torch.cat([x,ce],-1)
        x=self.input_drop(x)
        typ=self.config['encoder']
        if typ in ['lstm','gru']:
            # Fixed-shape unrolled sequence support is also available in ONNX.
            # Padding embeddings are zero and final padded states are masked.
            x,_=self.encoder(x)
        elif typ=='cnn':x=self.encoder(x.transpose(1,2)).transpose(1,2)
        else:
            x=self.project(x)+self.position(torch.arange(words.shape[1],device=words.device))[None]
            x=self.encoder(x,src_key_padding_mask=~mask)
        x=x*mask.unsqueeze(-1)
        s=torch.bmm(spans,x);c=torch.bmm(clauses,x);k=self.kind(kinds)
        q=self.query(torch.cat([s,k],-1))
        attention=torch.bmm(q,x.transpose(1,2)) / (x.shape[-1]**.5)
        attention=attention.masked_fill(~mask[:,None,:],-10000)
        context=torch.bmm(attention.softmax(-1),x)
        return self.head(torch.cat([s,c,context,k],-1))

def collate(rows):
    b=len(rows);t=max(len(r['tokens']) for r in rows);c=max(len(r['candidates']) for r in rows)
    words=torch.zeros(b,t,dtype=torch.long);chars=torch.zeros(b,t,24,dtype=torch.long)
    spans=torch.zeros(b,c,t);clauses=torch.zeros(b,c,t);kinds=torch.zeros(b,c,dtype=torch.long);labels=torch.full((b,c),-100,dtype=torch.long)
    for i,r in enumerate(rows):
        words[i,:len(r['tokens'])]=torch.tensor(r['tokens'])
        for j,w in enumerate(r['chars']):chars[i,j,:len(w)]=torch.tensor(w)
        for j,v in enumerate(r['candidates']):
            spans[i,j,v['lo']:v['hi']]=1/(v['hi']-v['lo'])
            clauses[i,j,v['clo']:v['chi']]=1/(v['chi']-v['clo'])
            kinds[i,j]=v['kind'];labels[i,j]=v.get('label',-100)
    return (words,chars,spans,clauses,kinds),labels,rows
