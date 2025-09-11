## Translator — Developer Manual

---

### Purpose
The Translator class converts a Brick RDF/Turtle model into an AF (PI AF) representation and supports PI import/export operations, rule-based analysis attachment, and simple inspections of the RDF graph.

---

### High-level flow (order of operations)
1. Instantiate Translator: __init__ -> init_graph -> read_config_file sets up required objects, namespaces, paths, and default state.
2. Optionally call add_rules to load AFDD rules and validated rule bindings from JSON files.
3. Use load to parse one or more TTL/TTL-like files into the RDFLib graph.
4. Use get_rule_bindings to evaluate rules against a TTL model and produce binding dictionaries for rule instances.
5. Use createAFTree to:
   - Load the TTL(s) (calls load).
   - Walk all RDF triples and build AF elements/attributes/analyses according to Brick predicates.
   - Use helper methods addpoint, addTag, addAnalysis, getUOMs, match_equation, getParent, findFullPath.
   - Build an af.AFDatabase and output XML (via xml_dump) and optionally write an updated TTL when merge is used.
6. Optionally use export_pi_database and import_pi_database to run external PI export/import commands using configured paths.
7. Use inspect to query the RDF graph for triples matching optional subject/predicate/object.

---

### Key components and responsibilities

- Translator.__init__()
  - Calls init_graph and read_config_file.
  - Initializes internal structures:
    - graph: RDFLib Graph
    - af_root: af.AF() root container
    - BRICK and EX namespaces
    - datas, afddrules, validrules, manifest, bmmodel, validation flag
    - templates for Analysis/Element/Attribute

- init_graph()
  - Creates BuildingMOTIF instance (BM) (connection string "sqlite://", shacl_engine="topquadrant").
  - Initializes RDF graph, AF root, and Brick & example Namespaces.

- read_config_file()
  - Loads "../pi_config.json". Expects keys:
    - piexportpath, piimportpath, server, database
  - Sets piexportpath, piimportpath, defaultserver, defaultdatabase, defaulturi.
  - Raises NameError if config file missing.

- export_pi_database(database, outpath)
  - Builds and runs a shell command to export PI database using configured piexportpath and server/database.
  - Uses os.system to execute.

- import_pi_database(database, inpath)
  - Builds and runs shell command to import PI database using piimportpath and server/database.
  - Uses os.system to execute.

- load(ttlpath, merge=None)
  - Parses ttlpath into self.graph.
  - If merge provided, parses merge (string or iterable of paths) as additional TTLs.

- add_rules(rulespath, validatedpath)
  - Loads JSON files:
    - afddrules: rule definitions (AFDD)
    - validrules: validated rule bindings

- inspect(subject=None, predicate=None, object=None)
  - Returns list of matching triples from self.graph.
  - If predicate == "type", uses RDF.type; otherwise resolves predicate to BRICK[predicate] when provided.
  - Attempts to resolve subject/object by prepending namespaces when needed (iterates graph namespaces).

- get_rule_bindings(firstttl)
  - Loads firstttl into a temporary Graph.
  - Requires self.afddrules to be loaded.
  - For each rule in afddrules:
    - For each applicable classname, builds SPARQL queries from definitions (via definition_to_sparql).
    - Runs queries against the model, collects bindings, groups them by root.
    - Filters instances to ensure a full set of definition bindings present.
  - Returns dict mapping rule -> instances (per-root binding dicts).
  - Note: depends on definition_to_sparql existing in class (not included in provided code).

- createAFTree(firstttl, outpath, merge=None)
  - Loads TTL(s) (calls load).
  - Iterates all triples; skips RDF.type and RDFS.label when building AF.
  - get_type(node): returns the local name of RDF type or None.
  - make_element(node): creates af.AFElement with Name (node local name or RDFS label), id, Description (type or fallback), and adds analyses returned by addAnalysis. Stores element in afdict keyed by full node URI.
  - Handles Brick predicates:
    - Predicates that mark tags/units/limits are appended to ignored list (so points/units are not exported as top-level AF elements).
    - When encountering hasPoint/isPointOf → delegates to addpoint to create AFAttributes and DataReferences.
    - For hasPart/isLocationOf and isPartOf/hasLocation → establishes Parent-Child relationships by adding child element into parent (using AF element addition).
  - Builds an af.AFDatabase named by defaultdatabase and adds all non-ignored elements (excluding those flagged ReferenceType == "Parent-Child" unless not set).
  - Packages newaf with metadata (PISystem, ExportedType, Identity, Database).
  - Writes AF XML via xml_dump to outpath (if merge True, writes updated XML and updated TTL).
  - Returns the newaf object.

- addpoint(s, p, o, stype, otype, ign, afd)
  - Creates af.AFAttribute for the point (either o or s depending on predicate direction).
  - Uses getUOMs to fetch unit-of-measure, attribute type, and default value.
  - Calls addTag to detect PI Point tags and add DataReference/ConfigString if present.
  - Marks point element as ignored and sets ReferenceType = "Parent-Child".
  - Adds attribute and child element into parent element (afd mapping).
  - Returns updated afd and ign lists.

- addTag(parent, point, attr)
  - Checks graph for hasTag from point. If present, adds DataReference("PI Point") and ConfigString with full path and RelativeTime suffix.
  - findFullPath used to compute full PI path.
  - Returns (modified attribute, is_point_flag).

- getUOMs(obj)
  - Looks for hasUnit triple on obj and maps the unit local name to a units entry (self.units expected).
  - Returns (uom, aftype, value) or (None, None, None) and prints a warning when no unit found.
  - Note: requires self.units to be initialized elsewhere.

- addAnalysis(candidate)
  - Iterates self.validrules and for any validated binding whose root matches candidate:
    - Creates an AFAnalysis with Name "{candidate local} {ruleName}", enabled, with Target set to the parent element path (findFullPath(getParent(candidate))).
    - Builds AFAnalysisRule with AFPlugIn "PerformanceEquation", a ConfigString built by match_equation using details and afddrules output, and VariableMapping for Output.
    - Adds AFTimeRule using afddrules[rulename]["aftimerule"] and frequency.
  - Returns list of AFAnalysis objects (or empty list).

- match_equation(details, output)
  - Replaces keys found in details with their local names (after '#') in output to form a performance equation string.

- getParent(obj)
  - Traverses the graph to find a parent by inspecting triples where obj appears as object or subject with part/point/location relations.
  - Returns the immediate parent or obj if none found.

- findFullPath(obj)
  - Builds a backslash-delimited hierarchical name by walking up the graph following part/location/point relations.
  - Uses RDFS.label when available to use human-friendly names.
  - Returns a string path like "Building\Floor\Room\PointName".

---

### External dependencies
- utils.xml_dump: function to serialize af.AF objects to AF XML.
- afxml (imported as af): library exposing types like AF, AFElement, AFAttribute, AFDatabase, AFAnalysis, AFAnalysisRule, AFPlugIn, ConfigString, etc. Methods/operators used:
  - af.AFElement(af.Name(...)); element += subcomponents; element[...] for metadata
  - af.AFDatabase(af.Name(...)) and adding elements with +=
  - af.AF etc. The code assumes these classes support addition and indexing semantics shown.
- buildingmotif.BuildingMOTIF: used to instantiate a validator/modeler (BM) — side effects not used later.
- self.units: expected mapping of unit local names to objects with attributes uom, aftype, value. Must be set before createAFTree / addpoint calls.
- definition_to_sparql: method referenced from get_rule_bindings but not present in the provided code — must exist elsewhere in class or mixin.
- pi_config.json: expected in parent directory with keys piexportpath, piimportpath, server, database.

---

### Notable behavior, side effects, and error handling
- read_config_file raises NameError if config file is missing.
- get_rule_bindings asserts afddrules is loaded; otherwise raises AssertionError.
- getUOMs prints a warning and returns (None, None, None) if unit mapping missing.
- createAFTree writes files (XML + optionally updated TTL). If merge=True it writes two outputs: outpath_updated.xml and outpath_updated.ttl.
- add_rules expects valid JSON structure; createAFTree expects valid rules/validrules to be consistent when addAnalysis is used.
- The code mutates afdict entries by setting metadata keys like "ReferenceType"; these are plain dict-like operations on AF element objects (assumes af element supports dict-style item assignment).
- inspect attempts namespace concatenation heuristics which may produce unexpected URIs if subject/object already contain namespaces.

---

### Extension points & recommendations for maintainers
- Provide/verify definition_to_sparql implementation and self.units initialization.
- Add explicit exception handling around os.system or switch to subprocess.run for better control and error reporting.
- Validate that af element objects support dict-style metadata; consider using explicit attributes rather than arbitrary dict keys.
- Add unit tests for:
  - TTL->AF mapping of hasPoint/isPointOf relationships.
  - Parent-child relationships (hasPart/isPartOf).
  - getUOMs behavior when units missing.
  - addAnalysis creation when validrules/afddrules present.
- Consider supporting named graph parsing and clearer namespace handling in inspect (avoid blind concatenation).
- If performance is a concern, iterating graph.triples((None,None,None)) is O(n) for each call; limit scope or use queries where possible.
- Sanitize external command parameters (paths/filenames) to avoid injection via config.

---

### Quick mapping: Brick predicates → behavior
| Brick predicate | Effect in code |
|---|---|
| hasPoint / isPointOf | Create AFAttribute for point, possibly add DataReference/ConfigString for PI Point; link attribute to parent element (addpoint) |
| hasTag / isTagOf / Max_Limit / Min_limit / hasUnit / lastKnownValue | Mark related nodes to be ignored when exporting top-level AF elements |
| hasPart / isLocationOf | Add object as child of subject; mark ReferenceType="Parent-Child" |
| isPartOf / hasLocation | Add subject as child of object; mark ReferenceType="Parent-Child" |

---

### Important developer notes
- The code relies on the structure of afddrules and validrules JSON files — maintain schema compatibility.
- findFullPath and getParent implement graph traversal used to compute PI paths and analysis targets — changing Brick predicate usage will require updates here.