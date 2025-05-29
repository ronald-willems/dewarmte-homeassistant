class DeWarmteCard extends HTMLElement {
    static get properties() {
        return {
            hass: {},
            config: {},
        };
    }

    setConfig(config) {
        if (!config.entity) {
            throw new Error('Please define an entity');
        }
        this.config = config;
    }

    set hass(hass) {
        this._hass = hass;
        this.updateCard();
    }

    getCardSize() {
        return 3;
    }

    updateCard() {
        if (!this._hass || !this.config) return;

        const entity = this._hass.states[this.config.entity];
        if (!entity) {
            this.innerHTML = `
                <ha-card header="DeWarmte">
                    <div class="card-content">
                        Entity ${this.config.entity} not found
                    </div>
                </ha-card>
            `;
            return;
        }

        const state = entity.state;
        const attributes = entity.attributes;

        this.innerHTML = `
            <ha-card header="DeWarmte">
                <div class="card-content">
                    <div class="status">
                        <div class="temperature">
                            Current Temperature: ${attributes.current_temperature || 'N/A'}°C
                        </div>
                        <div class="mode">
                            Mode: ${attributes.cooling_control_mode || 'N/A'}
                        </div>
                        <div class="type">
                            Type: ${attributes.cooling_thermostat_type || 'N/A'}
                        </div>
                    </div>
                    <div class="controls">
                        <ha-select
                            label="Control Mode"
                            .value=${attributes.cooling_control_mode || ''}
                            @change=${this._handleControlModeChange}
                        >
                            <mwc-list-item value="thermostat">Thermostat</mwc-list-item>
                            <mwc-list-item value="heating_only">Heating Only</mwc-list-item>
                            <mwc-list-item value="cooling_only">Cooling Only</mwc-list-item>
                        </ha-select>
                    </div>
                </div>
            </ha-card>
        `;
    }

    _handleControlModeChange(ev) {
        const newMode = ev.target.value;
        this._hass.callService('dewarmte', 'set_control_mode', {
            entity_id: this.config.entity,
            mode: newMode
        });
    }

    static get styles() {
        return `
            .card-content {
                padding: 16px;
            }
            .status {
                margin-bottom: 16px;
            }
            .temperature {
                font-size: 24px;
                margin-bottom: 8px;
            }
            .mode, .type {
                font-size: 16px;
                margin-bottom: 4px;
            }
            .controls {
                margin-top: 16px;
            }
            ha-select {
                width: 100%;
            }
        `;
    }
}

customElements.define('dewarmte-card', DeWarmteCard);

// Register the card in the card picker
window.customCards = window.customCards || [];
window.customCards.push({
    type: 'dewarmte-card',
    name: 'DeWarmte Card',
    description: 'A card for controlling DeWarmte devices',
    preview: true,
    documentationURL: 'https://github.com/yourusername/dewarmte-homeassistant'
}); 