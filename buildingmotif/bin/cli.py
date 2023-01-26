import logging
import shutil
from pathlib import Path
from typing import Optional

import typer

from buildingmotif import BuildingMOTIF
from buildingmotif.dataclasses import Library

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]})
log = logging.getLogger()
log.setLevel(logging.INFO)

ONTOLOGY_FILE_SUFFIXES = ["ttl", "n3", "ntriples", "xml"]


@app.command()
def load_libraries(
    db_uri: str = typer.Argument("sqlite:///bmotif.db", envvar="DB_URI"),
    library_manifest_file: str = "libraries.yml",
):
    """
    Loads libraries from the provided YML file into the BuildingMOTIF instance at $DB_URI
    or whatever is in 'configs.py'. Use 'get_default_libraries_yml' for the format of
    the expected libraries.yml file
    """
    manifest_path = Path(library_manifest_file)
    log.info(f"Loading buildingmotif libraries listed in {manifest_path}")
    bm = BuildingMOTIF(db_uri)
    bm.setup_tables()
    bm.setup_tables()
    Library.load_from_libraries_yml(library_manifest_file)
    bm.session.commit()


@app.command()
def get_default_libraries_yml():
    """
    Creates a default 'libraries.default.yml' file in the current directory
    that can be edited and used with buildingmotif
    """
    default_file = (
        Path(__file__).resolve().parents[1] / "resources" / "libraries.default.yml"
    )
    shutil.copyfile(default_file, "libraries.default.yml")
    print("libraries.default.yml created in the current directory")


@app.command()
def serve(
    host: str = "localhost",
    port: int = 5000,
    db_uri: Optional[str] = typer.Argument(None, envvar="DB_URI"),
):
    """
    Serves the BuildingMOTIF API on the indicated host:port
    """
    from buildingmotif.api.app import create_app

    if db_uri is None:
        import configs as building_motif_configs

        db_uri = building_motif_configs.DB_URI
    webapp = create_app(db_uri)
    webapp.run(host=host, port=port, threaded=False)


# entrypoint is actually defined in pyproject.toml; this is here for convenience/testing
if __name__ == "__main__":
    app()
