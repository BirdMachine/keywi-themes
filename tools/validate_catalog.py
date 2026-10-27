"""Validate catalog packages, preview metadata and preserved OilSlyck settings.

Standard library only; run from any working directory.
"""
from pathlib import Path
import json,hashlib,zipfile,re,struct

ROOT=Path(__file__).resolve().parents[1]
SAFE=re.compile(r'[a-z0-9][a-z0-9-]*')

def local(url):
    assert isinstance(url,str) and not url.startswith('/') and ':' not in url and '..' not in url.split('/')
    p=(ROOT/url).resolve();assert p.is_relative_to(ROOT) and p.is_file(),url
    return p

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def color(c):assert isinstance(c,str) and c.isdecimal() and 0<=int(c)<2**64
def gradient(g):
    assert isinstance(g['angle'],(float,int)) and g['stops']
    ps=[s['position'] for s in g['stops']];assert ps==sorted(ps) and all(0<=p<=1 for p in ps)
    for s in g['stops']:color(s['color'])

def validate(entry):
    assert SAFE.fullmatch(entry['id'])
    assert entry['revision']>=1 and entry['compatibility']['themeSchemaVersion']==3
    package=local(entry['package']['url'])
    assert package.stat().st_size==entry['package']['bytes']
    assert digest(package)==entry['package']['sha256']
    with zipfile.ZipFile(package) as z:
        names=z.namelist();assert len(names)==len(set(names)) and len(names)<=64
        assert z.testzip() is None
        assert sum(i.file_size for i in z.infolist())<=128*1024**2
        for i in z.infolist():
            assert i.file_size<=64*1024**2
            assert i.filename=='theme.json' or re.fullmatch(r'assets/[A-Za-z0-9_.-]+',i.filename)
        doc=json.loads(z.read('theme.json'));assert doc['schemaVersion']==3
        assert doc['id']==entry['themeDocumentId'] and doc['id']!='custom'
        assert doc['name']==entry['name']
        assert len(z.read('theme.json'))<1024**2
        refs=[]
        for name in ['backdrop','toolbar']:
            s=doc[name];assert s['mode'] in ['COLORFUL','IMAGE','GIF','NONE']
            assert 0<=s['opacity']<=1;gradient(s)
            if s.get('mediaUri'):refs.append(s['mediaUri'])
        if doc.get('font'):refs.append(doc['font']['asset'])
        assert set(names)=={'theme.json',*refs},'Only referenced media belongs in theme ZIPs'
        for ref in refs:assert ref in names and ref.startswith('assets/')
        k=doc['keys'];assert k['surfaceStyle'] in ['SOLID','GRADIENT','NONE']
        assert k['borderStyle'] in ['SOLID','GRADIENT','NONE','SHADOW']
        for g in ['surfaceGradient','borderGradient']:gradient(k[g])
        for key in ['surfaceColor','borderColor','shadowColor']:color(k[key])
        groups=k.get('keyGroups',[])
        assert entry['features']['keyGroupCount']==len(groups)
        for g in groups:
            assert g['keys'] and len(g['keys'])==len(set(g['keys']))
            for id in g['keys']:assert re.fullmatch(r'\d+:\d+',id)
            for key,value in g['design'].items():gradient(value) if key.endswith('Gradient') else color(value)
        if entry['id']=='oilslyck':
            original=json.loads((ROOT/'provenance/oilslyck-original-theme.json').read_text())
            assert doc['keys']==original['keys']
            assert doc['suggestionLozenges']==original['suggestionLozenges']
            asset=z.read(doc['backdrop']['mediaUri']);assert asset.startswith((b'GIF87a',b'GIF89a'))
            assert hashlib.sha256(asset).hexdigest()==Path(doc['backdrop']['mediaUri']).stem
            assert groups[0]['id']=='MainTools' and groups[0]['sharedGradientCanvas'] is True
            assert 'glyphColor' in groups[0]['design']
    gif=local(entry['preview']['animation']);raw=gif.read_bytes()
    assert raw[:6] in [b'GIF89a',b'GIF87a']
    assert b'NETSCAPE2.0\x03\x01\x00\x00\x00' in raw,'GIF must repeat infinitely'
    assert len(raw)==entry['preview']['animationBytes'] and digest(gif)==entry['preview']['animationSha256']
    assert struct.unpack('<HH',raw[6:10])[0]>0
    assert local(entry['preview']['thumbnail']).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert entry['preview']['type']=='rendered-demo'
    assert json.loads((ROOT/'themes'/entry['id']/'entry.json').read_text())==entry
    return {'id':entry['id'],'packageBytes':package.stat().st_size,'previewBytes':len(raw),'keyGroups':len(groups),'valid':True,'deviceTested':False}

if __name__=='__main__':
    c=json.loads((ROOT/'catalog.json').read_text());assert c['catalogVersion']==1
    assert len({e['id'] for e in c['entries']})==len(c['entries'])
    report=[validate(e) for e in c['entries']]
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
