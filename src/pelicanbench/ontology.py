"""Ontology loading, validation, abstraction and scene composition."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from .io import read_json

@dataclass(frozen=True,slots=True)
class Ontology:
    ontology_id: str
    version: str
    concepts: dict[str,dict[str,Any]]
    relations: dict[str,dict[str,Any]]
    competency_questions: tuple[dict[str,Any],...]
    @classmethod
    def from_dict(cls,value:dict[str,Any]):
        result=cls(str(value['id']),str(value['version']),{str(x['id']):x for x in value.get('concepts',[])},{str(x['id']):x for x in value.get('relations',[])},tuple(value.get('competency_questions',[])))
        result.validate();return result
    @classmethod
    def load(cls,path:str|Path):
        value=read_json(path)
        if not isinstance(value,dict): raise TypeError("ontology root must be an object")
        return cls.from_dict(value)
    def validate(self)->None:
        for cid,c in self.concepts.items():
            parent=c.get('parent')
            if parent is not None and parent not in self.concepts: raise ValueError(f"unknown parent {parent!r} for {cid!r}")
        for rid,r in self.relations.items():
            inv=r.get('inverse')
            if inv is not None and inv not in self.relations: raise ValueError(f"unknown inverse {inv!r} for {rid!r}")
        self._assert_acyclic()
    def _assert_acyclic(self):
        visiting:set[str]=set();visited:set[str]=set()
        def visit(node:str):
            if node in visiting: raise ValueError(f"ontology inheritance cycle at {node}")
            if node in visited:return
            visiting.add(node); parent=self.concepts[node].get('parent')
            if parent is not None:visit(str(parent))
            visiting.remove(node);visited.add(node)
        for node in self.concepts:visit(node)
    def ancestors(self,concept_id:str)->tuple[str,...]:
        if concept_id not in self.concepts:raise KeyError(concept_id)
        out=[];cur=self.concepts[concept_id].get('parent')
        while cur is not None:out.append(str(cur));cur=self.concepts[str(cur)].get('parent')
        return tuple(out)
    def required_features(self,concept_id:str)->tuple[str,...]:
        lineage=(*reversed(self.ancestors(concept_id)),concept_id);out=[]
        for item in lineage:
            for feature in self.concepts[item].get('required_features',[]):
                if feature not in out:out.append(str(feature))
        return tuple(out)
    def is_a(self,concept_id:str,parent_id:str)->bool:
        return concept_id==parent_id or parent_id in self.ancestors(concept_id)

def merge_ontologies(ontologies:Iterable[Ontology],*,ontology_id:str,version:str)->Ontology:
    concepts={};relations={};questions=[]
    for o in ontologies:
        for key,value in o.concepts.items():
            if key in concepts and concepts[key]!=value:raise ValueError(f"conflicting concept {key}")
            concepts[key]=value
        for key,value in o.relations.items():
            if key in relations and relations[key]!=value:raise ValueError(f"conflicting relation {key}")
            relations[key]=value
        questions.extend(o.competency_questions)
    result=Ontology(ontology_id,version,concepts,relations,tuple(questions));result.validate();return result

def compose_scene(animal:Ontology,mobile:Ontology,interface:Ontology,*,animal_id:str,mobile_id:str,relation_id:str)->dict[str,Any]:
    if animal_id not in animal.concepts:raise KeyError(animal_id)
    if mobile_id not in mobile.concepts:raise KeyError(mobile_id)
    if relation_id not in interface.relations:raise KeyError(relation_id)
    relation=interface.relations[relation_id]
    allowed=set(relation.get('allowed_object_classes',[]))
    obj_class=mobile.concepts[mobile_id].get('class')
    if allowed and obj_class not in allowed:raise ValueError(f"{relation_id} is not compatible with object class {obj_class}")
    return {'animal':animal_id,'mobile_object':mobile_id,'relation':relation_id,'required_animal_features':animal.required_features(animal_id),'required_object_features':mobile.required_features(mobile_id),'required_interface_features':tuple(relation.get('required_features',[]))}

def abstract_specialised_ontology(value:dict[str,Any],*,new_id:str,parent_mapping:dict[str,str])->dict[str,Any]:
    """Create a reviewable candidate abstraction; never mutates normative ontologies."""
    out={'id':new_id,'version':'candidate-1','status':'candidate-human-review-required','concepts':[],'relations':value.get('relations',[]),'competency_questions':value.get('competency_questions',[])}
    seen=set()
    for concept in value.get('concepts',[]):
        target=parent_mapping.get(concept['id'],concept['id'])
        if target in seen:continue
        seen.add(target);candidate={**concept,'id':target}
        if candidate.get('parent') in parent_mapping:candidate['parent']=parent_mapping[candidate['parent']]
        out['concepts'].append(candidate)
    return out
