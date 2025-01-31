from lxml import etree
from xmldiff import main, formatting
from buildingmotif.namespaces import BRICK
import random, string
from rdflib import Namespace

BRICK = Namespace('https://brickschema.org/schema/Brick#')

# build relationship
RELATIONSHIPS = ["hasPoint", "hasPart", "isPointOf", "isPartOf", "feeds"]
RELATIONSHIPS += [f"{r}+" for r in RELATIONSHIPS]
RELATIONSHIPS += [f"{r}?" for r in RELATIONSHIPS]
RELATIONSHIPS += [f"{r}*" for r in RELATIONSHIPS]

def pretty_print(element):
    """Simple printing of an xml element from the bsync library"""
    print(etree.tostring(element.toxml(), pretty_print=True).decode('utf-8'))
    
def xml_dump(root_element, file="example1.xml"):
    """Write the element to the specified file"""
    doctype = '<?xml version="1.0" encoding="UTF-8"?>'
    as_etree = root_element.toxml()
    #as_etree.set("xmlns", "http://buildingsync.net/schemas/bedes-auc/2019")
    output = etree.tostring(as_etree, doctype=doctype, pretty_print=True)
    with open(file, 'wb+') as f:
        f.write(output)
        return True
    
def xml_compare(left, right):
    file_diff = main.diff_files(left, right, diff_options={'ratio_mode':'faster'},
                       formatter=formatting.XMLFormatter())
    return file_diff

def _definition_to_sparql(self, classname, defn, variable):
    """
    defn is a JSON structure like this:
        "Chilled_Water_Valve_Command": {
            "choice": [
                {"hasPoint": "Chilled_Water_Valve_Command"},
                {"hasPart": {"Chilled_Water_Valve": {"hasPoint": "Valve_Command"}}}
            ]
        },
    This method turns this into a SPARQL query which retrieves values into a variable
    named whatever the top-level key is
    """
    query = f"""SELECT ?root ?{variable} WHERE {{ 
        ?root rdf:type {classname.n3()} .
        {_sparql_recurse(defn, variable, hook="root")} 
    }}"""
    return query

def _gensym(self):
    """generates random sparql variable name"""
    return 'var' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def _sparql_recurse(self, defn, varname, hook=None):
    """
    Generate a SPARQL query recursively based on the definition provided.
    
    Args:
        self (object): The instance of the class containing the RDF graph and BRICK definitions.
        defn (dict or str): The definition to be converted into a SPARQL query. If it's a string, it represents a type. If it's a dictionary, it 
            can contain relationships or other types.
        varname (str): The base variable name for the current level of recursion in the SPARQL query.
        hook (str or None, optional): A placeholder variable to be used as the subject of certain relationships. Defaults to None.
    
    Returns:
        str: The generated SPARQL query string.
    """
    relationships = ["hasPoint", "hasPart", "isPointOf", "isPartOf", "feeds"]
    # add '+' versions to relationships
    relationships += [f"{r}+" for r in relationships]
    # add '?' versions to relationships
    relationships += [f"{r}?" for r in relationships]
    # add '*' versions to relationships
    relationships += [f"{r}*" for r in relationships]
    query = ""
    if isinstance(defn, str):
        if hook is not None and hook != varname:
            # then varname is hasPoint from hook
            query += f"?{hook} brick:hasPoint ?{varname} .\n"
        query += f"?{varname} rdf:type {BRICK[defn].n3()} .\n"
        return query
    for key, value in defn.items():
        if key == "choice":
            # UNION of the list of descriptions in 'value'
            query += "{\n"
            query += " UNION ".join([f"{{ {_sparql_recurse(v, varname, hook=hook)} }}\n" for v in value])
            query += "}\n"
        elif key in relationships:
            # start with a random var
            subject_var = hook or _gensym()
            
            # get the relationship name
            suffix = key[-1] if key[-1] in ["+", "?", "*"] else ""
            relname = key.replace("+", "").replace("?", "").replace("*", "")
            # get the relationship type
            reltype = BRICK[relname]
            
            # the object of the relationship is one of two things:
            # - varname, if 'value' is a type
            # - a new variable, if 'value' is a dict
            if isinstance(value, str):
                object_var = varname
            else:
                object_var = _gensym()

            # add the relationship to the query
            query += f"?{subject_var} {reltype.n3()}{suffix} ?{object_var} .\n"
            # add the object to the query
            query += _sparql_recurse(value, varname, hook=object_var)
        else: # key represents a type
            subject_var = hook or _gensym()
            query += f"?{subject_var} rdf:type {BRICK[key].n3()} .\n"
            # value should be a dictionary
            query += _sparql_recurse(value, varname, hook=subject_var)

    return query

