# Developer Quick Start Guide

The fastest way to get up and running with a BuildingMOTIF developer environment is through the provided devcontainer.
The BuildingMOTIF dev container image (located at `ghcr.io/nrel/buildingmotif/devcontainer`) comes with all of the python
depencencies currently on the `develop` branch pre-installed. It also includes an install of node and angular for app
development. Additionally the container includes the Docker CLI which will attempt to interface with the docker engine
running on the host.

## Prerequisites
1. [Docker](https://docs.docker.com/engine/install/)
2. A supporting tool like [Visual Studio Code](https://code.visualstudio.com/) or the [Dev Container CLI](https://github.com/devcontainers/cli)

## Setup

The following sections provide instructions on using the devcontainer with several common setups.

All setup instructions assume you have already cloned the BuildingMOTIF repository to your local machine.

## VS Code
1. Open the BuildingMOTIF repository in VS Code.
1. A notification will appear saying that the "Folder contains a Dev Container configuration file"
1. Click "Reopen in Container"
1. VS Code will reopen, download the container and open BuildingMOTIF inside of it

## Dev Container CLI
1. Navigate to BuildingMOTIF
1. Start the devcontainer `devcontainer up --workspace-folder .`
1. Enter the devcontainer `devcontainer exec --workspace-folder . /bin/bash`

## Other Tools
More information about tools that support dev containers can be found on the [Dev Containers website](https://containers.dev/supporting).
