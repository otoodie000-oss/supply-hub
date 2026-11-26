import time, torch, torch.nn as nn, torch.nn.functional as F
torch.set_num_threads(4)
def mk(d,L,ff,V):
    layer=nn.TransformerEncoderLayer(d,4,ff,batch_first=True,norm_first=True,activation='gelu',dropout=0.0)
    return nn.ModuleDict({'emb':nn.Embedding(V,d),'tf':nn.TransformerEncoder(layer,L,enable_nested_tensor=False),'out':nn.Linear(d,V)})
for d,L,ff in [(128,4,512),(192,4,768),(256,6,1024)]:
    m=mk(d,L,ff,4096); opt=torch.optim.AdamW(m.parameters(),1e-3)
    n=sum(p.numel() for p in m.parameters())
    B,T=64,128
    x=torch.randint(0,4096,(B,T)); mask=nn.Transformer.generate_square_subsequent_mask(T)
    for mode in ['fp32','bf16']:
        ts=[]
        for it in range(6):
            t0=time.time()
            with torch.autocast('cpu',dtype=torch.bfloat16,enabled=(mode=='bf16')):
                h=m['tf'](m['emb'](x),mask=mask,is_causal=True); lg=m['out'](h)
            loss=F.cross_entropy(lg.float().view(-1,4096),x.view(-1)); loss.backward(); opt.step(); opt.zero_grad()
            ts.append(time.time()-t0)
        dt=sorted(ts[2:])[1]
        print('d%d L%d params %.2fM %s: %.0f tok/s'%(d,L,n/1e6,mode,B*T/dt),flush=True)
