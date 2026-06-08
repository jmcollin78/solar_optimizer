const TRANSLATIONS = {
  fr: {
    disabled: 'Désactivé',
    active: 'Actif',
    waiting: 'Attente',
    inactive: 'Inactif',
    manual: 'Manuel',
    usable: 'Utilisable',
    waitingIndicator: 'En attente',
    offpeakForced: 'HC forcées',
    priority: 'Priorité',
    enableTitle: 'Activer/Désactiver la gestion par l\'algorithme',
    stopManually: 'Arrêter manuellement',
    startManually: 'Démarrer manuellement',
    stop: 'Stop',
    start: 'Start',
    nextAvailable: 'Prochaine dispo',
    powerAvailable: 'Dispo puissance',
    offpeakHours: 'Heures creuses',
    batterySocThreshold: 'Seuil SOC batterie',
    onTime: 'Temps marche',
    resetTitle: 'Remettre à zéro le temps de marche',
    reset: 'Reset',
    timedDurationSelect: 'Durée forcée',
    timedRemaining: 'Reste',
    timedDuration1h: '1h',
    timedDuration4h: '4h',
    timedDuration12h: '12h',
    timedDuration24h: '24h',
    expand: 'Déplier',
    collapse: 'Plier',
    expandAll: 'Tout déplier',
    collapseAll: 'Tout plier',
    managedDevices: 'Appareils Gérés',
    noDevices: 'Aucun appareil géré trouvé.',
    requiredPower: 'Puissance requise',
    smoothedProduction: 'Production lissée',
    netConsumption: 'Consommation nette',
    batterySoc: 'SOC Batterie',
    totalOptimized: 'Total Optimisé',
    algoObjective: 'Objectif Algo',
    availableNow: 'Disponible immédiatement',
    historyBar: 'Historique d\'activation',
    powerHistory: 'Puissance courante',
    editorHistoryHours: 'Durée de l\'historique (heures)',
    editorAutoConfig: 'Cette carte est configurée de façon automatique.',
    editorDesc: 'Elle scanne et agrège automatiquement les mesures de l\'algorithme ainsi que tous vos commutateurs et entités de priorité commençant par <code>solar_optimizer</code>.',
    editorNote: '<strong>Note :</strong> Aucun paramètre optionnel ou configuration YAML supplémentaire n\'est nécessaire pour le fonctionnement de cette carte !',
    editorSecondaryInfoDesc: 'Affichez des informations personnalisées par appareil (supporte <code>states()</code> et <code>state_attr()</code>) :',
    cardDescription: 'Carte interactive pour contrôler et suivre les appareils gérés par le planificateur de charges Solar Optimizer.',
  },
  en: {
    disabled: 'Disabled',
    active: 'Active',
    waiting: 'Waiting',
    inactive: 'Inactive',
    manual: 'Manual',
    usable: 'Usable',
    waitingIndicator: 'Waiting',
    offpeakForced: 'Off-peak forced',
    priority: 'Priority',
    enableTitle: 'Enable/Disable algorithm management',
    stopManually: 'Stop manually',
    startManually: 'Start manually',
    stop: 'Stop',
    start: 'Start',
    nextAvailable: 'Next available',
    powerAvailable: 'Power available',
    offpeakHours: 'Off-peak hours',
    batterySocThreshold: 'Battery SOC threshold',
    onTime: 'On time',
    resetTitle: 'Reset on-time counter',
    reset: 'Reset',
    timedDurationSelect: 'Forced duration',
    timedRemaining: 'Remaining',
    timedDuration1h: '1h',
    timedDuration4h: '4h',
    timedDuration12h: '12h',
    timedDuration24h: '24h',
    expand: 'Expand',
    collapse: 'Collapse',
    expandAll: 'Expand all',
    collapseAll: 'Collapse all',
    managedDevices: 'Managed Devices',
    noDevices: 'No managed device found.',
    requiredPower: 'Required power',
    smoothedProduction: 'Smoothed production',
    netConsumption: 'Net consumption',
    batterySoc: 'Battery SOC',
    totalOptimized: 'Total optimized',
    algoObjective: 'Algo objective',
    availableNow: 'Available immediately',
    historyBar: 'Activation history',
    powerHistory: 'Current power',
    editorHistoryHours: 'History duration (hours)',
    editorAutoConfig: 'This card is automatically configured.',
    editorDesc: 'It automatically scans and aggregates algorithm measurements and all your switches and priority entities starting with <code>solar_optimizer</code>.',
    editorNote: '<strong>Note:</strong> No optional parameters or additional YAML configuration are needed for this card to work!',
    editorSecondaryInfoDesc: 'Display custom info per device (supports <code>states()</code> and <code>state_attr()</code>):',
    cardDescription: 'Interactive card to control and monitor devices managed by the Solar Optimizer load scheduler.',
  }
};

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
            grid-template-columns: repeat(3, 1fr);
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
            box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.10));
            border-left-width: 4px;
            border-left-style: solid;
          }
          solar-optimizer-card .so-device-card-active {
            border-left-color: var(--success-color, #4caf50);
            background-color: color-mix(in srgb, var(--success-color, #4caf50) 5%, var(--card-background-color, #fff));
          }
          solar-optimizer-card .so-device-card-waiting {
            border-left-color: var(--warning-color, #ff9800);
            background-color: color-mix(in srgb, var(--warning-color, #ff9800) 5%, var(--card-background-color, #fff));
          }
          solar-optimizer-card .so-device-card-disabled {
            background-color: color-mix(in srgb, var(--disabled-text-color, #9e9e9e) 5%, var(--card-background-color, #fff));
          }
          solar-optimizer-card .so-device-card-inactive {
            border-left-color: var(--divider-color, #e0e0e0);
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
          solar-optimizer-card .so-badge-manual {
            background-color: #f59e0b;
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
          solar-optimizer-card .so-btn-reset {
            background-color: transparent;
            color: var(--secondary-text-color);
            border: 1px solid var(--divider-color, #ccc);
          }
          solar-optimizer-card .so-duration-select {
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            border: 1px solid var(--divider-color, #ccc);
            border-radius: 4px;
            padding: 2px 4px;
            font-size: 0.8em;
            cursor: pointer;
            max-width: 72px;
          }
          solar-optimizer-card .so-timed-remaining {
            font-size: 0.78em;
            font-weight: bold;
            color: var(--warning-color, #ff9800);
            border: 1px solid var(--warning-color, #ff9800);
            border-radius: 4px;
            padding: 2px 7px;
            white-space: nowrap;
            background: color-mix(in srgb, var(--warning-color, #ff9800) 12%, var(--card-background-color, #fff));
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
          solar-optimizer-card .so-history-bar-wrapper {
            margin-top: 6px;
          }
          solar-optimizer-card .so-history-bar-container {
            display: flex;
            background-color: var(--secondary-background-color, #e0e0e0);
            border-radius: 4px;
            height: 8px;
            width: 100%;
            overflow: hidden;
          }
          solar-optimizer-card .so-history-segment-on {
            background-color: var(--history-state-on-color, #fdd835);
            height: 100%;
            flex-shrink: 0;
          }
          solar-optimizer-card .so-history-segment-off {
            background-color: var(--secondary-background-color, #e0e0e0);
            height: 100%;
            flex-shrink: 0;
          }
          solar-optimizer-card .so-history-bar-label {
            font-size: 0.72em;
            color: var(--secondary-text-color);
            margin-top: 2px;
            text-align: right;
            opacity: 0.8;
          }
          solar-optimizer-card .so-power-history-svg {
            display: block;
            width: 100%;
            height: 40px;
            border-radius: 4px;
            overflow: hidden;
          }
          solar-optimizer-card .so-secondary-info {
            font-size: 0.82em;
            color: var(--secondary-text-color);
            background-color: var(--secondary-background-color, #f5f5f5);
            border-radius: 6px;
            padding: 4px 8px;
            display: flex;
            align-items: center;
            gap: 6px;
          }
        </style>
        <ha-card header="Solar Optimizer">
          <div class="so-card-body" id="content" style="display:block;width:100%;box-sizing:border-box;padding:16px;"></div>
        </ha-card>
      `;
      this.content = this.querySelector("#content");
    }

    // Debounce pour éviter les rebuilds DOM pendant un clic (race condition avec HA)
    if (this._updateTimer) clearTimeout(this._updateTimer);
    this._updateTimer = setTimeout(() => this.updateCard(), 50);
  }

  updateCard() {
    if (!this._hass || !this.content) return;

    if (!this._collapsedDevices) this._collapsedDevices = {};

    const lang = this._hass.locale?.language;
    const isFr = lang && lang.toLowerCase().startsWith('fr');
    const t = (key) => TRANSLATIONS[isFr ? 'fr' : 'en'][key] || key;

    // Formate une date ISO en heure locale avec secondes
    // Si la date est dans le passé, retourne le texte de disponibilité immédiate
    const formatAvailability = (dateStr) => {
      if (!dateStr) return t('availableNow');
      const date = new Date(dateStr);
      if (date <= new Date()) return t('availableNow');
      return date.toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    };

    // Recherche robuste d'un sensor SO central : essai direct, puis avec préfixe,
    // puis scan des states (gère les entity_id générés par HA avec préfixe d'instance)
    const getSoState = (idx) => {
      if (this._hass.states[`sensor.${idx}`])
        return this._hass.states[`sensor.${idx}`].state;
      if (this._hass.states[`sensor.solar_optimizer_${idx}`])
        return this._hass.states[`sensor.solar_optimizer_${idx}`].state;
      const found = Object.keys(this._hass.states).find(k =>
        k.startsWith('sensor.') && k.includes('solar_optimizer') && k.endsWith(`_${idx}`)
      );
      return found ? this._hass.states[found].state : 'N/A';
    };

    // Récupérer les entités centrales
    const bestObjective = getSoState('best_objective');
    const totalPower = getSoState('total_power');
    const powerProduction = getSoState('power_production');
    const powerConsumption = getSoState('power_consumption');
    const batterySoc = getSoState('battery_soc');

    // Récupérer la liste des switch (les Managed Devices) de solar_optimizer
    const devicesSwitches = Object.keys(this._hass.states).filter(key =>
      key.startsWith("switch.solar_optimizer_") && !key.startsWith("switch.solar_optimizer_enable_")
    );

    // État global : tous pliés ?
    const allCollapsed = devicesSwitches.length > 0 && devicesSwitches.every(k => {
      const id = k.replace("switch.solar_optimizer_", "");
      return this._collapsedDevices[id] !== false;
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
      // Si l'équipement est éteint, on force la puissance affichée à 0
      // pour éviter qu'une valeur résiduelle dans les attributs ne remplisse la barre
      const currentPower = isActive ? (attrs.current_power || 0) : 0;
      const requestedPower = attrs.requested_power || 0;

      // Priorité
      const prioritySelectKey = `select.solar_optimizer_priority_${deviceId}`;
      const priorityStateObj = this._hass.states[prioritySelectKey];
      const currentPriority = priorityStateObj ? priorityStateObj.state : "";
      const priorityOptions = priorityStateObj && priorityStateObj.attributes.options
        ? priorityStateObj.attributes.options
        : [];

      // Calcul du pourcentage de la barre de puissance (clampé entre 0 et 100)
      const totalRange = powerMax - powerMin;
      const rawPercent = totalRange > 0 ? ((currentPower - powerMin) / totalRange) * 100 : (currentPower > 0 ? 100 : 0);
      const powerPercent = Math.min(100, Math.max(0, Math.round(rawPercent)));

      let statusBadge = "";
      if (!isEnabled && isActive) {
        statusBadge = `<span class="so-badge so-badge-manual">${t('manual')}</span>`;
      } else if (!isEnabled) {
        statusBadge = `<span class="so-badge so-badge-inactive">${t('disabled')}</span>`;
      } else if (isActive) {
        statusBadge = `<span class="so-badge so-badge-active">${t('active')}</span>`;
      } else if (isWaiting) {
        statusBadge = `<span class="so-badge so-badge-waiting">${t('waiting')}</span>`;
      } else {
        statusBadge = `<span class="so-badge so-badge-inactive">${t('inactive')}</span>`;
      }

      // Informations secondaires configurées par l'utilisateur
      const secondaryInfoTemplate = this._config?.secondary_info?.[deviceId] || null;
      const secondaryInfoValue = secondaryInfoTemplate ? this._evaluateTemplate(secondaryInfoTemplate) : null;
      const secondaryInfoHtml = secondaryInfoValue
        ? `<div class="so-secondary-info">
            <ha-icon icon="mdi:information-outline" style="--mdi-icon-size: 14px; flex-shrink:0;"></ha-icon>
            <span>${secondaryInfoValue}</span>
          </div>`
        : '';

      // Indicateurs booléens
      const indicatorsHtml = `
        <div class="so-indicators">
          <span class="so-indicator ${isUsable ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${isUsable ? 'mdi:check-circle' : 'mdi:cancel'}" style="--mdi-icon-size: 14px;"></ha-icon>
            ${t('usable')}
          </span>
          <span class="so-indicator ${isWaiting ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${isWaiting ? 'mdi:timer-sand' : 'mdi:timer-sand-empty'}" style="--mdi-icon-size: 14px;"></ha-icon>
            ${t('waitingIndicator')}
          </span>
          <span class="so-indicator ${shouldBeOForcedOffpeak ? 'so-indicator-true' : 'so-indicator-false'}">
            <ha-icon icon="${shouldBeOForcedOffpeak ? 'mdi:weather-night' : 'mdi:weather-night'}" style="--mdi-icon-size: 14px;"></ha-icon>
            ${t('offpeakForced')}
          </span>
        </div>
      `;

      // Construction des sélections d'options de priorité
      let prioritySelectHtml = "";
      if (priorityStateObj) {
        prioritySelectHtml = `
          <div class="so-priority-control">
            <span>${t('priority')}:</span>
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
          title="${t('enableTitle')}"
        ></ha-switch>
      `;

      // Timed activation: forced_end_time depuis les attributs du switch
      const forcedEndTimeStr = attrs.forced_end_time || null;
      const forcedEndTime = forcedEndTimeStr ? new Date(forcedEndTimeStr) : null;
      const isForcedActive = forcedEndTime && forcedEndTime > new Date();

      // Calcul du temps restant (affiché si activation forcée en cours)
      const formatRemaining = (endTime) => {
        const diffMs = endTime - new Date();
        if (diffMs <= 0) return '0 min';
        const diffMin = Math.ceil(diffMs / 60000);
        if (diffMin < 60) return `${diffMin} min`;
        const h = Math.floor(diffMin / 60);
        const m = diffMin % 60;
        return m > 0 ? `${h}h ${m}min` : `${h}h`;
      };

      // Sélecteur de durée ou badge temps restant
      const durationSelectorHtml = isForcedActive
        ? `<span class="so-timed-remaining" title="${t('timedRemaining')}">${formatRemaining(forcedEndTime)}</span>`
        : `<select class="so-duration-select device-duration-select" data-device-id="${deviceId}" title="${t('timedDurationSelect')}">
            <option value="">—</option>
            <option value="1">${t('timedDuration1h')}</option>
            <option value="4">${t('timedDuration4h')}</option>
            <option value="12">${t('timedDuration12h')}</option>
            <option value="24">${t('timedDuration24h')}</option>
          </select>`;

      // Bouton start/stop manuel
      const startStopHtml = `
        ${durationSelectorHtml}
        <button
          class="so-btn ${isActive ? 'so-btn-stop' : 'so-btn-start'} device-startstop"
          data-entity-id="${switchKey}"
          data-device-id="${deviceId}"
          data-is-active="${isActive}"
          data-is-forced="${isForcedActive ? 'true' : 'false'}"
          title="${isActive ? t('stopManually') : t('startManually')}"
        >${isActive ? t('stop') : t('start')}</button>
      `;

      // Infos disponibilité
      const availHtml = `
        <div class="so-info-grid">
          <div class="so-info-item">
            <span class="so-info-label">${t('nextAvailable')}</span>
            <span class="so-info-value">${formatAvailability(attrs.next_date_available)}</span>
          </div>
          ${attrs.can_change_power ? `
          <div class="so-info-item">
            <span class="so-info-label">${t('powerAvailable')}</span>
            <span class="so-info-value">${formatAvailability(attrs.next_date_available_power)}</span>
          </div>
          ` : ''}
          ${offpeakTime ? `
          <div class="so-info-item">
            <span class="so-info-label">${t('offpeakHours')}</span>
            <span class="so-info-value">${offpeakTime}</span>
          </div>
          ` : ''}
          ${attrs.battery_soc_threshold != null && attrs.battery_soc_threshold > 0 ? `
          <div class="so-info-item">
            <span class="so-info-label">${t('batterySocThreshold')}</span>
            <span class="so-info-value">${attrs.battery_soc_threshold} %</span>
          </div>
          ` : ''}
          <div class="so-info-item">
            <span class="so-info-label">${t('onTime')}</span>
            <span class="so-info-value">${todayOnTimeHms}${maxOnTimeHms ? ' / ' + maxOnTimeHms : ''}</span>
          </div>
        </div>
      `;

      const isCollapsed = this._collapsedDevices[deviceId] !== false;
      const chevronClass = isCollapsed ? 'so-collapse-btn collapsed' : 'so-collapse-btn';
      const physicalClass = isActive ? 'so-device-card-active'
        : isWaiting ? 'so-device-card-waiting'
          : 'so-device-card-inactive';
      const cardStateClass = !isEnabled ? `${physicalClass} so-device-card-disabled` : physicalClass;

      devicesHtml += `
        <div class="so-device-card ${cardStateClass}" data-device-id="${deviceId}">
          <div class="so-device-header">
            <div style="display:flex;align-items:center;gap:6px;">
              <button class="${chevronClass}" data-collapse-id="${deviceId}" title="${isCollapsed ? t('expand') : t('collapse')}">
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
          <div style="display:flex; align-items:center; gap:8px; font-size:0.85em; color:var(--secondary-text-color); padding: 0 4px;">
            <span><strong style="color:var(--primary-text-color);">${currentPower} W</strong> / ${powerMax} W</span>
            ${powerMax > 0 ? `
              <div class="so-power-bar-container" style="flex:1; margin-top:0;">
                ${powerPercent > 0 ? `<div class="so-power-bar" style="width: ${powerPercent}%"></div>` : ''}
              </div>
            ` : ''}
          </div>
          <div class="so-device-details${isCollapsed ? ' hidden' : ''}">
            ${secondaryInfoHtml}
            ${indicatorsHtml}
            <div class="so-device-meta">
              <div>${t('requiredPower')}: <strong>${requestedPower} W</strong></div>
            </div>
            ${availHtml}
            <div style="display:flex; gap:12px; align-items:flex-start; margin-top:6px;">
              <div style="flex:1; min-width:0;">
                ${this._renderHistoryBar(switchKey, t)}
                ${attrs.can_change_power ? this._renderPowerHistoryGraph(switchKey, powerMax, t) : ''}
              </div>
              <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px; flex-shrink:0;">
                <button
                  class="so-btn so-btn-reset device-reset-on-time"
                  data-entity-id="sensor.on_time_today_solar_optimizer_${deviceId}"
                  title="${t('resetTitle')}"
                >
                  <ha-icon icon="mdi:timer-refresh-outline" style="--mdi-icon-size: 14px;"></ha-icon>
                  ${t('reset')}
                </button>
                ${prioritySelectHtml}
              </div>
            </div>
          </div>
        </div>
      `;
    });

    this.content.innerHTML = `
      <div class="so-grid-stats">
        <div class="so-stat-box">
          <ha-icon icon="mdi:solar-power-variant" style="color:var(--warning-color,#ff9800);margin-bottom:4px;"></ha-icon>
          <span class="so-stat-title">${t('smoothedProduction')}</span>
          <span class="so-stat-value">${powerProduction} W</span>
        </div>
        <div class="so-stat-box">
          <ha-icon icon="mdi:home-lightning-bolt" style="color:var(--primary-color);margin-bottom:4px;"></ha-icon>
          <span class="so-stat-title">${t('netConsumption')}</span>
          <span class="so-stat-value">${powerConsumption} W</span>
        </div>
        <div class="so-stat-box">
          <ha-icon icon="mdi:battery" style="color:var(--success-color,#4caf50);margin-bottom:4px;"></ha-icon>
          <span class="so-stat-title">${t('batterySoc')}</span>
          <span class="so-stat-value">${batterySoc !== "N/A" ? batterySoc + " %" : "N/A"}</span>
        </div>
        <div class="so-stat-box">
          <ha-icon icon="mdi:flash" style="color:var(--primary-color);margin-bottom:4px;"></ha-icon>
          <span class="so-stat-title">${t('totalOptimized')}</span>
          <span class="so-stat-value">${totalPower} W</span>
        </div>
        <div class="so-stat-box">
          <ha-icon icon="mdi:bullseye-arrow" style="color:var(--primary-color);margin-bottom:4px;"></ha-icon>
          <span class="so-stat-title">${t('algoObjective')}</span>
          <span class="so-stat-value">${!isNaN(parseFloat(bestObjective)) ? parseFloat(bestObjective).toFixed(2) + " €" : bestObjective}</span>
        </div>
      </div>
      <div style="display:block;">
        <div style="display:flex; justify-content:flex-start; align-items:center; margin-bottom:12px; border-bottom: 1px solid var(--divider-color); padding-bottom: 6px; gap:6px;">
          <button class="so-collapse-btn so-collapse-all" title="${allCollapsed ? t('expandAll') : t('collapseAll')}" style="transform: rotate(${allCollapsed ? '-90deg' : '0deg'});">
            <ha-icon icon="mdi:chevron-down" style="--mdi-icon-size: 20px;"></ha-icon>
          </button>
          <h3 style="margin: 0; font-size: 1.1em;">${t('managedDevices')}</h3>
        </div>
        <div class="so-device-list">
          ${devicesHtml || `<p style="color: var(--secondary-text-color); text-align: center;">${t('noDevices')}</p>`}
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
        const deviceId = btn.getAttribute("data-device-id");
        const isActive = btn.getAttribute("data-is-active") === "true";
        const isForced = btn.getAttribute("data-is-forced") === "true";

        if (isActive) {
          // STOP: si activation forcée active → service stop_device, sinon comportement standard
          if (isForced) {
            this._hass.callService("solar_optimizer", "stop_device", { device_id: deviceId });
          } else {
            this._hass.callService("switch", "turn_off", { entity_id: entityId });
          }
        } else {
          // START: si une durée est sélectionnée → service start_device, sinon comportement standard
          const durationSelect = this.content.querySelector(`.device-duration-select[data-device-id="${deviceId}"]`);
          const duration = durationSelect ? durationSelect.value : "";
          if (duration) {
            this._hass.callService("solar_optimizer", "start_device", { device_id: deviceId, duration: parseInt(duration, 10) });
          } else {
            this._hass.callService("switch", "turn_on", { entity_id: entityId });
          }
        }
      });
    });

    // Attacher les écouteurs pour les boutons reset_on_time
    this.content.querySelectorAll(".device-reset-on-time").forEach(btn => {
      btn.addEventListener("click", () => {
        const entityId = btn.getAttribute("data-entity-id");
        this._hass.callService("solar_optimizer", "reset_on_time", {}, { entity_id: entityId });
      });
    });

    // Attacher les écouteurs pour les boutons plier/déplier individuels
    this.content.querySelectorAll(".so-collapse-btn[data-collapse-id]").forEach(btn => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const deviceId = btn.getAttribute("data-collapse-id");
        // FIX: évaluer l'état courant avant basculement (undefined !== false = true = collapsed)
        const currentlyCollapsed = this._collapsedDevices[deviceId] !== false;
        this._collapsedDevices[deviceId] = !currentlyCollapsed;
        try { localStorage.setItem('solar-optimizer-card-collapsed', JSON.stringify(this._collapsedDevices)); } catch (e) { }
        // Mise à jour en place du DOM pour éviter la race condition avec set hass()
        const card = this.content.querySelector(`.so-device-card[data-device-id="${deviceId}"]`);
        if (card) {
          const details = card.querySelector('.so-device-details');
          const willBeCollapsed = !currentlyCollapsed;
          if (details) details.classList.toggle('hidden', willBeCollapsed);
          btn.classList.toggle('collapsed', willBeCollapsed);
          btn.setAttribute('title', willBeCollapsed ? t('expand') : t('collapse'));
          // Mettre à jour le chevron global
          const stillAllCollapsed = devicesSwitches.length > 0 && devicesSwitches.every(k => {
            const id = k.replace("switch.solar_optimizer_", "");
            return this._collapsedDevices[id] !== false;
          });
          const globalChevron = this.content.querySelector(".so-collapse-all");
          if (globalChevron) globalChevron.style.transform = `rotate(${stillAllCollapsed ? '-90deg' : '0deg'})`;
        }
      });
    });

    // Attacher l'écouteur pour le chevron global
    const globalBtn = this.content.querySelector(".so-collapse-all");
    if (globalBtn) {
      globalBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        const targetCollapsed = !allCollapsed;
        devicesSwitches.forEach(k => {
          const id = k.replace("switch.solar_optimizer_", "");
          this._collapsedDevices[id] = targetCollapsed;
        });
        try { localStorage.setItem('solar-optimizer-card-collapsed', JSON.stringify(this._collapsedDevices)); } catch (e) { }
        // Mise à jour en place du DOM
        this.content.querySelectorAll('.so-device-card[data-device-id]').forEach(card => {
          const deviceId = card.getAttribute('data-device-id');
          const details = card.querySelector('.so-device-details');
          const chevron = card.querySelector('.so-collapse-btn[data-collapse-id]');
          if (details) details.classList.toggle('hidden', targetCollapsed);
          if (chevron) chevron.classList.toggle('collapsed', targetCollapsed);
        });
        globalBtn.style.transform = `rotate(${targetCollapsed ? '-90deg' : '0deg'})`;
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
    if (!this._collapsedDevices) {
      try {
        const saved = localStorage.getItem('solar-optimizer-card-collapsed');
        this._collapsedDevices = saved ? JSON.parse(saved) : {};
      } catch (e) {
        this._collapsedDevices = {};
      }
    }
    if (!this._historyCache) this._historyCache = {};
    if (!this._fetchingHistory) this._fetchingHistory = new Set();
    if (!this._powerHistoryCache) this._powerHistoryCache = {};
    if (!this._fetchingPowerHistory) this._fetchingPowerHistory = new Set();
    if (!this._templateCache) this._templateCache = {};
    if (!this._fetchingTemplates) this._fetchingTemplates = new Set();

    // Ticker toutes les 30s pour rafraîchir l'affichage du temps restant (timed activation)
    if (!this._timedTicker) {
      this._timedTicker = setInterval(() => {
        if (this._hass) this.updateCard();
      }, 30000);
    }
  }

  disconnectedCallback() {
    if (this._timedTicker) {
      clearInterval(this._timedTicker);
      this._timedTicker = null;
    }
  }

  async _fetchHistory(entityId) {
    const historyHours = (this._config && this._config.history_hours) ? this._config.history_hours : 24;
    const endTime = new Date();
    const startTime = new Date(endTime.getTime() - historyHours * 3600 * 1000);
    try {
      const result = await this._hass.callApi("GET",
        `history/period/${startTime.toISOString()}?filter_entity_id=${encodeURIComponent(entityId)}&end_time=${encodeURIComponent(endTime.toISOString())}&minimal_response&no_attributes`
      );
      this._historyCache[entityId] = {
        data: (result && result[0]) ? result[0] : [],
        startTime,
        endTime,
        fetchedAt: Date.now(),
      };
    } catch (e) {
      console.error("[SolarOptimizerCard] History fetch failed for", entityId, e);
      this._historyCache[entityId] = {
        data: [], startTime, endTime, fetchedAt: Date.now()
      };
    }
    this._fetchingHistory.delete(entityId);
    this.updateCard();
  }

  async _fetchPowerHistory(entityId) {
    const historyHours = (this._config && this._config.history_hours) ? this._config.history_hours : 24;
    const endTime = new Date();
    const startTime = new Date(endTime.getTime() - historyHours * 3600 * 1000);
    try {
      const result = await this._hass.callApi("GET",
        `history/period/${startTime.toISOString()}?filter_entity_id=${encodeURIComponent(entityId)}&end_time=${encodeURIComponent(endTime.toISOString())}`
      );
      this._powerHistoryCache[entityId] = {
        data: (result && result[0]) ? result[0] : [],
        startTime,
        endTime,
        fetchedAt: Date.now(),
      };
    } catch (e) {
      console.error("[SolarOptimizerCard] Power history fetch failed for", entityId, e);
      this._powerHistoryCache[entityId] = {
        data: [], startTime, endTime, fetchedAt: Date.now()
      };
    }
    this._fetchingPowerHistory.delete(entityId);
    this.updateCard();
  }

  _renderPowerHistoryGraph(entityId, powerMax, t) {
    const CACHE_TTL = 5 * 60 * 1000;
    if (!this._powerHistoryCache) this._powerHistoryCache = {};
    if (!this._fetchingPowerHistory) this._fetchingPowerHistory = new Set();
    const historyHours = (this._config && this._config.history_hours) ? this._config.history_hours : 24;
    const cached = this._powerHistoryCache[entityId];
    const label = `${t('powerHistory')} – ${historyHours}h`;
    const pMax = powerMax > 0 ? powerMax : 1;

    const emptyGraph = `
      <div class="so-history-bar-wrapper" style="margin-top:4px;">
        <svg class="so-power-history-svg" viewBox="0 0 100 30" preserveAspectRatio="none">
          <rect x="0" y="0" width="100" height="30" fill="var(--secondary-background-color, #e0e0e0)" />
        </svg>
        <div class="so-history-bar-label">${label}</div>
      </div>`;

    if (!cached || (Date.now() - cached.fetchedAt > CACHE_TTL)) {
      if (!this._fetchingPowerHistory.has(entityId)) {
        this._fetchingPowerHistory.add(entityId);
        this._fetchPowerHistory(entityId);
      }
      if (!cached) return emptyGraph;
    }

    const { data, startTime, endTime } = cached;
    const totalMs = endTime.getTime() - startTime.getTime();

    const sorted = [...(data || [])]
      .sort((a, b) => new Date(a.last_changed) - new Date(b.last_changed))
      .filter(s => s.attributes && s.attributes.current_power != null);

    if (sorted.length === 0) return emptyGraph;

    const toPoint = (tMs, power) => {
      const x = ((tMs - startTime.getTime()) / totalMs) * 100;
      const y = 30 - (parseFloat(power) / pMax) * 28;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    };

    const linePoints = sorted.map(s =>
      toPoint(new Date(s.last_changed).getTime(), s.attributes.current_power)
    );
    const lastPower = sorted[sorted.length - 1].attributes.current_power;
    linePoints.push(toPoint(endTime.getTime(), lastPower));

    const polylinePoints = linePoints.join(' ');
    const polygonPoints = `0,30 ${linePoints.join(' ')} 100,30`;

    return `
      <div class="so-history-bar-wrapper" style="margin-top:4px;">
        <svg class="so-power-history-svg" viewBox="0 0 100 30" preserveAspectRatio="none">
          <polygon points="${polygonPoints}" fill="var(--primary-color)" fill-opacity="0.2" />
          <polyline points="${polylinePoints}" fill="none" stroke="var(--primary-color)" stroke-width="1.5" vector-effect="non-scaling-stroke" />
        </svg>
        <div class="so-history-bar-label">${label}</div>
      </div>`;
  }

  _evaluateTemplate(template) {
    if (!template || !this._hass) return null;

    if (!this._templateCache) this._templateCache = {};
    if (!this._fetchingTemplates) this._fetchingTemplates = new Set();

    const CACHE_TTL = 5 * 1000; // 5 secondes
    const cached = this._templateCache[template];

    if (!cached || (Date.now() - cached.fetchedAt > CACHE_TTL)) {
      if (!this._fetchingTemplates.has(template)) {
        this._fetchingTemplates.add(template);
        this._hass.callApi('POST', 'template', { template })
          .then(result => {
            this._templateCache[template] = { value: String(result).trim(), fetchedAt: Date.now() };
            this._fetchingTemplates.delete(template);
            if (this._updateTimer) clearTimeout(this._updateTimer);
            this._updateTimer = setTimeout(() => this.updateCard(), 50);
          })
          .catch(() => {
            // Fallback sur l'évaluation regex client-side si l'API échoue
            const fallback = this._evaluateTemplateSimple(template);
            this._templateCache[template] = { value: fallback, fetchedAt: Date.now() };
            this._fetchingTemplates.delete(template);
          });
      }
    }

    return cached ? cached.value : null;
  }

  _evaluateTemplateSimple(template) {
    if (!template || !this._hass) return null;
    return template
      .replace(/\{\{\s*states\(['"]([^'"]+)['"]\)\s*\}\}/g, (_, entityId) => {
        return this._hass.states[entityId]?.state ?? 'unknown';
      })
      .replace(/\{\{\s*state_attr\(['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\)\s*\}\}/g, (_, entityId, attr) => {
        return this._hass.states[entityId]?.attributes?.[attr] ?? 'unknown';
      });
  }

  _renderHistoryBar(entityId, t) {
    const CACHE_TTL = 5 * 60 * 1000;
    if (!this._historyCache) this._historyCache = {};
    if (!this._fetchingHistory) this._fetchingHistory = new Set();
    const historyHours = (this._config && this._config.history_hours) ? this._config.history_hours : 24;
    const cached = this._historyCache[entityId];
    const label = `${t('historyBar')} – ${historyHours}h`;

    if (!cached || (Date.now() - cached.fetchedAt > CACHE_TTL)) {
      if (!this._fetchingHistory.has(entityId)) {
        this._fetchingHistory.add(entityId);
        this._fetchHistory(entityId);
      }
      if (!cached) {
        return `
          <div class="so-history-bar-wrapper">
            <div class="so-history-bar-container">
              <div class="so-history-segment-off" style="width:100%;"></div>
            </div>
            <div class="so-history-bar-label">${label}</div>
          </div>`;
      }
    }

    const { data, startTime, endTime } = cached;
    const totalMs = endTime.getTime() - startTime.getTime();

    if (!data || data.length === 0) {
      return `
        <div class="so-history-bar-wrapper">
          <div class="so-history-bar-container">
            <div class="so-history-segment-off" style="width:100%;"></div>
          </div>
          <div class="so-history-bar-label">${label}</div>
        </div>`;
    }

    const sorted = [...data].sort((a, b) => new Date(a.last_changed) - new Date(b.last_changed));
    const segments = [];
    for (let i = 0; i < sorted.length; i++) {
      const segStart = Math.max(new Date(sorted[i].last_changed).getTime(), startTime.getTime());
      const segEnd = i < sorted.length - 1
        ? Math.min(new Date(sorted[i + 1].last_changed).getTime(), endTime.getTime())
        : endTime.getTime();
      const widthPct = Math.max(0, ((segEnd - segStart) / totalMs) * 100);
      if (widthPct > 0.01) {
        segments.push({ width: widthPct, isOn: sorted[i].state === "on" });
      }
    }

    if (segments.length === 0) {
      return `
        <div class="so-history-bar-wrapper">
          <div class="so-history-bar-container">
            <div class="so-history-segment-off" style="width:100%;"></div>
          </div>
          <div class="so-history-bar-label">${label}</div>
        </div>`;
    }

    const segmentsHtml = segments.map(seg =>
      `<div class="so-history-segment-${seg.isOn ? 'on' : 'off'}" style="width:${seg.width.toFixed(3)}%;"></div>`
    ).join('');

    return `
      <div class="so-history-bar-wrapper">
        <div class="so-history-bar-container">${segmentsHtml}</div>
        <div class="so-history-bar-label">${label}</div>
      </div>`;
  }
}


class SolarOptimizerCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _render() {
    const lang = this._hass?.locale?.language || navigator.language || 'en';
    const isFr = lang.toLowerCase().startsWith('fr');
    const t = (key) => TRANSLATIONS[isFr ? 'fr' : 'en'][key] || key;
    const historyHours = (this._config && this._config.history_hours) ? this._config.history_hours : 24;

    this.innerHTML = `
      <div style="padding: 16px; font-family: var(--paper-font-body1_-_font-family); color: var(--primary-text-color);">
        <h3 style="margin-top: 0; color: var(--primary-color);">Solar Optimizer Card</h3>
        <p style="margin-bottom: 8px;">${t('editorAutoConfig')}</p>
        <p style="margin-top: 0; font-size: 0.9em; color: var(--secondary-text-color);">
          ${t('editorDesc')}
        </p>
        <div style="background-color: var(--secondary-background-color); padding: 12px; border-radius: 6px; font-size: 0.85em; border-left: 4px solid var(--primary-color);">
          ${t('editorNote')}
        </div>
        <div style="margin-top: 16px; display: flex; align-items: center; gap: 12px;">
          <label style="font-size: 0.9em; color: var(--primary-text-color);">${t('editorHistoryHours')}</label>
          <input type="number" id="so-history-hours-input" min="1" max="168" value="${historyHours}"
            style="width: 72px; padding: 4px 8px; border-radius: 4px; border: 1px solid var(--divider-color, #ccc); background: var(--card-background-color, #fff); color: var(--primary-text-color); font-size: 0.9em;">
        </div>
        <div style="margin-top: 16px;">
          <p style="font-size: 0.9em; color: var(--primary-text-color); margin-bottom: 4px;">${t('editorSecondaryInfoDesc')}</p>
          <pre style="font-size: 0.78em; background: var(--secondary-background-color, #f5f5f5); padding: 8px; border-radius: 4px; overflow-x: auto; color: var(--primary-text-color); margin: 0;">secondary_info:
  device_id: "{{ states('sensor.my_entity') }}"
  device_id2: "{{ state_attr('sensor.my_entity', 'attribute') }}"</pre>
        </div>
      </div>
    `;

    const input = this.querySelector("#so-history-hours-input");
    if (input) {
      input.addEventListener("change", (e) => {
        const value = parseInt(e.target.value, 10);
        if (!isNaN(value) && value > 0) {
          this._config = { ...this._config, history_hours: value };
          this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
        }
      });
    }
  }
}

// Enregistrer l'éditeur personnalisé
customElements.define("solar-optimizer-card-editor", SolarOptimizerCardEditor);

// Afficher un log au démarrage dans la console du navigateur avec la version de la carte
console.info(
  `%c  SOLAR-OPTIMIZER-CARD  %c Version 1.5.0 `,
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
  description: "Interactive card to control and monitor devices managed by the Solar Optimizer load scheduler."
});
