"""Recoverable local house replacement, houses-r1.
Requires Blender 4.3+. No automatic writes or world transforms on import.
Authority: official classic Nuketown BO6 -004 street/minimap for visible shell;
BO1 thesis p128/p130 corroborates two upper rooms and rear pergola/stair handedness; exact dimensions remain gameplay calibration.
Frame: Z up, front=-Y, rear=+Y, +X image-right from camera at(0,-d,z).
Manager owns integration and supplies root matrix once; never scale world twice.
"""
import bpy, math, json
from pathlib import Path
from mathutils import Vector, Matrix
VERSION='houses-r7'
OUT=Path(__file__).resolve().parent
CONFIG=OUT.parent / 'layout/site_frames.json'
DEFAULT_COLORS={'V2_Warm_Plaster':(.70,.61,.42),'V2_Sage_Plaster':(.24,.50,.39),'V2_Saffron_Plaster':(.83,.56,.17),'V2_Weathered_Roof':(.08,.14,.16),'V2_Aged_Timber':(.31,.21,.13),'SW2_Arch_WeatheredTimber':(.16,.12,.08),'SW2_Arch_TimberEdge':(.35,.25,.14),'SW2_Arch_Limestone_01':(.52,.49,.37),'SW2_Arch_Limestone_02':(.42,.42,.33),'SW2_Arch_MasonryJoints':(.29,.29,.24),'ivory':(.90,.85,.69),'chalk':(.74,.72,.61),'floor':(.36,.27,.16),'wood_light':(.61,.42,.22),'roof':(.07,.14,.19),'roof_light':(.10,.23,.29),'mint_dark':(.055,.26,.32),'steel':(.16,.21,.23),'coral':(.65,.24,.16),'glass':(.07,.18,.21),'concrete':(.50,.51,.45),'interior':(.64,.64,.49),'ochre_light':(.92,.65,.25)}

def material(name):
    m=bpy.data.materials.get(name)
    if m is None:
        m=bpy.data.materials.new(name);m.diffuse_color=(*DEFAULT_COLORS.get(name,(.5,.5,.5)),1);m.use_nodes=True
        p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Roughness'].default_value=.85
    return m

def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c

def remove_old_house_visuals(house_ids=('A_Mint','B_Saffron')):
    """Visual cleanup, including untagged generated split plaster.
    Exact legacy collections/prefixes only; new H3 roots and collections protected.
    Old joined collider is deliberately left for manager's collision rebuild.
    """
    legacy_names={str(n)+'_'+h+'_'+part for h in house_ids for n,part in [(10,'Architecture'),(11,'Garage'),(12,'RearDeck'),(13,'Interior')]}
    legacy_prefixes=tuple(h+'_' for h in house_ids)
    removed=[]
    for o in list(bpy.data.objects):
        protected=o.name.startswith(('H3_','COL_V3_H3_','HOUSE_ROOT_','COL_HOUSE_ROOT_')) or any('_H3_' in c.name for c in o.users_collection)
        if protected:continue
        own=o.get('building') in house_ids or o.name.startswith(legacy_prefixes) or any(c.name in legacy_names for c in o.users_collection)
        decor=any(o.name.startswith('SW2_Arch_'+('Mint' if h=='A_Mint' else 'Saffron')+'_') for h in house_ids)
        ivy=any(o.name.startswith(p) for h in house_ids for k in ['FrontCorner','SideCorner'] for p in ['V2_Ivy_'+('A' if h=='A_Mint' else 'B')+'_'+k,'V2_IvyStems_'+('A' if h=='A_Mint' else 'B')+'_'+k])
        garageivy=any(o.name.startswith(p) for h in house_ids for p in ['V2_Ivy_Garage_'+('A' if h=='A_Mint' else 'B')+'_','V2_IvyStems_Garage_'+('A' if h=='A_Mint' else 'B')+'_'])
        if own or decor or ivy or garageivy:removed.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
    survivors=[o.name for o in bpy.data.objects if o.name.startswith(legacy_prefixes) or any(c.name in legacy_names for c in o.users_collection)]
    if survivors:raise AssertionError('Legacy house visuals survived cleanup: '+', '.join(survivors))
    for name in legacy_names:
        c=bpy.data.collections.get(name)
        if c is not None and len(c.objects):raise AssertionError('Legacy collection not empty: '+name)
    return removed

class HouseBuilder:
    def __init__(self,frame,root_matrix=None):
        self.frame=frame;self.id=frame['house_id'];self.tag='H3_'+self.id;self.green=self.id=='A_Mint';self.count={};self.parts=[];self.colliders=[];self.portals={};self.routes={}
        self.col=collection('10_'+self.id+'_H3_Architecture');self.cc=collection('91_'+self.id+'_H3_Collision')
        self.root=bpy.data.objects.new('HOUSE_ROOT_'+self.id,None);self.col.objects.link(self.root);self.root['house_id']=self.id;self.root['house_version']=VERSION;self.root['source_frame']='local';self.root['frame']='local front=-Y, rear=+Y, Z up; +X camera-right from street'
        self.root['scale_assumption']='Gameplay calibration only; primary reference supplies ratios, not meters'
        if root_matrix is not None:self.root.matrix_world=root_matrix
        self.croot=bpy.data.objects.new('COL_'+'HOUSE_ROOT_'+self.id,None);self.cc.objects.link(self.croot)
        if root_matrix is not None:self.croot.matrix_world=root_matrix
        self.croot['house_id']=self.id;self.croot['source_frame']='local';self.croot['collision']='static nonconvex triangle meshes; no convex hull'
        lo,hi=frame['components']['main_body']['local_bbox_m'];self.x0,self.y0=lo;self.x1,self.y1=hi;self.w=self.x1-self.x0;self.d=self.y1-self.y0;self.cx=(self.x0+self.x1)/2;self.cy=(self.y0+self.y1)/2
        self.gx0,self.gy0=frame['components']['garage']['local_bbox_m'][0];self.gx1,self.gy1=frame['components']['garage']['local_bbox_m'][1]
        self.f0=.18;self.f1=3.18;self.eave=6.20;self.paint='V2_Sage_Plaster' if self.green else 'V2_Saffron_Plaster'
    def name(self,label):
        n=self.count.get(label,0);self.count[label]=n+1;return self.tag+'_'+label+('_%03d'%n if n else '')
    def uv(self,o):
        uv=o.data.uv_layers.new(name='UVMap')
        for p in o.data.polygons:
            axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=([1,2],[0,2],[0,1])[axis]
            for li in p.loop_indices:
                v=o.data.vertices[o.data.loops[li].vertex_index].co+o.location;uv.data[li].uv=(v[axes[0]]/2.6,v[axes[1]]/2.6)
    def mesh(self,label,vs,fs,mat,collide=False,bevel=.015):
        name=self.name(label);me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);self.col.objects.link(o);me.materials.append(material(mat));o.parent=self.root;o['house_id']=self.id;o['house_version']=VERSION;o['part_id']=label;self.parts.append(o);self.uv(o)
        if bevel:
            mod=o.modifiers.new('Small painterly edge','BEVEL');mod.width=bevel;mod.segments=1
            mod=o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True
        if collide:
            cp=bpy.data.objects.new('COL_V3_'+name,me.copy());self.cc.objects.link(cp);collection('V3_COLLISION').objects.link(cp);cp.parent=self.croot;cp['house_id']=self.id;cp['collision']='static';cp['collision_source_id']=name;cp.data.materials.clear();self.colliders.append(cp)
        return o
    def box(self,label,xyz,dims,mat,collide=False,bevel=.015):
        x,y,z=xyz;w,d,h=(a/2 for a in dims)
        return self.mesh(label,[(x-w,y-d,z-h),(x+w,y-d,z-h),(x+w,y+d,z-h),(x-w,y+d,z-h),(x-w,y-d,z+h),(x+w,y-d,z+h),(x+w,y+d,z+h),(x-w,y+d,z+h)],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,collide,bevel)
    def beam(self,label,a,b,width,mat,depth=None):
        a,b=Vector(a),Vector(b);o=self.box(label,(0,0,0),(width,depth or width,(b-a).length),mat,False,.008);o.location=(a+b)/2;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o
    def wall(self,label,axis,fixed,a,b,z0,z1,holes,mat,thick=.20):
        xs=sorted(set([a,b]+[q for hole in holes for q in hole[:2] if a<q<b]));zs=sorted(set([z0,z1]+[q for hole in holes for q in hole[2:] if z0<q<z1]))
        for l,r in zip(xs,xs[1:]):
            for lo,hi in zip(zs,zs[1:]):
                mid=(l+r)/2;z=(lo+hi)/2
                if any(h[0]<mid<h[1] and h[2]<z<h[3] for h in holes):continue
                xyz=((l+r)/2,fixed,z) if axis=='X' else (fixed,(l+r)/2,z)
                dim=(r-l,thick,hi-lo) if axis=='X' else (thick,r-l,hi-lo)
                self.box(label,xyz,dim,mat,True,.009)
    def frame_x(self,label,x,y,z,w,h,shutters=False,mat='ivory',mullion=False):
        for xx in [x-w/2,x+w/2]:self.box(label+'_Jamb',(xx,y,z+h/2),(.10,.18,h+.10),mat)
        for zz in [z,z+h]:self.box(label+'_Lintel',(x,y,zz),(w+.16,.20,.10),mat)
        self.box(label+'_Sill',(x,y-.08,z-.025),(w+.25,.32,.11),mat)
        if mullion:self.box(label+'_Mullion',(x,y-.035,z+h/2),(.07,.08,h),mat)
        if shutters:
            sm='mint_dark' if self.green else 'wood_light'
            for xx in [x-w/2-.36,x+w/2+.36]:
                self.box(label+'_Shutter',(xx,y-.045,z+h/2),(.55,.14,h+.08),sm)
                for j in range(10):self.box(label+'_Louvre',(xx,y-.126,z+.10+j*(h-.18)/9),(.48,.06,.045),sm,False,.004)
    def roof_prism(self,label,x0,x1,y0,y1,heights,mat='V2_Weathered_Roof'):
        # one pitched slab, thickness .16. heights specify corners CCW
        zs=heights;v=[(x0,y0,zs[0]),(x1,y0,zs[1]),(x1,y1,zs[2]),(x0,y1,zs[3])];v+= [(x,y,z-.16) for x,y,z in v]
        return self.mesh(label,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],mat,True,.012)
    def shell(self):
        x0,x1,y0,y1=self.x0,self.x1,self.y0,self.y1;cx,cy=self.cx,self.cy
        self.box('Foundation',(cx,cy,.08),(self.w+.28,self.d+.28,.16),'chalk',True)
        self.box('GroundFloor',(cx,cy,self.f0-.07),(self.w-.20,self.d-.20,.14),'floor',True)
        lowerfront=y0+(.38 if not self.green else 0);lowerx0=x0+(.22 if not self.green else 0);lowerx1=x1-(.22 if not self.green else 0)
        doorx=cx-1.12;doorw=1.16;windowx=cx+2.1;winw=1.95;door=(doorx-doorw/2,doorx+doorw/2,self.f0,self.f0+2.15);win=(windowx-winw/2,windowx+winw/2,1.02,2.57)
        self.wall('FrontLower','X',lowerfront,lowerx0,lowerx1,self.f0,self.f1,[door,win],'V2_Warm_Plaster')
        self.portals['front_door']={'center':[doorx,lowerfront,self.f0],'clear_width':doorw,'clear_height':2.15}
        self.frame_x('FrontDoor',doorx,lowerfront-.09,self.f0,doorw,2.15,False)
        self.frame_x('FrontWindow',windowx,lowerfront-.11,1.02,winw,1.55,True,mullion=True)
        # paired upper apertures are essential classic silhouette, not a wide slot
        upperholes=[]
        for label,wx in [('UpperLeft',cx-(2.60 if self.green else 2.05)),('UpperRight',cx+(2.60 if self.green else 2.05))]:
            ww=2.40 if self.green else (1.66 if label=='UpperLeft' else 2.16);upperholes.append((wx-ww/2,wx+ww/2,4.02,5.73));self.frame_x(label,wx,y0-.13,4.02,ww,1.71,True,mat='ivory' if self.green else 'wood_light',mullion=(not self.green and label=='UpperLeft'))
        self.wall('FrontUpper','X',y0,x0,x1,self.f1,self.eave,upperholes,self.paint)
        reardoorx=cx+.2;rearupperx=cx-.6;rearholes=[(reardoorx-.60,reardoorx+.60,self.f0,self.f0+2.15),(rearupperx-.60,rearupperx+.60,self.f1,self.f1+2.15)]
        self.wall('RearLower','X',y1,x0,x1,self.f0,self.f1,rearholes,'V2_Warm_Plaster');self.wall('RearUpper','X',y1,x0,x1,self.f1,self.eave,rearholes,self.paint)
        self.frame_x('RearGroundDoor',reardoorx,y1+.08,self.f0,1.2,2.15);self.frame_x('RearUpperDoor',rearupperx,y1+.08,self.f1,1.2,2.15)
        self.portals['rear_door']={'center':[reardoorx,y1,self.f0],'clear_width':1.2,'clear_height':2.15,'certainty':'rear doorway family verified by BO1 thesis capture; exact width/position estimated'}
        self.portals['rear_upper_door']={'center':[rearupperx,y1,self.f1],'clear_width':1.2,'clear_height':2.15,'certainty':'rear doorway family verified by BO1 thesis capture; exact width/position estimated'}
        connectory=max(self.gy0+.8,min(self.gy1-.8,self.cy+1.1));conn=(connectory-.65,connectory+.65,self.f0,self.f0+2.15)
        self.wall('GarageConnectorLower','Y',x0,y0,y1,self.f0,self.f1,[conn],'V2_Warm_Plaster');self.wall('WestUpper','Y',x0,y0,y1,self.f1,self.eave,[],self.paint)
        self.portals['garage_connector']={'center':[x0,connectory,self.f0],'clear_width':1.3,'clear_height':2.15}
        self.box('GarageConnectorThreshold',(x0,connectory,self.f0-.07),(.44,1.3,.14),'floor',True)
        for label,px,py,pz in [('FrontThreshold',doorx,lowerfront,self.f0),('RearThreshold',reardoorx,y1,self.f0),('RearUpperThreshold',rearupperx,y1,self.f1)]:self.box(label,(px,py,pz-.07),(1.3,.44,.14),'floor',True)
        self.wall('EastLower','Y',x1,y0,y1,self.f0,self.f1,[],'V2_Warm_Plaster');self.wall('EastUpper','Y',x1,y0,y1,self.f1,self.eave,[(cy-.6,cy+.6,4.18,5.64)],self.paint)
        for yy in [cy-.6,cy+.6]:self.box('SideWindowJamb',(x1+.10,yy,4.91),(.18,.1,1.56),'ivory')
        for zz in [4.18,5.64]:self.box('SideWindowLintel',(x1+.10,cy,zz),(.18,1.35,.10),'ivory')
        self.box('SideWindowMullion',(x1+.10,cy,4.91),(.08,.065,1.46),'ivory')
        for zz in [.72,self.f1,6.09]:
            for yy,holes in [(y0-.12,[door,win]+upperholes),(y1+.12,rearholes)]:
                spans=[(x0-.115,x1+.115)]
                for a,b,bot,top in holes:
                    if bot-.08<zz<top+.08:
                        spans=[q for l,r in spans for q in [(l,min(r,a-.08)),(max(l,b+.08),r)] if q[1]>q[0]]
                for l,r in spans:self.box('HorizontalTrim',((l+r)/2,yy,zz),(r-l,.13,.15),'ivory' if self.green else 'wood_light')
            for xx in [x0-.12,x1+.12]:
                spans=[(y0-.07,y1+.07)]
                if xx<x0 and conn[2]-.08<zz<conn[3]+.08:spans=[(y0-.07,conn[0]-.08),(conn[1]+.08,y1+.07)]
                for l,r in spans:self.box('SideTrim',(xx,(l+r)/2,zz),(.13,r-l,.15),'ivory' if self.green else 'wood_light')
        for xx in [x0-.10,x1+.10]:
            for yy in [y0-.10,y1+.10]:self.box('CornerTrim',(xx,yy,3.18),(.15,.15,6.15),'ivory' if self.green else 'wood_light')
        # Keep fine siding accents on solid side/rear panels, without portal-crossing slabs
        for j in range(10):
            zz=3.4+j*.265
            if self.green:self.box('SideSiding',(x0-.111,cy,zz),(.022,self.d-.18,.026),self.paint,False,0)
            else:
                for xx in [x0+.5+j*(self.w-1)/9]:self.box('YellowVerticalSiding',(xx,y0-.111,3.59),(.026,.022,.55),self.paint,False,0)
        # Internal stairs; 1.45m clear flight, two-floor free shaft and explicit ramps
        stairx=x1-1.10;sy0=y0+1.15;run=5.65;sy1=sy0+run;sw=1.45
        self.box('UpperFloorMain',((x0+stairx-sw/2-.13)/2,cy,self.f1-.07),(stairx-sw/2-.13-x0-.1,self.d-.2,.14),'floor',True)
        for a,b in [(y0,sy0-.05),(sy1+.05,y1)]:self.box('UpperFloorLanding',(stairx,(a+b)/2,self.f1-.07),(sw+.5,b-a,.14),'floor',True)
        n=18;rise=(self.f1-self.f0)/n
        for i in range(n):
            z=self.f0+(i+1)*rise;self.box('InteriorStair',(stairx,sy0+(i+.5)*run/n,(z+self.f0)/2),(sw,run/n+.008,z-self.f0),'wood_light',False,.006)
        self.ramp('InteriorRamp',[(stairx-sw/2,sy0,self.f0+rise),(stairx+sw/2,sy0,self.f0+rise),(stairx+sw/2,sy1,self.f1),(stairx-sw/2,sy1,self.f1)])
        self.routes['interior_stairs']={'bottom':[stairx,sy0-.25,self.f0],'top':[stairx,sy1+.55,self.f1],'ramp_start':[stairx,sy0,self.f0+rise],'ramp_end':[stairx,sy1,self.f1],'width':sw,'rise':self.f1-self.f0,'run':run,'uncertainty':'gameplay-calibrated location, not primary measured stair plan'}
        self.beam('InteriorHandrail',(stairx-sw/2,sy0,self.f0+.93),(stairx-sw/2,sy1,self.f1+.93),.065,'steel')
        # Small ground-floor divider with generous central passage, kept off stairs
        dy=cy+.6;da=x0+.25;db=stairx-sw/2-.20;passx=cx+.2
        self.wall('RoomDivider','X',dy,da,db,self.f0,2.93,[(passx-.80,passx+.80,self.f0,2.43)],'interior',.12)
        self.portals['room_passage']={'center':[passx,dy,self.f0],'clear_width':1.6,'clear_height':2.25,'certainty':'unverified room partition approximation'}
        self.wall('UpperRoomDivider','X',cy-.30,x0+.18,stairx-sw/2-.18,self.f1,6.08,[(cx-.40,cx+.90,self.f1,self.f1+2.15)],'interior',.12)
        self.portals['upper_room_passage']={'center':[cx+.25,cy-.30,self.f1],'clear_width':1.3,'clear_height':2.15,'certainty':'two-room connection verified in BO1 thesis plan; exact coordinates estimated'}
        self.routes['upper_rooms']={'front_room':[cx,(y0+cy-.30)/2,self.f1],'rear_room':[cx,(y1+cy-.30)/2,self.f1],'passage':self.portals['upper_room_passage']['center'],'balcony_door':self.portals['rear_upper_door']['center'],'topology_evidence':'BO1 thesis plan p128 and rear gameplay photographs p130; no primary meter dimensions'}
        self.box('Ceiling',(cx,cy,6.12),(self.w-.2,self.d-.2,.13),'interior',True)
        self.box('FrontPorch',(doorx,y0-.80,.09),(3.4,1.6,.18),'concrete',True)
        if self.green:
            self.box('GreenNarrowEntryEave',(doorx,y0-.27,2.67),(2.40,.55,.085),'roof')
        else:
            # Primary yellow frontage has open timber lattice, not a solid slab
            aw0=x0-.15;aw1=x1-.64;awy=y0-.85;awdep=1.75
            for xx in [aw0,aw1]:self.box('YellowFrontPergolaBeam',(xx,awy,2.72),(.16,awdep,.17),'wood_light')
            self.box('YellowFrontPergolaHeader',((aw0+aw1)/2,y0-1.70,2.72),(aw1-aw0+.18,.16,.17),'wood_light')
            for j in range(25):self.box('YellowFrontPergolaSlat',(aw0+(aw1-aw0)*j/24,awy,2.80),(.065,awdep,.085),'wood_light',False,.004)
            for j in range(6):self.box('YellowFrontPergolaCrossSlat',((aw0+aw1)/2,y0-.05-j*awdep/5,2.865),(aw1-aw0+.12,.065,.06),'wood_light',False,.004)
            self.box('YellowFrontPergolaPost',(aw1,y0-1.69,1.40),(.16,.16,2.70),'wood_light')
        # exposed lattice post, thin enough to preserve passage
        self.box('FrontTrellisPost',(doorx-1.12,y0-(.47 if self.green else 1.34),1.43),(.13,.13,2.70),'ivory')
        for xx in [doorx-1.10,doorx-.78]:self.box('FrontTrellisVertical',(xx,y0-(.49 if self.green else 1.36),1.55),(.043,.043,2.2),'ivory',False,.004)
        for zz in [.7,1.1,1.5,1.9,2.3]:self.box('FrontTrellisHorizontal',(doorx-.94,y0-(.49 if self.green else 1.36),zz),(.6,.043,.043),'ivory',False,.004)
        if self.green:
            ex0,ex1=x0-.45,x1+.45;ey0,ey1=y0-.45,y1+.45;peak=7.38
            self.roof_prism('GreenRoofLeft',ex0,cx,ey0,ey1,[6.25,peak,peak,6.25]);self.roof_prism('GreenRoofRight',cx,ex1,ey0,ey1,[peak,6.25,6.25,peak])
            for yy in [y0-.11,y1+.11]:self.mesh('GreenGable',[(x0,yy,self.eave),(x1,yy,self.eave),(cx,yy,peak-.12)],[(0,1,2)],self.paint,False,0)
            for yy in [ey0,ey1]:
                self.beam('GreenGableFascia',(ex0,yy,6.25),(cx,yy,peak),.14,'ivory');self.beam('GreenGableFascia',(cx,yy,peak),(ex1,yy,6.25),.14,'ivory')
            self.box('GreenChimney',(x0+1.15,cy+2.3,7.36),(1.00,1.13,1.85),'coral',True)
            self.box('GreenChimneyCap',(x0+1.15,cy+2.3,8.33),(1.21,1.34,.15),'roof')
        else:
            # Yellow low single-slope roof + upper overhang; distinctive stone chimney on -X
            ex0,ex1=x0-.65,x1+.65;ey0,ey1=y0-.65,y1+.40
            self.roof_prism('YellowShedRoof',ex0,ex1,ey0,ey1,[6.78,6.30,6.30,6.78])
            for yy in [ey0,ey1]:self.beam('YellowSlopedFascia',(ex0,yy,6.76),(ex1,yy,6.28),.18,'wood_light')
            for xx,zz in [(ex0,6.76),(ex1,6.28)]:self.beam('YellowLongFascia',(xx,ey0,zz),(xx,ey1,zz),.17,'wood_light')
            # shallow clerestory gap closed by triangular painted wall, not a second gable
            for yy in [y0-.10,y1+.10]:self.mesh('YellowUpperClerestory',[(x0,yy,6.15),(x1,yy,6.15),(x1,yy,6.29),(x0,yy,6.73)],[(0,1,2,3)],self.paint)
            chimneyx=x0+.23;chimneyy=y0+1.48;cw=1.38;cd=3.36
            self.box('YellowStoneChimney',(chimneyx,chimneyy,3.86),(cw,cd,7.72),'SW2_Arch_Limestone_01',True,.025)
            self.box('YellowChimneyCap',(chimneyx,chimneyy,7.78),(cw+.26,cd+.24,.19),'roof')
            for j in range(13):
                z=.37+j*.55
                self.box('ChimneyStoneCourse',(chimneyx-cw/2-.012,chimneyy,z),(.022,cd,.035),'SW2_Arch_MasonryJoints',False,0)
                self.box('ChimneyStoneFrontCourse',(chimneyx,chimneyy-cd/2-.012,z),(cw,.022,.035),'SW2_Arch_MasonryJoints',False,0)
                for k in range(4):self.box('ChimneyStoneJoint',(chimneyx-cw/2-.017,chimneyy-cd/2+.45+k*.78+(j%2)*.30,z+.26),(.02,.025,.49),'SW2_Arch_MasonryJoints',False,0)
            for yy in [chimneyy-cd/2,chimneyy+cd/2]:self.beam('ChimneyTopGuard',(chimneyx-cw/2,yy,8.23),(chimneyx+cw/2,yy,8.23),.085,'steel')
            for xx in [chimneyx-cw/2,chimneyx+cw/2]:
                self.beam('ChimneyTopGuard',(xx,chimneyy-cd/2,8.23),(xx,chimneyy+cd/2,8.23),.085,'steel')
                for yy in [chimneyy-cd/2,chimneyy,chimneyy+cd/2]:self.beam('ChimneyGuardUpright',(xx,yy,7.83),(xx,yy,8.23),.07,'steel')
    def ramp(self,label,points):
        # clockwise underside / CCW top: verified upwards support normal
        v=points+[(x,y,z-.13) for x,y,z in points]
        o=self.mesh(label,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],'wood_light',True,0);o.hide_render=True
        return o
    def garage(self):
        x0,x1,y0,y1=self.gx0,self.gx1,self.gy0,self.gy1;w=x1-x0;d=y1-y0;cx=(x0+x1)/2;cy=(y0+y1)/2
        self.box('GarageFloor',(cx,cy,.11),(w-.18,d-.18,.14),'concrete',True)
        h=2.97
        if self.green:
            center=(x0+x1)/2;outer=(x0+.32,center-.12,.18,2.63);inner=(center+.12,x1-.26,.18,2.63)
            self.wall('GarageFront','X',y0,x0,x1,.18,h,[inner],self.paint)
            # Closed exterior bay confirmed by primary street image, separate from open inner portal
            self.box('GarageOuterClosedDoor',((outer[0]+outer[1])/2,y0-.14,1.40),(outer[1]-outer[0],.12,2.44),'mint_dark',True)
            for j in range(4):self.box('GarageClosedDoorPanel',((outer[0]+outer[1])/2,y0-.211,.57+j*.51),(outer[1]-outer[0]-.14,.022,.045),'roof_light',False,0)
            self.frame_x('GarageInnerBay',(inner[0]+inner[1])/2,y0-.12,.18,inner[1]-inner[0],2.45)
            self.portals['garage_front']={'center':[(inner[0]+inner[1])/2,y0,.18],'clear_width':inner[1]-inner[0],'clear_height':2.45}
            # garage ridge runs X: street side shows sloping roof, outer -X elevation gable
            ey0,ey1=y0-.36,y1+.36;ridgey=cy;zpeak=4.20
            self.roof_prism('GreenGarageRoofFront',x0-.33,x1+.15,ey0,ridgey,[3.03,3.03,zpeak,zpeak]);self.roof_prism('GreenGarageRoofRear',x0-.33,x1+.15,ridgey,ey1,[zpeak,zpeak,3.03,3.03])
            for xx in [x0-.11,x1]:self.mesh('GarageGable',[(xx,y0,h),(xx,y1,h),(xx,cy,zpeak-.12)],[(0,1,2)],'V2_Warm_Plaster',False,0)
            for xx in [x0-.33,x1+.15]:
                self.beam('GarageGableFascia',(xx,ey0,3.03),(xx,ridgey,zpeak),.14,'ivory');self.beam('GarageGableFascia',(xx,ridgey,zpeak),(xx,ey1,3.03),.14,'ivory')
        else:
            inner=(cx-1.47,cx+1.47,.18,2.60)
            self.wall('GarageFront','X',y0,x0,x1,.18,h,[inner],'V2_Warm_Plaster')
            self.frame_x('GarageBay',cx,y0-.12,.18,2.94,2.42)
            self.portals['garage_front']={'center':[cx,y0,.18],'clear_width':2.94,'clear_height':2.42,'certainty':'visible garage location, bay detail partly occluded in primary photo'}
            self.roof_prism('YellowGarageShallowRoof',x0-.28,x1+.16,y0-.32,y1+.25,[3.12,3.64,3.64,3.12])
        rearx=x1-1.0
        self.wall('GarageRear','X',y1,x0,x1,.18,h,[(rearx-.60,rearx+.60,.18,2.33)],'V2_Warm_Plaster')
        self.portals['garage_rear']={'center':[rearx,y1,.18],'clear_width':1.2,'clear_height':2.15,'certainty':'reversible traversal approximation, rear evidence limited'}
        self.wall('GarageOuter','Y',x0,y0,y1,.18,h,[],'V2_Warm_Plaster')
        # shared main shell already contains connector portal; don't add a closed inner garage wall
        self.box('GarageHeader',(cx,y0-.17,h-.05),(w+.21,.20,.15),'ivory' if self.green else 'wood_light')
    def rear(self):
        # Compact original traversal approximation; not presented as a surveyed classic rear elevation
        y=self.y1+1.05;deckx=self.cx;dw=self.w-.40;dep=2.1
        self.box('RearDeck',(deckx,y,self.f1-.07),(dw,dep,.14),'wood_light',True)
        for xx in [deckx-dw/2+.15,deckx+dw/2-.15]:
            for yy in [self.y1+.12,self.y1+1.94]:self.box('RearDeckPost',(xx,yy,3.11),(.14,.14,6.12),'wood_light')
        for xx in [deckx-dw/2,deckx+dw/2]:self.box('RearPergolaBeam',(xx,y,6.18),(.16,2.25,.18),'wood_light')
        for j in range(33):self.box('RearPergolaSlat',(deckx-dw/2+j*dw/32,y,6.29),(.06,2.30,.09),'wood_light',False,.004)
        for j in range(8):self.box('RearPergolaCrossSlat',(deckx,self.y1-.02+j*2.30/7,6.35),(dw+.15,.065,.07),'wood_light',False,.004)
        # straight flight along rear facade, entirely within body width; grass landing on +X
        topx=deckx+dw/2+.74;bottomx=topx-5.65;stairy=self.y1+2.82;sw=1.45;run=5.65;n=18
        # Real raised support before the flight: yard .014 -> pad .18 -> first tread .3467.
        # Matches the authored anchor and avoids a .3327m unsupported first rise.
        self.box('RearStairBottomLanding',(bottomx-.675,stairy,self.f0/2),(1.45,1.75,self.f0),'concrete',True,.012)
        # L-shaped landing: cap begins after flight, side connector lies beside it.
        # Prevent previous 0.775m overlap from creating a 0.41m abrupt final step.
        self.box('RearStairTopCap',(topx+.585,stairy,self.f1-.07),(1.23,sw,.14),'wood_light',True)
        sideleft=deckx+dw/2-.20;sideright=topx+1.20;sylo=self.y1+.95;syhi=stairy-sw/2+.005
        self.box('RearStairSideConnector',((sideleft+sideright)/2,(sylo+syhi)/2,self.f1-.07),(sideright-sideleft,syhi-sylo,.14),'wood_light',True)
        for i in range(n):
            z=self.f0+(i+1)*(self.f1-self.f0)/n;x=bottomx+(i+.5)*run/n
            self.box('RearStair',(x,stairy,z-.045),(run/n+.01,sw,.09),'wood_light',False,.006)
        # ordering chosen so top polygon normal faces up
        self.ramp('RearStairRamp',[(bottomx,stairy+sw/2,self.f0+.1667),(bottomx,stairy-sw/2,self.f0+.1667),(topx,stairy-sw/2,self.f1),(topx,stairy+sw/2,self.f1)])
        for yy in [stairy-sw/2,stairy+sw/2]:
            self.beam('RearStairHandrail',(bottomx,yy,self.f0+.95),(topx,yy,self.f1+.95),.075,'wood_light')
            self.beam('RearStairStringer',(bottomx,yy,self.f0),(topx,yy,self.f1-.15),.16,'wood_light',.12)
            for j in range(24):
                t=j/23;x=bottomx+t*run;z=self.f0+t*3.0;self.beam('RearStairBaluster',(x,yy,z),(x,yy,z+.95),.07,'wood_light')
        # rear rail omitted across stair landing connector to keep top passage open
        self.beam('RearDeckRail',(deckx-dw/2,self.y1+1.95,self.f1+.95),(topx-.83,self.y1+1.95,self.f1+.95),.085,'wood_light')
        for j in range(38):
            xx=deckx-dw/2+j*max(.1,(topx-.85-deckx+dw/2))/37;self.beam('RearDeckBaluster',(xx,self.y1+1.95,self.f1),(xx,self.y1+1.95,self.f1+.95),.055,'wood_light')
        self.routes['rear_stairs']={'bottom':[bottomx-.55,stairy,self.f0],'top':[topx+.585,stairy,self.f1],'deck_connector':[deckx+dw/2-.7,self.y1+1.5,self.f1],'side_landing':[topx+.585,self.y1+1.50,self.f1],'top_cap':[topx+.585,stairy,self.f1],'ramp_start':[bottomx,stairy,self.f0+.1667],'ramp_end':[topx,stairy,self.f1],'bottom_landing_bbox':[[bottomx-1.40,stairy-.875,0],[bottomx+.05,stairy+.875,self.f0]],'bottom_landing_floor':self.f0,'width':sw,'run':run,'rise':3.0,'certainty':'rear pergola/diagonal façade-parallel stair corroborated by BO1 thesis capture; exact dimensions estimated'}
        self.routes['rear_deck']={'door':self.portals['rear_upper_door']['center'],'landing':[deckx,y,self.f1],'width':dw,'depth':dep}
    def report(self):
        bpy.context.view_layer.update()
        bounds=[]
        for o in self.parts:
            if o.type=='MESH':bounds.extend(o.matrix_basis@Vector(v) for v in o.bound_box)
        report={'version':VERSION,'house_id':self.id,'frame':'Blender Z up; local front=-Y, rear=+Y, +X right from street camera','root_local':[0,0,0],'layout_frame_version':json.loads(CONFIG.read_text())['version'],'geometric_lot_id':self.frame.get('geometric_lot_id'),'family_source_color':self.frame.get('source_color'),'root_transform_supplied':self.root.matrix_world[:],'main_body_bbox_local_m':[[self.x0,self.y0],[self.x1,self.y1]],'garage_bbox_local_m':[[self.gx0,self.gy0],[self.gx1,self.gy1]],'main_body_width_depth_m':[self.w,self.d],'garage_width_depth_m':[self.gx1-self.gx0,self.gy1-self.gy0],'floor_to_floor_m':3.0,'wall_eave_m':6.20,'local_geometry_bounds_m':[[min(v[i] for v in bounds) for i in range(3)],[max(v[i] for v in bounds) for i in range(3)]],'portals':self.portals,'routes':self.routes,'visual_objects':len(self.parts),'collision_objects':len(self.colliders),'collision_triangles':sum(len(p.vertices)-2 for o in self.colliders for p in o.data.polygons),'visible_reference_criteria':['distinct roof silhouettes','green paired upper windows/shutters','green outer garage bay closed and inner bay open','yellow stone chimney continuous ground-to-roof','yellow upper overhang','separate body/garage minimap ratio'],'uncertainties':['Metric dimensions are provisional gameplay calibration, not authenticated Nuketown meters','Minimap component polygons ±6 pixels; rectangular conservative bounding approximation','Rear pergola/stair direction and two upper rooms corroborated in BO1 thesis p128/p130; exact dimensions and side openings remain calibrated approximations','Yellow garage bay detail partially occluded']}
        # Matrix row objects must be converted to ordinary lists
        report['root_transform_supplied']=[list(row) for row in self.root.matrix_world]
        return report

def build_house(house_id,frames=None,root_matrix=None):
    frames=frames or json.loads(CONFIG.read_text())['house_frames']
    for c in list(bpy.data.collections):
        if c.name in ['10_'+house_id+'_H3_Architecture','91_'+house_id+'_H3_Collision']:
            for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
            bpy.data.collections.remove(c)
    h=HouseBuilder(frames[house_id],root_matrix);h.shell();h.garage();h.rear();h.cc.hide_render=True;collection('V3_COLLISION').hide_render=True
    return h,h.report()

def world_root(frame):
    return Matrix.Translation(Vector(frame['position_blender'])) @ Matrix.Rotation(frame['yaw_radians'],4,'Z')

def apply_local_houses(frames=None):
    """Manager integration entry point. Creates local identity-root assets only.
    Call layout.apply AFTER this. Never apply world_root plus layout.apply.
    Does not save, export, publish, or edit shared materials.
    """
    frames=frames or json.loads(CONFIG.read_text())['house_frames']
    removed=remove_old_house_visuals()
    houses=[];reports={}
    for house_id in ['A_Mint','B_Saffron']:
        h,r=build_house(house_id,frames);houses.append(h);reports[house_id]=r
    return {'version':VERSION,'removed_old_visuals':removed,'reports':reports,'roots':[h.root.name for h in houses],'collision_roots':[h.croot.name for h in houses]}
