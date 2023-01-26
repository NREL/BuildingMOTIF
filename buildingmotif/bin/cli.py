import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import git
import rdflib
import typer
import yaml

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
log = logging.getLogger()
log.setLevel(logging.INFO)

ONTOLOGY_FILE_SUFFIXES = ["ttl", "n3", "ntriples", "xml"]


def resolve(desc: Dict[str, Any]):
    """
    Loads a library from a description in libraries.yml
    """
    if "directory" in desc:
        spath = Path(desc["directory"]).absolute()
        if spath.exists() and spath.is_dir():
            log.info(f"Load local library {spath} (directory)")
            Library.load(directory=str(spath))
        else:
            raise Exception(f"{spath} is not an existing directory")
    elif "ontology" in desc:
        ont = desc["ontology"]
        g = rdflib.Graph().parse(ont, format=rdflib.util.guess_format(ont))
        log.info(f"Load library {ont} as ontology graph")
        Library.load(ontology_graph=g)
    elif "git" in desc:
        repo = desc["git"]["repo"]
        branch = desc["git"]["branch"]
        path = desc["git"]["path"]
        log.info(f"Load library {path} from git repository: {repo}@{branch}")
        with tempfile.TemporaryDirectory() as temp_loc:
            git.Repo.clone_from(repo, temp_loc, branch=branch, depth=1)
            new_path = Path(temp_loc) / Path(path)
            if new_path.is_dir():
                resolve({"directory": new_path})
            else:
                resolve({"ontology": new_path})


@app.command()
def load_libraries(
    db_uri: str = typer.Argument("sqlite:///bmotif.db", envvar="DB_URI"),
    library_manifest_file: str = "libraries.yml",
):
    manifest_path = Path(library_manifest_file)
    log.info(f"Loading buildingmotif libraries listed in {manifest_path}")
    bm = BuildingMOTIF(db_uri)
    bm.setup_tables()
    libraries = yaml.load(open(library_manifest_file, "r"), Loader=yaml.FullLoader)
    for description in libraries:
        resolve(description)
    bm.session.commit()


@app.command()
def serve(
    host: str = "0.0.0.0",
    port: int = 5000,
    db_uri: Optional[str] = typer.Argument(None, envvar="DB_URI"),
):
    from buildingmotif.api.app import create_app

    if db_uri is None:
        import configs as building_motif_configs

        db_uri = building_motif_configs.DB_URI
    webapp = create_app(db_uri)
    webapp.run(host=host, port=port, threaded=False)


# entrypoint is actually defined in pyproject.toml; this is here for convenience/testing
if __name__ == "__main__":
    app()
