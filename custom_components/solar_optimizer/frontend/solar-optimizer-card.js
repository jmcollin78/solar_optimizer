class SolarOptimizerCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      this.innerHTML = `
        <ha-card header="Solar Optimizer">
          <style>
            .container {
              padding: 16px;
              color: var(--primary-text-color);
            }
            .grid-stats {
              display: grid;
              grid-template-columns: repeat(2, 1fr);
              gap: 12px;
              margin-bottom: 16px;
            }
            .stat-box {
              background-color: var(--card-background-color, var(--paper-card-background-color, #fff));
              border: 1px solid var(--divider-color, #e0e0e0);
              border-radius: 8px;
              padding: 10px;
              box-shadow: var(--ha-card-box-shadow, none);
              display: flex;
              flex-direction: column;
              align-items: center;
              text-align: center;
            }
            .stat-title {
              font-size: 0.85em;
              color: var(--secondary-text-color);
              margin-bottom: 4px;
            }
            .stat-value {
              font-size: 1.25em;
              font-weight: bold;
              color: var(--primary-color);
            }
            .device-list {
              display: flex;
              flex-direction: column;
              gap: 12px;
            }
            .device-card {
              background-color: var(--card-background-color, var(--paper-card-background-color, #fff));
              border: 1px solid var(--divider-color, #e0e0e0);
              border-radius: 8px;
              padding: 12px;
              display: flex;
              flex-direction: column;
              gap: 8px;
            }
            .device-header {
              display: flex;
              justify-content: space-between;
              align-items: center;
            }
            .device-name {
              font-weight: bold;
              font-size: 1.05em;
              margin-right: 8px;
            }
            .device-meta {
              display: flex;
              justify-content: space-between;
              font-size: 0.85em;
              color: var(--secondary-text-color);
              flex-wrap: wrap;
              gap: 8px;
            }
            .badge {
              border-radius: 4px;
              padding: 2px 6px;
              font-size: 0.75em;
              font-weight: bold;
              text-transform: uppercase;
              display: inline-block;
              vertical-align: middle;
            }
            .badge-active {
              background-color: var(--success-color, #4caf50);
              color: white;
            }
            .badge-inactive {
              background-color: var(--disabled-text-color, #9e9e9e);
              color: white;
            }
            .badge-waiting {
              background-color: var(--warning-color, #ff9800);
              color: white;
            }
            .power-bar-container {
              background-color: var(--secondary-background-color, #f5f5f5);
              border-radius: 4px;
              height: 8px;
              width: 100%;
              overflow: hidden;
              position: relative;
              margin-top: 4px;
            }
            .power-bar {
              background-color: var(--primary-color);
              height: 100%;
              transition: width 0.3s ease;
            }
            .priority-control {
              display: flex;
              align-items: center;
              gap: 6px;
              font-size: 0.85em;
            }
            .priority-select {
              background: var(--card-background-color, #fff);
              color: var(--primary-text-color);
              border: 1px solid var(--divider-color, #ccc);
              border-radius: 4px;
              padding: 2px 4px;
              cursor: pointer;
            }
          </style>
          <div class="container" id="content"></div>
        </ha-card>
      `;
      this.content = this.querySelector("#content");
    }

    this.updateCard();
  }

  updateCard() {
    if (!this._hass || !this.content) return;

    // Récupérer les entités centrales
    const bestObjective = this._hass.states["sensor.solar_optimizer_best_objective"]?.state || "N/A";
    const totalPower = this._hass.states["sensor.solar_optimizer_total_power"]?.state || "N/A";
    const powerProduction = this._hass.states["sensor.solar_optimizer_power_production"]?.state || "N/A";
    const powerProductionBrut = this._hass.states["sensor.solar_optimizer_power_production_brut"]?.state || "N/A";

    // Récupérer la liste des switch (les Managed Devices) de solar_optimizer
    // Ce sont les switchs switch.solar_optimizer_XX, mais on évite switch.solar_optimizer_enable_XX
    const devicesSwitches = Object.keys(this._hass.states).filter(key =>
      key.startsWith("switch.solar_optimizer_") && !key.startsWith("switch.solar_optimizer_enable_")
    );

    let devicesHtml = "";

    devicesSwitches.forEach(switchKey => {
      const switchStateObj = this._hass.states[switchKey];
      if (!switchStateObj) return;

      const deviceId = switchKey.replace("switch.solar_optimizer_", "");
      const attrs = switchStateObj.attributes;

      const isEnabledObj = this._hass.states[`switch.solar_optimizer_enable_${deviceId}`];
      const isEnabled = isEnabledObj ? (isEnabledObj.state === "on") : (attrs.is_enabled !== false);
      const isActive = switchStateObj.state === "on";
      const isWaiting = attrs.is_waiting === true;
      const todayOnTimeSensor = this._hass.states[`sensor.solar_optimizer_today_on_time_${deviceId}`];
      const todayOnTime = todayOnTimeSensor ? todayOnTimeSensor.state : "0";

      const powerMin = attrs.power_min || 0;
      const powerMax = attrs.power_max || 0;
      const currentPower = attrs.current_power || 0;
      const requestedPower = attrs.requested_power || 0;

      // Priorité
      const prioritySelectKey = `select.solar_optimizer_priority_${deviceId}`;
      const priorityStateObj = this._hass.states[prioritySelectKey];
      const currentPriority = priorityStateObj ? priorityStateObj.state : "";
      const priorityOptions = priorityStateObj && priorityStateObj.attributes.options
        ? priorityStateObj.attributes.options
        : [];

      // Calcul du pourcentage de la barre de puissance
      const totalRange = powerMax - powerMin;
      const powerPercent = totalRange > 0 ? Math.round(((requestedPower - powerMin) / totalRange) * 100) : 0;

      let statusBadge = "";
      if (!isEnabled) {
        statusBadge = `<span class="badge badge-inactive">Désactivé</span>`;
      } else if (isActive) {
        statusBadge = `<span class="badge badge-active">Actif</span>`;
      } else if (isWaiting) {
        statusBadge = `<span class="badge badge-waiting">Attente</span>`;
      } else {
        statusBadge = `<span class="badge badge-inactive">Inactif</span>`;
      }

      // Construction des sélections d'options de priorité
      let prioritySelectHtml = "";
      if (priorityStateObj) {
        prioritySelectHtml = `
          <div class="priority-control">
            <span>Priorité:</span>
            <select class="priority-select" data-entity-id="${prioritySelectKey}">
              ${priorityOptions.map(opt => `
                <option value="${opt}" ${opt === currentPriority ? "selected" : ""}>${opt}</option>
              `).join("")}
            </select>
          </div>
        `;
      }

      // Bouton pour activer / désactiver l'interrupteur
      const switchToggleHtml = `
        <ha-switch
          .checked="${isActive}"
          class="device-toggle"
          data-entity-id="${switchKey}"
        ></ha-switch>
      `;

      devicesHtml += `
        <div class="device-card">
          <div class="device-header">
            <div>
              <span class="device-name">${attrs.friendly_name || deviceId}</span>
              ${statusBadge}
            </div>
            <div>
              ${switchToggleHtml}
            </div>
          </div>
          <div class="device-meta">
            <div>Puissance active: <strong>${currentPower} W</strong> (Dmd: ${requestedPower} W)</div>
            <div>Temps marche: <strong>${todayOnTime} min</strong></div>
          </div>
          ${powerMax > 0 ? `
            <div style="font-size: 0.85em; color: var(--secondary-text-color); margin-top: 4px; display: flex; justify-content: space-between;">
              <span>Min: ${powerMin} W</span>
              <span>Max: ${powerMax} W</span>
            </div>
            <div class="power-bar-container">
              <div class="power-bar" style="width: ${powerPercent}%"></div>
            </div>
          ` : ''}
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
            ${prioritySelectHtml}
            <div style="font-size: 0.85em; color: var(--secondary-text-color);">
              ${attrs.next_date_available ? `Dispo: ${new Date(attrs.next_date_available).toLocaleTimeString()}` : 'Prêt immédiatement'}
            </div>
          </div>
        </div>
      `;
    });

    this.content.innerHTML = `
      <div class="grid-stats">
        <div class="stat-box">
          <span class="stat-title">Prod. Nette</span>
          <span class="stat-value">${powerProduction} W</span>
        </div>
        <div class="stat-box">
          <span class="stat-title">Prod. Brute</span>
          <span class="stat-value">${powerProductionBrut} W</span>
        </div>
        <div class="stat-box">
          <span class="stat-title">Optimisé</span>
          <span class="stat-value">${totalPower} W</span>
        </div>
        <div class="stat-box">
          <span class="stat-title">Objectif Algo</span>
          <span class="stat-value">${typeof bestObjective === 'number' || !isNaN(parseFloat(bestObjective)) ? parseFloat(bestObjective).toFixed(2) : bestObjective}</span>
        </div>
      </div>
      <div>
        <h3 style="margin: 0 0 12px 0; font-size: 1.1em; border-bottom: 1px solid var(--divider-color); padding-bottom: 6px;">Appareils Gérés</h3>
        <div class="device-list">
          ${devicesHtml || '<p style="color: var(--secondary-text-color); text-align: center;">Aucun appareil géré trouvé.</p>'}
        </div>
      </div>
    `;

    // Attacher des écouteurs d'événements pour les dropdowns de priorité
    this.content.querySelectorAll(".priority-select").forEach(select => {
      select.addEventListener("change", (e) => {
        const entityId = e.target.getAttribute("data-entity-id");
        const value = e.target.value;
        this._hass.callService("select", "select_option", {
          entity_id: entityId,
          option: value
        });
      });
    });

    // Attacher des écouteurs d'événements pour les commutateurs (ha-switch)
    this.content.querySelectorAll(".device-toggle").forEach(sw => {
      sw.addEventListener("change", (e) => {
        const entityId = sw.getAttribute("data-entity-id");
        // Lors du clic sur ha-switch, le changement d'état se produit. On lit l'état actuel de son switch dans l'état de HASs
        const isActive = this._hass.states[entityId].state === "on";
        const service = isActive ? "turn_off" : "turn_on";
        this._hass.callService("switch", service, {
          entity_id: entityId
        });
      });
    });
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    return {
      columns: 4,
      rows: 4,
      min_columns: 2,
      min_rows: 2,
    };
  }

  static getConfigElement() {
    return document.createElement("solar-optimizer-card-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:solar-optimizer-card"
    };
  }

  setConfig(config) {
    this._config = config;
  }
}

// Définir l'éditeur visuel de la carte pour Home Assistant
class SolarOptimizerCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
  }

  connectedCallback() {
    this.innerHTML = `
      <div style="padding: 16px; font-family: var(--paper-font-body1_-_font-family); color: var(--primary-text-color);">
        <h3 style="margin-top: 0; color: var(--primary-color);">Solar Optimizer Card</h3>
        <p style="margin-bottom: 8px;">Cette carte est configurée de façon automatique.</p>
        <p style="margin-top: 0; font-size: 0.9em; color: var(--secondary-text-color);">
          Elle scanne et agrège automatiquement les mesures de l'algorithme ainsi que tous vos commutateurs et entités de priorité commençant par <code>solar_optimizer</code>.
        </p>
        <div style="background-color: var(--secondary-background-color); padding: 12px; border-radius: 6px; font-size: 0.85em; border-left: 4px solid var(--primary-color);">
          <strong>Note :</strong> Aucun paramètre optionnel ou configuration YAML supplémentaire n'est nécessaire pour le fonctionnement de cette carte !
        </div>
      </div>
    `;
  }
}

// Enregistrer l'éditeur personnalisé
customElements.define("solar-optimizer-card-editor", SolarOptimizerCardEditor);

// Afficher un log au démarrage dans la console du navigateur avec la version de la carte
console.info(
  `%c  SOLAR-OPTIMIZER-CARD  %c Version 1.0.2 `,
  "color: white; background: #4caf50; font-weight: bold;",
  "color: #4caf50; background: white; font-weight: bold; border: 1px solid #4caf50;"
);

// Enregistrer l'élément personnalisé avec la clé custom de la carte
customElements.define("solar-optimizer-card", SolarOptimizerCard);

// Ajout de la carte au configurateur de cartes de Home Assistant (Lovelace)
window.customCards = window.customCards || [];
window.customCards.push({
  type: "solar-optimizer-card",
  name: "Solar Optimizer Card",
  preview: true,
  description: "Carte interactive pour contrôler et suivre les appareils gérés par le planificateur de charges Solar Optimizer."
});
