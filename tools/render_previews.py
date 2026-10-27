"""Rendered ME-Like demos, not device captures. Requires Pillow, NumPy, ffmpeg.

Uses the current Compose gradient endpoints, positional key groups and shared
group bounds. Typing is illustrative, uses synthetic 'hello', and returns empty.
Theme definitions, backgrounds and group settings are not altered by rendering.
"""
from pathlib import Path
import json, math, zipfile, io, subprocess, hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageOps

ROOT=Path(__file__).resolve().parents[1]
W,H,TOP,BAR=640,744,40,64
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
TAU=math.tau

def rgba(s):
    v=int(s);assert v&0xffffffff==0,'Preview renderer needs sRGB colors'
    v>>=32;return ((v>>16)&255,(v>>8)&255,v&255,(v>>24)&255)

def flat(value,size):return Image.new('RGBA',size,rgba(value))

def grad(g,rect,canvas=None,phase=0):
    x,y,w,h=map(int,rect);cx,cy,cw,ch=canvas or rect
    yy,xx=np.mgrid[0:h,0:w];xx=xx+x;yy=yy+y
    a=math.radians(g.get('angle',135));dx,dy=math.cos(a),math.sin(a)
    span=abs(dx)*cw+abs(dy)*ch
    t=.5+((xx-(cx+cw/2))*dx+(yy-(cy+ch/2))*dy)/max(span,1)+phase/360
    if phase:t=t%1
    stops=sorted(g['stops'],key=lambda s:s['position']);p=[s['position'] for s in stops];c=np.array([rgba(s['color']) for s in stops])
    return Image.fromarray(np.stack([np.interp(t,p,c[:,i]) for i in range(4)],axis=2).astype(np.uint8),'RGBA')

def masked(im,mask):
    a=np.asarray(im.getchannel('A'),dtype=float)*np.asarray(mask)/255
    im.putalpha(Image.fromarray(a.astype(np.uint8)));return im

def face(layer,rect,g=None,solid=None,radius=12,border=None,borderSolid=None,width=2,canvas=None,borderCanvas=None):
    x,y,w,h=map(int,rect);mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius,fill=255)
    if g is not None or solid is not None:
        f=grad(g,rect,canvas) if g is not None else flat(solid,(w,h))
        layer.alpha_composite(masked(f,mask),(x,y))
    if border is not None or borderSolid is not None:
        m=Image.new('L',(w,h));ImageDraw.Draw(m).rounded_rectangle((0,0,w-1,h-1),radius,outline=255,width=max(1,round(width)))
        f=grad(border,rect,borderCanvas) if border is not None else flat(borderSolid,(w,h))
        layer.alpha_composite(masked(f,m),(x,y))

RECTS={}
for row in range(4):
    for col in range(4 if row<3 else 2):
        x=col*160+6 if row<3 else (6 if col==0 else 486)
        y=TOP+BAR+row*160+6
        RECTS[f'{row}:{col}']=(x,y,148 if row<3 or col else 468,148)

def union(keys):
    rs=[RECTS[k] for k in keys if k in RECTS]
    if not rs:return None
    x=min(r[0] for r in rs);y=min(r[1] for r in rs)
    return (x,y,max(r[0]+r[2] for r in rs)-x,max(r[1]+r[3] for r in rs)-y)

def resolved(theme,id):
    out=theme.copy()
    for group in theme.get('keyGroups',[]):
        if id in group['keys']:
            out.update(group['design'])
            if group['design'].get('surfaceGradient'):out['surfaceStyle']='GRADIENT'
            elif group['design'].get('surfaceColor'):out['surfaceStyle']='SOLID'
            if group['design'].get('borderGradient'):out['borderStyle']='GRADIENT'
            elif group['design'].get('borderColor'):out['borderStyle']='SOLID'
    spec=theme.get('keyOverrides',{}).get(id,{})
    out.update(spec)
    if spec.get('surfaceGradient'):out['surfaceStyle']='GRADIENT'
    elif spec.get('surfaceColor'):out['surfaceStyle']='SOLID'
    if spec.get('borderGradient'):out['borderStyle']='GRADIENT'
    elif spec.get('borderColor'):out['borderStyle']='SOLID'
    return out

def group_canvas(theme,id,layer):
    field=layer+'Gradient';solid=layer+'Color';spec=theme.get('keyOverrides',{}).get(id,{})
    if field in spec or solid in spec:return RECTS[id] if layer=='surface' and field in spec else None
    for group in reversed(theme.get('keyGroups',[])):
        if id in group['keys'] and (group.get('sharedGradientCanvas') or field in group['design'] or solid in group['design']):
            if group.get('sharedGradientCanvas') or (layer=='surface' and field in group['design']):return union(group['keys'])
            return None
    return None

LABELS={'0:0':'a','0:1':'n','0:2':'i','0:3':'☺','1:0':'h','1:1':'o','1:2':'r','1:3':'123','2:0':'t','2:1':'e','2:2':'s','2:3':'⌫','3:0':'space','3:1':'↵'}
HINTS={'0:0':[(.8,.8,'v')],'0:1':[(.5,.85,'l')],'0:2':[(.2,.8,'x')],'1:0':[(.85,.5,'k')],'1:1':[(.2,.18,'q'),(.5,.15,'u'),(.8,.18,'p'),(.85,.5,'b'),(.8,.8,'j'),(.5,.85,'d'),(.2,.8,'g'),(.15,.5,'c')],'1:2':[(.15,.5,'m'),(.5,.15,'▴')],'2:0':[(.8,.2,'y')],'2:1':[(.5,.15,'w'),(.85,.5,'z'),(.5,.85,'.')],'2:2':[(.2,.2,'f')]}
EVENTS=[(6,'1:0','h'),(14,'2:1','e'),(22,'0:1','l'),(30,'0:1','l'),(38,'1:1','o'),(60,'2:3',None),(68,'2:3',None),(76,'2:3',None),(84,'2:3',None),(92,'2:3',None)]

def backdrop(doc,asset_frames,t,rect):
    x,y,w,h=rect
    if doc['mode']=='COLORFUL':im=grad(doc,rect)
    elif doc['mode'] in ('IMAGE','GIF') and asset_frames:
        frames,durations=asset_frames;stamp=t%sum(durations);index=0
        while stamp>=durations[index] and index<len(frames)-1:stamp-=durations[index];index+=1
        im=ImageOps.fit(frames[index],(w,h),method=Image.Resampling.LANCZOS).convert('RGBA')
    else:im=Image.new('RGBA',(w,h))
    im.putalpha(im.getchannel('A').point(lambda a:round(a*doc.get('opacity',1))))
    return im

def media(z,doc):
    if not doc.get('mediaUri'):return None
    with Image.open(io.BytesIO(z.read(doc['mediaUri']))) as im:
        frames=[];times=[]
        for i in range(getattr(im,'n_frames',1)):
            im.seek(i);frames.append(im.convert('RGB').copy());times.append(im.info.get('duration',80))
    return frames,times

def render(entry):
    folder=ROOT/'themes'/entry['id'];package=ROOT/entry['package']['url']
    with zipfile.ZipFile(package) as z:
        doc=json.loads(z.read('theme.json'));bgframes=media(z,doc['backdrop']);tbframes=media(z,doc['toolbar'])
    static=Image.new('RGBA',(W,H));labels=Image.new('RGBA',(W,H));keytheme=doc['keys']
    for id,rect in RECTS.items():
        k=resolved(keytheme,id);s=k['surfaceStyle'];b=k['borderStyle']
        canvas=group_canvas(keytheme,id,'surface');bc=group_canvas(keytheme,id,'border')
        if bc is None and k.get('borderDistribution')=='SHARED':bc=union(RECTS)
        face(static,rect,g=k['surfaceGradient'] if s=='GRADIENT' else None,solid=k['surfaceColor'] if s=='SOLID' else None,
            border=k['borderGradient'] if b=='GRADIENT' else None,borderSolid=k['borderColor'] if b=='SOLID' else None,
            canvas=canvas,borderCanvas=bc)
        d=ImageDraw.Draw(labels);x,y,w,h=rect;glyph=rgba(k['glyphColor']) if k.get('glyphColor') else (237,244,255,255)
        d.text((x+w/2,y+h/2-1),LABELS[id],font=ImageFont.truetype(FONT,24 if len(LABELS[id])==1 else 17),fill=glyph,anchor='mm')
        for px,py,hint in HINTS.get(id,[]):
            hintcolor=tuple(glyph[:3])+(round(glyph[3]*.78),)
            d.text((x+px*w,y+py*h),hint,font=ImageFont.truetype(FONT,10),fill=hintcolor,anchor='mm')
    static=Image.alpha_composite(static,labels)
    # Suggestion styling is rendered separately from key styling.
    loz=doc['suggestionLozenges'];suggestions=Image.new('RGBA',(W,H))
    for x,label in [(10,'hello'),(160,'help'),(310,'helicopter')]:
        rect=(x,TOP+11,138,40)
        face(suggestions,rect,g=loz['surfaceGradient'] if loz['surfaceStyle']=='GRADIENT' else None,
            solid=loz['surfaceColor'] if loz['surfaceStyle']=='SOLID' else None,
            border=loz['borderGradient'] if loz['borderStyle']=='GRADIENT' else None,
            borderSolid=loz['borderColor'] if loz['borderStyle']=='SOLID' else None,width=loz['borderWidth']*1.4,radius=11)
        ImageDraw.Draw(suggestions).text((x+69,TOP+31),label,font=ImageFont.truetype(FONT,13),fill='#EAF2FF',anchor='mm')
    d=ImageDraw.Draw(suggestions)
    for x,label in [(485,'f'),(550,'☺'),(610,'◆')]:d.text((x,TOP+31),label,font=ImageFont.truetype(FONT,20),fill='#EAF2FF',anchor='mm')
    d.line((0,TOP+BAR-1,W,TOP+BAR-1),fill=rgba(doc['toolbarBorderColor']),width=max(1,round(doc['toolbarBorderWidth'])))
    lossless=folder/'.preview-lossless.mkv'
    proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','12.5','-i','-','-an','-c:v','ffv1','-pix_fmt','bgr0','-threads','2',str(lossless)],stdin=subprocess.PIPE)
    for f in range(108):
        im=Image.new('RGBA',(W,H),'#0B0D17')
        im.alpha_composite(backdrop(doc['backdrop'],bgframes,f*80,(0,TOP+BAR,W,640)),(0,TOP+BAR))
        im.alpha_composite(backdrop(doc['toolbar'],tbframes,f*80,(0,TOP,W,BAR)),(0,TOP))
        im=Image.alpha_composite(im,static);im=Image.alpha_composite(im,suggestions)
        text='';active=None
        for start,key,char in EVENTS:
            if f>=start:text=text[:-1] if char is None else text+char
            if start<=f<start+4:active=key
        if active:
            x,y,w,h=RECTS[active];pulse=Image.new('RGBA',(W,H));dr=ImageDraw.Draw(pulse)
            dr.rounded_rectangle((x,y,x+w-1,y+h-1),radius=12,fill=(171,213,255,42),outline=(244,235,198,210),width=3)
            im=Image.alpha_composite(im,pulse)
        d=ImageDraw.Draw(im);d.rectangle((0,0,W,TOP-1),fill='#131726')
        d.text((15,TOP/2),text+'│',font=ImageFont.truetype(FONT,18),fill='#EAF2FF',anchor='lm')
        d.text((W-12,TOP/2),'typing demo',font=ImageFont.truetype(FONT,12),fill='#8394B3',anchor='rm')
        rgb=im.convert('RGB')
        if f==46:
            rgb.save(folder/'preview.png');rgb.resize((320,372),Image.Resampling.LANCZOS).save(folder/'thumbnail.png',optimize=True)
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close();assert proc.wait()==0
    vf=('fps=6.25,scale=288:334:flags=lanczos,split[a][b];[a]palettegen=stats_mode=full:max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4'
        if bgframes else 'scale=384:446:flags=lanczos,split[a][b];[a]palettegen=stats_mode=full:max_colors=256[p];[b][p]paletteuse=dither=bayer:bayer_scale=3')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(lossless),'-filter_complex',vf,'-loop','0','-threads','2',str(folder/'preview.gif')],check=True)
    lossless.unlink()
    gif=folder/'preview.gif';entry['preview'].update(animationBytes=gif.stat().st_size,animationSha256=hashlib.sha256(gif.read_bytes()).hexdigest())
    (folder/'entry.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')
    print(entry['name'],'preview',gif.stat().st_size,'bytes',flush=True)

if __name__=='__main__':
    c=json.loads((ROOT/'catalog.json').read_text())
    for e in c['entries']:render(e)
    (ROOT/'catalog.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    board=Image.new('RGB',(1320,930),'#0B0D20');d=ImageDraw.Draw(board)
    d.text((30,25),'KEYWI THEMES / STARTER CATALOG',font=ImageFont.truetype(FONT,30),fill='#EAF2FF')
    d.text((30,73),'ME-Like · MessagEase labels · rendered keyboard demos',font=ImageFont.truetype(FONT,18),fill='#A6B9D4')
    for i,e in enumerate(c['entries']):
        x=25+i*325;im=Image.open(ROOT/'themes'/e['id']/'preview.png').resize((300,349))
        board.paste(im,(x,140));d.text((x,515),e['name'],font=ImageFont.truetype(FONT,23),fill='#EAF2FF')
        d.text((x,557),f"{e['features']['keyGroupCount']} groups · GIF preview",font=ImageFont.truetype(FONT,16),fill='#AAC4DD')
        d.text((x,590),f"ZIP {e['package']['bytes']/1024**2:.2f} MiB",font=ImageFont.truetype(FONT,16),fill='#AAC4DD')
    lines=['Browse existing local themes as before. Explore opens the online catalog.',
           'Download adds a named local entry. Apply is a separate, explicit action.',
           'Previews are separate from theme ZIPs; the full wallpaper is downloaded only on request.',
           'OilSlyck preserves its MainTools group, shared gradients, glyph color, and original GIF.',
           'Preview geometry and synthetic typing illustrate themes; these are not emulator captures.']
    for i,line in enumerate(lines):d.text((30,685+i*40),line,font=ImageFont.truetype(FONT,17),fill='#9FB5CF')
    board.save(ROOT/'catalog-preview.jpg',quality=93)
