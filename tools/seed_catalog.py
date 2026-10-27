"""Prepare the starter catalog. Requires Pillow, NumPy and ffmpeg for previews.

Usage: python tools/seed_catalog.py /path/to/oilSlyck.zip
The source upload is read only. Packages contain theme.json and referenced assets;
catalog previews are separate so browsing never downloads full theme packages.
"""
from pathlib import Path
import json, zipfile, hashlib, copy, sys, re

ROOT=Path(__file__).resolve().parents[1]
SOURCE_COMMIT='232070cbde42c9e7c893874bc50e2145140609b9'

def color(argb):return str(int(argb,16)<<32)
def gradient(colors,angle=135,positions=None):
    positions=positions or [i/(len(colors)-1) for i in range(len(colors))]
    return {'angle':angle,'stops':[{'position':p,'color':color(c)} for p,c in zip(positions,colors)]}
RAINBOW=gradient(['FFFF4FA3','FFFFD84D','FF58F5FF','FF8C5CFF'])
SINEBOW=gradient(['FF00BFBF','FF11EE80','FF40FF40','FF7FEE11','FFBFBF00','FFEE8011','FFFF4040','FFEE117F','FFBF00BF','FF8011EE','FF4040FF','FF117FEE','FF00BFBF'],0)
GREY=gradient(['FF090A0F','FF242631','FF555866','FF151720'],22,[0,.34,.67,1])
GOLD=gradient(['FF6B3F00','FFB97700','FFFFD86B','FFFFF4C2','FFFFC94A','FFD99816','FF704100'],135,[0,.18,.42,.5,.58,.78,1])

def backdrop(g,preset='CUSTOM',opacity=1):return dict(copy.deepcopy(g),preset=preset,mode='COLORFUL',opacity=opacity,mediaUri=None)

def base(name,id,bg,preset='CUSTOM'):
    return {'schemaVersion':3,'id':'catalog-'+id,'name':name,
        'backdrop':backdrop(bg,preset),'toolbar':backdrop(bg,preset),
        'toolbarBorderWidth':1,'toolbarBorderColor':color('FFFFC247'),'toolbarKeyboardGap':0,
        'keys':{'surfaceStyle':'GRADIENT','surfaceGradient':GREY,'surfaceColor':color('FF242631'),
            'borderStyle':'GRADIENT','borderGradient':GOLD,'borderColor':color('FFFFD86B'),
            'shadowColor':color('FF000000'),'shadowAlpha':.55,'shadowElevation':4,
            'borderDistribution':'SAME','borderPhaseStepDegrees':30,'borderRandomSeed':0,
            'keyOverrides':{},'keyGroups':[]},
        'suggestionLozenges':{'surfaceStyle':'SOLID','surfaceGradient':GREY,'surfaceColor':color('B8343540'),
            'borderStyle':'SOLID','borderGradient':GOLD,'borderColor':color('70FFFFFF'),'borderWidth':1,
            'currentWordBackgroundColor':color('FF031005'),'currentWordHighlightColor':None},'font':None}

def defaults():
    rainbow=base('Birdie Rainbow','birdie-rainbow',RAINBOW,'BIRDIE_RAINBOW')
    sinebow=base('Sinebow','sinebow',SINEBOW,'SINEBOW')
    night=gradient(['FF090818','FF19113A','FF052B35'],132,[0,.46,1])
    keys=gradient(['FF24104A','FF8D1E78','FF087B82'],118)
    neon=gradient(['FFFF4FCB','FFFFD85A','FF45F6E8'],28,[0,.48,1])
    aviary=base('Neon Aviary','neon-aviary',night)
    aviary.update(toolbar=backdrop(gradient(['E61A0C35','E6053540'],105),opacity=.96),toolbarBorderWidth=1.4,toolbarBorderColor=color('FFFF67D4'),toolbarKeyboardGap=3)
    aviary['keys'].update(surfaceGradient=keys,surfaceColor=color('FF24104A'),borderGradient=neon,borderColor=color('FFFFD85A'),shadowAlpha=.62,shadowElevation=5)
    aviary['suggestionLozenges'].update(surfaceStyle='GRADIENT',surfaceGradient=gradient(['CC4A155E','CC07535C'],90),surfaceColor=color('CC28113F'),borderStyle='GRADIENT',borderGradient=neon,borderColor=color('FFFF67D4'),borderWidth=1.2)
    return [('birdie-rainbow',rainbow,{},'Original pink, gold, cyan and violet backdrop with grey keys and gold rims.',['default','rainbow','gradient']),
        ('sinebow',sinebow,{},'The Sinebow backdrop preset packaged as a complete named theme.',['default','rainbow','gradient']),
        ('neon-aviary',aviary,{},'The built-in Neon Aviary theme: midnight purple, magenta and teal.',['default','neon','gradient'])]

def oil(path):
    with zipfile.ZipFile(path) as z:
        doc=json.loads(z.read('theme.json'));original=copy.deepcopy(doc)
        refs=[s.get('mediaUri') for s in [doc['backdrop'],doc['toolbar']] if s.get('mediaUri')]
        if doc.get('font'):refs.append(doc['font']['asset'])
        assets={r:z.read(r) for r in set(refs)}
    doc.update(id='catalog-oilslyck',name='OilSlyck')
    renamed={}
    for ref,data in assets.items():
        new=ref[:-4]+'.gif' if ref.endswith('.bin') and data.startswith((b'GIF87a',b'GIF89a')) else ref
        renamed[new]=data
        for s in [doc['backdrop'],doc['toolbar']]:
            if s.get('mediaUri')==ref:s['mediaUri']=new
        if doc.get('font') and doc['font']['asset']==ref:doc['font']['asset']=new
    assert doc['keys']==original['keys']
    assert doc['suggestionLozenges']==original['suggestionLozenges']
    (ROOT/'provenance/oilslyck-original-theme.json').write_text(json.dumps(original,indent=2)+'\n')
    (ROOT/'provenance/oilslyck-source.json').write_text(json.dumps({'upload':'oilSlyck.zip','sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'originalId':original['id'],'originalName':original['name'],'changes':['catalog identity/display name','GIF filename extension; media bytes unchanged'],'keyGroupCount':len(doc['keys'].get('keyGroups',[]))},indent=2)+'\n')
    return ('oilslyck',doc,renamed,'Birdie’s OilSlyck export, including MainTools shared gradients and group glyph color.',['oilslick','animated','gold','key-groups'])

def write_package(id,doc,assets):
    folder=ROOT/'themes'/id;folder.mkdir(parents=True,exist_ok=True)
    (folder/'theme.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    package=folder/f'{id}-1.0.0.keywi-theme.zip';tmp=package.with_suffix('.building')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in [('theme.json',json.dumps(doc,ensure_ascii=False,indent=2).encode()),*sorted(assets.items())]:
            info=zipfile.ZipInfo(name,(2026,10,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    with zipfile.ZipFile(tmp) as z:assert z.testzip() is None
    tmp.replace(package)
    return package

def main(path):
    entries=[]
    for id,doc,assets,description,tags in defaults()+[oil(path)]:
        package=write_package(id,doc,assets)
        groups=doc['keys'].get('keyGroups',[])
        entry={'id':id,'name':doc['name'],'version':'1.0.0','revision':1,
            'author':'Birdie' if id=='oilslyck' else 'Keywi contributors','license':None,
            'description':description,'tags':tags,'themeDocumentId':doc['id'],
            'compatibility':{'themeSchemaVersion':3,'requiredFeatures':['key-groups','group-gradient-canvas','group-glyph-color'] if groups else []},
            'package':{'url':package.relative_to(ROOT).as_posix(),'bytes':package.stat().st_size,'sha256':hashlib.sha256(package.read_bytes()).hexdigest()},
            'preview':{'thumbnail':f'themes/{id}/thumbnail.png','animation':f'themes/{id}/preview.gif','type':'rendered-demo','layout':'ENMessagEase','facet':'ME_LIKE','durationMs':8640,'geometry':{'keyBorderWidthDp':1.5,'keyRadiusDp':8},'animationBytes':None,'animationSha256':None},
            'features':{'animatedBackground':doc['backdrop']['mode']=='GIF','keyGroupCount':len(groups),'perKeyOverrideCount':len(doc['keys'].get('keyOverrides',{}))},
            'provenance':{'source':'user-export' if id=='oilslyck' else 'app-default-definition','appCommit':SOURCE_COMMIT}}
        entries.append(entry)
    catalog={'catalogVersion':1,'id':'keywi-official','name':'Keywi Themes','description':'Optional premade themes. Downloading adds a named entry; only Apply changes the keyboard.',
        'repository':'https://github.com/BirdMachine/keywi-themes','entries':entries}
    (ROOT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    print('Prepared',len(entries),'theme packages')

if __name__=='__main__':main(sys.argv[1])
