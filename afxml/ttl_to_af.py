import json, os, uuid
from collections import defaultdict
from rdflib import RDF, RDFS, Graph, Namespace
from utils import xml_dump
import afxml as af
from buildingmotif import BuildingMOTIF

class Translator:
    def __init__(self):
        self.init_graph()
        self.read_config_file()
        self.datas = {}
        self.afddrules = self.validrules = None
        self.manifest = self.bmmodel = None
        self.validation = True
        self.templates = {'Analysis': {}, 'Element': {}, 'Attribute': {}}

    def init_graph(self):
        bm = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        self.graph = Graph()
        self.af_root = af.AF()
        self.BRICK = Namespace('https://brickschema.org/schema/Brick#')
        self.EX = Namespace('http://example.org/building#')

    def read_config_file(self):
        cfg = "../pi_config.json"
        if not os.path.exists(cfg):
            raise NameError("Cannot find pi_config.json")
        with open(cfg, 'r') as f:
            c = json.load(f)
        self.piexportpath = c["piexportpath"]
        self.piimportpath = c["piimportpath"]
        self.defaultserver = c["server"]
        self.defaultdatabase = c["database"]
        self.defaulturi = f"\\{self.defaultserver}\\{self.defaultdatabase}"

    def export_pi_database(self, database, outpath):
        args = "/A /U"
        cmd = f"{self.piexportpath} \\{self.defaultserver}\\{self.defaultdatabase} /File:{outpath} {args}"
        os.system(cmd)

    def import_pi_database(self, database, inpath):
        args = "/A /C /U /CC /G"
        cmd = f"{self.piimportpath} \\{self.defaultserver}\\{self.defaultdatabase} /File:{inpath} {args}"
        os.system(cmd)

    def load(self, ttlpath, merge=None):
        self.graph.parse(ttlpath)
        if merge:
            if isinstance(merge, str):
                self.graph.parse(merge)
            else:
                for p in merge:
                    self.graph.parse(p)

    def add_rules(self, rulespath, validatedpath):
        with open(rulespath) as f:
            self.afddrules = json.load(f)
        with open(validatedpath) as f:
            self.validrules = json.load(f)

    def inspect(self, subject=None, predicate=None, object=None):
        results = []
        pred = RDF["type"] if predicate == "type" else self.BRICK[predicate] if predicate else None
        for ns_prefix, ns in self.graph.namespaces():
            nsub = (ns + subject) if subject and ns not in subject else subject
            nob = (ns + object) if object and ns not in object else object
            for s, o, p in self.graph.triples((nsub, pred, nob)):
                results.append((s, o, p))
        return results

    def get_rule_bindings(self, firstttl):
        model = Graph()
        model.parse(firstttl)
        assert self.afddrules is not None, "No rules found."
        rules = {}
        for rule, defn in self.afddrules.items():
            instances = defaultdict(dict)
            for classname in defn["applicability"]:
                cls = self.BRICK[classname]
                for var, dfn in defn["definitions"].items():
                    q = self.definition_to_sparql(cls, dfn, var)
                    for row in model.query(q).bindings:
                        row = {str(k): v for k, v in row.items()}
                        instances[row["root"]].update(row)
            instances = {k: v for k, v in instances.items() if len(v) == len(defn["definitions"]) + 1}
            rules[rule] = dict(instances)
        return rules

    def createAFTree(self, firstttl, outpath, merge=None):
        self.load(firstttl, merge)
        newaf = af.AF()
        afdict = {}
        ignored = []

        for subj, pred, obj in self.graph.triples((None, None, None)):
            if pred in (RDF["type"], RDFS["label"]):
                continue

            def get_type(node):
                for _, _, t in self.graph.triples((node, RDF["type"], None)):
                    return str(t).split("#")[-1]
                return None

            def make_element(node):
                if node in afdict or node is None:
                    return
                name = node.split("#")[-1]
                for _, _, label in self.graph.triples((node, RDFS["label"], None)):
                    name = label
                el = af.AFElement(af.Name(name))
                el += af.id(uuid.uuid4().hex)
                el += (af.Description(get_type(node)) if get_type(node) else af.Description("No description"))
                analyses = self.addAnalysis(node)
                if analyses:
                    for a in analyses:
                        el += a
                afdict[node] = el

            subjtype, objtype = get_type(subj), get_type(obj)
            make_element(subj); make_element(obj)

            if pred in (self.BRICK["hasTag"], self.BRICK["Max_Limit"], self.BRICK["Min_limit"],
                        self.BRICK["hasUnit"], self.BRICK["lastKnownValue"]):
                ignored.append(afdict.get(obj))
            elif pred == self.BRICK["isTagOf"]:
                ignored.append(afdict.get(subj))

            if pred in (self.BRICK["hasPoint"], self.BRICK["isPointOf"]):
                afdict, ignored = self.addpoint(subj, pred, obj, subjtype, objtype, ignored, afdict)

            if pred in (self.BRICK["hasPart"], self.BRICK["isLocationOf"]):
                afdict[obj]["ReferenceType"] = "Parent-Child"
                afdict[subj] += afdict[obj]
            elif pred in (self.BRICK["isPartOf"], self.BRICK["hasLocation"]):
                afdict[subj]["ReferenceType"] = "Parent-Child"
                afdict[obj] += afdict[subj]

        db = af.AFDatabase(af.Name(self.defaultdatabase))
        for key, val in afdict.items():
            if val not in ignored:
                try:
                    if val["ReferenceType"] != "Parent-Child":
                        db += val
                except KeyError:
                    db += val

        newaf += db
        newaf["PISystem"] = self.defaultserver
        newaf["ExportedType"] = "AFDatabase"
        newaf["Identity"] = "Database"
        newaf["Database"] = self.defaultdatabase

        if merge:
            xml_dump(newaf, file=outpath.replace(".xml", "_updated.xml"))
            self.graph.serialize(outpath.replace(".xml", "_updated.ttl"), format="turtle")
        else:
            xml_dump(newaf, file=outpath)

        return newaf
    
    def addpoint(self, s, p, o, stype, otype, ign, afd):
        if p == self.BRICK["hasPoint"]:
            otype = otype or ""
            attr = af.AFAttribute(af.Name(o.split("#")[-1]), af.Description(otype))
            uom, aftype, val = self.getUOMs(o)
            if uom is not None:
                if uom != "": attr += af.DefaultUOM(uom)
                attr += af.Type(aftype)
                vattr = af.Value(val, type=aftype)
            ign.append(afd[o])
            nattr, ispt = self.addTag(s, o, attr)
            if not ispt and uom is not None: nattr += vattr
            afd[o]["ReferenceType"] = "Parent-Child"
            afd[s] += nattr
            afd[s] += afd[o]

        elif p == self.BRICK["isPointOf"]:
            stype = stype or ""
            attr = af.AFAttribute(af.Name(s.split("#")[-1]), af.Description(stype))
            uom, aftype, val = self.getUOMs(s)
            if uom is not None:
                if uom != "": attr += af.DefaultUOM(uom)
                attr += af.Type(aftype)
                vattr = af.Value(val, type=aftype)
            ign.append(afd[s])
            nattr, ispt = self.addTag(o, s, attr)
            if not ispt and uom is not None: nattr += vattr
            afd[s]["ReferenceType"] = "Parent-Child"
            afd[o] += nattr
            afd[o] += afd[s]

        return afd, ign

    def addTag(self, parent, point, attr):
        ispt = False
        for tagname in self.graph.objects(subject=point, predicate=self.BRICK["hasTag"]):
            if not ispt:
                attr += af.DataReference("PI Point")
                attr += af.ConfigString(f"{self.findFullPath(tagname)};RelativeTime=-2y")
                ispt = True
        return attr, ispt

    def getUOMs(self, obj):
        for _, _, unit in self.graph.triples((obj, self.BRICK["hasUnit"], None)):
            unit = str(unit).split('#')[-1]
            u = self.units[unit].uom
            t = self.units[unit].aftype
            v = self.units[unit].value
        try:
            return u, t, v
        except UnboundLocalError:
            print(f"No units of measure available for {obj}. Skipping.")
            return None, None, None

    def addAnalysis(self, candidate):
        all_analyses = []
        for key, inner in self.validrules.items():
            for node_uri, node_obj in inner.items():
                if node_obj.get("root") == str(candidate):
                    rulename = key.split("#")[-1]
                    aname = f"{candidate.split('#')[-1]} {rulename}"
                    na = af.AFAnalysis(af.Name(aname))
                    na += af.Status("Enabled")
                    parent_path = self.findFullPath(self.getParent(candidate))
                    na += af.Target(af.AFElementRef(parent_path))
                    na += af.AFAnalysisCategoryRef("Analytics")
                    ar = af.AFAnalysisRule()
                    ar += af.AFPlugIn("PerformanceEquation")
                    perfstr = self.match_equation(node_obj, self.afddrules[rulename]["output"])
                    ar += af.ConfigString(perfstr)
                    ar += af.VariableMapping(f"Output||{aname};")
                    na += ar
                    na += af.AFTimeRule(
                        af.AFPlugIn(self.afddrules[rulename]["aftimerule"]),
                        af.ConfigString(f"Frequency={self.afddrules[rulename]['frequency']}")
                    )
                    all_analyses.append(na)
        if all_analyses:
            print(all_analyses)
        return all_analyses

    def match_equation(self, details, output):
        for k in details.keys():
            output = output.replace(k, details[k].split("#")[-1])
        return output

    def getParent(self, obj):
        for s, p, o in self.graph.triples((None, None, None)):
            if p in (self.BRICK["hasPart"], self.BRICK["hasPoint"], self.BRICK["isLocationOf"]) and o == obj:
                return s
            if p in (self.BRICK["isPartOf"], self.BRICK["isPointOf"], self.BRICK["hasLocation"]) and s == obj:
                return o
        return obj

    def findFullPath(self, obj):
        objpath = obj.split("#")[-1]
        for _, _, label in self.graph.triples((obj, RDFS["label"], None)):
            objpath = label
        while True:
            parent = ""
            for s, p, o in self.graph.triples((obj, None, None)):
                if p in (self.BRICK["isPartOf"], self.BRICK["hasLocation"], self.BRICK["isPointOf"]) and obj != o:
                    obj = o
                    name = o.split("#")[-1]
                    for _, _, lab in self.graph.triples((o, RDFS["label"], None)):
                        name = lab
                    parent = name
            for s, p, o in self.graph.triples((None, None, obj)):
                if p in (self.BRICK["hasPart"], self.BRICK["isLocationOf"], self.BRICK["hasPoint"]) and obj != s:
                    obj = s
                    name = s.split("#")[-1]
                    for _, _, lab in self.graph.triples((s, RDFS["label"], None)):
                        name = lab
                    parent = name
            if parent == "":
                break
            objpath = parent + "\\" + objpath
        return objpath