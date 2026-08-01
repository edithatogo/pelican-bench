"""Deterministic generation of dynamic compositional benchmark tasks."""
from __future__ import annotations
import itertools,random
from pathlib import Path
from typing import Any,Iterable
from .io import content_hash,read_json
from .models import BenchmarkTask,EntitySpec,RelationSpec
HERITAGE_PROMPT="Generate an SVG of a pelican riding a bicycle"

def load_grammar(path:str|Path)->dict[str,Any]:
    grammar=read_json(path)
    if not isinstance(grammar,dict):raise TypeError("task grammar must be an object")
    validate_grammar(grammar);return grammar

def validate_grammar(g:dict[str,Any])->None:
    if 'version' not in g:raise ValueError('grammar version is required')
    for key in ('animals','mobile_objects','relations'):
        if not isinstance(g.get(key),list) or not g[key]:raise ValueError(f'grammar requires {key}')
        ids=[str(x.get('id','')) for x in g[key]]
        if any(not x for x in ids) or len(ids)!=len(set(ids)):raise ValueError(f'{key} identifiers must be present and unique')

def _compatible(a:dict[str,Any],o:dict[str,Any],g:dict[str,Any]):
    modes=set(a.get('interaction_modes',[]))&set(o.get('interaction_modes',[]))
    return [r for r in g['relations'] if r['id'] in modes]

def _entity(x:dict[str,Any],prefix:str)->EntitySpec:
    return EntitySpec(id=str(x['id']),label=str(x.get('label',x['id'])),ontology_ref=str(x.get('ontology_ref',f"{prefix}#{x['id']}")),required_features=tuple(map(str,x.get('required_features',[]))))

def build_task(*,animal:dict[str,Any],mobile_object:dict[str,Any],relation:dict[str,Any],seed:int,release:str,track:str='compositional-svg',viewpoint:str='side',style:str='simple vector illustration',public:bool=True,prompt_template:str|None=None)->BenchmarkTask:
    ae=_entity(animal,'animal');oe=_entity(mobile_object,'mobile-object')
    template=prompt_template or relation.get('prompt_template','Generate an SVG of a {animal} {relation_phrase} {mobile_object}, viewed from the {viewpoint}, in a {style} style.')
    prompt=str(template).format(animal=ae.label,mobile_object=oe.label,relation=relation['id'],relation_phrase=relation.get('prompt_phrase',relation['id'].replace('_',' ')),viewpoint=viewpoint,style=style)
    payload={'release':release,'track':track,'animal':ae.id,'object':oe.id,'relation':relation['id'],'viewpoint':viewpoint,'style':style,'seed':seed,'prompt':prompt}
    task_id='pb:'+content_hash(payload).split(':',1)[1][:16]
    difficulty=1+(viewpoint not in {'side','profile'})+(relation['id'] not in {'rides_on','passenger_in'})+(len(ae.required_features)+len(oe.required_features)>=10)+(style not in {'simple vector illustration','flat icon'})
    return BenchmarkTask(task_id=task_id,benchmark_release=release,track=track,prompt=prompt,animal=ae,mobile_object=oe,relations=(RelationSpec(predicate=str(relation['id']),subject=ae.id,object=oe.id),),viewpoint=viewpoint,style=style,difficulty=min(int(difficulty),5),seed=seed,public=public,metadata={'grammar_relation':relation['id'],'object_class':mobile_object.get('class'),'animal_class':animal.get('class')})

def heritage_task(*,release:str='PB-2026.08',seed:int=0)->BenchmarkTask:
    return BenchmarkTask(task_id='pb:heritage-pelican-bike-v1',benchmark_release=release,track='heritage-svg',prompt=HERITAGE_PROMPT,animal=EntitySpec(id='pelican',label='pelican',ontology_ref='pelican#pelican',required_features=('bill','gular-pouch','wing','webbed-foot')),mobile_object=EntitySpec(id='bicycle',label='bicycle',ontology_ref='bicycle#bicycle',required_features=('front-wheel','rear-wheel','frame','handlebar','pedal')),relations=(RelationSpec(predicate='rides_on',subject='pelican',object='bicycle'),),viewpoint='unspecified',style='unspecified',difficulty=2,seed=seed,public=True,metadata={'heritage_anchor':True,'exact_prompt':True})

def generate_tasks(grammar:dict[str,Any],*,count:int,seed:int,release:str='PB-2026.08',public:bool=True,include_heritage:bool=True)->list[BenchmarkTask]:
    if count<1:raise ValueError('count must be positive')
    rng=random.Random(seed);candidates=[]
    for a,o in itertools.product(grammar['animals'],grammar['mobile_objects']):
        for r in _compatible(a,o,grammar):candidates.append((a,o,r))
    if not candidates:raise ValueError('grammar has no compatible combinations')
    rng.shuffle(candidates);out=[]
    if include_heritage:out.append(heritage_task(release=release,seed=seed))
    i=0
    while len(out)<count:
        a,o,r=candidates[i%len(candidates)];s=rng.randrange(0,2**31)
        task=build_task(animal=a,mobile_object=o,relation=r,seed=s,release=release,viewpoint=rng.choice(grammar.get('viewpoints',['side'])),style=rng.choice(grammar.get('styles',['simple vector illustration'])),public=public)
        if any(x.task_id==task.task_id for x in out):
            data=task.model_dump();data['task_id']=f"{task.task_id}-r{i+1}";data['metadata']={**task.metadata,'replicate':i+1};task=BenchmarkTask.model_validate(data)
        out.append(task);i+=1
    return out

def full_factorial(grammar:dict[str,Any],*,release:str,seed:int,animals:Iterable[str]|None=None,mobile_objects:Iterable[str]|None=None)->list[BenchmarkTask]:
    af=set(animals or ());of=set(mobile_objects or ());out=[];i=0
    for a in grammar['animals']:
        if af and a['id'] not in af:continue
        for o in grammar['mobile_objects']:
            if of and o['id'] not in of:continue
            for r in _compatible(a,o,grammar):out.append(build_task(animal=a,mobile_object=o,relation=r,seed=seed+i,release=release));i+=1
    return out

def split_public_sealed(tasks:list[BenchmarkTask],*,sealed_fraction:float,seed:int)->tuple[list[BenchmarkTask],list[BenchmarkTask]]:
    if not 0<sealed_fraction<1:raise ValueError('sealed_fraction must be between 0 and 1')
    heritage=[t for t in tasks if t.track=='heritage-svg'];rest=[t for t in tasks if t.track!='heritage-svg'];random.Random(seed).shuffle(rest)
    n=max(1,round(len(rest)*sealed_fraction));sealed=[]
    for t in rest[:n]:sealed.append(BenchmarkTask.model_validate({**t.model_dump(),'public':False}))
    return heritage+rest[n:],sealed
