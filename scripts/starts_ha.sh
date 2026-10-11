#!/bin/bash

set -e
set -x

cd "$(dirname "$0")/.."
pwd

# Create config dir if not present
if [[ ! -d "${PWD}/config" ]]; then
    mkdir -p "${PWD}/config"
    # Add defaults configuration
    hass --config "${PWD}/config" --script ensure_config
fi

# Overwrite configuration.yaml if provided
if [ -f ${PWD}/.devcontainer/configuration.yaml ]; then
    rm -f ${PWD}/config/configuration.yaml
    ln -s ${PWD}/.devcontainer/configuration.yaml ${PWD}/config/configuration.yaml
fi

# Development Lovelace dashboards are versioned in .devcontainer. Home Assistant
# replaces storage files atomically, so synchronize them before startup and when
# the process exits instead of using symbolic links.
echo "Installation des dashboards de développement..."
python3 "${PWD}/scripts/manage_lovelace_dashboards.py" install

# Set the path to custom_components
## This let's us have the structure we want <root>/custom_components/integration_blueprint
## while at the same time have Home Assistant configuration inside <root>/config
## without resulting to symlinks.
export PYTHONPATH="${PYTHONPATH}:${PWD}/custom_components"

## Link custom_components into config
# rm -f ${PWD}/config/custom_components
# ln -s ${PWD}/custom_components ${PWD}/config/

# Start Home Assistant and persist dashboard changes made through the UI.
hass --config "${PWD}/config" --debug &
hass_pid=$!

watch_dashboards() {
    python3 "${PWD}/scripts/manage_lovelace_dashboards.py" watch
}

sync_dashboards() {
    kill "${dashboard_sync_pid}" 2>/dev/null || true
    wait "${dashboard_sync_pid}" 2>/dev/null || true
    echo "Sauvegarde des dashboards de développement..."
    python3 "${PWD}/scripts/manage_lovelace_dashboards.py" sync
}

watch_dashboards &
dashboard_sync_pid=$!
echo "Synchronisation des dashboards déclenchée à chaque modification."

trap sync_dashboards EXIT
wait "${hass_pid}"