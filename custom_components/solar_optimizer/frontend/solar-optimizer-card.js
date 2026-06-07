class SolarOptimizerCard extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.style.display = "block";
    this.style.width = "100%";
    if (!this.content) {
      this.innerHTML = `
        <style>
          solar-optimizer-card {
            display: block !important;
            width: 100% !important;
          }
          solar-optimizer-card ha-card {
            display: block;
            width: 100%;
            box-sizing: border-box;
          }
          solar-optimizer-card .so-card-body {
            display: block;
            padding: 16px;
            color: var(--primary-text-color);
            width: 100%;
            box-sizing: border-box;
          }
          solar-optimizer-card .so-grid-stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 16px;
          }
          solar-optimizer-card .so-stat-box {
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
          solar-optimizer-card .so-stat-title {
            font-size: 0.85em;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
          }
          solar-optimizer-card .so-stat-value {
            font-size: 1.25em;
            font-weight: bold;
            color: var(--primary-color);
          }
          solar-optimizer-card .so-device-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
          }
          solar-optimizer-card .so-device-card {
            background-color: var(--card-background-color, var(--paper-card-background-color, #fff));
            border: 1px solid var(--divider-color, #e0e0e0);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          solar-optimizer-card .so-device-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          solar-optimizer-card .so-device-name {
            font-weight: bold;
            font-size: 1.05em;
            margin-right: 8px;
          }
          solar-optimizer-card .so-device-meta {
            display: flex;
            justify-content: space-between;
            font-size: 0.85em;
            color: var(--secondary-text-color);
            flex-wrap: wrap;
            gap: 8px;
          }
          solar-optimizer-card .so-badge {
            border-radius: 4px;
            padding: 2px 6px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
            display: inline-block;
            vertical-align: middle;
          }
          solar-optimizer-card .so-badge-active {
            background-color: var(--success-color, #4caf50);
            color: white;
          }
          solar-optimizer-card .so-badge-inactive {
            background-color: var(--disabled-text-color, #9e9e9e);
            color: white;
          }
          solar-optimizer-card .so-badge-waiting {
            background-color: var(--warning-color, #ff9800);
            color: white;
          }
          solar-optimizer-card .so-indicators {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 6px;
          }
          solar-optimizer-card .so-indicator {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 0.8em;
            padding: 3px 8px;
            border-radius: 12px;
            border: 1px solid transparent;
          }
          solar-optimizer-card .so-indicator-true {
            background-color: rgba(76, 175, 80, 0.15);
            border-color: var(--success-color, #4caf50);
            color: var(--success-color, #4caf50);
          }
          solar-optimizer-card .so-indicator-false {
            background-color: var(--secondary-background-color, #f5f5f5);
            border-color: var(--divider-color, #ccc);
            color: var(--disabled-text-color, #9e9e9e);
          }
          solar-optimizer-card .so-info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 12px;
            font-size: 0.85em;
            color: var(--secondary-text-color);
            margin-top: 6px;
          }
          solar-optimizer-card .so-info-item {
            display: flex;
            flex-direction: column;
          }
          solar-optimizer-card .so-info-label {
            font-size: 0.85em;
            color: var(--secondary-text-color);
          }
          solar-optimizer-card .so-info-value {
            font-weight: 500;
            color: var(--primary-text-color);
          }
          solar-optimizer-card .so-actions {
            display: flex;
            align-items: center;
            gap: 8px;
          }
          solar-optimizer-card .so-btn {
            border: none;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.8em;
            font-weight: bold;
            cursor: pointer;
            text-transform: uppercase;
            line-height: 1.5;
          }
          solar-optimizer-card .so-btn-start {
            background-color: var(--success-color, #4caf50);
            color: white;
          }
          solar-optimizer-card .so-btn-stop {
            background-color: var(--error-color, #f44336);
            color: white;
          }
          solar-optimizer-card .so-power-bar-container {
            background-color: var(--secondary-background-color, #f5f5f5);
            border-radius: 4px;
            height: 8px;
            width: 100%;
            overflow: hidden;
            position: relative;
            margin-top: 4px;
          }
          solar-optimizer-card .so-power-bar {
            background-color: var(--primary-color);
            height: 100%;
            transition: width 0.3s ease;
          }
          solar-optimizer-card .so-priority-control {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85em;
          }
          solar-optimizer-card .so-priority-select {
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            border: 1px solid var(--divider-color, #ccc);
            border-radius: 4px;
            padding: 2px 4px;
            cursor: pointer;
          }
          solar-optimizer-card .so-collapse-btn {
            background: none;
            border: none;
            cursor: pointer;
            color: var(--secondary-text-color);
            padding: 2px 4px;
            display: flex;
            align-items: center;
            transition: transform 0.2s ease;
          }
          solar-optimizer-card .so-collapse-btn.collapsed {
            transform: rotate(-90deg);
          }
          solar-optimizer-card .so-device-details {
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
          solar-optimizer-card .so-device-details.hidden {
            display: none;
          }
        </style>
        <ha-card header="Solar Optimizer">
          <div class="so-card-body" id="content" style="display:block;width:100%;box-sizing:border-box;padding:16px;"></div>
        </ha-card>
      `;
      this.content = this.querySelector("#content");
    }

    this.updateCard();
  }

  updateCard() {
    if (!this._hass || !this.content) return;

    if (!this._collapsedDevices) this._collapsedDevices = {};

    const lang = this._hass.locale?.language;

    // Formate une date ISO en heure locale avec secondes
    // Si la date est dans le passé, retourne "Disponible immédiatement"
    const formatAvailability = (dateStr) => {
      if (!dateStr) return 'Disponible immédiatement';
      const date = new Date(dateStr);
      if (date <= new Date()) return 'Disponible immédiatement';
      return date.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };

    // Récupérer les entités centrales
    const bestObjective = this._hass.states["sensor.best_objective"]?.state || "N/A";
    const totalPower = this._hass.states["sensor.total_power"]?.state || "N/A";
    const powerProduction = this._hass.states["sensor.power_production"]?.state || "N/A";
    const powerProductionBrut = this._hass.states["sensor.power_production_brut"]?.state || "N/A";

    // Récupérer la liste des switch (les Managed Devices) de solar_optimizer
    const devicesSwitches = Object.keys(this._hass.states).filter(key =>
      key.startsWith("switch.solar_optimizer_") && !key.startsWith("switch.solar_optimizer_enable_")
    );

    // État global : tous pliés ?
    const allCollapsed = devicesSwitches.length > 0 && devicesSwitches.every(k => {
      const id = k.replace("switch.solar_optimizer_", "");
      return this._collapsedDevices[id] === true;
    });

    let devicesHtml = "";

    devicesSwitches.forEach(switchKey => {
      const switchStateObj = this._hass.states[switchKey];
      if (!switchStateObj) return;

      const deviceId = switchKey.replace("switch.solar_optimizer_", "");
      const attrs = switchStateObj.attributes;

      const isEnabledObj = this._hass.states[`switch.enable_solar_optimizer_${deviceId}`];
      const isEnabled = isEnabledObj ? (isEnabledObj.state === "on") : (attrs.is_enabled !== false);
      const isActive = switchStateObj.state === "on";
      const isWaiting = attrs.is_waiting === true;
      const isUsable = attrs.is_usable === true;

      const todayOnTimeSensor = this._hass.states[`sensor.on_time_today_solar_optimizer_${deviceId}`];
      const todayOnTime = todayOnTimeSensor ? todayOnTimeSensor.state : "0";
      const sensorAttrs = todayOnTimeSensor ? todayOnTimeSensor.attributes : {};
      const todayOnTimeHms = sensorAttrs.on_time_hms || todayOnTime;
      const maxOnTimeHms = sensorAttrs.max_on_time_hms || null;
      const shouldBeOForcedOffpeak = sensorAttrs.should_be_forced_offpeak === true;
      const offpeakTime = sensorAttrs.offpeak_time || null;

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
        statusBadge = `<span class="so-badge so-badge-inactive">Désactivé</span>`;
      } else if (isActive) {
        statusBadge = `<span class="so-badge so-badge-active">Actif</span>`;
      } else if (isWaiting) {
        statusBadge = `<span class="so-badge so-badge-waiting">Attente</span>`;
      } else {
        statusBadge = `<span class="so-badge so-badge-inactive">Inactif</span>`;
      }

      // Indicateurs booléens
      const indicatorsHtml = `
        <div class="so-indicators">
          <span class="so-indicator ${isUsable ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${isUsable ? 'mdi:check-circle' : 'mdi:cancel'}" style="--mdi-icon-size: 14px;"></ha-icon>
            Utilisable
          </span>
          <span class="so-indicator ${isWaiting ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${isWaiting ? 'mdi:timer-sand' : 'mdi:timer-sand-empty'}" style="--mdi-icon-size: 14px;"></ha-icon>
            En attente
          </span>
          <span class="so-indicator ${shouldBeOForcedOffpeak ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${shouldBeOForcedOffpeak ? 'mdi:weather-night' : 'mdi:weather-night'}" style="--mdi-icon-size: 14px;"></ha-icon>
            HC forcées
          </span>
        </div>
      `;

      // Construction des sélections d'options de priorité
      let prioritySelectHtml = "";
      if (priorityStateObj) {
        prioritySelectHtml = `
          <div class="so-priority-control">
            <span>Priorité:</span>
            <select class="so-priority-select" data-entity-id="${prioritySelectKey}">
              ${priorityOptions.map(opt => `
                <option value="${opt}" ${opt === currentPriority ? "selected" : ""}>${opt}</option>
              `).join("")}
            </select>
          </div>
        `;
      }

      // Bouton enable/disable
      const enableEntityKey = `switch.enable_solar_optimizer_${deviceId}`;
      const switchToggleHtml = `
        <ha-switch
          class="device-toggle"
          data-entity-id="${enableEntityKey}"
          title="Activer/Désactiver la gestion par l'algorithme"
        ></ha-switch>
      `;

      // Bouton start/stop manuel
      const startStopHtml = `
        <button
          class="so-btn ${isActive ? 'so-btn-stop' : 'so-btn-start'} device-startstop"
          data-entity-id="${switchKey}"
          data-is-active="${isActive}"
          title="${isActive ? 'Arrêter manuellement' : 'Démarrer manuellement'}"
        >${isActive ? 'Stop' : 'Start'}</button>
      `;

      // Infos disponibilité
      const availHtml = `
        <div class="so-info-grid">
          <div class="so-info-item">
            <span class="so-info-label">Prochaine dispo</span>
            <span class="so-info-value">${formatAvailability(attrs.next_date_available)}</span>
          </div>
          ${attrs.can_change_power ? `
          <div class="so-info-item">
            <span class="so-info-label">Dispo puissance</span>
            <span class="so-info-value">${formatAvailability(attrs.next_date_available_power)}</span>
          </div>
          ` : ''}
          ${offpeakTime ? `
          <div class="so-info-item">
            <span class="so-info-label">Heures creuses</span>
            <span class="so-info-value">${offpeakTime}</span>
          </div>
          ` : ''}
          <div class="so-info-item">
            <span class="so-info-label">Temps marche</span>
            <span class="so-info-value">${todayOnTimeHms}${maxOnTimeHms ? ' / ' + maxOnTimeHms : ''}</span>
          </div>
        </div>
      `;

      const isCollapsed = this._collapsedDevices[deviceId] === true;
      const chevronClass = isCollapsed ? 'so-collapse-btn collapsed' : 'so-collapse-btn';

      devicesHtml += `
        <div class="so-device-card" data-device-id="${deviceId}">
          <div class="so-device-header">
            <div style="display:flex;align-items:center;gap:6px;">
              <button class="${chevronClass}" data-collapse-id="${deviceId}" title="${isCollapsed ? 'Déplier' : 'Plier'}">
                <ha-icon icon="mdi:chevron-down" style="--mdi-icon-size: 20px;"></ha-icon>
              </button>
              <span class="so-device-name">${attrs.device_name || deviceId}</span>
              ${statusBadge}
            </div>
            <div class="so-actions">
              ${startStopHtml}
              ${switchToggleHtml}
            </div>
          </div>
          <div class="so-device-details${isCollapsed ? ' hidden' : ''}">
            ${indicatorsHtml}
            <div class="so-device-meta">
              <div>Puissance requise: <strong>${requestedPower} W</strong></div>
              <div>Puissance courante: <strong>${currentPower} W</strong></div>
            </div>
            ${powerMax > 0 ? `
              <div style="font-size: 0.85em; color: var(--secondary-text-color); margin-top: 4px; display: flex; justify-content: space-between;">
                <span>Min: ${powerMin} W</span>
                <span>Max: ${powerMax} W</span>
              </div>
              <div class="so-power-bar-container">
                <div class="so-power-bar" style="width: ${powerPercent}%"></div>
              </div>
            ` : ''}
            ${availHtml}
            <div style="display: flex; justify-content: flex-end; align-items: center; margin-top: 4px;">
              ${prioritySelectHtml}
            </div>
          </div>
        </div>
      `;
    });

    this.content.innerHTML = `
      <div class="so-grid-stats">
        <div class="so-stat-box">
          <span class="so-stat-title">Prod. Nette</span>
          <span class="so-stat-value">${powerProduction} W</span>
        </div>
        <div class="so-stat-box">
          <span class="so-stat-title">Prod. Brute</span>
          <span class="so-stat-value">${powerProductionBrut} W</span>
        </div>
        <div class="so-stat-box">
          <span class="so-stat-title">Optimisé</span>
          <span class="so-stat-value">${totalPower} W</span>
        </div>
        <div class="so-stat-box">
          <span class="so-stat-title">Objectif Algo</span>
          <span class="so-stat-value">${typeof bestObjective === 'number' || !isNaN(parseFloat(bestObjective)) ? parseFloat(bestObjective).toFixed(2) : bestObjective}</span>
        </div>
      </div>
      <div style="display:block;">
        <div style="display:flex; justify-content:flex-start; align-items:center; margin-bottom:12px; border-bottom: 1px solid var(--divider-color); padding-bottom: 6px; gap:6px;">
          <button class="so-collapse-btn so-collapse-all" title="${allCollapsed ? 'Tout déplier' : 'Tout plier'}" style="transform: rotate(${allCollapsed ? '-90deg' : '0deg'});">
            <ha-icon icon="mdi:chevron-down" style="--mdi-icon-size: 20px;"></ha-icon>
          </button>
          <h3 style="margin: 0; font-size: 1.1em;">Appareils Gérés</h3>
        </div>
        <div class="so-device-list">
          ${devicesHtml || '<p style="color: var(--secondary-text-color); text-align: center;">Aucun appareil géré trouvé.</p>'}
        </div>
      </div>
    `;

    // Fixer l'état checked des ha-switch enable
    this.content.querySelectorAll("ha-switch.device-toggle").forEach(sw => {
      const entityId = sw.getAttribute("data-entity-id");
      const stateObj = this._hass.states[entityId];
      if (stateObj) sw.checked = stateObj.state === "on";
    });

    // Attacher les écouteurs pour les dropdowns de priorité
    this.content.querySelectorAll(".so-priority-select").forEach(select => {
      select.addEventListener("change", (e) => {
        const entityId = e.target.getAttribute("data-entity-id");
        const value = e.target.value;
        this._hass.callService("select", "select_option", {
          entity_id: entityId,
          option: value
        });
      });
    });

    // Attacher les écouteurs pour les toggles enable
    this.content.querySelectorAll(".device-toggle").forEach(sw => {
      sw.addEventListener("change", (e) => {
        const entityId = sw.getAttribute("data-entity-id");
        const isActive = this._hass.states[entityId].state === "on";
        const service = isActive ? "turn_off" : "turn_on";
        this._hass.callService("switch", service, { entity_id: entityId });
      });
    });

    // Attacher les écouteurs pour les boutons start/stop
    this.content.querySelectorAll(".device-startstop").forEach(btn => {
      btn.addEventListener("click", () => {
        const entityId = btn.getAttribute("data-entity-id");
        const isActive = btn.getAttribute("data-is-active") === "true";
        const service = isActive ? "turn_off" : "turn_on";
        this._hass.callService("switch", service, { entity_id: entityId });
      });
    });

    // Attacher les écouteurs pour les boutons plier/déplier individuels
    this.content.querySelectorAll(".so-collapse-btn[data-collapse-id]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const deviceId = btn.getAttribute("data-collapse-id");
        this._collapsedDevices[deviceId] = !this._collapsedDevices[deviceId];
        this.updateCard();
      });
    });

    // Attacher l'écouteur pour le chevron global
    const globalBtn = this.content.querySelector(".so-collapse-all");
    if (globalBtn) {
      globalBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        devicesSwitches.forEach(k => {
          const id = k.replace("switch.solar_optimizer_", "");
          this._collapsedDevices[id] = !allCollapsed;
        });
        this.updateCard();
      });
    }
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    return {
      columns: 12,
      rows: "auto",
      min_columns: 3,
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
    if (!this._collapsedDevices) this._collapsedDevices = {};
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
  `%c  SOLAR-OPTIMIZER-CARD  %c Version 1.2.0 `,
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
