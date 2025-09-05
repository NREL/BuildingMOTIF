import argparse
import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, DefaultDict, Dict, List

from rdflib import Graph, Namespace, URIRef

from buildingmotif import BuildingMOTIF, get_building_motif
from buildingmotif.dataclasses import Library, Model, ShapeCollection
from buildingmotif.exports.brick2af.utils import (
    _definition_to_shape,
    _definition_to_sparql,
)

BRICK = Namespace("https://brickschema.org/schema/Brick#")

# build relationship
RELATIONSHIPS = ["hasPoint", "hasPart", "isPointOf", "isPartOf", "feeds"]
RELATIONSHIPS += [f"{r}+" for r in RELATIONSHIPS]
RELATIONSHIPS += [f"{r}?" for r in RELATIONSHIPS]
RELATIONSHIPS += [f"{r}*" for r in RELATIONSHIPS]


def find_original_shape(model, shape_uri: URIRef) -> URIRef:
    """
    From the given property or node shape URI, find *users* of the URI
    until we find the original shape. Users of the URI can be related to this
    URI through sh:property or sh:node.
    """
    original_shape = shape_uri
    while True:
        query = f"""
            SELECT ?shape WHERE {{
                ?shape (sh:or|sh:and|sh:xone)?/sh:property|sh:node {original_shape.n3()} .
            }}
        """
        res = model.get_manifest().graph.query(query)
        if len(res) == 0:
            break
        original_shape = list(res)[0][0]
    return original_shape


def generate_markdown_report(
    grouped_diffs: defaultdict, successful_rules: defaultdict, output_path: str
):
    def format_reason(reason):
        url_pattern = re.compile(r"(http?://[^\s]+)")
        namespace_pattern = re.compile(r"(\w+:\w+)")
        formatted_reason = url_pattern.sub(r"\1", reason)
        formatted_reason = namespace_pattern.sub(r"\1", formatted_reason)
        return formatted_reason

    def format_successful_rules(successful_rules):
        formatted = ""
        for rule, focus_nodes in successful_rules.items():
            formatted += f"## {rule}\n\n"
            formatted += "### Equipment and Point Names\n\n"
            for focus_node, entries in focus_nodes.items():
                entry_dict = {str(k): str(v) for k, v in entries.items()}
                formatted += f"- **Equipment**: {focus_node}\n"
                formatted += f"  - Points: {', '.join(entry_dict.values())}\n\n"
        return formatted

    def format_unsuccessful_rules(grouped_diffs):
        formatted = ""
        for focus_node, reasons in grouped_diffs.items():
            formatted += f"## {focus_node}\n\n"
            formatted += "### Reasons for Failure\n\n"
            for reason in reasons:
                if "missing point" in format_reason(
                    reason
                ) or "BRICK attribute" in format_reason(reason):
                    formatted += f"- **Reason**: {format_reason(reason)}\n\n"
        return formatted

    def generate_summary(successful_rules, grouped_diffs):
        total_successful = len(successful_rules)
        total_failed = len(grouped_diffs)
        return f"# Summary\n\n- Total Successful Rules: {total_successful}\n- Total Failed Rules: {total_failed}\n\n"

    summary = generate_summary(successful_rules, grouped_diffs)
    successful_rules_section = format_successful_rules(successful_rules)
    unsuccessful_rules_section = format_unsuccessful_rules(grouped_diffs)

    markdown_content = f"""
{summary}
## Detailed Successful Rules
{successful_rules_section}

## Detailed Unsuccessful Rules
{unsuccessful_rules_section}
"""

    if output_path != "":
        with open(output_path, "w") as file:
            file.write(markdown_content)
        return None
    else:
        return markdown_content


def generate_html_report(
    grouped_diffs: defaultdict, successful_rules: defaultdict, output_path: str
):
    html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; }}
        h2, h3 {{ color: #333; }}
        .accordion {{
            cursor: pointer; padding: 10px; width: 100%; text-align: left;
            border: none; background-color: #e2e2e2; margin-bottom: 5px; border-radius: 5px;
            transition: background-color 0.2s ease;
        }}
        .active, .accordion:hover {{ background-color: #ccc; }}
        .panel {{
            padding: 0 15px; display: none; background-color: white;
            border: 1px solid #ccc; margin-top: 5px; border-radius: 5px;
        }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ padding: 5px; border-bottom: 1px solid #ddd; }}
        .success {{
            background-color: #d4edda;
        }}
        .failed  {{
            background-color: #f8d7da;
        }}
        .some-success {{
            background-color: #fff3cd;
        }}
    </style>
</head>
<body>

<h2>Validation Report</h2>

<h3>By Rule / Application</h3>
{grouped_by_top_level}

<h3>By Asset</h3>
{grouped_by_focus_node}

<script>
    document.addEventListener("DOMContentLoaded", () => {{
        document.querySelectorAll(".accordion").forEach(btn => {{
            btn.addEventListener("click", () => {{
                btn.classList.toggle("active");
                const panel = btn.nextElementSibling;
                panel.style.display = panel.style.display === "block" ? "none" : "block";
            }});
        }});
    }});
</script>

</body>
</html>
    """

    def format_reason(reason):
        url_pattern = re.compile(r"(https?://[^\s]+)")
        namespace_pattern = re.compile(r"(\w+:\w+)")
        formatted_reason = url_pattern.sub(r"<b><code>\1</code></b>", reason)
        formatted_reason = namespace_pattern.sub(
            r"<b><code>\1</code></b>", formatted_reason
        )
        return formatted_reason

    def format_diffs(grouped_diffs, successful_rules):
        formatted = ""

        # Format successful rules
        for rule, focus_nodes in successful_rules.items():
            formatted += f"<button class='accordion success'>{rule}</button><div class='panel'><ul>"
            for focus_node, entries in focus_nodes.items():
                formatted += f"<li><button class='accordion success'>{focus_node}</button><div class='panel'><ul>"
                entry_dict = {str(k): str(v) for k, v in entries.items()}
                formatted += f"<li class='success'>{entry_dict}</li>"
                formatted += "</ul></div></li>"
            formatted += "</ul></div>"

        # Format failed rules
        for original_shape, focus_nodes in grouped_diffs.items():
            formatted += f"<button class='accordion'>{original_shape} (failed assets)</button><div class='panel'><ul>"
            for focus_node, reasons in focus_nodes.items():
                formatted += f"<li><button class='accordion'>{focus_node}</button><div class='panel'><ul>"
                for reason in reasons:
                    formatted += f"<li>{format_reason(reason)}</li>"
                formatted += "</ul></div></li>"
            formatted += "</ul></div>"
        return formatted

    def format_by_focus_node(grouped_diffs, successful_rules):
        focus_node_dict = defaultdict(dict)

        # Build a dict for successful rules
        for rule, focus_nodes in successful_rules.items():
            for focus_node, entries in focus_nodes.items():
                focus_node_dict[focus_node][rule] = {
                    "entries": entries,
                    "success": True,
                }

        with open("focusnode1.json", "w") as f:
            json.dump(focus_node_dict, f, indent=4)

        # Build a dict for failed rules
        # print(grouped_diffs)
        # NOTE: for some reason it seems like this loop is using the wrong name for a rule when it produces the output
        for rule, focus_nodes in grouped_diffs.items():
            for focus_node, reasons in focus_nodes.items():
                focus_node_dict[focus_node][rule] = {
                    "entries": reasons,
                    "success": False,
                }

        with open("focusnode2.json", "w") as f:
            json.dump(focus_node_dict, f, indent=4)

        formatted = ""
        # save focus node dict to a json file
        with open("focus_node_dict.json", "w") as f:
            json.dump(focus_node_dict, f, indent=4)
        for focus_node, original_shape_dict in focus_node_dict.items():
            all_successful = all(
                data["success"] for data in original_shape_dict.values()
            )
            none_successful = all(
                not data["success"] for data in original_shape_dict.values()
            )
            focus_node_success_class = (
                " success"
                if all_successful
                else " failed" if none_successful else " some-success"
            )

            # print(focus_node, len(original_shape_dict))
            formatted += f"<button class='accordion{focus_node_success_class}'>{focus_node}</button><div class='panel'><ul>"
            for rule, data in original_shape_dict.items():
                success_class = " success" if data["success"] else ""
                formatted += f"<li><button class='accordion{success_class}'>{rule}</button><div class='panel'><ul>"
                # print(f"focus_node: {focus_node} rule: {rule}")
                reason_text = ""
                # If the rule failed, the data['entries'] is a list of reasons. make it an unordered list
                if not data["success"]:
                    reason_text += "<ul>"
                    for reason in data["entries"]:
                        reason_text += f"<li>{format_reason(reason)}</li>"
                    reason_text += "</ul>"
                entry_dict = (
                    {str(k): str(v) for k, v in data["entries"].items()}
                    if data["success"]
                    else reason_text
                )
                entry_class = "success" if data["success"] else "failed"
                formatted += f"<li class='{entry_class}'>{entry_dict}</li>"
                formatted += "</ul></div></li>"
            formatted += "</ul></div>"
        return formatted

    grouped_by_top_level = format_diffs(grouped_diffs, successful_rules)
    grouped_by_focus_node = format_by_focus_node(grouped_diffs, successful_rules)

    html_content = html_template.format(
        grouped_by_top_level=grouped_by_top_level,
        grouped_by_focus_node=grouped_by_focus_node,
    )

    with open(output_path, "w") as file:
        file.write(html_content)


def generate_report(model: Model, rules_definition: dict):
    """
    rules_definition is the content of one of the rules JSON files
    """
    manifest = model.get_manifest()
    NS = Namespace("urn:fdd_rules/")
    for rule, defn in rules_definition.items():
        sg = _definition_to_shape(defn, NS)
        manifest.graph += sg

    successful_rules: DefaultDict[str, DefaultDict[Any, Dict[Any, Any]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for rule, defn in rules_definition.items():
        rule = NS[rule]
        for classname in defn["applicability"]:
            class_ = BRICK[classname]
            for variable in defn["definitions"]:
                # this only queries for 1 variable
                query = _definition_to_sparql(
                    class_, defn["definitions"][variable], variable
                )
                results = model.graph.query(query)
                for row in results.bindings:
                    inst = row["root"]
                    successful_rules[rule][inst].update(row)
        # loop through all 'inst' for this rule. If the length of its dictionary == len(defn["definitions"]), then it's successful
        for inst in deepcopy(successful_rules[rule]):
            if len(successful_rules[rule][inst]) != len(defn["definitions"]) + 1:
                # +1 for the 'root' variable
                del successful_rules[rule][inst]

    validation_report = model.validate(error_on_missing_imports=False)
    grouped_diffs: DefaultDict[Any, DefaultDict[Any, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for focus_node, diffs in validation_report.diffset.items():
        for diff in diffs:
            original_shape = find_original_shape(model, diff.failed_shape)
            grouped_diffs[original_shape][focus_node].append(diff.reason())

    return grouped_diffs, successful_rules, validation_report


def validate(manifest_ttl, model_ttl, rule_json, output_path, output_format):
    # Ensure a BuildingMOTIF instance exists (use in-memory SQLite by default)
    try:
        bm = get_building_motif()
    except Exception:
        bm = BuildingMOTIF("sqlite://")

    here = Path(__file__).resolve()
    # Prefer bundled libraries to avoid network access
    builtin_lib_dir = here.parents[2] / "libraries"  # buildingmotif/libraries
    repo_lib_dir = here.parents[3] / "libraries"  # repo-level libraries

    # Brick + constraints
    Library.load(ontology_graph=str(builtin_lib_dir / "brick" / "Brick.ttl"))
    Library.load(
        ontology_graph=str(builtin_lib_dir / "constraints" / "constraints.ttl")
    )

    # QUDT (local copies under repo-level libraries/qudt)
    qudt_dir = repo_lib_dir / "qudt"
    for qudt_file in [
        qudt_dir / "unit.ttl",
        qudt_dir / "quantitykind.ttl",
        qudt_dir / "VOCAB_QUDT-DIMENSION-VECTORS.ttl",
        qudt_dir / "SCHEMA-FACADE_QUDT.ttl",
    ]:
        if qudt_file.exists():
            Library.load(ontology_graph=str(qudt_file))

    O27 = Namespace("http://example.org/building#")

    model = Model.create(O27)
    model.graph.parse(model_ttl, format="ttl")

    manifest = ShapeCollection.create()
    manifest.graph.parse(manifest_ttl, format="ttl")
    model.update_manifest(manifest)

    successful_rules = defaultdict(lambda: defaultdict(dict))
    # get the SPARQL query for each rule
    with open(rule_json, "r") as f:
        rules = json.load(f)
        for rule, defn in rules.items():
            rule = f"http://example.org/building#{rule}"
            for classname in defn["applicability"]:
                class_ = BRICK[classname]
                for variable in defn["definitions"]:
                    # this only queries for 1 variable
                    query = _definition_to_sparql(
                        class_, defn["definitions"][variable], variable
                    )
                    results = model.graph.query(query)
                    for row in results.bindings:
                        inst = row["root"]
                        successful_rules[rule][inst].update(row)
            # loop through all 'inst' for this rule. If the length of its dictionary == len(defn["definitions"]), then it's successful
            for inst in deepcopy(successful_rules[rule]):
                if (
                    len(successful_rules[rule][inst]) != len(defn["definitions"]) + 1
                ):  # +1 for the 'root' variable
                    del successful_rules[rule][inst]

    res = model.validate(error_on_missing_imports=False)
    try:
        res.report.serialize("output.ttl", format="ttl")
    except Exception:
        pass

    grouped_diffs = defaultdict(lambda: defaultdict(list))
    for focus_node, diffs in res.diffset.items():
        for diff in diffs:
            original_shape = find_original_shape(model, diff.failed_shape)
            ## remove focus_node from the successful rules
            # if original_shape in successful_rules:
            #    if focus_node in successful_rules[original_shape]:
            #        del successful_rules[original_shape][focus_node]
            grouped_diffs[original_shape][focus_node].append(diff.reason())

    # NOTE: everything seems to be in 'grouped_diffs'. One rule gets dropped for some reason...
    # doesn't seem to be the same one each time
    with open("grouped_diffs.json", "w") as f:
        json.dump(grouped_diffs, f, indent=4)
    if output_format == "html":
        generate_html_report(grouped_diffs, successful_rules, output_path + ".html")
    else:
        generate_markdown_report(grouped_diffs, successful_rules, output_path + ".md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate a model against a manifest and output the results as an HTML file."
    )
    parser.add_argument("manifest_ttl", help="Path to the manifest.ttl file")
    parser.add_argument("model_ttl", help="Path to the model.ttl file")
    parser.add_argument("rule_json", help="Path to the rule.json file")
    parser.add_argument("output_path", help="Path to the output file")
    parser.add_argument("format", help="Format of the output file [md, html]")

    args = parser.parse_args()
    validate(
        args.manifest_ttl, args.model_ttl, args.rule_json, args.output_path, args.format
    )


def apply_rules_to_model(model: Model, rules: Dict[str, Any]):
    successful_rules: DefaultDict[str, DefaultDict[Any, Dict[Any, Any]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for rule, defn in rules.items():
        rule = f"http://example.org/building#{rule}"
        for classname in defn["applicability"]:
            class_ = BRICK[classname]
            for variable in defn["definitions"]:
                query = _definition_to_sparql(
                    class_, defn["definitions"][variable], variable
                )

                results = model.graph.query(query)
                for row in results.bindings:
                    inst = row["root"]
                    successful_rules[rule][inst].update(row)

        # loop through all 'inst' for this rule. If the length of its dictionary == len(defn["definitions"]), then it's successful
        for inst in deepcopy(successful_rules[rule]):
            if (
                len(successful_rules[rule][inst]) != len(defn["definitions"]) + 1
            ):  # +1 for the 'root' variable
                del successful_rules[rule][inst]

    return successful_rules


def _successful_rules_to_results_list(
    successful_rules: Dict[str, Dict[Any, Dict[Any, Any]]],
) -> List[Dict[str, Any]]:
    """Convert nested successful_rules mapping into a flat list of result
    objects expected by the AF XML translator."""
    results = []
    for rule_uri, focus_map in successful_rules.items():
        for focus_node, entries in focus_map.items():
            details = {}
            for k, v in entries.items():
                if str(k) == "root":
                    continue
                details[str(k)] = str(v)
            results.append(
                {
                    "success": True,
                    "focus_node": str(focus_node),
                    "rule": str(rule_uri),
                    "details": details,
                }
            )
    return results


def apply_rules_to_model_paths(
    model_ttl_path: str, rules_json_path: str
) -> List[Dict[str, Any]]:
    """Convenience wrapper: load a Model from a TTL path and apply rules from a JSON file."""
    # Ensure BM exists
    try:
        _ = get_building_motif()
    except Exception:
        BuildingMOTIF("sqlite://")

    O27 = Namespace("http://example.org/building#")
    model = Model.create(O27)
    model.graph.parse(model_ttl_path, format="ttl")
    with open(rules_json_path, "r") as f:
        rules = json.load(f)
    successful_rules = apply_rules_to_model(model, rules)
    return _successful_rules_to_results_list(successful_rules)


def get_model_diffs(model):
    validation_context = model.validate(error_on_missing_imports=False)

    grouped_diffs = defaultdict(lambda: defaultdict(list))
    for focus_node, diffs in validation_context.diffset.items():
        for diff in diffs:
            original_shape = find_original_shape(model, diff.failed_shape)
            ## remove focus_node from the successful rules
            # if original_shape in successful_rules:
            #    if focus_node in successful_rules[original_shape]:
            #        del successful_rules[original_shape][focus_node]
            grouped_diffs[original_shape][focus_node].append(diff.reason())

    return grouped_diffs


def get_report(grouped_diffs: defaultdict, successful_rules: defaultdict):
    return generate_markdown_report(grouped_diffs, successful_rules, "")
