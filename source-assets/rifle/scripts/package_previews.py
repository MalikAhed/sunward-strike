from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
r=Path(__file__).resolve().parent.parent
f='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
font=ImageFont.truetype(f,24);small=ImageFont.truetype(f,17);title=ImageFont.truetype(f,35)
W,H=1920,1290;img=Image.new('RGB',(W,H),'#e7e9eb');d=ImageDraw.Draw(img)
d.text((50,32),'COMPACT CARBINE',font=title,fill='#242a2f')
d.text((50,80),'Exterior game asset | Blender render review',font=small,fill='#59616b')
items=[('hero','01  THREE-QUARTER'),('left_final','02  SOURCE-FACING LEFT'),('right_inferred','03  OPPOSITE SIDE / INFERRED'),('top','04  TOP / INFERRED')]
for i,(name,label) in enumerate(items):
 x=40+(i%2)*940;y=125+(i//2)*545
 panel=Image.open(r/'renders'/f'{name}.png').convert('RGB');panel.thumbnail((920,460))
 img.paste(panel,(x+(920-panel.width)//2,y));d.text((x+12,y+475),label,font=font,fill='#303841')
d.text((50,1230),'Modeled from a single supplied side image. Unseen surfaces are artistic interpretation; not engineering specifications.',font=small,fill='#59616b')
img.save(r/'exports'/'render_sheet.png')
