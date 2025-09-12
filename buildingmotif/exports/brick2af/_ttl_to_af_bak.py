import json
import os
import uuid
from collections import defaultdict

from rdflib import RDF, RDFS, Graph, Namespace
from utils import xml_dump

import afxml as af
from buildingmotif import BuildingMOTIF


class Translator:
    def __init__(self) -> None:
        self.init_graph()
        self.read_config_file()

        self.datas = {}
        self.afddrules = None
        self.manifest = None
        self.bmmodel = None
        self.validation = True
        self.templates = {"Analysis": {}, "Element": {}, "Attribute": {}}

    def init_graph(self):
        """
        Initialize an RDF graph and set up its namespaces
        """
        bm = BuildingMOTIF("sqlite://", shacl_engine="topquadrant")
        self.graph = Graph()
        self.af_root = af.AF()
        self.BRICK = Namespace("https://brickschema.org/schema/Brick#")
        self.EX = Namespace("http://example.org/building#")

    def read_config_file(self):
        """
        Read a configuration file for default PI Server URIs
        """
        if not os.path.exists("../pi_config.json"):
            raise NameError("Cannot find pi_config.json")
        else:
            with open("../pi_config.json", "rb") as f:
                config = json.load(f)
        self.piexportpath = config["piexportpath"]
        self.piimportpath = config["piimportpath"]
        self.defaultserver = config["server"]
        self.defaultdatabase = config["database"]
        self.defaulturi = f"\\{self.defaultserver}\{self.defaultdatabase}"

    def export_pi_database(self, database, outpath):
        """
        Call the OSISoft PI executable with the path as an argument.
         - This method is only used for testing purposes
        """
        args = ["/A", "/U"]  # export all references  # export unique IDs
        cmd = f"{self.piexportpath} \\{self.defaultserver}\{self.defaultdatabase} /File:{outpath} {args}"
        os.system(cmd)

    def import_pi_database(self, database, inpath):
        """
        Call the OSISoft PI executable with the path as an argument.
         - This method is only used for testing purposes
        """
        args = [
            "/A",  # Auto check-in. Disable to avoid overriding data by accident.
            "/C",  # Allow new elements
            "/U",  # Allow updates
            "/CC",  # create categories that are referenced but do not exist
            "/G",  # Generate unique names
            # "/CE"
        ]
        cmd = f"{self.piimportpath} \\{self.defaultserver}\{self.defaultdatabase} /File:{inpath} {args}"
        os.system(cmd)

    def load(self, ttlpath, merge=None):
        """
        Load a Turtle file into the graph and optionally merge additional files.

        Args:
            self (object): The instance of the class containing the graph.
            ttlpath (str): Path to the TTL (Turtle) file that will be parsed and loaded into the graph.
            merge (list or str, optional): Specifies additional files to be merged with the main file.
                If a string, it is treated as a single path to be parsed.
                If a list, each element in the list should be a path string, all of which will be parsed and merged into the graph.
                Defaults to None.

        Returns:
            None
        """
        self.graph.parse(ttlpath)
        if merge is not None:
            if isinstance(merge, str):
                self.graph.parse(merge)
            else:
                for path in merge:
                    self.graph.parse(path)

    def add_rules(self, rulespath, validatedpath):
        """
        Load and store rule data from JSON files.

        Args:
            self (object): The instance of the class containing the rule data.
            rulespath (str): Path to a JSON file that contains the rules in dictionary format.
            validatedpath (str): Path to a JSON file that contains the validated rules in dictionary format.

        Returns:
            None
        """
        with open(rulespath, "r") as f:
            self.afddrules = json.load(f)
        with open(validatedpath, "r") as f:
            self.validrules = json.load(f)

    def inspect(self, subject=None, predicate=None, object=None):
        """
        Inspect triples in the graph based on optional criteria.

        Args:
            self (object): The instance of the class containing the RDF graph.
            subject (str or None, optional): The subject of the triples to search for. If a namespace is included, it should be prefixed with the
                namespace (e.g., 'ns1:subject'). Defaults to None.
            predicate (str or None, optional): The predicate of the triples to search for. This can be either a predefined predicate in the graph's
                namespace or a custom predicate string. If set to 'type', it will use RDF['type'] as the predicate. Defaults to None.
            object (str or None, optional): The object of the triples to search for. If a namespace is included, it should be prefixed with the
                namespace (e.g., 'ns1:object'). Defaults to None.

        Returns:
            list: A list of tuples representing the found triples that match the criteria. Each tuple contains (subject, predicate, object).
        """
        results = []
        if predicate == "type":
            predicate = RDF["type"]
        else:
            predicate = self.BRICK[predicate]
        for ns_prefix, namespace in self.graph.namespaces():
            if subject is not None and namespace not in subject:
                nsub = namespace + subject
            else:
                nsub = subject
            if object is not None and namespace not in object:
                nob = namespace + object
            else:
                nob = object
            for s, o, p in self.graph.triples((nsub, predicate, nob)):
                results.append((s, o, p))
        return results

    def get_rule_bindings(self, firstttl):
        """
        Retrieves instances of Brick classes from a given model based on defined rules and their applicability.

        Args:
            self (object): The instance of the class containing this method.
            firstttl (str): A string representing the RDF data in TTL format to be parsed into a graph model.

        Returns:
            dict: A dictionary where keys are rule names and values are dictionaries mapping instances to their properties, based on the defined
            rules.

        Raises:
            AssertionError: If no rules have been loaded before calling this method.

        This method does the following:
        1. Parses the provided TTL data into a graph model.
        2. Asserts that rules are available; if not, raises an error.
        3. Initializes an empty dictionary to store rule bindings.
        4. Iterates over each defined rule and its applicability in `self.afddrules`.
        5. For each applicable class, constructs a SPARQL query to find instances of that class.
        6. Executes the SPARQL query against the graph model and collects results.
        7. Filters out instances with incomplete property sets.
        8. Stores the filtered instances in the rules dictionary under their respective rule names.
        """
        model = Graph()
        model.parse(firstttl)

        assert (
            self.afddrules is not None
        ), "No rules found. Please load rules before creating the AF tree."

        rules = {}

        # loop through all defns in self.afddrules
        for rule, defn in self.afddrules.items():
            # get the 'applicability' field (list of Brick classes) and find all instances of those classes in the model
            instances = defaultdict(dict)
            for classname in defn["applicability"]:
                class_ = self.BRICK[classname]
                for variable in defn["definitions"]:
                    query = self.definition_to_sparql(
                        class_, defn["definitions"][variable], variable
                    )
                    results = model.query(query)
                    for row in results.bindings:
                        row = {str(k): v for k, v in row.items()}
                        inst = row["root"]
                        instances[inst].update(row)
            # find all instances which have less than len(defn["definitions"])+1 keys and remove them
            instances = {
                k: v
                for k, v in instances.items()
                if len(v) == len(defn["definitions"]) + 1
            }
            rules[rule] = dict(instances)
        return rules

    def createAFTree(self, firstttl, outpath, merge=None):
        """
        Create an Asset Framework (AF) tree from a given RDF/TTL file and save it as an XML file.

        Args:
            self: The instance of the class containing this method.
            firstttl (str): Path to the initial RDF/TTL file used to create the AF tree.
            outpath (str): Path where the resulting XML file will be saved.
            merge (bool, optional): Flag indicating whether to merge new data with an existing graph. Defaults to None.

        Returns:
            af.AF: The newly created AF object representing the AF tree.
        """
        # Load the initial RDF/TTL file into the graph database
        self.load(firstttl, merge)

        # Initialize new AF object and dictionaries for tracking elements and ignored items
        newaf = af.AF()
        afdict = {}
        ignored = []

        # Iterate over all triples in the graph
        for subj, pred, obj in self.graph.triples((None, None, None)):
            if pred not in [RDF["type"], RDFS["label"]]:
                # Determine types of subject and object if they are not already known
                subjtype = None
                objtype = None
                for _, _, bricktype in self.graph.triples((subj, RDF["type"], None)):
                    subjtype = bricktype.split("#")[-1]
                for _, _, bricktype in self.graph.triples((obj, RDF["type"], None)):
                    objtype = bricktype.split("#")[-1]

                # Create or update AF elements for subject and object if not already in afdict
                if subj is not None and subj not in afdict:
                    name = subj.split("#")[-1]
                    for _, _, label in self.graph.triples((subj, RDFS["label"], None)):
                        name = label
                    newel = af.AFElement(af.Name(name))
                    newel += af.id(uuid.uuid4().hex)
                    try:
                        newel += af.Description(subjtype)
                    except:
                        newel += af.Description("No description")
                    analyses = self.addAnalysis(subj)
                    if analyses:
                        for a in analyses:
                            newel += a
                    afdict[subj] = newel

                if obj is not None and obj not in afdict:
                    name = obj.split("#")[-1]
                    for _, _, label in self.graph.triples((obj, RDFS["label"], None)):
                        name = label
                    newel = af.AFElement(af.Name(name))
                    newel += af.id(uuid.uuid4().hex)
                    try:
                        newel += af.Description(objtype)
                    except:
                        newel += af.Description("No description")
                    analyses = self.addAnalysis(obj)
                    if analyses:
                        for a in analyses:
                            newel += a
                    afdict[obj] = newel

                # Handle specific predicates by adding points or setting reference types
                if pred in [
                    self.BRICK["hasTag"],
                    self.BRICK["Max_Limit"],
                    self.BRICK["Min_limit"],
                    self.BRICK["hasUnit"],
                    self.BRICK["lastKnownValue"],
                ]:
                    ignored.append(afdict[obj])
                elif pred == self.BRICK["isTagOf"]:
                    ignored.append(afdict[subj])

                if pred in [self.BRICK["hasPoint"], self.BRICK["isPointOf"]]:
                    afdict, ignored = self.addpoint(
                        subj, pred, obj, subjtype, objtype, ignored, afdict
                    )

                if pred == self.BRICK["hasPart"] or pred == self.BRICK["isLocationOf"]:
                    afdict[obj]["ReferenceType"] = "Parent-Child"
                    afdict[subj] += afdict[obj]
                elif (
                    pred == self.BRICK["isPartOf"] or pred == self.BRICK["hasLocation"]
                ):
                    afdict[subj]["ReferenceType"] = "Parent-Child"
                    afdict[obj] += afdict[subj]

        # Create an AF database and add elements except those marked for ignoring
        db = af.AFDatabase(af.Name(self.defaultdatabase))
        for key in afdict:
            if afdict[key] not in ignored:
                try:
                    if afdict[key]["ReferenceType"] != "Parent-Child":
                        db += afdict[key]
                except:
                    db += afdict[key]

        # Add the database to the new AF object and set metadata
        newaf += db
        newaf["PISystem"] = self.defaultserver
        newaf["ExportedType"] = "AFDatabase"
        newaf["Identity"] = "Database"
        newaf["Database"] = self.defaultdatabase

        # Save the AF tree to the specified output path, updating if merge is enabled
        if merge is not None:
            xml_dump(newaf, file=outpath.replace(".xml", "_updated.xml"))
            self.graph.serialize(
                outpath.replace(".xml", "_updated.ttl"), format="turtle"
            )
        else:
            xml_dump(newaf, file=outpath)

        return newaf

    def addpoint(self, s, p, o, stype, otype, ign, afd):
        """
        Add a point to the AF tree based on specific conditions.

        Args:
            self: The instance of the class containing this method.
            s (any): The subject node in the RDF graph.
            p (any): The predicate representing the relationship between nodes.
            o (any): The object node in the RDF graph.
            stype (str): Type or description of the subject node.
            otype (str): Type or description of the object node.
            ign (list): List of elements to be ignored during AF tree creation.
            afd (dict): Dictionary containing created AF elements for each node in the graph.

        Returns:
            tuple: A tuple containing the updated dictionary `afd` and the list `ign`.
        """
        if p == self.BRICK["hasPoint"]:
            # Handle 'hasPoint' relationship by creating an attribute for the object node
            otype = otype if otype is not None else ""
            attr = af.AFAttribute(af.Name(o.split("#")[-1]), af.Description(otype))
            uom, aftype, val = self.getUOMs(o)
            if uom is not None:
                if uom != "":
                    attr += af.DefaultUOM(uom)
                attr += af.Type(aftype)
                vattr = af.Value(val, type=aftype)

            # Mark the object node for ignoring and add it to the ignored list
            ign.append(afd[o])

            # Add a tag or value attribute based on whether a unit of measure is available
            nattr, ispt = self.addTag(s, o, attr)
            if not ispt and uom is not None:
                nattr += vattr

            # Set the reference type for the object node as "Parent-Child"
            afd[o]["ReferenceType"] = "Parent-Child"

            # Add the attribute to the subject node and link it with the object node
            afd[s] += nattr
            afd[s] += afd[o]

        elif p == self.BRICK["isPointOf"]:
            # Handle 'isPointOf' relationship by creating an attribute for the subject node
            stype = stype if stype is not None else ""
            attr = af.AFAttribute(af.Name(s.split("#")[-1]), af.Description(stype))
            uom, aftype, val = self.getUOMs(s)
            if uom is not None:
                if uom != "":
                    attr += af.DefaultUOM(uom)
                attr += af.Type(aftype)
                vattr = af.Value(val, type=aftype)

            # Mark the subject node for ignoring and add it to the ignored list
            ign.append(afd[s])

            # Add a tag or value attribute based on whether a unit of measure is available
            nattr, ispt = self.addTag(o, s, attr)
            if not ispt and uom is not None:
                nattr += vattr

            # Set the reference type for the subject node as "Parent-Child"
            afd[s]["ReferenceType"] = "Parent-Child"

            # Add the attribute to the object node and link it with the subject node
            afd[o] += nattr
            afd[o] += afd[s]

        return afd, ign

    def addTag(self, parent, point, attr):
        """
        Add a tag to an AF element based on whether it has a PI Point associated with it.

        Args:
            self: The instance of the class containing this method.
            parent (any): The node in the graph that potentially contains the tag.
            point (any): The node in the graph for which to find and add tags.
            attr (af.AFAttribute): The attribute object where the tag will be added if found.

        Returns:
            tuple: A tuple containing the updated `attr` object and a boolean indicating whether a PI Point was associated (`ispt`).
        """
        ispt = False  # Initialize flag to check if a PI Point is associated

        # Iterate over all tags associated with the point node
        for tagname in self.graph.objects(
            subject=point, predicate=self.BRICK["hasTag"]
        ):
            if not ispt:
                # Add data reference and configuration string to the attribute object
                attr += af.DataReference("PI Point")
                attr += af.ConfigString(
                    f"{self.findFullPath(tagname)};RelativeTime=-2y"
                )
                ispt = True  # Set flag to indicate a PI Point was found

        return attr, ispt

    def getUOMs(self, obj):
        """
        Find the correct PI AFXML unit of measure in the config file
        """
        for __, __, unit in self.graph.triples((obj, self.BRICK["hasUnit"], None)):
            unit = unit.split("#")[-1]
            uom = self.units[unit].uom
            aftype = self.units[unit].aftype
            value = self.units[unit].value
        try:
            return uom, aftype, value
        except UnboundLocalError:
            print(f"No units of measure available for {obj}. Skipping.")
            return None, None, None

    def addAnalysis(self, candidate):
        """
        Adds a new analysis based on the given candidate and valid rules.

        Args:
            candidate (str): The identifier of the candidate node.

        Returns:
            list: A list of newly created AFAnalysis objects.
        """

        all_analyses = []
        for (
            key,
            inner,
        ) in self.validrules.items():  # key = top-level URI, inner = dict of nodes
            for (
                node_uri,
                node_obj,
            ) in (
                inner.items()
            ):  # node_uri = 'http://example.org#vav1', node_obj = {...}
                if node_obj.get("root") == str(candidate):
                    rulename = key.split("#")[-1]
                    aname = f"{candidate.split('#')[-1]} {rulename}"
                    newanalysis = af.AFAnalysis(af.Name(aname))
                    newanalysis += af.Status("Enabled")
                    parent_path = self.findFullPath(self.getParent(candidate))
                    newanalysis += af.Target(af.AFElementRef(parent_path))
                    newanalysis += af.AFAnalysisCategoryRef("Analytics")
                    analysisrule = af.AFAnalysisRule()
                    analysisrule += af.AFPlugIn("PerformanceEquation")
                    perfstr = self.match_equation(
                        node_obj, self.afddrules[rulename]["output"]
                    )
                    analysisrule += af.ConfigString(perfstr)
                    analysisrule += af.VariableMapping(f"Output||{aname};")
                    newanalysis += analysisrule
                    newanalysis += af.AFTimeRule(
                        af.AFPlugIn(self.afddrules[rulename]["aftimerule"]),
                        af.ConfigString(
                            f"Frequency={self.afddrules[rulename]['frequency']}"
                        ),
                    )
                    all_analyses.append(newanalysis)
        if all_analyses:
            print(all_analyses)
        return all_analyses

    def match_equation(self, details, output):
        """
        Replaces placeholders in the output with actual values from details.

        Args:
            details (dict): A dictionary containing detailed information.
            output (str): The initial string which may contain placeholders.

        Returns:
            str: The output string after replacing placeholders.
        """
        for metapoint in details.keys():
            output = output.replace(metapoint, details[metapoint].split("#")[-1])
        return output

    def getParent(self, obj):
        """
        Retrieves the parent node of a given object based on graph relationships.

        Args:
            obj (str): The identifier of the current node.

        Returns:
            str: The identifier of the parent node.
        """
        for s, p, o in self.graph.triples((None, None, None)):
            if (
                p
                in [
                    self.BRICK["hasPart"],
                    self.BRICK["hasPoint"],
                    self.BRICK["isLocationOf"],
                ]
                and o == obj
            ):
                return s
            elif (
                p
                in [
                    self.BRICK["isPartOf"],
                    self.BRICK["isPointOf"],
                    self.BRICK["hasLocation"],
                ]
                and s == obj
            ):
                return o
        return obj

    def findFullPath(self, obj):
        """
        Constructs the full path from the root to a given node using graph relationships.

        Args:
            obj (str): The identifier of the current node.

        Returns:
            str: The full path as a string.
        """

        objpath = obj.split("#")[-1]
        for _, _, label in self.graph.triples((obj, RDFS["label"], None)):
            objpath = label
        while True:
            parent = ""
            for s, p, o in self.graph.triples((obj, None, None)):
                if p in [
                    self.BRICK["isPartOf"],
                    self.BRICK["hasLocation"],
                    self.BRICK["isPointOf"],
                ]:
                    if obj != o:
                        obj = o
                        name = o.split("#")[-1]
                        for _, _, label in self.graph.triples((o, RDFS["label"], None)):
                            name = label
                        parent = name
            for s, p, o in self.graph.triples((None, None, obj)):
                if p in [
                    self.BRICK["hasPart"],
                    self.BRICK["isLocationOf"],
                    self.BRICK["hasPoint"],
                ]:
                    if obj != s:
                        obj = s
                        name = s.split("#")[-1]
                        for _, _, label in self.graph.triples((s, RDFS["label"], None)):
                            name = label
                        parent = name

            if parent == "":
                break
            else:
                objpath = parent + "\\" + objpath
        return objpath
