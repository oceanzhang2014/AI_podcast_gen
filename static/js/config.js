/**
 * Configuration Management JavaScript for API Key Configuration
 * Handles API key management, agent configuration, and form interactions
 * Follows the same patterns as main.js for consistency
 */

// Configuration state management
const ConfigState = {
    isLoading: false,
    isSaving: false,
    isValidating: false,
    currentConfiguration: {
        api_keys: {},
        agent_configs: []
    },
    availableModels: {},
    validationResults: {},
    session_id: null,
    lastError: null,
    lastSuccess: null
};

// DOM element cache
const ConfigElements = {
    form: null,
    apiKeyInputs: {},
    validationStatuses: {},
    validationButtons: {},
    toggleButtons: {},
    saveButtons: {},
    clearButton: null,
    exportButton: null,
    importButton: null,
    agentContainer: null,
    addAgentButton: null,
    statusSection: null,
    importModal: null,
    exportModal: null,
    importForm: null,
    importKey: null,
    importData: null,
    confirmImportBtn: null,
    exportKey: null,
    exportData: null,
    copyKeyBtn: null,
    copyDataBtn: null,
    apiKeysStatus: null,
    agentCount: null
};

/**
 * Configuration Manager Class
 * Handles all configuration-related operations
 */
class ConfigurationManager {
    constructor() {
        this.apiEndpoints = {
            config: '/api/config',
            validate: '/api/config/validate',
            models: '/api/config/models',
            export: '/api/config/export'
        };

        this.providers = ['deepseek', 'bigmodel', 'openai'];
        this.debounceTimers = {};

        this.initialize();
    }

    /**
     * Initialize the configuration manager
     */
    async initialize() {
        try {
            console.log('Configuration Manager initializing...');

            // Cache DOM elements
            this.cacheElements();

            // Setup event listeners
            this.setupEventListeners();

            // Load existing configuration
            await this.loadConfiguration();

            // Load available models
            await this.loadAvailableModels();

            // Initialize tooltips
            this.initializeTooltips();

            console.log('Configuration Manager initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Configuration Manager:', error);
            this.showNotification('Failed to initialize configuration manager', 'error');
        }
    }

    /**
     * Cache DOM elements for better performance
     */
    cacheElements() {
        // Form elements
        ConfigElements.form = document.getElementById('configForm');
        ConfigElements.clearButton = document.getElementById('clear-config-btn');
        ConfigElements.exportButton = document.getElementById('export-config-btn');
        ConfigElements.importButton = document.getElementById('import-config-btn');

        // Agent configuration elements
        ConfigElements.agentContainer = document.getElementById('agent-config-container');
        ConfigElements.addAgentButton = document.getElementById('add-agent-btn');

        // Status elements
        ConfigElements.statusSection = document.getElementById('status-section');
        ConfigElements.apiKeysStatus = document.getElementById('api-keys-status');
        ConfigElements.agentCount = document.getElementById('agent-count');

        // Modal elements
        ConfigElements.importModal = document.getElementById('importModal');
        ConfigElements.exportModal = document.getElementById('exportModal');
        ConfigElements.importForm = document.getElementById('importForm');
        ConfigElements.importKey = document.getElementById('importKey');
        ConfigElements.importData = document.getElementById('importData');
        ConfigElements.confirmImportBtn = document.getElementById('confirmImportBtn');
        ConfigElements.exportKey = document.getElementById('exportKey');
        ConfigElements.exportData = document.getElementById('exportData');
        ConfigElements.copyKeyBtn = document.getElementById('copyKeyBtn');
        ConfigElements.copyDataBtn = document.getElementById('copyDataBtn');

        // API key elements for each provider
        this.providers.forEach(provider => {
            ConfigElements.apiKeyInputs[provider] = document.getElementById(`${provider}-api-key`);
            ConfigElements.validationStatuses[provider] = document.getElementById(`${provider}-validation`);
            ConfigElements.validationButtons[provider] = document.querySelector(`[data-provider="${provider}"]`);
            ConfigElements.toggleButtons[provider] = document.querySelector(`[data-input-id="${provider}-api-key"]`);
        });

        // Save buttons (both desktop and mobile)
        ConfigElements.saveButtons.desktop = document.getElementById('save-config-btn');
        ConfigElements.saveButtons.mobile = document.getElementById('save-config-btn-mobile');

        // Mobile action buttons
        ConfigElements.saveButtons.mobile = document.getElementById('save-config-btn-mobile');
        ConfigElements.clearButton = document.getElementById('clear-config-btn-mobile') || ConfigElements.clearButton;
        ConfigElements.exportButton = document.getElementById('export-config-btn-mobile') || ConfigElements.exportButton;
        ConfigElements.importButton = document.getElementById('import-config-btn-mobile') || ConfigElements.importButton;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Form submission
        if (ConfigElements.form) {
            ConfigElements.form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // API key inputs
        Object.keys(ConfigElements.apiKeyInputs).forEach(provider => {
            const input = ConfigElements.apiKeyInputs[provider];
            if (input) {
                // Debounced validation on input
                input.addEventListener('input', (e) => {
                    this.debounceValidation(provider, e.target.value);
                });

                // Clear validation on focus
                input.addEventListener('focus', () => {
                    this.clearValidationStatus(provider);
                });

                // Validate on blur
                input.addEventListener('blur', (e) => {
                    if (e.target.value.trim()) {
                        this.validateAPIKeyFormat(provider, e.target.value);
                    }
                });
            }
        });

        // Validation buttons
        Object.keys(ConfigElements.validationButtons).forEach(provider => {
            const button = ConfigElements.validationButtons[provider];
            if (button) {
                button.addEventListener('click', () => {
                    this.validateAPIKey(provider);
                });
            }
        });

        // Toggle visibility buttons
        Object.keys(ConfigElements.toggleButtons).forEach(provider => {
            const button = ConfigElements.toggleButtons[provider];
            if (button) {
                button.addEventListener('click', () => {
                    this.toggleAPIKeyVisibility(provider);
                });
            }
        });

        // Action buttons
        [ConfigElements.saveButtons.desktop, ConfigElements.saveButtons.mobile].forEach(button => {
            if (button) {
                button.addEventListener('click', () => this.saveConfiguration());
            }
        });

        if (ConfigElements.clearButton) {
            ConfigElements.clearButton.addEventListener('click', () => this.clearConfiguration());
        }

        if (ConfigElements.exportButton) {
            ConfigElements.exportButton.addEventListener('click', () => this.exportConfiguration());
        }

        if (ConfigElements.importButton) {
            ConfigElements.importButton.addEventListener('click', () => this.showImportModal());
        }

        // Agent configuration
        if (ConfigElements.addAgentButton) {
            ConfigElements.addAgentButton.addEventListener('click', () => this.addAgentConfiguration());
        }

        // Setup dynamic event listeners for agent configurations
        this.setupAgentConfigListeners();

        // Modal events
        if (ConfigElements.confirmImportBtn) {
            ConfigElements.confirmImportBtn.addEventListener('click', () => this.importConfiguration());
        }

        if (ConfigElements.copyKeyBtn) {
            ConfigElements.copyKeyBtn.addEventListener('click', () => this.copyToClipboard('exportKey'));
        }

        if (ConfigElements.copyDataBtn) {
            ConfigElements.copyDataBtn.addEventListener('click', () => this.copyToClipboard('exportData'));
        }

        // Keyboard shortcuts
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup event listeners for agent configurations
     */
    setupAgentConfigListeners() {
        // Use event delegation for dynamic agent configurations
        if (ConfigElements.agentContainer) {
            ConfigElements.agentContainer.addEventListener('change', (e) => {
                // Handle provider selection change
                if (e.target.name && e.target.name.includes('provider_')) {
                    const index = e.target.name.split('_')[1];
                    this.updateModelSelectForAgent(index);
                }
            });

            // Handle agent ID validation
            ConfigElements.agentContainer.addEventListener('input', (e) => {
                if (e.target.name && e.target.name.includes('agent_id_')) {
                    this.validateAgentIdUniqueness();
                }
            });
        }
    }

    /**
     * Update model select for a specific agent
     */
    updateModelSelectForAgent(index) {
        const providerSelect = document.querySelector(`[name="provider_${index}"]`);
        const modelSelect = document.querySelector(`[name="model_${index}"]`);

        if (!providerSelect || !modelSelect) return;

        // Store current selection
        const currentModel = modelSelect.value;

        // Clear current options
        modelSelect.innerHTML = '<option value="">Select model</option>';

        // Add models based on selected provider
        const selectedProvider = providerSelect.value;
        if (selectedProvider && ConfigState.availableModels[selectedProvider]) {
            ConfigState.availableModels[selectedProvider].forEach(modelInfo => {
                const option = document.createElement('option');
                option.value = modelInfo.model;
                option.textContent = modelInfo.display_name || modelInfo.model;
                if (modelInfo.model === currentModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        } else {
            // Add placeholder option if no models available
            const option = document.createElement('option');
            option.value = '';
            option.textContent = selectedProvider ? 'No models available (validate API key first)' : 'Select a provider first';
            option.disabled = true;
            modelSelect.appendChild(option);
        }
    }

    /**
     * Validate agent ID uniqueness
     */
    validateAgentIdUniqueness() {
        const agentCards = ConfigElements.agentContainer?.querySelectorAll('.agent-config-card') || [];
        const agentIds = new Set();
        let hasDuplicates = false;

        agentCards.forEach((card, index) => {
            const agentIdInput = card.querySelector(`[name="agent_id_${index}"]`);
            if (!agentIdInput) return;

            const agentId = agentIdInput.value.trim().toLowerCase();
            if (agentId) {
                if (agentIds.has(agentId)) {
                    agentIdInput.classList.add('is-invalid');
                    hasDuplicates = true;
                } else {
                    agentIdInput.classList.remove('is-invalid');
                    agentIds.add(agentId);
                }
            }
        });

        return !hasDuplicates;
    }

    /**
     * Load existing configuration from the server
     */
    async loadConfiguration() {
        if (ConfigState.isLoading) return;

        try {
            ConfigState.isLoading = true;
            this.setLoadingState(true);

            console.log('Loading configuration...');

            const response = await this.apiRequest(this.apiEndpoints.config, {
                method: 'GET'
            });

            if (response.success) {
                ConfigState.currentConfiguration = response.data;
                ConfigState.session_id = response.data.session_id;

                // Populate form with loaded data
                this.populateForm(response.data);

                console.log('Configuration loaded successfully');
                this.showNotification('Configuration loaded successfully', 'success');
            } else {
                throw new Error(response.error || 'Failed to load configuration');
            }
        } catch (error) {
            console.error('Failed to load configuration:', error);
            ConfigState.lastError = error.message;
            this.showNotification('Failed to load configuration: ' + error.message, 'error');
        } finally {
            ConfigState.isLoading = false;
            this.setLoadingState(false);
        }
    }

    /**
     * Save API keys configuration
     */
    async saveAPIKeys(apiKeys) {
        if (ConfigState.isSaving) return;

        try {
            ConfigState.isSaving = true;
            this.setSavingState(true);

            console.log('Saving API keys...');

            const response = await this.apiRequest(this.apiEndpoints.config, {
                method: 'POST',
                body: JSON.stringify({
                    api_keys: apiKeys
                })
            });

            if (response.success) {
                // Update current configuration
                ConfigState.currentConfiguration.api_keys = { ...ConfigState.currentConfiguration.api_keys, ...apiKeys };

                console.log('API keys saved successfully');
                return true;
            } else {
                throw new Error(response.error || 'Failed to save API keys');
            }
        } catch (error) {
            console.error('Failed to save API keys:', error);
            ConfigState.lastError = error.message;
            throw error;
        } finally {
            ConfigState.isSaving = false;
            this.setSavingState(false);
        }
    }

    /**
     * Make API request with error handling
     */
    async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        };

        const requestOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(url, requestOptions);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    /**
     * Debounced validation for API key input
     */
    debounceValidation(provider, value) {
        // Clear existing timer
        if (this.debounceTimers[provider]) {
            clearTimeout(this.debounceTimers[provider]);
        }

        // Set new timer
        this.debounceTimers[provider] = setTimeout(() => {
            this.validateAPIKeyFormat(provider, value);
        }, 500); // 500ms delay
    }

    /**
     * Validate API key format (client-side)
     */
    validateAPIKeyFormat(provider, value) {
        if (!value || !value.trim()) {
            this.setValidationStatus(provider, 'empty', 'No API key provided');
            return false;
        }

        const patterns = {
            deepseek: /^sk-[a-zA-Z0-9]{48}$/,
            bigmodel: /^[a-zA-Z0-9]{64}$/,
            openai: /^sk-[a-zA-Z0-9]{48}$/
        };

        const pattern = patterns[provider];
        if (pattern && !pattern.test(value)) {
            this.setValidationStatus(provider, 'invalid', 'Invalid API key format');
            return false;
        }

        this.setValidationStatus(provider, 'pending', 'Ready to validate');
        return true;
    }

    /**
     * Set validation status for a provider
     */
    setValidationStatus(provider, status, message = '') {
        const statusElement = ConfigElements.validationStatuses[provider];
        const inputElement = ConfigElements.apiKeyInputs[provider];
        const cardElement = document.getElementById(`${provider}-card`);

        if (!statusElement) return;

        const statusConfig = {
            empty: {
                class: 'bg-secondary',
                icon: 'bi-dash-circle',
                text: 'Not Validated'
            },
            pending: {
                class: 'bg-warning',
                icon: 'bi-clock',
                text: 'Ready to Validate'
            },
            validating: {
                class: 'bg-info',
                icon: 'bi-arrow-repeat',
                text: 'Validating...'
            },
            valid: {
                class: 'bg-success',
                icon: 'bi-check-circle',
                text: 'Valid'
            },
            invalid: {
                class: 'bg-danger',
                icon: 'bi-x-circle',
                text: 'Invalid'
            },
            error: {
                class: 'bg-danger',
                icon: 'bi-exclamation-triangle',
                text: 'Error'
            }
        };

        const config = statusConfig[status] || statusConfig.empty;

        // Update badge
        statusElement.innerHTML = `
            <span class="badge ${config.class}">
                <i class="bi ${config.icon} me-1"></i>${config.text}
            </span>
        `;

        // Add message if provided
        if (message) {
            const messageElement = document.createElement('div');
            messageElement.className = 'small text-muted mt-1';
            messageElement.textContent = message;
            statusElement.appendChild(messageElement);
        }

        // Update input validation classes
        if (inputElement) {
            inputElement.classList.remove('is-valid', 'is-invalid');
            if (status === 'valid') {
                inputElement.classList.add('is-valid');
            } else if (status === 'invalid' || status === 'error') {
                inputElement.classList.add('is-invalid');
            }
        }

        // Update card classes
        if (cardElement) {
            cardElement.classList.remove('validated', 'error');
            if (status === 'valid') {
                cardElement.classList.add('validated');
            } else if (status === 'invalid' || status === 'error') {
                cardElement.classList.add('error');
            }
        }

        // Store validation result
        ConfigState.validationResults[provider] = { status, message };
    }

    /**
     * Clear validation status for a provider
     */
    clearValidationStatus(provider) {
        this.setValidationStatus(provider, 'pending');
    }

    /**
     * Toggle API key visibility
     */
    toggleAPIKeyVisibility(provider) {
        const input = ConfigElements.apiKeyInputs[provider];
        const button = ConfigElements.toggleButtons[provider];
        const icon = button?.querySelector('.toggle-icon');

        if (!input) return;

        if (input.type === 'password') {
            input.type = 'text';
            if (icon) icon.classList.replace('bi-eye', 'bi-eye-slash');
            if (button) button.setAttribute('title', 'Hide API key');
        } else {
            input.type = 'password';
            if (icon) icon.classList.replace('bi-eye-slash', 'bi-eye');
            if (button) button.setAttribute('title', 'Show API key');
        }
    }

    /**
     * Validate API key with server
     */
    async validateAPIKey(provider) {
        const input = ConfigElements.apiKeyInputs[provider];
        const button = ConfigElements.validationButtons[provider];

        if (!input || !input.value.trim()) {
            this.showNotification('Please enter an API key first', 'warning');
            return;
        }

        if (ConfigState.isValidating) return;

        try {
            ConfigState.isValidating = true;
            this.setValidationStatus(provider, 'validating');

            if (button) {
                button.disabled = true;
                button.classList.add('loading');
            }

            console.log(`Validating ${provider} API key...`);

            const response = await this.apiRequest(this.apiEndpoints.validate, {
                method: 'POST',
                body: JSON.stringify({
                    provider: provider,
                    api_key: input.value.trim()
                })
            });

            if (response.success && response.data.validation_result.valid) {
                this.setValidationStatus(provider, 'valid', 'API key is valid');
                ConfigState.lastSuccess = `${provider} API key validated successfully`;
                this.showNotification(`${provider} API key validated successfully`, 'success');

                // Load available models for this provider
                if (response.data.available_models) {
                    ConfigState.availableModels[provider] = response.data.available_models;
                }
            } else {
                const errorMsg = response.data?.validation_result?.error || 'API key validation failed';
                this.setValidationStatus(provider, 'invalid', errorMsg);
                this.showNotification(`${provider} API key validation failed: ${errorMsg}`, 'error');
            }
        } catch (error) {
            console.error(`Failed to validate ${provider} API key:`, error);
            this.setValidationStatus(provider, 'error', 'Validation failed');
            this.showNotification(`Failed to validate ${provider} API key: ${error.message}`, 'error');
        } finally {
            ConfigState.isValidating = false;
            if (button) {
                button.disabled = false;
                button.classList.remove('loading');
            }
        }
    }

    /**
     * Set loading state for UI elements
     */
    setLoadingState(loading) {
        // Update loading states for various elements
        const loadingElements = document.querySelectorAll('.loading-indicator');
        loadingElements.forEach(element => {
            element.style.display = loading ? 'block' : 'none';
        });

        // Disable form inputs during loading
        if (ConfigElements.form) {
            ConfigElements.form.style.opacity = loading ? '0.6' : '1';
            ConfigElements.form.style.pointerEvents = loading ? 'none' : 'auto';
        }
    }

    /**
     * Set saving state for UI elements
     */
    setSavingState(saving) {
        const saveButtons = [
            ConfigElements.saveButtons.desktop,
            ConfigElements.saveButtons.mobile
        ].filter(Boolean);

        saveButtons.forEach(button => {
            if (saving) {
                button.disabled = true;
                const spinner = button.querySelector('.spinner-border');
                if (spinner) spinner.classList.remove('d-none');
                button.innerHTML = button.innerHTML.replace('Save Configuration', 'Saving...');
            } else {
                button.disabled = false;
                const spinner = button.querySelector('.spinner-border');
                if (spinner) spinner.classList.add('d-none');
                button.innerHTML = button.innerHTML.replace('Saving...', 'Save Configuration');
            }
        });
    }

    /**
     * Populate form with configuration data
     */
    populateForm(data) {
        // Populate API keys (masked)
        if (data.api_keys) {
            Object.keys(data.api_keys).forEach(provider => {
                const input = ConfigElements.apiKeyInputs[provider];
                if (input && data.api_keys[provider]) {
                    // Show masked version
                    const apiKey = data.api_keys[provider];
                    if (apiKey && apiKey.length > 4) {
                        input.value = apiKey; // This will be masked on the server side
                    }
                }
            });
        }

        // Populate agent configurations
        if (data.agent_configs && Array.isArray(data.agent_configs)) {
            this.populateAgentConfigurations(data.agent_configs);
        }

        // Update status indicators
        this.updateStatusIndicators();
    }

    /**
     * Populate agent configurations
     */
    populateAgentConfigurations(agentConfigs) {
        if (!ConfigElements.agentContainer) return;

        ConfigElements.agentContainer.innerHTML = '';

        agentConfigs.forEach((config, index) => {
            const agentElement = this.createAgentConfigurationElement(config, index);
            ConfigElements.agentContainer.appendChild(agentElement);
        });

        this.updateAgentCount();
    }

    /**
     * Create agent configuration element
     */
    createAgentConfigurationElement(config, index) {
        const element = document.createElement('div');
        element.className = 'agent-config-card card mb-3';
        element.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <h6 class="mb-0">Agent ${index + 1}</h6>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="this.closest('.agent-config-card').remove()">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Agent ID</label>
                        <input type="text" class="form-control" name="agent_id_${index}" value="${config.agent_id || ''}" placeholder="e.g., narrator, expert">
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Provider</label>
                        <select class="form-select" name="provider_${index}">
                            <option value="">Select provider</option>
                            ${this.providers.map(provider =>
                                `<option value="${provider}" ${config.provider === provider ? 'selected' : ''}>${provider}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label class="form-label">Model</label>
                        <select class="form-select" name="model_${index}">
                            <option value="">Select model</option>
                            <!-- Models will be populated dynamically -->
                        </select>
                    </div>
                </div>
            </div>
        `;

        return element;
    }

    /**
     * Add new agent configuration
     */
    addAgentConfiguration() {
        if (!ConfigElements.agentContainer) return;

        const newConfig = {
            agent_id: '',
            provider: '',
            model: ''
        };

        const agentElement = this.createAgentConfigurationElement(newConfig, ConfigElements.agentContainer.children.length);
        ConfigElements.agentContainer.appendChild(agentElement);

        this.updateAgentCount();
        this.showNotification('Agent configuration added', 'info');
    }

    /**
     * Update agent count display
     */
    updateAgentCount() {
        if (ConfigElements.agentCount && ConfigElements.agentContainer) {
            const count = ConfigElements.agentContainer.children.length;
            ConfigElements.agentCount.innerHTML = `<i class="bi bi-people me-1"></i>${count} Agent${count !== 1 ? 's' : ''}`;
        }
    }

    /**
     * Update status indicators
     */
    updateStatusIndicators() {
        // Update API keys status
        if (ConfigElements.apiKeysStatus) {
            const configuredProviders = Object.keys(ConfigState.currentConfiguration.api_keys || {}).length;
            const totalProviders = this.providers.length;

            if (configuredProviders === 0) {
                ConfigElements.apiKeysStatus.innerHTML = '<i class="bi bi-circle-fill me-1"></i>Not Configured';
                ConfigElements.apiKeysStatus.className = 'badge bg-secondary ms-2';
            } else if (configuredProviders === totalProviders) {
                ConfigElements.apiKeysStatus.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>Fully Configured';
                ConfigElements.apiKeysStatus.className = 'badge bg-success ms-2';
            } else {
                ConfigElements.apiKeysStatus.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i>${configuredProviders}/${totalProviders} Configured`;
                ConfigElements.apiKeysStatus.className = 'badge bg-warning ms-2';
            }
        }
    }

    /**
     * Load available models from server
     */
    async loadAvailableModels() {
        try {
            console.log('Loading available models...');

            const response = await this.apiRequest(this.apiEndpoints.models, {
                method: 'GET'
            });

            if (response.success) {
                ConfigState.availableModels = response.data.models;
                console.log('Available models loaded:', ConfigState.availableModels);

                // Update all model selects with new data
                this.updateAllModelSelects();
            }
        } catch (error) {
            console.error('Failed to load available models:', error);
            // Non-critical error, don't show notification
        }
    }

    /**
     * Load available models for a specific agent (dynamic loading)
     */
    async loadAvailableModelsForAgent(agentId, provider) {
        if (!provider) {
            // Clear models if no provider selected
            this.updateModelSelectForAgent(agentId, []);
            return;
        }

        try {
            console.log(`Loading models for agent ${agentId} with provider ${provider}...`);

            // Check if we already have models for this provider
            if (ConfigState.availableModels[provider] && ConfigState.availableModels[provider].length > 0) {
                this.updateModelSelectForAgent(agentId, ConfigState.availableModels[provider]);
                return;
            }

            // Try to validate the API key to get models
            const apiKeyInput = ConfigElements.apiKeyInputs[provider];
            if (apiKeyInput && apiKeyInput.value.trim()) {
                const validationResult = await this.validateAPIKey(provider, true);
                if (validationResult && ConfigState.availableModels[provider]) {
                    this.updateModelSelectForAgent(agentId, ConfigState.availableModels[provider]);
                } else {
                    // API key validation failed, show default models or empty state
                    this.updateModelSelectForAgent(agentId, this.getDefaultModels(provider));
                }
            } else {
                // No API key, show default models
                this.updateModelSelectForAgent(agentId, this.getDefaultModels(provider));
            }

        } catch (error) {
            console.error(`Failed to load models for agent ${agentId}:`, error);
            this.updateModelSelectForAgent(agentId, this.getDefaultModels(provider));
        }
    }

    /**
     * Get default models for a provider when API key is not available
     */
    getDefaultModels(provider) {
        const defaultModels = {
            deepseek: [
                { model: 'deepseek-chat', display_name: 'DeepSeek Chat', provider: 'deepsearch' },
                { model: 'deepseek-coder', display_name: 'DeepSeek Coder', provider: 'deepsearch' }
            ],
            bigmodel: [
                { model: 'glm-4', display_name: 'GLM-4', provider: 'bigmodel' },
                { model: 'glm-3-turbo', display_name: 'GLM-3 Turbo', provider: 'bigmodel' }
            ],
            openai: [
                { model: 'gpt-4', display_name: 'GPT-4', provider: 'openai' },
                { model: 'gpt-4-turbo', display_name: 'GPT-4 Turbo', provider: 'openai' },
                { model: 'gpt-3.5-turbo', display_name: 'GPT-3.5 Turbo', provider: 'openai' }
            ]
        };

        return defaultModels[provider] || [];
    }

    /**
     * Update all model selects with available models
     */
    updateAllModelSelects() {
        const agentCards = ConfigElements.agentContainer?.querySelectorAll('.agent-config-card') || [];

        agentCards.forEach((card, index) => {
            const providerSelect = card.querySelector(`[name="provider_${index}"]`);
            if (providerSelect && providerSelect.value) {
                this.updateModelSelectForAgent(index);
            }
        });
    }

    /**
     * Enhanced debounced validation with configurable delay
     */
    debounceValidation(provider, value, delay = 500) {
        // Clear existing timer for this provider
        if (this.debounceTimers[provider]) {
            clearTimeout(this.debounceTimers[provider]);
        }

        // Skip validation if value is empty
        if (!value || !value.trim()) {
            this.clearValidationStatus(provider);
            return;
        }

        // Set new timer
        this.debounceTimers[provider] = setTimeout(async () => {
            // Check if value has changed since timer was set
            const currentInput = ConfigElements.apiKeyInputs[provider];
            if (currentInput && currentInput.value.trim() === value.trim()) {
                await this.performDebouncedValidation(provider, value);
            }
        }, delay);
    }

    /**
     * Perform debounced validation with smart caching
     */
    async performDebouncedValidation(provider, value) {
        try {
            // First, perform client-side format validation
            if (!this.validateAPIKeyFormat(provider, value)) {
                return false;
            }

            // Check if we already have a recent successful validation for this key
            const validationKey = `${provider}:${value.substring(0, 8)}`; // Use first 8 chars as cache key
            const cachedResult = this.getValidationCache(validationKey);

            if (cachedResult && (Date.now() - cachedResult.timestamp) < 300000) { // 5 minutes cache
                console.log(`Using cached validation for ${provider}`);
                this.setValidationStatus(provider, cachedResult.status, cachedResult.message);

                if (cachedResult.status === 'valid' && cachedResult.models) {
                    ConfigState.availableModels[provider] = cachedResult.models;
                    this.updateAllModelSelects();
                }
                return cachedResult.status === 'valid';
            }

            // Set status to pending
            this.setValidationStatus(provider, 'pending', 'Ready to validate');

            return true; // Format is valid, waiting for user to click validate button

        } catch (error) {
            console.error(`Debounced validation error for ${provider}:`, error);
            this.setValidationStatus(provider, 'error', 'Validation error');
            return false;
        }
    }

    /**
     * Get cached validation result
     */
    getValidationCache(key) {
        if (!this.validationCache) {
            this.validationCache = new Map();
        }
        return this.validationCache.get(key);
    }

    /**
     * Set cached validation result
     */
    setValidationCache(key, result) {
        if (!this.validationCache) {
            this.validationCache = new Map();
        }
        this.validationCache.set(key, {
            ...result,
            timestamp: Date.now()
        });

        // Clean old cache entries (keep only last 50)
        if (this.validationCache.size > 50) {
            const entries = Array.from(this.validationCache.entries());
            entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
            const toDelete = entries.slice(0, this.validationCache.size - 40);
            toDelete.forEach(([k]) => this.validationCache.delete(k));
        }
    }

    /**
     * Debounced model loading for performance optimization
     */
    debounceModelLoading(agentId, provider, delay = 200) {
        const cacheKey = `model_loading_${agentId}`;

        // Clear existing timer
        if (this.debounceTimers[cacheKey]) {
            clearTimeout(this.debounceTimers[cacheKey]);
        }

        // Set new timer
        this.debounceTimers[cacheKey] = setTimeout(() => {
            this.loadAvailableModelsForAgent(agentId, provider);
        }, delay);
    }

    /**
     * Batch API key validation for multiple providers
     */
    async validateMultipleAPIKeys(providers) {
        const results = {};
        const validationPromises = [];

        // Create validation promises for all providers
        providers.forEach(provider => {
            const input = ConfigElements.apiKeyInputs[provider];
            if (input && input.value.trim()) {
                validationPromises.push(
                    this.validateAPIKey(provider, true)
                        .then(result => {
                            results[provider] = result;
                        })
                        .catch(error => {
                            console.error(`Failed to validate ${provider}:`, error);
                            results[provider] = false;
                        })
                );
            }
        });

        // Wait for all validations to complete
        await Promise.allSettled(validationPromises);

        return results;
    }

    /**
     * Smart model loading based on user behavior
     */
    async smartModelLoading() {
        // Get all agents with selected providers
        const agentCards = ConfigElements.agentContainer?.querySelectorAll('.agent-config-card') || [];
        const uniqueProviders = new Set();

        agentCards.forEach((card, index) => {
            const providerSelect = card.querySelector(`[name="provider_${index}"]`);
            if (providerSelect && providerSelect.value) {
                uniqueProviders.add(providerSelect.value);
            }
        });

        // Load models for all unique providers in parallel
        const loadingPromises = Array.from(uniqueProviders).map(provider => {
            return this.ensureModelsLoaded(provider);
        });

        try {
            await Promise.allSettled(loadingPromises);
            console.log('Smart model loading completed');
        } catch (error) {
            console.error('Smart model loading error:', error);
        }
    }

    /**
     * Ensure models are loaded for a provider
     */
    async ensureModelsLoaded(provider) {
        if (ConfigState.availableModels[provider] && ConfigState.availableModels[provider].length > 0) {
            return ConfigState.availableModels[provider];
        }

        // Try to load models by validating API key
        const apiKeyInput = ConfigElements.apiKeyInputs[provider];
        if (apiKeyInput && apiKeyInput.value.trim()) {
            const validationResult = await this.validateAPIKey(provider, true);
            if (validationResult && ConfigState.availableModels[provider]) {
                return ConfigState.availableModels[provider];
            }
        }

        // Return default models
        const defaultModels = this.getDefaultModels(provider);
        ConfigState.availableModels[provider] = defaultModels;
        return defaultModels;
    }

    /**
     * Optimized model selection update
     */
    updateModelSelectForAgent(index, models = null) {
        const providerSelect = document.querySelector(`[name="provider_${index}"]`);
        const modelSelect = document.querySelector(`[name="model_${index}"]`);

        if (!providerSelect || !modelSelect) return;

        const selectedProvider = providerSelect.value;
        const currentModel = modelSelect.value;

        // Clear current options
        modelSelect.innerHTML = '<option value="">Select model</option>';

        if (models === null) {
            // Use cached models or load them
            if (selectedProvider && ConfigState.availableModels[selectedProvider]) {
                models = ConfigState.availableModels[selectedProvider];
            } else if (selectedProvider) {
                // Trigger debounced loading
                this.debounceModelLoading(index, selectedProvider);
                models = [];
            }
        }

        // Add model options
        if (models && models.length > 0) {
            models.forEach(modelInfo => {
                const option = document.createElement('option');
                option.value = modelInfo.model;
                option.textContent = modelInfo.display_name || modelInfo.model;

                // Add capabilities as data attributes if available
                if (modelInfo.capabilities) {
                    option.setAttribute('data-capabilities', JSON.stringify(modelInfo.capabilities));
                }

                if (modelInfo.model === currentModel) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        } else {
            // Add placeholder option
            const option = document.createElement('option');
            option.value = '';
            option.textContent = selectedProvider ?
                'No models available (validate API key first)' :
                'Select a provider first';
            option.disabled = true;
            modelSelect.appendChild(option);
        }

        // Trigger change event for other listeners
        modelSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }

    /**
     * Clear validation cache (useful for testing or manual refresh)
     */
    clearValidationCache() {
        if (this.validationCache) {
            this.validationCache.clear();
        }
        console.log('Validation cache cleared');
    }

    /**
     * Performance monitoring for validation operations
     */
    monitorValidationPerformance(provider, operation, startTime, endTime, success) {
        const duration = endTime - startTime;
        const performanceData = {
            provider,
            operation,
            duration,
            success,
            timestamp: Date.now()
        };

        // Store in performance history (keep last 100 entries)
        if (!this.performanceHistory) {
            this.performanceHistory = [];
        }
        this.performanceHistory.push(performanceData);

        if (this.performanceHistory.length > 100) {
            this.performanceHistory = this.performanceHistory.slice(-100);
        }

        // Log slow operations
        if (duration > 2000) {
            console.warn(`Slow validation operation: ${provider} ${operation} took ${duration}ms`);
        }
    }

    /**
     * Initialize Bootstrap tooltips
     */
    initializeTooltips() {
        // Initialize all tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + S to save
            if ((event.ctrlKey || event.metaKey) && event.key === 's') {
                event.preventDefault();
                if (!ConfigState.isSaving) {
                    this.saveConfiguration();
                }
            }

            // Ctrl/Cmd + E to export
            if ((event.ctrlKey || event.metaKey) && event.key === 'e') {
                event.preventDefault();
                this.exportConfiguration();
            }

            // Ctrl/Cmd + I to import
            if ((event.ctrlKey || event.metaKey) && event.key === 'i') {
                event.preventDefault();
                this.showImportModal();
            }

            // Escape to close modals
            if (event.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }

    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade-in`;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        `;

        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    /**
     * Handle form submission with validation
     */
    async handleFormSubmit(event) {
        event.preventDefault();

        try {
            // Validate entire form first
            const validationResult = await this.validateEntireForm();

            if (!validationResult.isValid) {
                this.showNotification('Please correct validation errors before saving', 'error');
                this.highlightValidationErrors(validationResult.errors);
                return;
            }

            // Save the configuration
            await this.saveConfiguration();

        } catch (error) {
            console.error('Form submission error:', error);
            this.showNotification('Failed to save configuration: ' + error.message, 'error');
        }
    }

    /**
     * Validate entire form before submission
     */
    async validateEntireForm() {
        const errors = [];
        const warnings = [];

        // Validate API keys
        const apiKeyValidation = await this.validateAllAPIKeys();
        if (!apiKeyValidation.isValid) {
            errors.push(...apiKeyValidation.errors);
        }
        warnings.push(...apiKeyValidation.warnings);

        // Validate agent configurations
        const agentValidation = this.validateAgentConfigurations();
        if (!agentValidation.isValid) {
            errors.push(...agentValidation.errors);
        }
        warnings.push(...agentValidation.warnings);

        return {
            isValid: errors.length === 0,
            errors: errors,
            warnings: warnings,
            hasWarnings: warnings.length > 0
        };
    }

    /**
     * Validate all API keys
     */
    async validateAllAPIKeys() {
        const errors = [];
        const warnings = [];
        let hasValidKey = false;

        for (const provider of this.providers) {
            const input = ConfigElements.apiKeyInputs[provider];

            if (!input) continue;

            const value = input.value.trim();

            if (!value) {
                // API key is optional, but warn if no keys are configured
                continue;
            }

            // Format validation
            if (!this.validateAPIKeyFormat(provider, value)) {
                errors.push(`Invalid ${provider} API key format`);
                continue;
            }

            // Check if validated
            const validationResult = ConfigState.validationResults[provider];
            if (!validationResult || validationResult.status !== 'valid') {
                warnings.push(`${provider} API key has not been validated. Consider validating before saving.`);
            } else {
                hasValidKey = true;
            }
        }

        // Require at least one valid API key
        if (!hasValidKey) {
            errors.push('At least one valid API key must be configured');
        }

        return {
            isValid: errors.length === 0,
            errors: errors,
            warnings: warnings
        };
    }

    /**
     * Validate agent configurations
     */
    validateAgentConfigurations() {
        const errors = [];
        const warnings = [];

        if (!ConfigElements.agentContainer) {
            return { isValid: true, errors: [], warnings: [] };
        }

        const agentCards = ConfigElements.agentContainer.querySelectorAll('.agent-config-card');
        const agentIds = new Set();

        agentCards.forEach((card, index) => {
            const agentIdInput = card.querySelector(`[name="agent_id_${index}"]`);
            const providerSelect = card.querySelector(`[name="provider_${index}"]`);
            const modelSelect = card.querySelector(`[name="model_${index}"]`);

            // Validate agent ID
            if (!agentIdInput || !agentIdInput.value.trim()) {
                errors.push(`Agent ${index + 1}: Agent ID is required`);
            } else if (agentIdInput.value.trim().length < 2) {
                errors.push(`Agent ${index + 1}: Agent ID must be at least 2 characters`);
            } else {
                const agentId = agentIdInput.value.trim().toLowerCase();
                if (agentIds.has(agentId)) {
                    errors.push(`Agent ${index + 1}: Duplicate agent ID "${agentId}"`);
                } else {
                    agentIds.add(agentId);
                }
            }

            // Validate provider
            if (!providerSelect || !providerSelect.value) {
                warnings.push(`Agent ${index + 1}: No provider selected`);
            }

            // Validate model
            if (!modelSelect || !modelSelect.value) {
                warnings.push(`Agent ${index + 1}: No model selected`);
            } else {
                // Check if model is available for selected provider
                const selectedProvider = providerSelect?.value;
                const selectedModel = modelSelect.value;

                if (selectedProvider && ConfigState.availableModels[selectedProvider]) {
                    const availableModels = ConfigState.availableModels[selectedProvider].map(m => m.model);
                    if (!availableModels.includes(selectedModel)) {
                        warnings.push(`Agent ${index + 1}: Model "${selectedModel}" may not be available for provider "${selectedProvider}"`);
                    }
                }
            }
        });

        // Require at least one agent configuration
        if (agentCards.length === 0) {
            warnings.push('No agent configurations defined. Consider adding at least one agent for better podcast generation.');
        }

        return {
            isValid: errors.length === 0,
            errors: errors,
            warnings: warnings
        };
    }

    /**
     * Highlight validation errors in the UI
     */
    highlightValidationErrors(errors) {
        // Clear previous error highlighting
        document.querySelectorAll('.is-invalid, .validation-error').forEach(element => {
            element.classList.remove('is-invalid', 'validation-error');
        });

        // Highlight API key errors
        errors.forEach(error => {
            if (error.includes('API key')) {
                const provider = this.providers.find(p => error.toLowerCase().includes(p));
                if (provider) {
                    const input = ConfigElements.apiKeyInputs[provider];
                    if (input) {
                        input.classList.add('is-invalid', 'validation-error');
                        this.setValidationStatus(provider, 'invalid', error);
                    }
                }
            }
        });

        // Highlight agent configuration errors
        errors.forEach(error => {
            if (error.includes('Agent')) {
                const match = error.match(/Agent (\d+):/);
                if (match) {
                    const agentIndex = parseInt(match[1]) - 1;
                    const agentCard = ConfigElements.agentContainer?.children[agentIndex];
                    if (agentCard) {
                        agentCard.classList.add('validation-error', 'border-danger');
                        agentCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        });
    }

    /**
     * Enhanced API key validation with server validation and caching
     */
    async validateAPIKey(provider, forceValidate = false) {
        const input = ConfigElements.apiKeyInputs[provider];
        const button = ConfigElements.validationButtons[provider];

        if (!input || !input.value.trim()) {
            this.showNotification('Please enter an API key first', 'warning');
            return false;
        }

        const startTime = Date.now();
        const apiKey = input.value.trim();

        // Check cache first (unless forced validation)
        if (!forceValidate) {
            const validationKey = `${provider}:${apiKey.substring(0, 8)}`;
            const cachedResult = this.getValidationCache(validationKey);

            if (cachedResult && (Date.now() - cachedResult.timestamp) < 300000) { // 5 minutes cache
                console.log(`Using cached validation for ${provider}`);
                this.setValidationStatus(provider, cachedResult.status, cachedResult.message);

                if (cachedResult.status === 'valid' && cachedResult.models) {
                    ConfigState.availableModels[provider] = cachedResult.models;
                    this.updateAllModelSelects();
                }

                this.monitorValidationPerformance(provider, 'cache_lookup', startTime, Date.now(), true);
                return cachedResult.status === 'valid';
            }
        }

        if (ConfigState.isValidating && !forceValidate) return false;

        try {
            ConfigState.isValidating = true;
            this.setValidationStatus(provider, 'validating');

            if (button) {
                button.disabled = true;
                button.classList.add('loading');
            }

            console.log(`Validating ${provider} API key...`);

            const response = await this.apiRequest(this.apiEndpoints.validate, {
                method: 'POST',
                body: JSON.stringify({
                    provider: provider,
                    api_key: apiKey
                })
            });

            const endTime = Date.now();
            const duration = endTime - startTime;

            if (response.success && response.data.validation_result.valid) {
                const successMessage = 'API key is valid and connected';
                this.setValidationStatus(provider, 'valid', successMessage);
                ConfigState.lastSuccess = `${provider} API key validated successfully`;

                // Cache the successful result
                const validationKey = `${provider}:${apiKey.substring(0, 8)}`;
                this.setValidationCache(validationKey, {
                    status: 'valid',
                    message: successMessage,
                    models: response.data.available_models
                });

                // Load available models for this provider
                if (response.data.available_models && response.data.available_models.length > 0) {
                    ConfigState.availableModels[provider] = response.data.available_models;
                    this.updateAllModelSelects();

                    this.showNotification(`${provider} API key validated successfully. ${response.data.available_models.length} models available.`, 'success');
                } else {
                    this.showNotification(`${provider} API key validated successfully`, 'success');
                }

                this.monitorValidationPerformance(provider, 'validation_success', startTime, endTime, true);
                return true;
            } else {
                const errorMsg = response.data?.validation_result?.error || 'API key validation failed';
                this.setValidationStatus(provider, 'invalid', errorMsg);
                this.showNotification(`${provider} API key validation failed: ${errorMsg}`, 'error');

                // Cache the failed result (with shorter cache time)
                const validationKey = `${provider}:${apiKey.substring(0, 8)}`;
                this.setValidationCache(validationKey, {
                    status: 'invalid',
                    message: errorMsg,
                    models: null
                });

                this.monitorValidationPerformance(provider, 'validation_failed', startTime, endTime, false);
                return false;
            }
        } catch (error) {
            const endTime = Date.now();
            console.error(`Failed to validate ${provider} API key:`, error);
            this.setValidationStatus(provider, 'error', 'Validation failed: ' + error.message);
            this.showNotification(`Failed to validate ${provider} API key: ${error.message}`, 'error');

            // Cache the error result (with short cache time)
            const validationKey = `${provider}:${apiKey.substring(0, 8)}`;
            this.setValidationCache(validationKey, {
                status: 'error',
                message: 'Validation failed: ' + error.message,
                models: null
            });

            this.monitorValidationPerformance(provider, 'validation_error', startTime, endTime, false);
            return false;
        } finally {
            ConfigState.isValidating = false;
            if (button) {
                button.disabled = false;
                button.classList.remove('loading');
            }
        }
    }

    /**
     * Update model selects with available models
     */
    updateModelSelects() {
        const agentCards = ConfigElements.agentContainer?.querySelectorAll('.agent-config-card') || [];

        agentCards.forEach((card, index) => {
            const providerSelect = card.querySelector(`[name="provider_${index}"]`);
            const modelSelect = card.querySelector(`[name="model_${index}"]`);

            if (providerSelect && modelSelect) {
                // Store current selection
                const currentModel = modelSelect.value;

                // Clear current options
                modelSelect.innerHTML = '<option value="">Select model</option>';

                // Add models based on selected provider
                const selectedProvider = providerSelect.value;
                if (selectedProvider && ConfigState.availableModels[selectedProvider]) {
                    ConfigState.availableModels[selectedProvider].forEach(modelInfo => {
                        const option = document.createElement('option');
                        option.value = modelInfo.model;
                        option.textContent = modelInfo.display_name || modelInfo.model;
                        if (modelInfo.model === currentModel) {
                            option.selected = true;
                        }
                        modelSelect.appendChild(option);
                    });
                }
            }
        });
    }

    /**
     * Enhanced save configuration with comprehensive validation
     */
    async saveConfiguration() {
        if (ConfigState.isSaving) {
            this.showNotification('Configuration is already being saved', 'warning');
            return;
        }

        try {
            ConfigState.isSaving = true;
            this.setSavingState(true);

            console.log('Saving configuration...');

            // Collect form data
            const configData = this.collectFormData();

            // Validate before saving
            const validationResult = await this.validateEntireForm();
            if (!validationResult.isValid) {
                throw new Error('Configuration validation failed: ' + validationResult.errors.join(', '));
            }

            // Show warnings if any
            if (validationResult.hasWarnings) {
                const warningMessage = validationResult.warnings.join('\n');
                if (!confirm(`Warning:\n${warningMessage}\n\nDo you want to continue saving?`)) {
                    return;
                }
            }

            // Save API keys
            if (Object.keys(configData.api_keys).length > 0) {
                await this.saveAPIKeys(configData.api_keys);
            }

            // Save agent configurations
            if (configData.agent_configs.length > 0) {
                await this.saveAgentConfig(configData.agent_configs);
            }

            // Update current configuration
            ConfigState.currentConfiguration = { ...ConfigState.currentConfiguration, ...configData };

            // Update status indicators
            this.updateStatusIndicators();

            console.log('Configuration saved successfully');
            this.showNotification('Configuration saved successfully', 'success');
            ConfigState.lastSuccess = 'Configuration saved successfully';

        } catch (error) {
            console.error('Failed to save configuration:', error);
            ConfigState.lastError = error.message;
            this.showNotification('Failed to save configuration: ' + error.message, 'error');
            throw error;
        } finally {
            ConfigState.isSaving = false;
            this.setSavingState(false);
        }
    }

    /**
     * Collect form data from all inputs
     */
    collectFormData() {
        const apiKeys = {};
        const agentConfigs = [];

        // Collect API keys
        this.providers.forEach(provider => {
            const input = ConfigElements.apiKeyInputs[provider];
            if (input && input.value.trim()) {
                // Only save if the API key has been validated or if it's already saved
                const validationResult = ConfigState.validationResults[provider];
                if (validationResult && (validationResult.status === 'valid' ||
                    (ConfigState.currentConfiguration.api_keys[provider] && input.value !== ConfigState.currentConfiguration.api_keys[provider]))) {
                    apiKeys[provider] = input.value.trim();
                }
            }
        });

        // Collect agent configurations
        const agentCards = ConfigElements.agentContainer?.querySelectorAll('.agent-config-card') || [];
        agentCards.forEach((card, index) => {
            const agentIdInput = card.querySelector(`[name="agent_id_${index}"]`);
            const providerSelect = card.querySelector(`[name="provider_${index}"]`);
            const modelSelect = card.querySelector(`[name="model_${index}"]`);

            if (agentIdInput && agentIdInput.value.trim() &&
                providerSelect && providerSelect.value &&
                modelSelect && modelSelect.value) {

                agentConfigs.push({
                    agent_id: agentIdInput.value.trim(),
                    provider: providerSelect.value,
                    model: modelSelect.value
                });
            }
        });

        return {
            api_keys: apiKeys,
            agent_configs: agentConfigs
        };
    }

    /**
     * Save API keys with validation
     */
    async saveAPIKeys(apiKeys) {
        if (Object.keys(apiKeys).length === 0) {
            return; // No API keys to save
        }

        try {
            const response = await this.apiRequest(this.apiEndpoints.config, {
                method: 'POST',
                body: JSON.stringify({
                    api_keys: apiKeys
                })
            });

            if (!response.success) {
                throw new Error(response.error || 'Failed to save API keys');
            }

            console.log('API keys saved successfully:', Object.keys(apiKeys));
            return response;

        } catch (error) {
            console.error('Failed to save API keys:', error);
            throw new Error(`Failed to save API keys: ${error.message}`);
        }
    }

    /**
     * Save agent configurations
     */
    async saveAgentConfig(agentConfigs) {
        if (agentConfigs.length === 0) {
            return; // No agent configs to save
        }

        try {
            const response = await this.apiRequest(this.apiEndpoints.config, {
                method: 'POST',
                body: JSON.stringify({
                    agent_configs: agentConfigs
                })
            });

            if (!response.success) {
                throw new Error(response.error || 'Failed to save agent configurations');
            }

            console.log('Agent configurations saved successfully:', agentConfigs.length);
            return response;

        } catch (error) {
            console.error('Failed to save agent configurations:', error);
            throw new Error(`Failed to save agent configurations: ${error.message}`);
        }
    }

    /**
     * Clear configuration with confirmation
     */
    async clearConfiguration() {
        if (!confirm('Are you sure you want to clear all configuration? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await this.apiRequest(this.apiEndpoints.config, {
                method: 'DELETE'
            });

            if (response.success) {
                // Clear form
                this.clearForm();

                // Clear state
                ConfigState.currentConfiguration = { api_keys: {}, agent_configs: [] };
                ConfigState.validationResults = {};
                ConfigState.availableModels = {};

                // Update UI
                this.updateStatusIndicators();
                this.updateModelSelects();

                this.showNotification('Configuration cleared successfully', 'success');
            } else {
                throw new Error(response.error || 'Failed to clear configuration');
            }
        } catch (error) {
            console.error('Failed to clear configuration:', error);
            this.showNotification('Failed to clear configuration: ' + error.message, 'error');
        }
    }

    /**
     * Clear form inputs
     */
    clearForm() {
        // Clear API key inputs
        this.providers.forEach(provider => {
            const input = ConfigElements.apiKeyInputs[provider];
            if (input) {
                input.value = '';
                input.classList.remove('is-valid', 'is-invalid');
            }
            this.setValidationStatus(provider, 'empty');
        });

        // Clear agent configurations
        if (ConfigElements.agentContainer) {
            ConfigElements.agentContainer.innerHTML = '';
        }

        this.updateAgentCount();
    }

    async exportConfiguration() {
        // Implementation will be added in next task
        console.log('Export configuration - to be implemented');
    }

    showImportModal() {
        // Implementation will be added in next task
        console.log('Show import modal - to be implemented');
    }

    async importConfiguration() {
        // Implementation will be added in next task
        console.log('Import configuration - to be implemented');
    }

    copyToClipboard(elementId) {
        // Implementation will be added in next task
        console.log('Copy to clipboard - to be implemented');
    }

    closeAllModals() {
        // Close all open modals
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }
}

// Global instance
let configManager = null;

/**
 * Initialize configuration manager when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    configManager = new ConfigurationManager();
});

// Export for global access
window.ConfigManager = ConfigurationManager;
window.configManager = configManager;