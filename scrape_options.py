"""KNULLI/EmulationStation screen labels vs capabilities of Windows Skyscraper 3.6.12.
The source menu is from batocera-emulationstation GuiScraperStart.cpp; no claim
that all modern KNULLI scraper options work with our old CLI engine.
"""
import xml.etree.ElementTree as ET

IMAGE_OPTIONS=[('스크린샷','ss',True),('타이틀 화면','sstitle',False),('MIX V1','mixrbv1',True),('MIX V2','mixrbv2',True),
               ('박스 2D','box-2D',True),('박스 3D','box-3D',False),('팬아트','fanart',False),('없음','',True)]
BOX_OPTIONS=[('없음','',True),('박스 2D','box-2D',True),('박스 3D','box-3D',False)]
LOGO_OPTIONS=[('없음','',True),('HD 휠','wheel-hd',False),('휠','wheel',True),('마키','marquee',False)]
REGION_OPTIONS=[('자동',''),('유럽','eu'),('미국','us'),('일본','jp'),('월드','wor')]
KNULLI_FLAGS=[
    ('overwrite_names','이름 덮어쓰기',False),
    ('overwrite_descriptions','설명 덮어쓰기',True),
    ('overwrite_medias','미디어 덮어쓰기',True),
    ('short_name','짧은 이름',False),
    ('rating','커뮤니티 평점',True),
    ('video','동영상',True),
    ('fanart','팬아트',False),
    ('bezel','베젤 (16:9)',False),
    ('boxback','박스 뒷면',False),
    ('map','맵',False),
    ('manual','게임 매뉴얼',False),
    ('padtokey','패드→키 설정',False),
]
EXTRA=[('desc','게임 설명'),('genre','장르'),('releasedate','출시일'),
       ('developer','개발사'),('publisher','배급사'),('players','지원 인원')]
DEFAULT={
    'image_source':'mixrbv1','box_source':'box-2D','logo_source':'wheel',
    'preferred_region':'','overwrite_names':False,'overwrite_descriptions':True,
    'overwrite_medias':True,'short_name':False,'rating':True,'video':False,
    'fanart':False,'bezel':False,'boxback':False,'map':False,'manual':False,'padtokey':False,
    'desc':True,'genre':True,'releasedate':True,'developer':True,'publisher':True,'players':True,
}

def options(config):
    values=dict(DEFAULT); values.update({k:v for k,v in config.get('knulli_scraper',{}).items() if k in DEFAULT})
    # Older settings migration. If explicit new scraper settings exist don't use old.
    if not config.get('knulli_scraper') and 'scrape_fields' in config:
        old=config['scrape_fields']
        for key in ['video','rating','desc','genre','releasedate','developer','publisher','players']:
            values[key]=key in old
        if 'image' not in old:values['image_source']=''
        if 'thumbnail' not in old:values['box_source']=''
        if 'marquee' not in old:values['logo_source']=''
    return values

def selection(config):
    s=options(config)
    wanted=[]
    if s['image_source']:wanted.append('image')
    if s['box_source']:wanted.append('thumbnail')
    if s['logo_source']:wanted.append('marquee')
    if s['video']:wanted.append('video')
    for key in ['desc','rating','genre','releasedate','developer','publisher','players']:
        if s[key]:wanted.append(key)
    return wanted

def recipe(config):
    """Skyscraper 3.6.x XML recipe; only modes supported by old resource types."""
    mode=options(config)['image_source']
    root=ET.Element('artwork')
    if mode=='box-2D':
        shot=ET.SubElement(root,'output',{'type':'screenshot','width':'640','height':'480'})
        ET.SubElement(shot,'layer',{'resource':'cover','width':'560','height':'440','align':'center','valign':'middle'})
    elif mode=='ss':
        shot=ET.SubElement(root,'output',{'type':'screenshot','width':'640','height':'480'})
        ET.SubElement(shot,'layer',{'resource':'screenshot','width':'640','height':'480','align':'center','valign':'middle'})
    else:
        shot=ET.SubElement(root,'output',{'type':'screenshot','width':'640','height':'480'})
        ET.SubElement(shot,'layer',{'resource':'screenshot','width':'640','height':'480','align':'center','valign':'middle'})
        # Different cover placement for MIX V1/V2.
        if mode=='mixrbv2':
            ET.SubElement(shot,'layer',{'resource':'cover','height':'250','x':'-8','y':'0','align':'right','valign':'middle'})
        else:
            ET.SubElement(shot,'layer',{'resource':'cover','height':'220','x':'10','y':'-10','valign':'bottom'})
    ET.SubElement(root,'output',{'type':'cover','resource':'cover'})
    ET.SubElement(root,'output',{'type':'marquee','resource':'wheel'})
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)
