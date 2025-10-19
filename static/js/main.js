/**
 * Main JavaScript for Podcast Generation Application
 * Enhanced with improved AJAX calls, audio controls, and download functionality
 * Handles dynamic form interactions and user interface enhancements
 */

// Application state management
const AppState = {
    isGenerating: false,
    currentStep: 1,
    formData: {},
    audioElement: null,
    progressInterval: null,
    generationId: null,
    audioUrl: null,
    downloadUrl: null,
    retryCount: 0,
    maxRetries: 3,
    // Form data persistence
    autoSaveTimeout: null,
    autoSaveDelay: 2000, // 2 seconds after form change
    hasUnsavedChanges: false
};

// DOM element cache
const Elements = {
    form: null,
    participantsSelect: null,
    characterConfig: null,
    generateBtn: null,
    progressSection: null,
    resultsSection: null,
    errorSection: null,
    progressBar: null,
    progressMessages: null,
    audioPlayer: null,
    downloadBtn: null,
    retryBtn: null,
    cancelBtn: null,
    copyLinkBtn: null,
    shareBtn: null,
    newPodcastBtn: null,
    resetFormBtn: null,
    reportIssueBtn: null,
    formValidationMessage: null,
    topicTextarea: null,
    topicCounter: null,
    characterCountBadge: null,
    fileSizeElement: null,
    audioDurationElement: null,
    generationTimestampElement: null,
    podcastTitleElement: null
};

/**
 * Initialize the application when DOM is ready
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    console.log("=== DEBUG: App initialization starting ===");
    cacheElements();
    setupEventListeners();
    initializeForm();
    initializeAPIConfiguration();
    initializeFormDataPersistence();
    console.log('Podcast Generation App initialized');
    console.log("=== DEBUG: App initialization completed ===");
}

/**
 * Cache DOM elements for better performance
 */
function cacheElements() {
    Elements.form = document.getElementById('generateForm');
    Elements.participantsSelect = document.getElementById('participants');
    Elements.characterConfig = document.getElementById('character-config');
    Elements.generateBtn = document.getElementById('generateBtn');
    Elements.progressSection = document.getElementById('progress-section');
    Elements.resultsSection = document.getElementById('results-section');
    Elements.errorSection = document.getElementById('error-section');
    Elements.progressBar = document.getElementById('progressBar');
    Elements.progressMessages = document.getElementById('progress-messages');
    Elements.audioPlayer = document.getElementById('audioPlayer');
    Elements.downloadBtn = document.getElementById('downloadBtn');
    Elements.retryBtn = document.getElementById('retryBtn');
    Elements.cancelBtn = document.getElementById('cancelBtn');
    Elements.copyLinkBtn = document.getElementById('copyLinkBtn');
    Elements.shareBtn = document.getElementById('shareBtn');
    Elements.newPodcastBtn = document.getElementById('newPodcastBtn');
    Elements.resetFormBtn = document.getElementById('resetFormBtn');
    Elements.reportIssueBtn = document.getElementById('reportIssueBtn');
    Elements.formValidationMessage = document.getElementById('form-validation-message');
    Elements.topicTextarea = document.getElementById('topic');
    Elements.topicCounter = document.querySelector('.topic-counter');
    Elements.characterCountBadge = document.getElementById('character-count');
    Elements.fileSizeElement = document.getElementById('file-size');
    Elements.audioDurationElement = document.getElementById('audio-duration');
    Elements.generationTimestampElement = document.getElementById('generation-timestamp');
    Elements.podcastTitleElement = document.getElementById('podcast-title');
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    console.log("=== DEBUG: Setting up event listeners ===");

    // Form interactions
    if (Elements.participantsSelect) {
        Elements.participantsSelect.addEventListener('change', handleParticipantsChange);
        console.log("DEBUG: Participants select event listener added");
    } else {
        console.log("ERROR: Participants select element not found!");
    }

    if (Elements.form) {
        Elements.form.addEventListener('submit', handleFormSubmit);
        console.log("DEBUG: Form submit event listener added");
    } else {
        console.log("ERROR: Form element not found!");
    }

    // Topic textarea counter
    if (Elements.topicTextarea && Elements.topicCounter) {
        Elements.topicTextarea.addEventListener('input', handleTopicInput);
    }

    // Button interactions
    if (Elements.generateBtn) {
        Elements.generateBtn.addEventListener('click', handleGenerateClick);
        console.log("DEBUG: Generate button event listener added");
    } else {
        console.log("ERROR: Generate button not found!");
    }

    if (Elements.retryBtn) {
        Elements.retryBtn.addEventListener('click', handleRetry);
    }

    if (Elements.downloadBtn) {
        Elements.downloadBtn.addEventListener('click', handleDownload);
    }

    if (Elements.cancelBtn) {
        Elements.cancelBtn.addEventListener('click', handleCancel);
    }

    if (Elements.copyLinkBtn) {
        Elements.copyLinkBtn.addEventListener('click', handleCopyLink);
    }

    if (Elements.shareBtn) {
        Elements.shareBtn.addEventListener('click', handleShare);
    }

    if (Elements.newPodcastBtn) {
        Elements.newPodcastBtn.addEventListener('click', handleNewPodcast);
    }

    if (Elements.resetFormBtn) {
        Elements.resetFormBtn.addEventListener('click', handleResetForm);
    }

    if (Elements.reportIssueBtn) {
        Elements.reportIssueBtn.addEventListener('click', handleReportIssue);
    }

    // Audio player interactions
    if (Elements.audioPlayer) {
        setupAudioPlayer();
    }

    // Character configuration interactions
    setupCharacterInteractions();

    // Keyboard shortcuts
    setupKeyboardShortcuts();

    // Form validation
    setupFormValidation();

    // Enhanced form monitoring
    setupFormMonitoring();

    // Page visibility handling
    setupVisibilityHandling();
}

/**
 * Initialize form with default values
 */
function initializeForm() {
    if (Elements.participantsSelect) {
        updateCharacterConfig(parseInt(Elements.participantsSelect.value) || 2);
    }

    // Initialize topic counter
    if (Elements.topicTextarea && Elements.topicCounter) {
        handleTopicInput.call(Elements.topicTextarea);
    }

    // Initialize character count badge
    updateCharacterCountBadge();
}

/**
 * Handle participants number change
 */
function handleParticipantsChange(event) {
    const participants = parseInt(event.target.value) || 2;
    updateCharacterConfig(participants);
}

/**
 * Update character configuration based on number of participants
 */
function updateCharacterConfig(participants) {
    if (!Elements.characterConfig) return;

    // Clear existing configuration
    Elements.characterConfig.innerHTML = '';

    // Create character cards for each participant
    for (let i = 1; i <= participants; i++) {
        const characterCard = createCharacterCard(i);
        Elements.characterConfig.appendChild(characterCard);
    }

    // Add fade-in animation
    Elements.characterConfig.classList.add('fade-in');

    // Update character count badge
    updateCharacterCountBadge();
}

/**
 * Update character count badge
 */
function updateCharacterCountBadge() {
    if (Elements.characterCountBadge && Elements.participantsSelect) {
        const count = parseInt(Elements.participantsSelect.value) || 2;
        Elements.characterCountBadge.textContent = `${count}个角色`;
    }
}

/**
 * Create a character configuration card
 */
function createCharacterCard(characterNumber) {
    const card = document.createElement('div');
    card.className = 'character-card';
    card.innerHTML = `
        <div class="character-header">
            <span>角色 ${characterNumber}</span>
            <button type="button" class="btn btn-sm btn-outline-secondary"
                    onclick="toggleCharacterCard(this)" title="展开/收起">
                <span>−</span>
            </button>
        </div>
        <div class="character-content">
            <div class="row">
                <div class="col-md-3 mb-3">
                    <label class="form-label">
                        姓名 <span class="text-danger">*</span>
                        <span class="form-text d-block">输入角色姓名</span>
                    </label>
                    <input type="text"
                           class="form-control"
                           name="character_${characterNumber}_name"
                           placeholder="例如：陈博士"
                           required
                           maxlength="100"
                           data-validation="required|min:2|max:100">
                </div>
                <div class="col-md-3 mb-3">
                    <label class="form-label">
                        性别 <span class="text-danger">*</span>
                        <span class="form-text d-block">选择角色性别</span>
                    </label>
                    <select class="form-select"
                            name="character_${characterNumber}_gender"
                            required
                            data-validation="required"
                            onchange="updateAgeAndStyleOptions(${characterNumber})">
                        <option value="">选择性别</option>
                        <option value="男性">男性</option>
                        <option value="女性">女性</option>
                    </select>
                </div>
                <div class="col-md-3 mb-3">
                    <label class="form-label">
                        年龄 <span class="text-danger">*</span>
                        <span class="form-text d-block">选择角色年龄</span>
                    </label>
                    <select class="form-select"
                            name="character_${characterNumber}_age"
                            required
                            data-validation="required"
                            onchange="updateStyleOptions(${characterNumber})">
                        <option value="">请先选择性别</option>
                    </select>
                </div>
                <div class="col-md-3 mb-3">
                    <label class="form-label">
                        声音风格 <span class="text-danger">*</span>
                        <span class="form-text d-block">选择声音风格</span>
                    </label>
                    <select class="form-select"
                            name="character_${characterNumber}_style"
                            required
                            data-validation="required">
                        <option value="">请先选择性别和年龄</option>
                    </select>
                    <div id="style-description-${characterNumber}" class="form-text text-muted mt-1"></div>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">
                    性格特点 <span class="text-danger">*</span>
                    <span class="form-text d-block">角色的说话风格和个性</span>
                </label>
                <select class="form-select"
                            name="character_${characterNumber}_personality"
                            required
                            data-validation="required"
                            onchange="updatePersonalityHint(${characterNumber}, this.value)">
                        <option value="">选择性格</option>
                        <option value="professional">专业型</option>
                        <option value="casual">轻松型</option>
                        <option value="energetic">活力型</option>
                        <option value="calm">冷静型</option>
                        <option value="humorous">幽默型</option>
                        <option value="analytical">分析型</option>
                        <option value="enthusiastic">热情型</option>
                        <option value="skeptical">怀疑型</option>
                    </select>
                    <div id="personality-hint-${characterNumber}" class="form-text text-muted mt-1"></div>
            </div>
            <div class="mb-3">
                <label class="form-label">
                    背景 <span class="text-danger">*</span>
                    <span class="form-text d-block">
                        角色的专业知识、角色定位和对主题的观点
                    </span>
                </label>
                <textarea class="form-control"
                          name="character_${characterNumber}_background"
                          rows="3"
                          placeholder="例如：一位拥有15年可再生能源研究经验的气候科学家..."
                          required
                          maxlength="500"
                          data-validation="required|min:20|max:500"></textarea>
                <div class="d-flex justify-content-between mt-1">
                    <small class="text-muted">描述角色的专业知识和角色</small>
                    <small class="character-count">0/500</small>
                </div>
            </div>
            <div class="mb-3">
                <label class="form-label">
                    AI模型选择
                    <span class="form-text d-block">为此角色选择AI模型</span>
                </label>
                <select class="form-select" name="character_${characterNumber}_model" id="character-model-${characterNumber}">
                    <option value="">自动选择</option>
                    <option value="deepseek-deepseek-chat">DeepSeek - deepseek-chat</option>
                    <option value="bigmodel-glm-4">智谱AI - glm-4</option>
                    <option value="openai-gpt-4">OpenAI - gpt-4</option>
                    <option value="openai-gpt-3.5-turbo">OpenAI - gpt-3.5-turbo</option>
                </select>
                <div class="form-text text-muted mt-1">
                    <i class="bi bi-info-circle me-1"></i>
                    请先在上方配置相应的API密钥
                </div>
            </div>
        </div>
    `;

    // Add character count listener
    const textarea = card.querySelector('textarea');
    const counter = card.querySelector('.character-count');

    textarea.addEventListener('input', function() {
        const length = this.value.length;
        counter.textContent = `${length}/500`;
        counter.className = length > 450 ? 'character-count text-warning' : 'character-count text-muted';
    });

    // Add validation listeners
    addValidationListeners(card);

    return card;
}

/**
 * Setup character interactions
 */
function setupCharacterInteractions() {
    // Character card collapse functionality
    window.toggleCharacterCard = function(button) {
        const content = button.closest('.character-card').querySelector('.character-content');
        const span = button.querySelector('span');

        if (content.style.display === 'none') {
            content.style.display = 'block';
            span.textContent = '−';
        } else {
            content.style.display = 'none';
            span.textContent = '+';
        }
    };

    // Personality hint functionality
    window.updatePersonalityHint = function(characterNumber, personality) {
        const hintElement = document.getElementById(`personality-hint-${characterNumber}`);
        const hints = {
            professional: '正式语调，适当使用专业术语',
            casual: '轻松语调，使用日常语言',
            energetic: '高能量，热情洋溢的表达',
            calm: '稳健的节奏，舒缓的语调',
            humorous: '轻松愉快，偶尔开玩笑',
            analytical: '详细、逻辑清晰的解释',
            enthusiastic: '充满激情，引人入胜的表达',
            skeptical: '质疑性、批判性的观点'
        };

        if (hintElement && hints[personality]) {
            hintElement.textContent = hints[personality];
        } else if (hintElement) {
            hintElement.textContent = '';
        }
    };

    // Voice preference functionality
    window.updateAgeAndStyleOptions = function(characterNumber) {
        updateAgeOptions(characterNumber);
        updateStyleOptions(characterNumber);
    };

    window.updateAgeOptions = function(characterNumber) {
        const genderSelect = document.querySelector(`select[name="character_${characterNumber}_gender"]`);
        const ageSelect = document.querySelector(`select[name="character_${characterNumber}_age"]`);

        if (!genderSelect || !ageSelect) return;

        const selectedGender = genderSelect.value;

        // Clear age options
        ageSelect.innerHTML = '<option value="">选择年龄</option>';

        if (!selectedGender) {
            ageSelect.innerHTML = '<option value="">请先选择性别</option>';
            return;
        }

        // Load voice preferences data
        loadVoicePreferences().then(data => {
            if (data && data.年龄选项) {
                Object.entries(data.年龄选项).forEach(([key, value]) => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value;
                    ageSelect.appendChild(option);
                });
            }
        }).catch(error => {
            console.error('Failed to load age options:', error);
            // Fallback age options
            const fallbackAges = ['年轻', '中年', '其他'];
            fallbackAges.forEach(age => {
                const option = document.createElement('option');
                option.value = age;
                option.textContent = age;
                ageSelect.appendChild(option);
            });
        });
    };

    window.updateStyleOptions = function(characterNumber) {
        const genderSelect = document.querySelector(`select[name="character_${characterNumber}_gender"]`);
        const ageSelect = document.querySelector(`select[name="character_${characterNumber}_age"]`);
        const styleSelect = document.querySelector(`select[name="character_${characterNumber}_style"]`);
        const descriptionDiv = document.getElementById(`style-description-${characterNumber}`);

        if (!genderSelect || !ageSelect || !styleSelect) return;

        const selectedGender = genderSelect.value;
        const selectedAge = ageSelect.value;

        // Clear style options
        styleSelect.innerHTML = '<option value="">选择声音风格</option>';
        if (descriptionDiv) {
            descriptionDiv.textContent = '';
        }

        if (!selectedGender || !selectedAge) {
            styleSelect.innerHTML = '<option value="">请先选择性别和年龄</option>';
            return;
        }

        // Load voice preferences data
        loadVoicePreferences().then(data => {
            if (data && data.所有组合) {
                const availableStyles = data.所有组合.filter(combo =>
                    combo.支持性别.includes(selectedGender) &&
                    combo.年龄显示 === selectedAge
                );

                availableStyles.forEach(combo => {
                    const option = document.createElement('option');
                    option.value = combo.风格;
                    option.textContent = combo.风格;
                    option.dataset.description = combo.风格描述;
                    styleSelect.appendChild(option);
                });

                // Show style descriptions on change
                styleSelect.onchange = function() {
                    if (descriptionDiv && this.value) {
                        const selectedOption = this.options[this.selectedIndex];
                        descriptionDiv.textContent = selectedOption.dataset.description || '';
                    } else if (descriptionDiv) {
                        descriptionDiv.textContent = '';
                    }
                };
            }
        }).catch(error => {
            console.error('Failed to load style options:', error);
        });
    };

    // Load voice preferences from API
    async function loadVoicePreferences() {
        try {
            const response = await fetch('/api/all-voice-combinations');
            if (response.ok) {
                const result = await response.json();
                return result.success ? result.data : null;
            }
        } catch (error) {
            console.error('Error loading voice preferences:', error);
        }
        return null;
    }
}

/**
 * Add validation listeners to form fields
 */
function addValidationListeners(container) {
    const fields = container.querySelectorAll('[data-validation]');

    fields.forEach(field => {
        // Validate on blur
        field.addEventListener('blur', () => validateField(field));

        // Clear validation on input
        field.addEventListener('input', () => {
            field.classList.remove('is-invalid', 'is-valid');
            clearFieldError(field);
        });
    });
}

/**
 * Validate a single field
 */
function validateField(field) {
    const validation = field.dataset.validation;
    const value = field.value.trim();
    const rules = validation.split('|');

    let isValid = true;
    let errorMessage = '';

    for (const rule of rules) {
        const [ruleName, ruleValue] = rule.split(':');

        switch (ruleName) {
            case 'required':
                if (!value) {
                    isValid = false;
                    errorMessage = '此字段为必填项';
                }
                break;

            case 'min':
                if (value.length < parseInt(ruleValue)) {
                    isValid = false;
                    errorMessage = `最少需要${ruleValue}个字符`;
                }
                break;

            case 'max':
                if (value.length > parseInt(ruleValue)) {
                    isValid = false;
                    errorMessage = `最多允许${ruleValue}个字符`;
                }
                break;
        }

        if (!isValid) break;
    }

    if (isValid) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        clearFieldError(field);
    } else {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        showFieldError(field, errorMessage);
    }

    return isValid;
}

/**
 * Show field error message
 */
function showFieldError(field, message) {
    clearFieldError(field);

    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;

    field.parentNode.appendChild(errorDiv);
}

/**
 * Clear field error message
 */
function clearFieldError(field) {
    const existingError = field.parentNode.querySelector('.invalid-feedback');
    if (existingError) {
        existingError.remove();
    }
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    if (!Elements.form) return;

    Elements.form.addEventListener('submit', function(event) {
        if (!validateForm()) {
            event.preventDefault();
            return false;
        }
    });
}

/**
 * Validate entire form
 */
function validateForm() {
    if (!Elements.form) return true;

    const fields = Elements.form.querySelectorAll('[data-validation]');
    let isValid = true;

    fields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
        }
    });

    return isValid;
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    console.log("=== DEBUG: Form submit handler called! ===");
    event.preventDefault();

    if (!validateForm()) {
        console.log("DEBUG: Form validation failed!");
        showNotification('请修正表单中的错误', 'error');
        return;
    }

    console.log("DEBUG: Form validation passed, saving configuration...");

    // Save configuration before starting generation
    try {
        await saveConfiguration();
        console.log("DEBUG: Configuration saved successfully");
    } catch (error) {
        console.warn("DEBUG: Failed to save configuration:", error);
        // Continue with generation even if save fails
    }

    console.log("DEBUG: Starting generation...");
    await startGeneration();
}

/**
 * Handle topic input with character counting
 */
function handleTopicInput() {
    const length = this.value.length;
    const maxLength = parseInt(this.getAttribute('maxlength')) || 1000;

    if (Elements.topicCounter) {
        Elements.topicCounter.textContent = `${length}/${maxLength}`;
        Elements.topicCounter.className = length > maxLength * 0.9 ?
            'topic-counter text-warning' : 'topic-counter text-muted';
    }

    // Show/hide validation message based on content
    if (Elements.formValidationMessage) {
        if (length === 0) {
            Elements.formValidationMessage.style.display = 'block';
        } else if (length < 20) {
            Elements.formValidationMessage.style.display = 'block';
            Elements.formValidationMessage.querySelector('i').className = 'bi bi-exclamation-triangle me-2';
            Elements.formValidationMessage.querySelector('strong').textContent = 'Tip:';
            Elements.formValidationMessage.lastChild.textContent =
                ' Please provide more detail about your topic for better results.';
        } else {
            Elements.formValidationMessage.style.display = 'none';
        }
    }
}

/**
 * Update topic counter display
 */
function updateTopicCounter() {
    if (Elements.topicTextarea && Elements.topicCounter) {
        handleTopicInput.call(Elements.topicTextarea);
    }
}

/**
 * Handle generate button click
 */
function handleGenerateClick() {
    console.log("=== DEBUG: handleGenerateClick() called! ===");
    console.log("DEBUG: AppState.isGenerating =", AppState.isGenerating);

    if (AppState.isGenerating) {
        console.log("DEBUG: Cancelling generation...");
        handleCancel();
    } else {
        console.log("DEBUG: Triggering form submit event...");
        Elements.form.dispatchEvent(new Event('submit'));
    }
}

/**
 * Start podcast generation with enhanced AJAX functionality
 */
async function startGeneration() {
    console.log("=== DEBUG: startGeneration() called ===");
    if (AppState.isGenerating) {
        console.log("DEBUG: Generation already in progress, ignoring");
        return;
    }

    AppState.isGenerating = true;
    AppState.generationId = generateUniqueId();
    AppState.retryCount = 0;
    updateUIState('generating');

    try {
        console.log("DEBUG: About to collect form data...");
        const formData = collectFormData();
        console.log("DEBUG: Form data collected, sending to server...");
        console.log("=== DEBUG: Frontend sending to backend ===");
        console.log("Request URL: /generate");
        console.log("Request method: POST");
        console.log("Request headers:", {
            'Content-Type': 'application/json',
            'X-Generation-ID': AppState.generationId,
            'X-Requested-With': 'XMLHttpRequest'
        });
        console.log("Request body (formData):", JSON.stringify(formData, null, 2));
        console.log("=== END DEBUG: Frontend request ===");

        // Enhanced error handling and timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout

        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Generation-ID': AppState.generationId,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(formData),
            signal: controller.signal
        });

        console.log("=== DEBUG: Backend response ===");
        console.log("Response status:", response.status);
        console.log("Response statusText:", response.statusText);
        console.log("Response headers:", [...response.headers.entries()]);

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log("=== DEBUG: Backend response body ===");
        console.log("Response data:", result);
        console.log("=== END DEBUG: Backend response ===");

        if (result.success) {
            await simulateProgress();
            showResults(result);
        } else {
            // Enhanced error handling with retry logic
            if (shouldRetry(result.error) && AppState.retryCount < AppState.maxRetries) {
                AppState.retryCount++;
                console.log(`Retrying generation (attempt ${AppState.retryCount}/${AppState.maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
                return startGeneration();
            }
            showError(result.error || 'Generation failed');
        }
    } catch (error) {
        console.error('Generation error:', error);

        if (error.name === 'AbortError') {
            showError('Generation timed out. Please try again with a simpler topic.');
        } else if (error.name === 'TypeError') {
            showError('Network error. Please check your internet connection and try again.');
        } else if (error.message.includes('429') || error.message.includes('TOO MANY REQUESTS')) {
            // Special handling for rate limit errors
            if (AppState.retryCount < AppState.maxRetries) {
                AppState.retryCount++;
                const waitTime = Math.min(10000 * Math.pow(2, AppState.retryCount - 1), 60000); // Exponential backoff, max 60s
                console.log(`Rate limit hit. Waiting ${waitTime/1000}s before retry (attempt ${AppState.retryCount}/${AppState.maxRetries})`);
                showNotification(`API请求过于频繁，等待${waitTime/1000}秒后重试...`, 'warning');
                await new Promise(resolve => setTimeout(resolve, waitTime));
                return startGeneration();
            } else {
                showError('API请求频率过高，请稍后再试或检查API密钥配置');
            }
        } else {
            showError('An unexpected error occurred. Please try again.');
        }
    } finally {
        stopGeneration();
    }
}

/**
 * Generate unique ID for tracking generation requests
 */
function generateUniqueId() {
    return 'gen_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

/**
 * Determine if generation should be retried based on error
 */
function shouldRetry(error) {
    const retryableErrors = [
        'timeout',
        'network',
        'temporary',
        'overloaded',
        'rate limit',
        'too many requests',
        '429'
    ];

    return retryableErrors.some(retryableError =>
        error.toLowerCase().includes(retryableError)
    );
}

/**
 * Stop podcast generation
 */
function stopGeneration() {
    AppState.isGenerating = false;
    updateUIState('ready');

    if (AppState.progressInterval) {
        clearInterval(AppState.progressInterval);
        AppState.progressInterval = null;
    }
}

/**
 * Collect form data
 */
function collectFormData() {
    console.log("=== DEBUG: collectFormData() START ===");
    const formData = new FormData(Elements.form);
    const flatData = Object.fromEntries(formData.entries());

    console.log("Form flatData keys:", Object.keys(flatData));
    console.log("Full flatData:", flatData);

    // Extract basic fields
    const podcastData = {
        topic: flatData.topic,
        participant_count: flatData.participants || flatData.participants,
        conversation_rounds: flatData.rounds || flatData.conversation_rounds
    };

    console.log("Basic podcastData:", podcastData);

    // Reorganize character data
    const characters = [];
    const participants = parseInt(podcastData.participant_count) || 2;

    console.log("Participants count:", participants);

    for (let i = 1; i <= participants; i++) {
        const characterData = {};

        // Collect character fields
        Object.keys(flatData).forEach(key => {
            if (key.startsWith(`character_${i}_`)) {
                const fieldName = key.replace(`character_${i}_`, '');
                characterData[fieldName] = flatData[key];
            }
        });

        console.log(`Character ${i} raw data:`, characterData);

        // Validate required fields (include new age and style fields)
        if (characterData.name && characterData.gender && characterData.age && characterData.style &&
            characterData.background && characterData.personality) {
            characters.push(characterData);
            console.log(`Character ${i} is VALID and added:`, characterData);
        } else {
            console.log(`Character ${i} is INVALID - missing fields:`, {
                name: !!characterData.name,
                gender: !!characterData.gender,
                age: !!characterData.age,
                style: !!characterData.style,
                background: !!characterData.background,
                personality: !!characterData.personality
            });
        }
    }

    podcastData.characters = characters;
    console.log("Final podcastData with characters:", podcastData);
    console.log("=== DEBUG: collectFormData() END ===");
    return podcastData;
}

/**
 * Update UI state based on generation status
 */
function updateUIState(state) {
    switch (state) {
        case 'generating':
            if (Elements.generateBtn) {
                Elements.generateBtn.disabled = true;
                Elements.generateBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2"></span>
                    生成中...
                `;
            }

            if (Elements.progressSection) {
                Elements.progressSection.classList.remove('d-none');
                Elements.progressSection.classList.add('slide-up');
            }

            if (Elements.resultsSection) {
                Elements.resultsSection.classList.add('d-none');
            }

            if (Elements.errorSection) {
                Elements.errorSection.classList.add('d-none');
            }
            break;

        case 'ready':
            if (Elements.generateBtn) {
                Elements.generateBtn.disabled = false;
                Elements.generateBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm d-none me-2"></span>
                    生成播客
                `;
            }
            break;
    }
}

/**
 * Simulate progress updates
 */
async function simulateProgress() {
    const steps = [
        { progress: 20, message: 'Initializing AI agents...' },
        { progress: 40, message: 'Generating character personalities...' },
        { progress: 60, message: 'Creating conversation dialogue...' },
        { progress: 80, message: 'Converting text to speech...' },
        { progress: 100, message: 'Finalizing audio file...' }
    ];

    return new Promise(resolve => {
        let currentStep = 0;

        AppState.progressInterval = setInterval(() => {
            if (currentStep < steps.length) {
                const step = steps[currentStep];
                updateProgress(step.progress, step.message);
                currentStep++;
            } else {
                clearInterval(AppState.progressInterval);
                resolve();
            }
        }, 1000);
    });
}

/**
 * Update progress bar and messages
 */
function updateProgress(progress, message) {
    if (Elements.progressBar) {
        Elements.progressBar.style.width = `${progress}%`;
        Elements.progressBar.textContent = `${progress}%`;
    }

    if (Elements.progressMessages) {
        const messageP = document.createElement('p');
        messageP.className = 'status-message fade-in';
        messageP.textContent = message;
        Elements.progressMessages.appendChild(messageP);

        // Scroll to latest message
        Elements.progressMessages.scrollTop = Elements.progressMessages.scrollHeight;
    }
}

/**
 * Show generation results with enhanced functionality
 */
function showResults(result) {
    if (Elements.progressSection) {
        Elements.progressSection.classList.add('d-none');
    }

    if (Elements.resultsSection) {
        Elements.resultsSection.classList.remove('d-none');
        Elements.resultsSection.classList.add('slide-up');
    }

    // Update results content
    const timestamp = new Date().toLocaleString();
    const topic = result.data?.topic || 'Generated Podcast';

    if (Elements.podcastTitleElement) {
        Elements.podcastTitleElement.querySelector('span').textContent = topic;
    }

    if (Elements.generationTimestampElement) {
        Elements.generationTimestampElement.textContent = timestamp;
    }

    // Set audio URL if available - check both direct and nested structure
    const audioUrl = result.data?.file_info?.audio_url || result.data?.audio_url;
    const downloadUrl = result.data?.file_info?.download_url || result.data?.download_url;

    if (audioUrl) {
        AppState.audioUrl = audioUrl;
        AppState.downloadUrl = downloadUrl || audioUrl;

        // Validate audio file before setting up player
        validateAndSetupAudio(AppState.audioUrl);

        console.log("=== DEBUG: Audio URLs updated ===");
        console.log("Audio URL:", AppState.audioUrl);
        console.log("Download URL:", AppState.downloadUrl);
        console.log("File info:", result.data?.file_info);
    }

    showNotification('Podcast generated successfully!', 'success');

    // Scroll to results
    setTimeout(() => {
        Elements.resultsSection?.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 500);
}

/**
 * Load audio metadata and display information
 */
function loadAudioMetadata() {
    if (!Elements.audioPlayer || !AppState.audioUrl) return;

    const audio = new Audio(AppState.audioUrl);

    audio.addEventListener('loadedmetadata', () => {
        const duration = formatDuration(audio.duration);
        if (Elements.audioDurationElement) {
            Elements.audioDurationElement.textContent = `Duration: ${duration}`;
        }
    });

    audio.addEventListener('loadeddata', async () => {
        try {
            // Try to get file size
            const response = await fetch(AppState.audioUrl, { method: 'HEAD' });
            const contentLength = response.headers.get('content-length');
            if (contentLength && Elements.fileSizeElement) {
                const size = formatFileSize(parseInt(contentLength));
                Elements.fileSizeElement.textContent = `Size: ${size}`;
            }
        } catch (error) {
            console.log('Could not determine file size:', error);
            if (Elements.fileSizeElement) {
                Elements.fileSizeElement.textContent = 'Size: Unknown';
            }
        }
    });
}

/**
 * Validate audio file and setup audio player
 */
async function validateAndSetupAudio(audioUrl) {
    try {
        // Show loading state
        showNotification('Validating audio file...', 'info');

        // Validate audio file accessibility
        const response = await fetch(audioUrl, { method: 'HEAD' });

        if (!response.ok) {
            throw new Error(`Audio file not accessible (HTTP ${response.status})`);
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('audio/')) {
            console.warn('Unexpected content type:', contentType);
        }

        // Update audio player
        if (Elements.audioPlayer) {
            Elements.audioPlayer.src = audioUrl;
            Elements.audioPlayer.load(); // Preload audio metadata

            // Setup enhanced error handling
            Elements.audioPlayer.addEventListener('error', handleAudioError);
        }

        // Update download button
        if (Elements.downloadBtn) {
            Elements.downloadBtn.href = AppState.downloadUrl;
            // Set proper download filename
            const filename = generateFilename();
            Elements.downloadBtn.setAttribute('download', filename);
        }

        // Get audio metadata
        loadAudioMetadata();

        showNotification('Audio file ready!', 'success');

    } catch (error) {
        console.error('Audio validation failed:', error);
        handleAudioError(error);
    }
}

/**
 * Handle audio player errors
 */
function handleAudioError(error) {
    console.error('Audio playback error:', error);

    // Show user-friendly error message
    showNotification('Unable to load audio file. Please try again.', 'error');

    // Disable audio player
    if (Elements.audioPlayer) {
        Elements.audioPlayer.src = '';
        Elements.audioPlayer.style.display = 'none';
    }

    // Update download button state
    if (Elements.downloadBtn) {
        Elements.downloadBtn.href = '#';
        Elements.downloadBtn.classList.add('disabled');
    }

    // Show retry option
    showRetryOption();
}

/**
 * Show retry option for failed audio
 */
function showRetryOption() {
    const resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        const retryHtml = `
            <div class="alert alert-warning mt-3" id="audio-retry-section">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Audio loading failed</strong>
                <p class="mb-2 mt-2">The audio file could not be loaded. This might be a temporary issue.</p>
                <button class="btn btn-sm btn-warning" onclick="retryAudioLoading()">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry Loading
                </button>
            </div>
        `;

        // Remove existing retry section if present
        const existingRetry = document.getElementById('audio-retry-section');
        if (existingRetry) {
            existingRetry.remove();
        }

        // Add retry section
        resultsSection.insertAdjacentHTML('beforeend', retryHtml);
    }
}

/**
 * Retry audio loading
 */
async function retryAudioLoading() {
    if (AppState.audioUrl) {
        // Remove retry section
        const retrySection = document.getElementById('audio-retry-section');
        if (retrySection) {
            retrySection.remove();
        }

        // Show audio player again
        if (Elements.audioPlayer) {
            Elements.audioPlayer.style.display = 'block';
        }

        // Re-enable download button
        if (Elements.downloadBtn) {
            Elements.downloadBtn.classList.remove('disabled');
        }

        // Retry validation
        await validateAndSetupAudio(AppState.audioUrl);
    }
}

/**
 * Format duration in seconds to human readable format
 */
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }
}

/**
 * Format file size in bytes to human readable format
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Show error message
 */
function showError(message) {
    if (Elements.progressSection) {
        Elements.progressSection.classList.add('d-none');
    }

    if (Elements.errorSection) {
        Elements.errorSection.classList.remove('d-none');
        Elements.errorSection.classList.add('slide-up');
    }

    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
    }

    showNotification(message, 'error');
}

/**
 * Handle retry action
 */
function handleRetry() {
    // Hide results and error sections
    if (Elements.resultsSection) {
        Elements.resultsSection.classList.add('d-none');
    }

    if (Elements.errorSection) {
        Elements.errorSection.classList.add('d-none');
    }

    // Clear progress messages
    if (Elements.progressMessages) {
        Elements.progressMessages.innerHTML = '';
    }

    // Reset progress bar
    if (Elements.progressBar) {
        Elements.progressBar.style.width = '0%';
        Elements.progressBar.textContent = '0%';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Handle download action with enhanced functionality
 */
async function handleDownload() {
    // Check both AppState and download button href
    const downloadBtn = document.getElementById('downloadBtn');
    const downloadUrl = AppState.downloadUrl || (downloadBtn && downloadBtn.href);

    if (!downloadUrl || downloadUrl === '#') {
        showNotification('No audio file available for download', 'error');
        return;
    }

    // Update AppState if it was not set
    if (!AppState.downloadUrl) {
        AppState.downloadUrl = downloadUrl;
    }

    try {
        // Show loading state
        showNotification('Preparing download...', 'info');

        // Validate download URL before initiating download
        const response = await fetch(downloadUrl, { method: 'HEAD' });

        if (!response.ok) {
            throw new Error(`Download file not accessible (HTTP ${response.status})`);
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('audio/')) {
            console.warn('Download file has unexpected content type:', contentType);
        }

        // Create a temporary link for download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = generateFilename();
        link.style.display = 'none';

        // Set proper download attributes
        const contentDisposition = response.headers.get('content-disposition');
        if (contentDisposition && contentDisposition.includes('filename=')) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                link.download = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        showNotification('Download started!', 'success');

        // Track download event
        trackDownloadEvent();
    } catch (error) {
        console.error('Download error:', error);
        showNotification('Download failed. Please try again.', 'error');

        // Offer retry option
        showDownloadRetryOption();
    }
}

/**
 * Generate filename for download
 */
function generateFilename() {
    const topic = Elements.topicTextarea?.value?.trim() || 'podcast';
    const sanitizedTopic = topic
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, '')
        .replace(/\s+/g, '-')
        .substring(0, 50);
    const timestamp = new Date().toISOString().slice(0, 10);
    return `${sanitizedTopic}-${timestamp}.wav`;
}

/**
 * Show download retry option
 */
function showDownloadRetryOption() {
    const resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        const retryHtml = `
            <div class="alert alert-warning mt-3" id="download-retry-section">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Download failed</strong>
                <p class="mb-2 mt-2">The audio file could not be downloaded. This might be a temporary issue.</p>
                <button class="btn btn-sm btn-warning" onclick="retryDownload()">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry Download
                </button>
            </div>
        `;

        // Remove existing download retry section if present
        const existingRetry = document.getElementById('download-retry-section');
        if (existingRetry) {
            existingRetry.remove();
        }

        // Add retry section
        resultsSection.insertAdjacentHTML('beforeend', retryHtml);
    }
}

/**
 * Retry download
 */
async function retryDownload() {
    // Remove retry section
    const retrySection = document.getElementById('download-retry-section');
    if (retrySection) {
        retrySection.remove();
    }

    // Retry download
    await handleDownload();
}

/**
 * Track download event for analytics
 */
function trackDownloadEvent() {
    // Placeholder for analytics tracking
    console.log('Download tracked:', {
        generationId: AppState.generationId,
        timestamp: new Date().toISOString(),
        filename: generateFilename()
    });
}

/**
 * Setup enhanced audio player functionality
 */
function setupAudioPlayer() {
    if (!Elements.audioPlayer) return;

    Elements.audioPlayer.addEventListener('play', () => {
        console.log('Audio playback started');
        trackAudioEvent('play');
    });

    Elements.audioPlayer.addEventListener('pause', () => {
        console.log('Audio playback paused');
        trackAudioEvent('pause');
    });

    Elements.audioPlayer.addEventListener('ended', () => {
        console.log('Audio playback ended');
        trackAudioEvent('ended');
    });

    Elements.audioPlayer.addEventListener('error', (e) => {
        console.error('Audio playback error:', e);
        showNotification('Error playing audio file', 'error');
        trackAudioEvent('error', e);
    });

    Elements.audioPlayer.addEventListener('timeupdate', () => {
        updateAudioProgress();
    });

    Elements.audioPlayer.addEventListener('loadeddata', () => {
        console.log('Audio data loaded successfully');
    });
}

/**
 * Update audio progress display
 */
function updateAudioProgress() {
    if (!Elements.audioPlayer) return;

    const current = Elements.audioPlayer.currentTime;
    const duration = Elements.audioPlayer.duration;

    if (duration && isFinite(duration)) {
        const progress = (current / duration) * 100;
        // Could update a progress bar here if needed
        console.log(`Audio progress: ${progress.toFixed(1)}%`);
    }
}

/**
 * Track audio events for analytics
 */
function trackAudioEvent(event, data = null) {
    console.log('Audio event tracked:', {
        event,
        generationId: AppState.generationId,
        currentTime: Elements.audioPlayer?.currentTime,
        duration: Elements.audioPlayer?.duration,
        data
    });
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl/Cmd + Enter to generate
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            if (!AppState.isGenerating) {
                handleGenerateClick();
            }
        }

        // Escape to stop generation
        if (event.key === 'Escape' && AppState.isGenerating) {
            stopGeneration();
        }

        // Ctrl/Cmd + R to retry
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            handleRetry();
        }
    });
}

/**
 * Show notification message
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade-in`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        box-shadow: var(--shadow-lg);
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
 * Utility function: debounce
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Handle cancel generation
 */
function handleCancel() {
    if (AppState.isGenerating) {
        stopGeneration();
        showNotification('Generation cancelled', 'info');

        // Clear progress
        if (Elements.progressMessages) {
            Elements.progressMessages.innerHTML = '';
        }
        if (Elements.progressBar) {
            Elements.progressBar.style.width = '0%';
            Elements.progressBar.textContent = '0%';
        }
    }
}

/**
 * Handle copy link functionality
 */
function handleCopyLink() {
    if (!AppState.audioUrl) {
        showNotification('No audio link available to copy', 'error');
        return;
    }

    try {
        navigator.clipboard.writeText(AppState.audioUrl).then(() => {
            showNotification('Link copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for browsers that don't support clipboard API
            const textArea = document.createElement('textarea');
            textArea.value = AppState.audioUrl;
            textArea.style.position = 'fixed';
            textArea.style.opacity = '0';
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('Link copied to clipboard!', 'success');
        });
    } catch (error) {
        console.error('Copy link error:', error);
        showNotification('Failed to copy link', 'error');
    }
}

/**
 * Handle share functionality
 */
function handleShare() {
    if (!AppState.audioUrl) {
        showNotification('No audio available to share', 'error');
        return;
    }

    if (navigator.share) {
        navigator.share({
            title: 'AI Generated Podcast',
            text: `Check out this podcast about: ${Elements.topicTextarea?.value?.trim() || 'AI-generated content'}`,
            url: AppState.audioUrl
        }).then(() => {
            showNotification('Podcast shared successfully!', 'success');
        }).catch((error) => {
            if (error.name !== 'AbortError') {
                console.log('Share cancelled or failed:', error);
            }
        });
    } else {
        // Fallback: copy link to clipboard
        handleCopyLink();
    }
}

/**
 * Handle new podcast creation
 */
function handleNewPodcast() {
    // Reset form and clear results
    handleResetForm();

    // Hide results section
    if (Elements.resultsSection) {
        Elements.resultsSection.classList.add('d-none');
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showNotification('Ready to create a new podcast!', 'info');
}

/**
 * Handle form reset
 */
function handleResetForm() {
    if (Elements.form) {
        Elements.form.reset();

        // Reset character configuration
        if (Elements.participantsSelect) {
            updateCharacterConfig(parseInt(Elements.participantsSelect.value) || 2);
        }

        // Reset topic counter
        if (Elements.topicTextarea && Elements.topicCounter) {
            handleTopicInput.call(Elements.topicTextarea);
        }

        // Clear validation states
        const fields = Elements.form.querySelectorAll('.is-invalid, .is-valid');
        fields.forEach(field => {
            field.classList.remove('is-invalid', 'is-valid');
        });

        // Clear error messages
        const errorMessages = Elements.form.querySelectorAll('.invalid-feedback');
        errorMessages.forEach(message => message.remove());
    }
}

/**
 * Handle report issue
 */
function handleReportIssue() {
    const issueData = {
        generationId: AppState.generationId,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        formData: collectFormData()
    };

    // Create issue report text
    const issueText = `
Issue Report - AI Podcast Generator
===================================

Generation ID: ${issueData.generationId}
Timestamp: ${issueData.timestamp}
User Agent: ${issueData.userAgent}

Form Data:
${JSON.stringify(issueData.formData, null, 2)}

Additional Information:
- Error occurred during generation
- Please describe what happened:

Please send this report to support@podcastgen.com
    `.trim();

    try {
        navigator.clipboard.writeText(issueText).then(() => {
            showNotification('Issue report copied to clipboard! Please send to support.', 'success');
        }).catch(() => {
            // Fallback: show in modal or console
            console.log('Issue Report:', issueText);
            showNotification('Issue report logged to console. Please send to support.', 'info');
        });
    } catch (error) {
        console.error('Failed to generate issue report:', error);
        showNotification('Failed to generate issue report', 'error');
    }
}

/**
 * Setup enhanced form monitoring
 */
function setupFormMonitoring() {
    if (!Elements.form) return;

    // Monitor form changes
    let formChanged = false;
    const inputs = Elements.form.querySelectorAll('input, select, textarea');

    inputs.forEach(input => {
        input.addEventListener('change', () => {
            formChanged = true;
        });
    });

    // Warn before leaving if form has changes
    window.addEventListener('beforeunload', (event) => {
        if (formChanged && !AppState.isGenerating) {
            event.preventDefault();
            event.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            return event.returnValue;
        }
    });

    // Auto-save form data to localStorage
    setupAutoSave();
}

/**
 * Setup auto-save functionality
 */
function setupAutoSave() {
    if (!Elements.form) return;

    // Load saved data on page load
    loadSavedFormData();

    // Save form data on change
    const inputs = Elements.form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('input', debounce(() => {
            saveFormData();
        }, 1000));
    });
}

/**
 * Save form data to localStorage
 */
function saveFormData() {
    if (!Elements.form) return;

    try {
        const formData = new FormData(Elements.form);
        const data = Object.fromEntries(formData.entries());
        localStorage.setItem('podcastFormData', JSON.stringify(data));
    } catch (error) {
        console.warn('Failed to save form data:', error);
    }
}

/**
 * Load saved form data from localStorage
 */
function loadSavedFormData() {
    try {
        const savedData = localStorage.getItem('podcastFormData');
        if (savedData) {
            const data = JSON.parse(savedData);

            // Fill form fields with saved data
            Object.keys(data).forEach(key => {
                const field = Elements.form.querySelector(`[name="${key}"]`);
                if (field) {
                    field.value = data[key];
                }
            });

            // Update character configuration
            if (data.participants) {
                updateCharacterConfig(parseInt(data.participants));
            }

            // Update topic counter
            if (Elements.topicTextarea && Elements.topicCounter) {
                handleTopicInput.call(Elements.topicTextarea);
            }
        }
    } catch (error) {
        console.warn('Failed to load saved form data:', error);
    }
}

/**
 * Setup page visibility handling
 */
function setupVisibilityHandling() {
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            // Page is hidden - pause background operations
            console.log('Page hidden - pausing background operations');
        } else {
            // Page is visible - resume operations
            console.log('Page visible - resuming operations');

            // Check if generation completed while page was hidden
            if (AppState.isGenerating) {
                // Could check generation status here
                console.log('Generation was in progress, checking status...');
            }
        }
    });
}

/**
 * Utility function: debounce
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Utility function: throttle
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Initialize API Configuration functionality
 */
function initializeAPIConfiguration() {
    // Setup API key visibility toggle
    document.querySelectorAll('.toggle-visibility-btn').forEach(button => {
        button.addEventListener('click', handleToggleVisibility);
    });

    // Setup API key validation
    document.querySelectorAll('.validate-api-btn').forEach(button => {
        button.addEventListener('click', handleAPIKeyValidation);
    });

    // Setup save configuration button
    const saveBtn = document.getElementById('save-api-config-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', handleSaveAPIConfiguration);
    }

    // Load existing configuration
    loadAPIConfiguration();
}

/**
 * Handle API key visibility toggle
 */
function handleToggleVisibility(event) {
    const button = event.currentTarget;
    const inputId = button.dataset.inputId;
    const input = document.getElementById(inputId);
    const icon = button.querySelector('.toggle-icon');

    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'bi bi-eye-slash toggle-icon';
        button.title = '隐藏密码';
    } else {
        input.type = 'password';
        icon.className = 'bi bi-eye toggle-icon';
        button.title = '显示/隐藏';
    }
}

/**
 * Handle API key validation
 */
async function handleAPIKeyValidation(event) {
    const button = event.currentTarget;
    const provider = button.dataset.provider;
    const inputId = button.dataset.inputId;
    const input = document.getElementById(inputId);
    const validationDiv = document.getElementById(`${provider}-validation-home`);

    if (!input.value.trim()) {
        showNotification('请先输入API密钥', 'warning');
        return;
    }

    // Update button state
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>验证中...';

    try {
        const response = await fetch('/api/config/validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                provider: provider,
                api_key: input.value.trim()
            })
        });

        const result = await response.json();

        if (result.success) {
            updateValidationStatus(validationDiv, 'success', '验证成功');
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            showNotification(`${provider} API密钥验证成功`, 'success');
        } else {
            updateValidationStatus(validationDiv, 'error', '验证失败');
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
            showNotification(`${provider} API密钥验证失败: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('API key validation error:', error);
        updateValidationStatus(validationDiv, 'error', '网络错误');
        showNotification('API密钥验证时发生网络错误', 'error');
    } finally {
        // Restore button state
        button.disabled = false;
        button.innerHTML = '<i class="bi bi-check-circle me-1"></i>验证';
    }
}

/**
 * Update validation status display
 */
function updateValidationStatus(element, status, message) {
    if (!element) return;

    const statusClasses = {
        success: 'bg-success',
        error: 'bg-danger',
        warning: 'bg-warning',
        neutral: 'bg-secondary'
    };

    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        neutral: 'bi-dash-circle'
    };

    const statusClass = statusClasses[status] || 'bg-secondary';
    const iconClass = icons[status] || 'bi-dash-circle';

    element.innerHTML = `
        <span class="badge ${statusClass}">
            <i class="bi ${iconClass} me-1"></i>${message}
        </span>
    `;
}

/**
 * Handle save API configuration
 */
async function handleSaveAPIConfiguration() {
    const saveBtn = document.getElementById('save-api-config-btn');

    // Collect API keys
    const apiKeys = {};
    document.querySelectorAll('.api-key-input').forEach(input => {
        if (input.value.trim()) {
            const provider = input.name.replace('api_keys.', '');
            apiKeys[provider] = input.value.trim();
        }
    });

    if (Object.keys(apiKeys).length === 0) {
        showNotification('请至少配置一个API密钥', 'warning');
        return;
    }

    // Update button state
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>保存中...';

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                api_keys: apiKeys
            })
        });

        const result = await response.json();

        if (result.success) {
            showNotification('API配置保存成功', 'success');
            updateAPIConfigStatus('configured');

            // Mark all valid inputs as successfully saved
            document.querySelectorAll('.api-key-input.is-valid').forEach(input => {
                const card = input.closest('.api-key-card');
                if (card) {
                    card.classList.add('configured');
                }
            });
        } else {
            showNotification(`API配置保存失败: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Save API configuration error:', error);
        showNotification('保存API配置时发生网络错误', 'error');
    } finally {
        // Restore button state
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-save me-2"></i>保存API配置';
    }
}

/**
 * Update API configuration status badge
 */
function updateAPIConfigStatus(status) {
    const statusBadge = document.getElementById('api-config-status');
    if (!statusBadge) return;

    if (status === 'configured') {
        statusBadge.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>已配置';
        statusBadge.className = 'badge bg-success ms-2';
    } else {
        statusBadge.innerHTML = '<i class="bi bi-circle-fill me-1"></i>未配置';
        statusBadge.className = 'badge bg-warning ms-2';
    }
}

/**
 * Load existing API configuration
 */
async function loadAPIConfiguration() {
    try {
        const response = await fetch('/api/config');
        const result = await response.json();

        if (result.success && result.data.api_keys) {
            // Fill in existing API keys
            Object.entries(result.data.api_keys).forEach(([provider, apiKey]) => {
                const input = document.getElementById(`${provider}-api-key-home`);
                if (input) {
                    input.value = apiKey;
                    input.classList.add('is-valid');
                }
            });

            updateAPIConfigStatus('configured');
        }
    } catch (error) {
        console.error('Load API configuration error:', error);
        // Don't show error to user on load, just log it
    }
}

/**
 * Form Data Persistence Functions
 */

/**
 * Initialize form data persistence
 */
function initializeFormDataPersistence() {
    console.log('=== DEBUG: Initializing form data persistence ===');
    console.log('HAS_SAVED_CONFIG:', window.HAS_SAVED_CONFIG);
    console.log('CURRENT_USER:', window.CURRENT_USER);

    // Restore saved configuration if available
    if (window.HAS_SAVED_CONFIG && window.SAVED_CONFIG) {
        restoreSavedConfiguration(window.SAVED_CONFIG);
    }

    // Setup auto-save for form changes
    setupAutoSave();

    console.log('=== DEBUG: Form data persistence initialized ===');
}

/**
 * Restore saved configuration to the form
 */
function restoreSavedConfiguration(config) {
    console.log('=== DEBUG: Restoring saved configuration ===', config);

    try {
        // Restore topic
        if (config.topic && Elements.topicTextarea) {
            Elements.topicTextarea.value = config.topic;
            updateTopicCounter();
        }

        // Restore participants and rounds
        if (config.participants && Elements.participantsSelect) {
            Elements.participantsSelect.value = config.participants;
            setTimeout(() => {
                updateCharacterConfig(parseInt(config.participants) || 2);
                // Restore character configs after character cards are created
                if (config.character_configs && Array.isArray(config.character_configs)) {
                    setTimeout(() => {
                        restoreCharacterConfigurations(config.character_configs);
                    }, 100);
                }
            }, 100);
        }

        if (config.rounds) {
            const roundsSelect = document.getElementById('rounds');
            if (roundsSelect) {
                roundsSelect.value = config.rounds;
            }
        }

        // Restore AI provider and model
        if (config.ai_provider) {
            const providerSelect = document.getElementById('ai_provider');
            if (providerSelect) {
                providerSelect.value = config.ai_provider;
            }
        }

        if (config.ai_model) {
            const modelSelect = document.getElementById('ai_model');
            if (modelSelect) {
                modelSelect.value = config.ai_model;
            }
        }

        // Restore API keys
        if (config.api_keys && typeof config.api_keys === 'object') {
            restoreAPIKeys(config.api_keys);
        }

        // Restore character configurations (if not already restored above)
        if (config.character_configs && Array.isArray(config.character_configs)) {
            if (!config.participants) {
                // If no participants value, restore immediately
                restoreCharacterConfigurations(config.character_configs);
            }
        }

        // Show notification that configuration was restored
        showNotification('配置已从上次保存的数据中恢复', 'success');

        console.log('=== DEBUG: Configuration restored successfully ===');

    } catch (error) {
        console.error('=== DEBUG: Error restoring configuration ===', error);
        showNotification('恢复配置时出错，请手动填写表单', 'warning');
    }
}

/**
 * Restore API keys to the form
 */
function restoreAPIKeys(apiKeys) {
    console.log('=== DEBUG: Restoring API keys ===', apiKeys);

    try {
        Object.entries(apiKeys).forEach(([provider, apiKey]) => {
            if (apiKey && apiKey.trim()) {
                // Look for API key input by provider name
                const inputSelectors = [
                    `#${provider}-api-key-home`,
                    `input[name="api_keys.${provider}"]`,
                    `input[data-provider="${provider}"]`
                ];

                let input = null;
                for (const selector of inputSelectors) {
                    input = document.querySelector(selector);
                    if (input) {
                        break;
                    }
                }

                if (input) {
                    input.value = apiKey;
                    input.classList.add('is-valid');
                    console.log(`=== DEBUG: Restored API key for ${provider} ===`);
                } else {
                    console.warn(`=== DEBUG: API key input not found for provider ${provider} ===`);
                }
            }
        });
    } catch (error) {
        console.error('=== DEBUG: Error restoring API keys ===', error);
    }
}

/**
 * Restore character configurations
 */
function restoreCharacterConfigurations(characterConfigs) {
    console.log('=== DEBUG: Restoring character configurations ===', characterConfigs);

    try {
        const participants = parseInt(Elements.participantsSelect.value) || 2;

        characterConfigs.forEach((charConfig, index) => {
            if (index < participants) {
                const characterNumber = index + 1;
                console.log(`=== DEBUG: Restoring character ${characterNumber} ===`, charConfig);

                // Restore character name
                const nameInput = document.querySelector(`input[name="character_${characterNumber}_name"]`);
                if (nameInput && charConfig.name) {
                    nameInput.value = charConfig.name;
                    console.log(`=== DEBUG: Restored name for character ${characterNumber}: ${charConfig.name} ===`);
                }

                // Restore character gender
                const genderSelect = document.querySelector(`select[name="character_${characterNumber}_gender"]`);
                if (genderSelect && charConfig.gender) {
                    genderSelect.value = charConfig.gender;
                    // Trigger change event to update age and style options
                    const changeEvent = new Event('change', { bubbles: true });
                    genderSelect.dispatchEvent(changeEvent);
                    console.log(`=== DEBUG: Restored gender for character ${characterNumber}: ${charConfig.gender} ===`);
                }

                // Restore character background
                const bgTextarea = document.querySelector(`textarea[name="character_${characterNumber}_background"]`);
                if (bgTextarea && charConfig.background) {
                    bgTextarea.value = charConfig.background;
                    // Update character count
                    const counter = bgTextarea.parentElement.querySelector('.character-count');
                    if (counter) {
                        counter.textContent = `${charConfig.background.length}/500`;
                    }
                    console.log(`=== DEBUG: Restored background for character ${characterNumber} ===`);
                }

                // Restore character personality
                const personalitySelect = document.querySelector(`select[name="character_${characterNumber}_personality"]`);
                if (personalitySelect && charConfig.personality) {
                    personalitySelect.value = charConfig.personality;
                    // Update personality hint
                    if (typeof updatePersonalityHint === 'function') {
                        updatePersonalityHint(characterNumber, charConfig.personality);
                    }
                    console.log(`=== DEBUG: Restored personality for character ${characterNumber}: ${charConfig.personality} ===`);
                }

                // Restore character age if available (with delay to wait for gender change)
                if (charConfig.age) {
                    setTimeout(() => {
                        const ageSelect = document.querySelector(`select[name="character_${characterNumber}_age"]`);
                        if (ageSelect) {
                            ageSelect.value = charConfig.age;
                            // Trigger change event to update style options
                            const changeEvent = new Event('change', { bubbles: true });
                            ageSelect.dispatchEvent(changeEvent);
                            console.log(`=== DEBUG: Restored age for character ${characterNumber}: ${charConfig.age} ===`);
                        }
                    }, 200);
                }

                // Restore character style if available (with longer delay to wait for age change)
                if (charConfig.style) {
                    setTimeout(() => {
                        const styleSelect = document.querySelector(`select[name="character_${characterNumber}_style"]`);
                        if (styleSelect) {
                            styleSelect.value = charConfig.style;
                            console.log(`=== DEBUG: Restored style for character ${characterNumber}: ${charConfig.style} ===`);
                        }
                    }, 400);
                }

                // Restore character model if available
                const modelSelect = document.querySelector(`select[name="character_${characterNumber}_model"]`);
                if (modelSelect && charConfig.model) {
                    modelSelect.value = charConfig.model;
                    console.log(`=== DEBUG: Restored model for character ${characterNumber}: ${charConfig.model} ===`);
                }
            }
        });

        console.log('=== DEBUG: Character configurations restored successfully ===');

    } catch (error) {
        console.error('=== DEBUG: Error restoring character configurations ===', error);
    }
}

/**
 * Setup auto-save functionality
 */
function setupAutoSave() {
    if (!Elements.form) return;

    // Add change event listeners to form elements
    const formInputs = Elements.form.querySelectorAll('input, select, textarea');

    formInputs.forEach(input => {
        // Skip file inputs and buttons
        if (input.type === 'file' || input.type === 'submit' || input.type === 'button') {
            return;
        }

        // Add event listeners for different input types
        input.addEventListener('input', () => debounceAutoSave());
        input.addEventListener('change', () => debounceAutoSave());

        // For select elements, also listen for blur events
        if (input.tagName === 'SELECT') {
            input.addEventListener('blur', () => debounceAutoSave());
        }
    });

    console.log('=== DEBUG: Auto-save listeners setup complete ===');
}

/**
 * Debounce auto-save to avoid too frequent saves
 */
function debounceAutoSave() {
    AppState.hasUnsavedChanges = true;

    // Clear existing timeout
    if (AppState.autoSaveTimeout) {
        clearTimeout(AppState.autoSaveTimeout);
    }

    // Set new timeout
    AppState.autoSaveTimeout = setTimeout(() => {
        saveConfiguration();
    }, AppState.autoSaveDelay);
}

/**
 * Save current form configuration
 */
async function saveConfiguration() {
    try {
        console.log('=== DEBUG: Saving configuration ===');

        // Collect all form data
        const configData = collectAllFormData();

        console.log('=== DEBUG: Collected configuration data ===', configData);

        // Send to server for saving
        const response = await fetch('/api/podcast-config/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(configData)
        });

        if (response.ok) {
            const result = await response.json();
            AppState.hasUnsavedChanges = false;
            console.log('=== DEBUG: Configuration saved successfully ===', result);
            return result;
        } else {
            const errorText = await response.text();
            console.warn('=== DEBUG: Failed to save configuration ===', errorText);
            throw new Error(`Save failed: ${response.status} ${errorText}`);
        }

    } catch (error) {
        console.error('=== DEBUG: Error saving configuration ===', error);
        throw error;
    }
}

/**
 * Collect all form data including API keys and character configurations
 */
function collectAllFormData() {
    console.log('=== DEBUG: Collecting all form data ===');

    // Basic form data
    const formData = new FormData(Elements.form);
    const flatData = Object.fromEntries(formData.entries());

    const configData = {
        topic: formData.get('topic') || '',
        participants: parseInt(formData.get('participants')) || 2,
        rounds: parseInt(formData.get('rounds')) || 8,
        ai_provider: formData.get('ai_provider') || 'deepseek',
        ai_model: formData.get('ai_model') || 'deepseek-chat',
        character_configs: []
    };

    // Collect API keys
    configData.api_keys = {};
    const apiKeyInputs = document.querySelectorAll('.api-key-input');
    apiKeyInputs.forEach(input => {
        if (input.value.trim()) {
            const provider = input.name.replace('api_keys.', '');
            configData.api_keys[provider] = input.value.trim();
        }
    });

    // Get character configurations
    const participants = configData.participants;
    for (let i = 1; i <= participants; i++) {
        const charConfig = {
            name: formData.get(`character_${i}_name`) || '',
            gender: formData.get(`character_${i}_gender`) || '',
            age: formData.get(`character_${i}_age`) || '',
            style: formData.get(`character_${i}_style`) || '',
            background: formData.get(`character_${i}_background`) || '',
            personality: formData.get(`character_${i}_personality`) || '',
            model: formData.get(`character_${i}_model`) || ''
        };
        configData.character_configs.push(charConfig);
    }

    console.log('=== DEBUG: Final configuration data ===', configData);
    return configData;
}

// Enhanced export for global access
window.PodcastApp = {
    AppState,
    Elements,
    showNotification,
    validateForm,
    startGeneration,
    stopGeneration,
    handleCancel,
    handleDownload,
    handleShare,
    handleCopyLink,
    handleNewPodcast,
    handleResetForm,
    handleReportIssue,
    loadAudioMetadata,
    formatDuration,
    formatFileSize,
    initializeAPIConfiguration,
    handleToggleVisibility,
    handleAPIKeyValidation,
    handleSaveAPIConfiguration,
    loadAPIConfiguration,
    initializeFormDataPersistence,
    restoreSavedConfiguration,
    restoreAPIKeys,
    restoreCharacterConfigurations,
    setupAutoSave,
    saveConfiguration,
    collectAllFormData,
    debounceAutoSave
};