import subprocess


def format():
    subprocess.run("black .", shell=True)
    subprocess.run("isort .", shell=True)
    subprocess.run("mypy buildingmotif/*.py tests/*.py migrations/*.py", shell=True)
