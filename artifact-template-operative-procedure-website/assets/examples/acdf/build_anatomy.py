"""Extract the cervical region from Z-Anatomy Startup.blend and build teaching meshes."""
import argparse
import base64
import sys
import hashlib
import json
from pathlib import Path

import numpy as np
SKILL = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(SKILL/'scripts'), str(SKILL/'assets/source/atlas-tools')]
from readblend import Blend
from mesh_geometry import axis_crossings, decode_triangles, transform_mesh

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('scene', type=Path)
parser.add_argument('--catalog', action='store_true')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
scene = Blend(args.scene)
objects = {scene.get(obj, 'id.name')[2:]: obj for obj in scene.bytype['Object']}
center = np.array([0, 0, 1.445])
scale = 75.
atlas = []
meshes = []
colors = {'skin':'#d9a184','fat':'#debd69','galea':'#bd8274','muscle':'#b87367',
          'deepfascia':'#75a99a','fascia':'#a4c7ba','bone':'#e2d5b8','disc':'#8ebfbc',
          'brain':'#bca99d','dura':'#95aeb7','arteries':'#dd6268','veins':'#5f6fae',
          'nerves':'#f2d776','viscera':'#d4a393','implant':'#a0b4c4','mark':'#ed6e6a',
          'tool':'#7ed8ea'}
palette = {'galea':'#bd8274','disc':'#83a8a2','viscera':'#bd8a7a','implant':'#a0b4c4'}

def display(obj, points, faces):
    # The fallback Blender reader exposes the saved matrix in row-vector order.
    world = np.array(scene.get(obj, 'obmat')).reshape(4, 4).T
    region = np.eye(4)
    region[:3, :3] = scale * np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
    region[:3, 3] = -region[:3, :3] @ center
    return transform_mesh(points, faces, world, region)

def mesh_points(obj, data):
    sizes = [scene.get(data, k) for k in ['totvert','totloop','totpoly']]
    positions = []
    for key, kind, size, shape, dtype in zip(['mvert','mloop','mpoly'], ['MVert','MLoop','MPoly'],
            sizes, [(sizes[0],3),(sizes[1],),(sizes[2],2)], ['<f4','<i4','<i4']):
        block, off = scene.find(scene.get(data,key), data)
        assert block['type'] == kind and block['count'] == size, (key, block, size)
        strides = (scene.types[kind]['size'],) + (4,) * (len(shape)-1)
        positions.append(np.ndarray(shape, dtype=dtype, buffer=scene.raw,
                                    offset=block['pos']+off, strides=strides))
    verts, loops, polys = positions
    faces = [(loops[start], loops[start+j], loops[start+j+1])
             for start, count in polys for j in range(1,count-1)]
    return display(obj, verts, faces)


def tube(path, radii, n=12):
    path = np.asarray(path, dtype=float)
    rings = []
    for i,p in enumerate(path):
        tangent = path[min(i+1,len(path)-1)] - path[max(i-1,0)]
        tangent /= np.linalg.norm(tangent) or 1
        ref = [0.,0.,1.] if abs(tangent[2]) < .9 else [0.,1.,0.]
        normal = np.cross(tangent,ref)
        normal /= np.linalg.norm(normal) or 1
        binormal = np.cross(tangent,normal)
        rings.extend(p + radii[i] * (np.cos(a)*normal + np.sin(a)*binormal)
                     for a in np.linspace(0,2*np.pi,n,endpoint=False))
    faces = []
    for i in range(len(path)-1):
        for j in range(n):
            a, d = i*n+j, i*n+(j+1)%n
            faces.extend([(a,d,a+n),(d,d+n,a+n)])
    faces.extend((0,j+1,j) for j in range(1,n-1))
    k = (len(path)-1)*n
    faces.extend((k,k+j,k+j+1) for j in range(1,n-1))
    return np.asarray(rings), np.asarray(faces)

def curve_points(obj, data):
    vertices, faces = [], []
    ptr = scene.get(data,'nurb.first')
    while ptr:
        curve,_ = scene.find(ptr, data)
        n = scene.get(curve,'pntsu')
        bez = scene.get(curve,'bezt')
        base = float(scene.get(data,'ext2')) or .0006
        path, radii = [], []
        if bez:
            block,_ = scene.find(bez,data)
            nodes = np.array([scene.get(block,'vec',i,'BezTriple') for i in range(n)]).reshape(n,3,3)
            rr = [scene.get(block,'radius',i,'BezTriple') for i in range(n)]
            cycle = bool(scene.get(curve,'flagu')&1)
            for i in range(n if cycle else n-1):
                j = (i+1)%n
                p0,p1,p2,p3 = nodes[i,1],nodes[i,2],nodes[j,0],nodes[j,1]
                for t in np.arange(0,1,1/6):
                    u = 1-t
                    path.append(u**3*p0+3*u*u*t*p1+3*u*t*t*p2+t**3*p3)
                    radii.append(base*(u*rr[i]+t*rr[j]))
            end = 0 if cycle else -1
            path.append(nodes[end,1]); radii.append(base*rr[end])
        elif point := scene.get(curve,'bp'):
            block,_ = scene.find(point,data)
            path = [scene.get(block,'vec',i,'BPoint')[:3] for i in range(n)]
            radii = [base*scene.get(block,'radius',i,'BPoint') for i in range(n)]
        if len(path)>1:
            v,f = tube(path,radii)
            faces.extend(f+len(vertices)); vertices.extend(v)
        ptr = scene.get(curve,'next')
    return display(obj, vertices, faces)


def encode(name, group, points, faces, **properties):
    assert len(points) and len(faces) and np.isfinite(points).all(), name
    assert faces.min() >= 0 and faces.max() < len(points), name
    face_normals = np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    faces = faces[np.linalg.norm(face_normals,axis=1)>1e-10]
    face_normals = np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
    normals = np.zeros_like(points)
    for j in range(3):
        np.add.at(normals,faces[:,j],face_normals)
    length = np.linalg.norm(normals,axis=1)
    normals /= np.maximum(length[:,None],1e-12)
    # Estimate local crease occlusion from the concentration of incident face normals.
    area = np.zeros(len(points))
    for j in range(3):
        np.add.at(area,faces[:,j],np.linalg.norm(face_normals,axis=1))
    ao = .72+.28*np.clip(length/np.maximum(area,1e-12),0,1)
    corner_normals = normals[faces] * ao[faces,None]
    # Opposing coincident atlas faces can cancel a vertex normal entirely.
    # Keep a per-face fallback so those corners still have a valid lighting direction.
    fallback = .72*face_normals/np.linalg.norm(face_normals,axis=1,keepdims=True)
    corner_normals = np.where((length[faces]<1e-10)[...,None],fallback[:,None,:],corner_normals)
    vertices = np.concatenate((points[faces],corner_normals),axis=2).reshape(-1,6).astype('<f4')
    low, high = points.min(axis=0),points.max(axis=0)
    mesh = dict(id=properties.pop('id',f'M-{len(meshes)+1:03d}'),name=name,
                nativeName=properties.pop('nativeName',name),group=group,
                color=properties.pop('color',colors[group]),bounds=[low.tolist(),high.tolist()],
                anchor=((low+high)/2).tolist(),count=len(vertices),
                data=base64.b64encode(vertices.tobytes()).decode(),**properties)
    meshes.append(mesh)
    return mesh

def region(points, faces, low=-4.8, high=5.6):
    # Trim only outside the displayed cervical band. Interpolate at both boundaries.
    inside = (points[:,1] >= low) & (points[:,1] <= high)
    within = inside[faces].all(axis=1)
    indices = faces[within]
    keep = np.unique(indices)
    remap = np.empty(len(points), dtype=int)
    remap[keep] = np.arange(len(keep))
    output = points[keep].tolist()
    triangles = remap[indices].tolist()
    for face in faces[~within & (points[faces,1].max(axis=1)>=low) & (points[faces,1].min(axis=1)<=high)]:
        poly = list(points[face])
        for boundary, sign in [(low,1),(high,-1)]:
            new = []
            for a,b in zip(poly,poly[1:]+poly[:1]):
                ina, inb = sign*(a[1]-boundary)>=0, sign*(b[1]-boundary)>=0
                if ina:
                    new.append(a)
                if ina != inb:
                    new.append(a+(b-a)*((boundary-a[1])/(b[1]-a[1])))
            poly = new
            if not poly:
                break
        index = len(output)
        output.extend(poly)
        triangles.extend((index,index+j,index+j+1) for j in range(1,len(poly)-1))
    return np.asarray(output),np.asarray(triangles)

def native(name, group, *, crop=False, context=False, key=None, display_name=None, **props):
    obj=objects[name]
    data,_=scene.find(scene.get(obj,'data'))
    kind=scene.get(obj,'type')
    points,faces=(mesh_points if kind==1 else curve_points)(obj,data)
    if crop:
        points,faces=region(points,faces)
    side='left' if name.endswith('.l') or name.startswith('Left ') else (
         'right' if name.endswith('.r') or name.startswith('Right ') else 'both')
    label=display_name or (side.title()+' '+name[:-2] if name.endswith(('.l','.r')) else name)
    if not len(faces):
        print(f"Unavailable cervical crop: {name}")
        return None
    record=encode(label,group,points,faces,id=key or f'ZA-{len(atlas)+1:02d}',nativeName=name,
                  procedureSide=side,contextOnly=context,source='Z-Anatomy, CC BY-SA 4.0',
                  description=props.pop('description','Atlas surface in its native anatomical position.'),**props)
    atlas.append(dict(id=record['id'],nativeName=name,objectAddress=obj['addr'],objectMatrix=scene.get(obj,'obmat'),
                      crop=crop,type=kind))
    print(f"{record['id']:12} {name:38} {len(faces):7} {np.round(record['bounds'], 2).tolist()}")
    return record

for level in ['C3','C4','C5','C6','C7','T1']:
    native('Vertebra '+level,'bone',key=level,context=level in ['C3','T1'])
for level in ['C3-C4','C4-C5','C5-C6','C6-C7','C7-T1']:
    native('Intervertebral disc '+level,'disc',key='disc-'+level,context=level in ['C3-C4','C7-T1'],level=level)
for side in ['r','l']:
    native(f'Longus colli muscle.{side}','muscle',crop=True,key=f'longus-{side}',retract='longus')
    native(f'Sternocleidomastoid muscle.{side}','muscle',crop=True,key=f'scm-{side}',retract='lateral',context=True)
    native(f'{"Right" if side=="r" else "Left"} common carotid artery','arteries',crop=True,key=f'carotid-{side}',retract='lateral')
    native(f'Internal jugular vein.{side}','veins',crop=True,key=f'jugular-{side}',retract='lateral')
    native(f'Vertebral artery.{side}','arteries',crop=True,key=f'va-{side}')
    native(f'Vagus nerve (X).{side}','nerves',crop=True,key=f'vagus-{side}',retract='lateral')
    native(f'Sympathetic trunk.{side}','nerves',crop=True,key=f'sympathetic-{side}',context=True)
    native(f'Sternohyoid muscle.{side}','muscle',crop=True,key=f'strap-{side}',retract='medial',context=True)
native('Trachea','viscera',crop=True,key='trachea',retract='medial')
native('Oesophagus','viscera',crop=True,key='esophagus',display_name='Esophagus',retract='medial')
native('Thyroid gland','viscera',crop=True,key='thyroid',retract='medial',
       display_name='Thyroid Gland (Atlas Segment)',
       description='Partial thyroid surface from the atlas, shown with the medial visceral structures.')
if args.catalog:
    raise SystemExit()

for name, group, key in [('Atlas (C1)','bone','C1'), ('Axis (C2)','bone','C2'),
    ('Mandible','bone','jaw'), ('Hyoid bone','bone','hyoid'),
    ('Thyroid cartilage','viscera','larynx'), ('Cricoid cartilage','viscera','cricoid')]:
    native(name,group,key=key,context=True,**({'retract':'medial'} if group=='viscera' else {}))
native('Spinal dura','dura',crop=True,key='dura',context=True)
native('Posterior longitudinal ligament','deepfascia',crop=True,key='pll-context',context=True,
       description='Atlas longitudinal ligament; the target-level operative windows are shown with separate illustrative geometry.')
native('Anterior longitudinal ligament','deepfascia',crop=True,key='all-context',context=True)

for side in ['r','l']:
    native(f'Platysma.{side}','galea',crop=True,key=f'platysma-{side}',context=True)
    native(f'Clavicle.{side}','bone',key=f'clavicle-{side}',context=True)

def original(name,group,points,faces,**props):
    return encode(name,group,np.asarray(points),np.asarray(faces),
                  source='Original cervical teaching illustration',**props)

def grid(name,group,surface,*,reverse=False,**props):
    nx, ny = 34, 34
    points=[surface(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+nx+1
            faces.extend([(a,a+1,b+1),(a,b+1,b)])
    faces = np.asarray(faces)
    return original(name,group,points,faces[:,[0,2,1]] if reverse else faces,**props)

def fz(x,y):
    # The cervical shell clears the broad anterior and lateral muscle envelope.
    return 4.69 - .057*x*x + .038*(y-1.5) - .023*(y-1.5)**2 + .31*max(0,y-3.5)

incisions={'1':1.93,'2':1.40,'3':1.95}
for n,y0 in incisions.items():
    for suffix,sign in [('r',-1),('l',1)]:
        side = 'right' if sign==-1 else 'left'
        for group,shift in [('skin',0),('fat',-.19),('galea',-.37)]:
            for edge,low,high in [('lower',y0-3.95,y0),('upper',y0,y0+3.6)]:
                def surface(u,v):
                    x=sign*u*3.65
                    y=low+(high-low)*v
                    return x,y,fz(x,y)+shift
                original_name={'skin':'Anterior Neck Skin','fat':'Subcutaneous Fat','galea':'Platysma Corridor'}[group]
                grid(original_name,group,surface,id=f'{group}-{n}-{suffix}-{edge}',
                     reverse=sign<0,configuration=n,procedureSide=side,edge=edge,incisionY=y0,
                     description='Illustrative anterior neck covering. The retracted opening marks the surgical access corridor.')
        for name,stages,col,yadj in [('Skin Landmark',['prepare'],'#e9ca6f',0),('Incision Line',['incise'],'#e26065',0),
                 ('Skin Closure',['close-skin'],'#e9ca6f',0)]:
            path=[(sign*x,y0+yadj,fz(sign*x,y0+yadj)+.045) for x in np.linspace(.34,2.7,30)]
            q,f=tube(path,[.025]*len(path),9)
            original(name,'mark',q,f,procedureSide=side,configuration=n,marker=True,markerStages=stages,
                     markerRadius=.025,markerKind=2,markerAxis=0,markerRange=[.34,2.7],color=col,
                     description='The marked location is illustrative.')
        for yoff in [-.19,0,.19]:
            x=sign*(1.25+yoff)
            p,f=tube([(x,y0-.13,fz(x,y0-.13)+.045),(x,y0+.13,fz(x,y0+.13)+.045)],[.014,.014],8)
            original('Skin Suture','mark',p,f,procedureSide=side,configuration=n,marker=True,
                     markerStages=['close-skin'],color='#8bc5af',markerRadius=.014)
        if sign==-1:
            for sideName in ['right','left']:
                # Only the approach-specific trajectory is shown for directional instruments.
                signT=-1 if sideName=='right' else 1
                def instrument(title, stage, points, widths, **props):
                    p,f=tube(points,widths,10)
                    return original(title,'tool',p,f,procedureSide=sideName,instrument=True,
                          instrumentStage=stage,configuration=n,description='Generic instrument illustration.',**props)
                instrument('Scalpel','incise',[(signT*.46,y0,fz(.46,y0)+.05),
                     (signT*.55,y0+.12,fz(.55,y0)+.58),(signT*.78,y0+.27,fz(.78,y0)+1.32)],
                     [.029,.07,.1],travel=[signT*1.95,0,fz(2.41,y0)-fz(.46,y0)-.04])
                instrument('Blunt Dissector','interval',[(signT*.48,y0,.68),(signT*.76,y0,2.1),
                           (signT*.95,y0+.02,4.8)],[.039,.046,.072],approach=[signT*.14,0,1.1])
                disc_y, disc_z = {'1':(1.67,-.22),'2':(1.67,-.22),'3':(3.00,-.10)}[n]
                instrument('Localization Marker','localize',[(0,disc_y,disc_z),
                           (signT*.24,disc_y-.12,1.0),(signT*.55,disc_y-.30,3.8)],
                           [.024,.032,.05],approach=[signT*.20,-.11,1.1])

for n,y0 in incisions.items():
    for suffix,sign in [('r',-1),('l',1)]:
        grid('Investing Fascia','fascia',
             lambda u,v:(sign*u*3.18,y0-2.9+v*5.35,
                         fz(sign*u*3.18,y0-2.9+v*5.35)-.67),
             reverse=sign<0,configuration=n,procedureSide='right' if sign==-1 else 'left',retract='superficial',
             description='Illustrative segment of the investing fascial layer.')
    for suffix,sign in [('r',-1),('l',1)]:
        grid('Prevertebral Fascia','deepfascia',
             lambda u,v:(sign*u*1.83,y0-2.5+v*4.45,
                         .42-.16*u*u+.07*(v-.5)),
             reverse=sign<0,configuration=n,procedureSide='right' if sign==-1 else 'left',retract='fascia',
             description='Illustrative fascia over the anterior spine and longus colli.')

def rounded(name,group,center,half,bevel,*,shape=None,**props):
    # Rounded solid using six projected, beveled face grids.
    p=[];f=[]
    center=np.array(center); half=np.array(half)
    for axis in range(3):
        a,b=(axis+1)%3,(axis+2)%3
        for sign in [-1,1]:
            start=len(p); n=12
            for j in range(n+1):
                for i in range(n+1):
                    v=np.zeros(3)
                    v[axis]=sign*half[axis]
                    v[a]=half[a]*(2*i/n-1)
                    v[b]=half[b]*(2*j/n-1)
                    inner=np.clip(v,-half+bevel,half-bevel)
                    normal=v-inner
                    p.append(center+inner+normal/np.linalg.norm(normal)*bevel)
            for j in range(n):
                for i in range(n):
                    x=start+j*(n+1)+i;y=x+n+1
                    tris=[(x,x+1,y+1),(x,y+1,y)]
                    f.extend(tris if sign>0 else [(a,c,b) for a,b,c in tris])
    return original(name,group,shape(np.asarray(p)) if shape else p,f,**props)

levels={
    'C4-C5': {'y':3.10,'front':-.08,'back':-1.11,'upper':3.64,'lower':2.65},
    'C5-C6': {'y':1.99,'front':-.25,'back':-1.23,'upper':2.55,'lower':1.61},
    'C6-C7': {'y':.91,'front':-.49,'back':-1.57,'upper':1.44,'lower':.44},
}
# Recess the cage footprint within the native endplates at each level.
cage_depths = {
    'C4-C5': (-.97,-.29),
    'C5-C6': (-1.09,-.41),
    'C6-C7': (-1.41,-.77),
}
# Posterior tip and anterior entry samples fitted between native endplates.
# Coordinate order is x, superior y, anterior z. Instrument dimensions are illustrative.
working_routes = {
    'C4-C5': ((.76,3.205,-.97),(.34,2.99,-.19),(.12,3.105,-1.02),(.12,2.98,-.14)),
    'C5-C6': ((.76,1.975,-1.085),(.34,1.70,-.27),(.12,1.98,-1.14),(.12,1.66,-.23)),
    'C6-C7': ((.76,.895,-1.425),(.34,.608,-.58),(.12,.84,-1.46),(.12,.60,-.55)),
}
# Each pin starts anterior to the body it distracts. The lower pin sits
# below the disc, away from the upper endplate used for access.
pins = {
    'C4-C5': ((3.67,-.22), (2.49,-.34)),
    'C5-C6': ((2.44,-.32), (1.25,-.49)),
    'C6-C7': ((1.36,-.51), (.25,-.71)),
}
uncinate_tips = {'C4-C5':3.19,'C5-C6':1.95,'C6-C7':.85}
# The atlas has a full spinal dura but no usable cervical cord surface. Use
# its lumen to center the cord. Fit the proximal exiting nerve paths separately
# through the native openings, including the small distraction travel.
native_surfaces = {m['id']: decode_triangles(m) for m in meshes
                   if m['id'] in ['C4','C5','C6','C7','dura']}
dural_surface = native_surfaces['dura']
axis = []
for y in np.linspace(-1.6,5.50,114):
    crossings = axis_crossings(dural_surface,2,[0,y])
    assert len(crossings)>=2, y
    axis.append([0,y,(crossings[0]+crossings[-1])/2])
p,f=tube(axis,[.26]*len(axis),24)
original('Cervical Spinal Cord','brain',p,f,id='cord',
         description='Illustrative cord centered within the native atlas dural canal.')

foraminal_routes = {
    'C4-C5': [(.25,3.059,-1.70),(.54,3.059,-1.627),(.82,3.059,-1.492),
              (1.1,3.086,-1.303),(1.38,3.005,-1.195),(1.80,2.951,-1.087)],
    'C5-C6': [(.25,1.959,-1.89),(.54,1.932,-1.849),(.82,1.932,-1.741),
              (1.1,1.932,-1.579),(1.38,1.932,-1.444),(1.80,1.878,-1.363)],
    'C6-C7': [(.25,.859,-2.295),(.54,.865,-2.234),(.82,.884,-2.103),
              (1.1,.975,-1.875),(1.38,.849,-1.788),(1.80,.697,-1.837)],
}
for k,coordinates in foraminal_routes.items():
    x,y,z=np.array(coordinates).T
    samples=np.linspace(x[0],x[-1],33)
    radii=np.interp(samples,[x[0],.6,1.25,x[-1]],[.05,.055,.062,.049])
    for side,sign in [('right',-1),('left',1)]:
        path=np.c_[sign*samples,np.interp(samples,x,y),np.interp(samples,x,z)]
        p,f=tube(path,radii,16)
        root=k.split('-')[1]
        original(f'{side.title()} {root} Exiting Nerve Root','nerves',p,f,
                 id=f'root-{root}-{side}',level=k,procedureSide=side,
                 description='Illustrative proximal nerve traced through the atlas intervertebral foramen.')

# Locate the centers of the vertebral bodies using the bony contours at the
# midline. Record the anterior surface at each screw column independently.
bodies={}
for body,reference in {'C4':3.65,'C5':2.48,'C6':1.31,'C7':.23}.items():
    surface=native_surfaces[body]
    posterior,front=axis_crossings(surface,2,[0,reference])[-2:]
    depth=(posterior+front)/2
    inf,sup=axis_crossings(surface,1,[0,depth])[[0,-1]]
    y=(inf+sup)/2
    front=max(axis_crossings(surface,2,[0,y]))
    bodies[body]={'y':y,'front':front,'center':[0,y,depth]}

implant_fits={}
for lk,d in levels.items():
    y,front,back=d['y'],d['front'],d['back']
    # Visible level collars and anterior/rear interfaces are fitted to the native disc bounds.
    rounded('Target Disc Landmark','mark',[0,y,front+.105],[.36,.024,.022],.014,
            id='target-'+lk,level=lk,marker=True,markerStages=['orient','localize'],color='#dfbd77')
    rounded('Posterior Longitudinal Ligament Window','deepfascia',[0,y,back-.055],[.70,.20,.07],.05,
            id='pll-'+lk,level=lk,remove='pll',description='Illustrative target-level PLL segment over the canal. The depicted focal release is pathology-dependent.')
    rounded('Posterior Disc–Osteophyte Complex','bone',[0,y-.16,back-.10],[.68,.14,.15],.12,
            id='osteophyte-'+lk,level=lk,remove='osteophyte',
            description='Illustrative posterior osteophyte at the disc–endplate margin.')
    rounded('Endplate Preparation Zone','mark',[0,d['lower']+.08,(front+back)/2],
            [.66,.025,.46],.02,id='endplate-'+lk,level=lk,marker=True,markerStages=['endplate'],
            color='#e4b36d')
    uncinate_y = uncinate_tips[lk]
    for suffix,sign in [('r',-1),('l',1)]:
        rounded('Foraminal Osteophyte','bone',[sign*.81,uncinate_y+.025,back+.105],
                [.125,.12,.12],.085,id='spur-'+lk+'-'+suffix,level=lk,remove='foramen',
                description='Schematic spur at the posteromedial uncovertebral margin.')
        path = [(sign*x,uncinate_y+dy,back+.235)
                for x,dy in [(.69,.03),(.74,.12),(.81,.165),(.88,.12),(.93,.03)]]
        p,f = tube(path,[.022]*len(path),9)
        original('Uncovertebral Decompression Zone','mark',p,f,id='foramen-'+lk+'-'+suffix,
                 level=lk,marker=True,markerStages=['foramen'],bilateral=True,
                 procedureSide='right' if sign<0 else 'left',color='#dd9969')
    upper, lower = lk.split('-')
    cage_back,cage_front = cage_depths[lk]
    cage_z = (cage_back+cage_front)/2
    depth = cage_front-cage_back
    xs = np.linspace(-.54,.54,23)
    zs = np.linspace(cage_back,cage_front,25)
    # Sample both opposing surfaces. Render a single ring-shaped cage with
    # endplate-conforming top and bottom faces instead of disconnected bars.
    high = np.empty((len(xs),len(zs)))
    low = np.empty_like(high)
    for i,x in enumerate(xs):
        for j,z in enumerate(zs):
            u = axis_crossings(native_surfaces[upper],1,[x,z])
            l = axis_crossings(native_surfaces[lower],1,[x,z])
            assert len(u) and len(l) and u[0]>l[-1], (lk,x,z)
            high[i,j]=u[0]-.012
            low[i,j]=l[-1]+.012

    def interpolate(table,x,z):
        xi=np.clip((np.asarray(x)-xs[0])/(xs[1]-xs[0]),0,len(xs)-1)
        zi=np.clip((np.asarray(z)-zs[0])/(zs[1]-zs[0]),0,len(zs)-1)
        i=np.minimum(xi.astype(int),len(xs)-2)
        j=np.minimum(zi.astype(int),len(zs)-2)
        a,b=xi-i,zi-j
        return ((1-a)*(1-b)*table[i,j]+a*(1-b)*table[i+1,j]+
                (1-a)*b*table[i,j+1]+a*b*table[i+1,j+1])

    def cage_center(z,x=0):
        return (interpolate(high,x,z)+interpolate(low,x,z))/2

    def cage_shape(points):
        x,z=points[:,0],points[:,2]
        mid=cage_center(z,x)
        room=interpolate(high,x,z)-mid
        points[:,1]=mid+points[:,1]*room
        return points

    slope = float((cage_center(cage_front)-cage_center(cage_back))/depth)
    implant_fits[lk]=[cage_back,cage_front,float(cage_center(cage_z)),slope]
    # Subdivide the contact belt radially as well as circumferentially.
    # This avoids long chord faces bridging over the curved bony surfaces.
    segments = 72
    radial_steps = 8
    angles = np.arange(segments)*2*np.pi/segments
    points=[]
    for top in [-1,1]:
        for t in np.linspace(0,1,radial_steps+1):
            width = .32+t*(.53-.32)
            length = depth/2-(1-t)*.086
            for angle in angles:
                x,z=np.cos(angle),np.sin(angle)
                norm=(x**4+z**4)**.25
                points.append([width*x/norm,top,cage_z+length*z/norm])
    points=cage_shape(np.asarray(points))
    faces=[]
    belt=(radial_steps+1)*segments
    for i in range(segments):
        j=(i+1)%segments
        for ring in range(radial_steps):
            a,b=ring*segments+i,(ring+1)*segments+i
            aj,bj=ring*segments+j,(ring+1)*segments+j
            faces.extend([(a,b,aj),(aj,b,bj),
                          (a+belt,aj+belt,b+belt),(aj+belt,bj+belt,b+belt)])
        a,b=i,radial_steps*segments+i
        aj,bj=j,radial_steps*segments+j
        faces.extend([(a,aj,a+belt),(aj,aj+belt,a+belt),
                      (b,b+belt,bj),(bj,b+belt,bj+belt)])

    lower_driver=None
    for construct in ['plated','zero']:
        tint = '#859eaa' if construct=='plated' else '#769caa'
        original('Interbody Cage','implant',points,faces,level=lk,
                 construct=construct,insert='cage',color=tint,
                 description='Midline cage fitted between the sampled superior and inferior endplates.')
        rounded('Interbody Graft','implant',[0,0,cage_z],[.30,.81,depth/2-.095],.072,
                shape=cage_shape,level=lk,construct=construct,insert='cage',color='#d5c5a0')
        if construct=='zero':
            head_z=cage_front-.035
            for x,direction,body in [(-.22,1,upper),(.22,-1,lower)]:
                a=np.array([x,float(cage_center(head_z,x))+direction*.024,head_z])
                b=np.array([x,*bodies[body]['center'][1:]])
                p,f=tube([a,b],[.047,.035],14)
                original('Integrated Anchor','implant',p,f,level=lk,construct=construct,
                         insert='anchor',fixation_body=body,fixation_tip=b.tolist(),
                         approach=(a-b).tolist())
                p,f=tube([a+[0,0,.038],a],[.069,.063],16)
                original('Anchor Head','implant',p,f,level=lk,construct=construct,
                         insert='anchor',color='#c4d2d7',approach=(a-b).tolist())
                if direction<0:
                    lower_driver=a+[0,0,.036]
    rounded('Cage Trial','tool',[0,0,cage_z],[.49,.73,depth/2],.078,
            shape=cage_shape,level=lk,instrument=True,instrumentStage='trial',approach=[0,2.2*slope,2.2])
    foraminal_tip, foraminal_entry, posterior, anterior = map(np.array,working_routes[lk])

    def axial_tool(title, stage, tip, direction, tip_radius=.038, shaft_radius=.048, travel=1.5, **props):
        # The whole shaft translates along its own axis during insertion. This keeps the deep
        # portion in the fitted corridor throughout the motion, not just in the final frame.
        tip = np.array(tip)
        direction = np.array(direction) / np.linalg.norm(direction)
        reach = (3.85-tip[2])/direction[2]
        positions = tip + np.array([0,min(.15,reach/3),reach-.41,reach])[:,None]*direction
        p,f=tube(positions,[tip_radius,shaft_radius,shaft_radius,.082],12)
        original(title,'tool',p,f,level=lk,instrument=True,instrumentStage=stage,
                 approach=(direction*(travel/direction[2])).tolist(),**props)

    for side,sign in [('right',-1),('left',1)]:
        mirror = np.array([sign,1,1])
        axial_tool('Kerrison Rongeur','foramen',foraminal_tip*mirror,
                   (foraminal_entry-foraminal_tip)*mirror,.032,.043,procedureSide=side,
                   description='Schematic Kerrison shaft through the opened disc space, with its tip at the posteromedial uncovertebral margin.')

    direction = anterior-posterior
    for stage,title,fraction in [('discectomy','Pituitary Rongeur',.24),
                                 ('osteophyte','High-Speed Burr',0),('pll','Microhook',0),
                                 ('endplate','Endplate Curette',.53)]:
        tip = posterior+fraction*direction
        if stage=='endplate':
            tip[1] -= .066
        axial_tool(title,stage,tip,direction,tip_radius=.033,shaft_radius=.043)
    axial_tool('Annulotomy Knife','annulus',anterior+[0,.022,0],direction,.024,.038)

    # Trial, cage and integrated-anchor tools connect to the anterior implant faces.
    # Their external shafts stay anterior and keep separate from the recessed implants.
    for stage,title,travel in [('trial','Trial Handle',2.2),('cage','Cage Inserter',2.05)]:
        tip=[0,float(cage_center(cage_front))-.02,cage_front+.035]
        axial_tool(title,stage,tip,[0,slope,1],.031,.045,travel=travel)
    # A bent driver approaches the recessed cage face through the gap. Its
    # handle stays nearly axial because extending the screw angle would cross
    # the upper vertebral body. The straight implant anchor uses its own path.
    driver_axis=np.array([0,slope*.85,1])
    axial_tool('Anchor Driver','anchor',lower_driver,driver_axis,.027,.039)

    for body,(pin_y,pin_z) in zip(lk.split('-'),pins[lk]):
        p,f=tube([[.23,pin_y,pin_z],[.23,pin_y,.87]],[.051,.058],12)
        original('Distraction Pin','tool',p,f,level=lk,instrument=True,pin_body=body,
                 instrumentStage='distraction',approach=[0,0,.68])
    p,f=tube([[.23,pins[lk][1][0],.82],[.23,pins[lk][0][0],.82]],[.064,.064],12)
    original('Distraction Frame','tool',p,f,level=lk,instrument=True,
              instrumentStage='distraction',approach=[0,0,.68])

layouts={'1':['C5','C6'],'2':['C5','C6','C7'],'3':['C4','C5','C6','C7']}
for n,levels_in_plate in layouts.items():
    traces=[[0,bodies[b]['y'],bodies[b]['front']+.102] for b in levels_in_plate]
    for x in [-.35,.35]:
        path=[[x,y,z] for _,y,z in traces]
        p,f=tube(path,[.135]*len(path),14)
        original('Anterior Cervical Plate','implant',p,f,insert='plate',configuration=n,construct='plated')
    for body,(_,y,z) in zip(levels_in_plate,traces):
        rounded('Anterior Cervical Plate','implant',[0,y,z],[.48,.24,.106],.083,
                configuration=n,construct='plated',insert='plate')
        for x in [-.25,.25]:
            front=max(axis_crossings(native_surfaces[body],2,[x,y]))
            tip=[x*.89,y,bodies[body]['center'][2]-.10]
            p,f=tube([[x,y,z+.13],[x,y,front+.006],tip],[.105,.062,.048],16)
            original('Anterior Plate Screw','implant',p,f,configuration=n,construct='plated',insert='screws',
                     color='#cbd6dc',fixation_body=body,fixation_tip=tip)
    y=traces[0][1]
    z=traces[0][2]
    for phase,title in [('plate','Plate Holder'),('screws','Screwdriver')]:
        p,f=tube([[.25,y,z+.155],[.25,y,z+1.2],[.25,y,3.85]],[.059,.068,.113],12)
        original(title,'tool',p,f,configuration=n,construct='plated',instrument=True,
                 instrumentStage=phase,approach=[0,0,1.25])
    yc=(traces[0][1]+traces[-1][1])/2
    for side,sign in [('right',-1),('left',1)]:
        for edge,x in [('medial',.79),('lateral',1.04)]:
            placement = dict(configuration=n,instrument=True,instrumentStage='blades',
                             approach=[0,0,1.30],retractor_side=side,retractor_edge=edge)
            rounded('Retractor Blade','tool',[sign*x,yc,.40],
                    [.082,(traces[0][1]-traces[-1][1])/2+.17,.40],.07,
                    description='Schematic self-retaining blade seated beside the operative field.',**placement)
            p,f=tube([[sign*x,yc,.72],[sign*x,yc,1.37],[sign*(x+.08),yc,2.22]],[.052,.059,.067],12)
            original('Retractor Arm','tool',p,f,**placement)
    for y1 in [yc-.23,yc,yc+.23]:
        p,f=tube([[-.20,y1,front+.29],[0,y1-.09,front+.47],[.20,y1,front+.29]],
                 [.018]*3,9)
        original('Platysma Approximation','mark',p,f,configuration=n,marker=True,
                 markerStages=['close-platysma'],markerRadius=.018,color='#92b4ad')

out=args.output
out.mkdir(parents=True, exist_ok=True)
(out/'mesh-data.json').write_text(json.dumps(meshes,separators=(',',':'))+'\n')
(out/'anatomy-data.json').write_text(json.dumps({
    'source': 'Z-Anatomy Startup.blend (Blender 3.5 scene)',
    'scene_sha256':hashlib.sha256(scene.raw).hexdigest(),
    'transform':{'center_meters':center.tolist(),'units_per_meter':scale,'axes':'+X patient left, +Y superior, +Z anterior'},
    'atlas_objects':atlas,'target_levels':list(levels),'levels':levels,'body_reference_points':bodies,
    'implant_fit':{'method':'Illustrative cage fitted to local native endplate intersections.',
                   'dimensions':['posterior_z','anterior_z','center_y','dy_per_dz'],
                   'values':implant_fits},
    'mesh_records':[{k:v for k,v in row.items() if k!='data'} for row in meshes]
},separators=(',',':'))+'\n')
print(f'Built {len(meshes)} surfaces and {sum(m["count"]//3 for m in meshes)} triangles.')
