/**
 * JavaScript functionality for AI Podcast Generator
 * Handles form submission, character configuration, and user interactions
 */

// Application state
let currentStep = 1;
let isGenerating = false;

// DOM Elements
const generateForm = document.getElementById('generateForm');
const participantsSelect = document.getElementById('participants');
const characterConfig = document.getElementById('character-config');
const generateBtn = document.getElementById('generateBtn');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const errorSection = document.getElementById('error-section');
const progressBar = document.getElementById('progressBar');
const progressMessages = document.getElementById('progress-messages');

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Load saved character configurations
    loadCharacterConfigurations();

    // Generate initial character configuration
    updateCharacterConfig();

    // Set up event listeners
    setupEventListeners();

    // Log initialization
    console.log('AI Podcast Generator initialized');
}

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Participants change event
    participantsSelect.addEventListener('change', updateCharacterConfig);

    // Form submission
    generateForm.addEventListener('submit', handleFormSubmit);

    // Retry button
    const retryBtn = document.getElementById('retryBtn');
    if (retryBtn) {
        retryBtn.addEventListener('click', handleRetry);
    }
}

/**
 * Update character configuration based on number of participants
 */
function updateCharacterConfig() {
    const participants = parseInt(participantsSelect.value);
    characterConfig.innerHTML = '';

    for (let i = 1; i <= participants; i++) {
        const characterCard = createCharacterCard(i);
        characterConfig.appendChild(characterCard);
    }

    // Load saved configurations for the new character cards
    setTimeout(() => {
        loadSavedCharacterData();
        setupCharacterAutoSave();
    }, 100);
}

/**
 * Create a character configuration card
 */
function createCharacterCard(characterNumber) {
    const card = document.createElement('div');
    card.className = 'character-card';
    card.innerHTML = `
        <div class="character-header">
            Character ${characterNumber}
        </div>
        <div class="row">
            <div class="col-md-4 mb-3">
                <label class="form-label">Name <span class="text-danger">*</span></label>
                <input type="text" class="form-control" name="character_${characterNumber}_name"
                       placeholder="Enter character name" required maxlength="100">
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Gender <span class="text-danger">*</span></label>
                <select class="form-select" name="character_${characterNumber}_gender" required>
                    <option value="">Select gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div class="col-md-4 mb-3">
                <label class="form-label">Personality <span class="text-danger">*</span></label>
                <select class="form-select" name="character_${characterNumber}_personality" required>
                    <option value="">Select personality</option>
                    <option value="professional">Professional</option>
                    <option value="casual">Casual</option>
                    <option value="energetic">Energetic</option>
                    <option value="calm">Calm</option>
                </select>
            </div>
        </div>
        <div class="mb-3">
            <label class="form-label">Background <span class="text-danger">*</span></label>
            <textarea class="form-control" name="character_${characterNumber}_background"
                      rows="3" placeholder="Describe the character's background, expertise, and role in the conversation"
                      required maxlength="500"></textarea>
            <div class="form-text">Maximum 500 characters</div>
        </div>
    `;
    return card;
}

/**
 * Handle form submission
 */
async function handleFormSubmit(event) {
    event.preventDefault();

    if (isGenerating) {
        return;
    }

    // Validate form
    if (!validateForm()) {
        return;
    }

    // Get form data
    const formData = new FormData(generateForm);
    const data = Object.fromEntries(formData.entries());

    // Start generation
    startGeneration();

    try {
        // Send generation request
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            // Show success result
            showResults(result);
        } else {
            // Show error
            showError(result.error || 'Generation failed');
        }
    } catch (error) {
        console.error('Generation error:', error);
        showError('Network error occurred. Please try again.');
    } finally {
        stopGeneration();
    }
}

/**
 * Validate form data
 */
function validateForm() {
    const topic = document.getElementById('topic').value.trim();
    const participants = parseInt(participantsSelect.value);

    // Basic validation
    if (!topic) {
        showFieldError('topic', 'Please enter a podcast topic');
        return false;
    }

    if (topic.length > 1000) {
        showFieldError('topic', 'Topic must be less than 1000 characters');
        return false;
    }

    // Character validation
    for (let i = 1; i <= participants; i++) {
        const name = document.querySelector(`input[name="character_${i}_name"]`).value.trim();
        const gender = document.querySelector(`select[name="character_${i}_gender"]`).value;
        const personality = document.querySelector(`select[name="character_${i}_personality"]`).value;
        const background = document.querySelector(`textarea[name="character_${i}_background"]`).value.trim();

        if (!name) {
            showFieldError(`character_${i}_name`, 'Character name is required');
            return false;
        }

        if (!gender) {
            showFieldError(`character_${i}_gender`, 'Please select a gender');
            return false;
        }

        if (!personality) {
            showFieldError(`character_${i}_personality`, 'Please select a personality');
            return false;
        }

        if (!background) {
            showFieldError(`character_${i}_background`, 'Character background is required');
            return false;
        }

        if (background.length > 500) {
            showFieldError(`character_${i}_background`, 'Background must be less than 500 characters');
            return false;
        }
    }

    return true;
}

/**
 * Show field error
 */
function showFieldError(fieldName, message) {
    const field = document.querySelector(`[name="${fieldName}"]`);
    if (field) {
        field.classList.add('is-invalid');

        // Remove existing error message
        const existingError = field.parentNode.querySelector('.invalid-feedback');
        if (existingError) {
            existingError.remove();
        }

        // Add new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'invalid-feedback';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);

        // Remove error on input
        field.addEventListener('input', function() {
            field.classList.remove('is-invalid');
            errorDiv.remove();
        }, { once: true });
    }
}

/**
 * Start generation process
 */
function startGeneration() {
    isGenerating = true;
    generateBtn.disabled = true;

    // Show spinner
    const spinner = generateBtn.querySelector('.spinner-border');
    spinner.classList.remove('d-none');

    // Update button text
    generateBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
        Generating...
    `;

    // Show progress section
    progressSection.classList.remove('d-none');
    progressSection.classList.add('slide-up');

    // Hide other sections
    resultsSection.classList.add('d-none');
    errorSection.classList.add('d-none');
}

/**
 * Stop generation process
 */
function stopGeneration() {
    isGenerating = false;
    generateBtn.disabled = false;

    // Restore button text
    generateBtn.innerHTML = `
        <span class="spinner-border spinner-border-sm d-none me-2" role="status" aria-hidden="true"></span>
        Generate Podcast
    `;
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

    for (const step of steps) {
        updateProgress(step.progress, step.message);
        await sleep(1000); // Simulate processing time
    }
}

/**
 * Update progress bar and messages
 */
function updateProgress(progress, message) {
    progressBar.style.width = `${progress}%`;
    progressBar.textContent = `${progress}%`;

    const messageP = document.createElement('p');
    messageP.className = 'status-message fade-in';
    messageP.textContent = message;
    progressMessages.appendChild(messageP);

    // Scroll to latest message
    progressMessages.scrollTop = progressMessages.scrollHeight;
}

/**
 * Show results
 */
function showResults(result) {
    progressSection.classList.add('d-none');
    resultsSection.classList.remove('d-none');
    resultsSection.classList.add('slide-up');

    // Update results content with actual data from backend
    const timestamp = new Date().toLocaleString();

    // Update title
    const titleElement = document.getElementById('results-section').querySelector('h4 span');
    if (titleElement) {
        titleElement.textContent = result.data?.topic || 'Generated Podcast';
    }

    // Update timestamp
    const timestampElement = document.getElementById('generation-timestamp');
    if (timestampElement) {
        timestampElement.textContent = result.data?.file_info?.created_at ?
            new Date(result.data.file_info.created_at).toLocaleString() :
            timestamp;
    }

    // Update audio player source
    const audioPlayer = document.getElementById('audioPlayer');
    const audioSource = audioPlayer?.querySelector('source');
    if (audioSource && result.data?.file_info?.audio_url) {
        audioSource.src = result.data.file_info.audio_url;
        audioPlayer.load(); // Reload the audio player with new source
    }

    // Update download button
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn && result.data?.file_info?.download_url) {
        downloadBtn.href = result.data.file_info.download_url;
    }

    // Update file size
    const fileSizeElement = document.getElementById('file-size');
    if (fileSizeElement && result.data?.file_info?.size) {
        const fileSize = formatFileSize(result.data.file_info.size);
        fileSizeElement.textContent = `Size: ${fileSize}`;
    }

    console.log('Audio URL set to:', result.data?.file_info?.audio_url);
    console.log('Download URL set to:', result.data?.file_info?.download_url);
}

/**
 * Show error
 */
function showError(message) {
    progressSection.classList.add('d-none');
    errorSection.classList.remove('d-none');
    errorSection.classList.add('slide-up');

    document.getElementById('error-message').textContent = message;
}

/**
 * Handle retry
 */
function handleRetry() {
    errorSection.classList.add('d-none');
    resultsSection.classList.add('d-none');
    progressSection.classList.add('d-none');

    // Clear progress messages
    progressMessages.innerHTML = '';

    // Reset progress bar
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
}

/**
 * Utility function to sleep
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Utility function to format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Utility function to validate email (if needed)
 */
function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Character Configuration Management Functions
 */

/**
 * Load character configurations from localStorage
 */
function loadCharacterConfigurations() {
    try {
        const savedConfig = localStorage.getItem('podcastCharacterConfigurations');
        if (savedConfig) {
            const config = JSON.parse(savedConfig);
            console.log('Loaded character configurations:', config);

            // Store globally for later use
            window.savedCharacterConfigurations = config;
        }
    } catch (error) {
        console.warn('Failed to load character configurations:', error);
        window.savedCharacterConfigurations = {};
    }
}

/**
 * Save current character configurations to localStorage
 */
function saveCharacterConfigurations() {
    try {
        const formData = new FormData(generateForm);
        const data = Object.fromEntries(formData.entries());

        // Extract character data
        const characterConfigs = {};
        const participants = parseInt(data.participants || '2');

        for (let i = 1; i <= participants; i++) {
            characterConfigs[`character_${i}`] = {
                name: data[`character_${i}_name`] || '',
                gender: data[`character_${i}_gender`] || '',
                personality: data[`character_${i}_personality`] || '',
                background: data[`character_${i}_background`] || ''
            };
        }

        // Save to localStorage
        localStorage.setItem('podcastCharacterConfigurations', JSON.stringify(characterConfigs));
        console.log('Saved character configurations:', characterConfigs);

    } catch (error) {
        console.warn('Failed to save character configurations:', error);
    }
}

/**
 * Load saved character data into form fields
 */
function loadSavedCharacterData() {
    try {
        const savedConfig = localStorage.getItem('podcastCharacterConfigurations');
        if (!savedConfig) {
            // Load default configurations if no saved data
            loadDefaultCharacterConfigurations();
            return;
        }

        const config = JSON.parse(savedConfig);
        const participants = parseInt(participantsSelect.value);

        // Fill form fields with saved data
        for (let i = 1; i <= participants; i++) {
            const characterKey = `character_${i}`;
            const characterData = config[characterKey];

            if (characterData) {
                // Fill name
                const nameField = document.querySelector(`[name="character_${i}_name"]`);
                if (nameField && characterData.name) {
                    nameField.value = characterData.name;
                }

                // Fill gender
                const genderField = document.querySelector(`[name="character_${i}_gender"]`);
                if (genderField && characterData.gender) {
                    genderField.value = characterData.gender;
                }

                // Fill personality
                const personalityField = document.querySelector(`[name="character_${i}_personality"]`);
                if (personalityField && characterData.personality) {
                    personalityField.value = characterData.personality;
                }

                // Fill background
                const backgroundField = document.querySelector(`[name="character_${i}_background"]`);
                if (backgroundField && characterData.background) {
                    backgroundField.value = characterData.background;
                }
            }
        }

    } catch (error) {
        console.warn('Failed to load saved character data:', error);
        loadDefaultCharacterConfigurations();
    }
}

/**
 * Load default character configurations
 */
function loadDefaultCharacterConfigurations() {
    const participants = parseInt(participantsSelect.value);

    // Default configurations for different scenarios
    const defaultConfigs = {
        '2': [
            {
                name: '张博士',
                gender: 'male',
                personality: 'professional',
                background: '计算机科学博士，人工智能研究专家，专注于机器学习和深度学习算法的研究与应用。在多家科技公司担任技术顾问，对AI技术的发展趋势有深入见解。'
            },
            {
                name: '李教授',
                gender: 'female',
                personality: 'professional',
                background: '哲学教授，伦理学专家，专注于科技伦理和社会影响研究。长期关注人工智能发展对社会的积极和消极影响，倡导负责任的AI开发和应用。'
            }
        ],
        '3': [
            {
                name: '张博士',
                gender: 'male',
                personality: 'professional',
                background: '计算机科学博士，人工智能研究专家，专注于机器学习和深度学习算法的研究与应用。在多家科技公司担任技术顾问，对AI技术的发展趋势有深入见解。'
            },
            {
                name: '李教授',
                gender: 'female',
                personality: 'professional',
                background: '哲学教授，伦理学专家，专注于科技伦理和社会影响研究。长期关注人工智能发展对社会的积极和消极影响，倡导负责任的AI开发和应用。'
            },
            {
                name: '王工程师',
                gender: 'male',
                personality: 'casual',
                background: '资深软件工程师，在大型互联网公司有10年以上的开发经验。从技术实践者的角度分享AI工具在实际工作中的应用体验和挑战。'
            }
        ],
        '4': [
            {
                name: '张博士',
                gender: 'male',
                personality: 'professional',
                background: '计算机科学博士，人工智能研究专家，专注于机器学习和深度学习算法的研究与应用。在多家科技公司担任技术顾问，对AI技术的发展趋势有深入见解。'
            },
            {
                name: '李教授',
                gender: 'female',
                personality: 'professional',
                background: '哲学教授，伦理学专家，专注于科技伦理和社会影响研究。长期关注人工智能发展对社会的积极和消极影响，倡导负责任的AI开发和应用。'
            },
            {
                name: '王工程师',
                gender: 'male',
                personality: 'casual',
                background: '资深软件工程师，在大型互联网公司有10年以上的开发经验。从技术实践者的角度分享AI工具在实际工作中的应用体验和挑战。'
            },
            {
                name: '陈记者',
                gender: 'female',
                personality: 'energetic',
                background: '科技记者，长期关注AI行业动态和创业公司发展。擅长从媒体角度分析AI技术对社会、经济和就业市场的潜在影响，为公众提供通俗易懂的技术解读。'
            }
        ]
    };

    const configs = defaultConfigs[participants.toString()] || defaultConfigs['2'];

    // Fill form fields with default configurations
    for (let i = 0; i < Math.min(participants, configs.length); i++) {
        const characterData = configs[i];
        const characterNum = i + 1;

        // Fill name
        const nameField = document.querySelector(`[name="character_${characterNum}_name"]`);
        if (nameField && characterData.name) {
            nameField.value = characterData.name;
        }

        // Fill gender
        const genderField = document.querySelector(`[name="character_${characterNum}_gender"]`);
        if (genderField && characterData.gender) {
            genderField.value = characterData.gender;
        }

        // Fill personality
        const personalityField = document.querySelector(`[name="character_${characterNum}_personality"]`);
        if (personalityField && characterData.personality) {
            personalityField.value = characterData.personality;
        }

        // Fill background
        const backgroundField = document.querySelector(`[name="character_${characterNum}_background"]`);
        if (backgroundField && characterData.background) {
            backgroundField.value = characterData.background;
        }
    }

    console.log('Loaded default character configurations for', participants, 'participants');
}

/**
 * Setup auto-save for character configuration changes
 */
function setupCharacterAutoSave() {
    // Add event listeners to all character fields
    const characterFields = document.querySelectorAll('[name^="character_"]');

    characterFields.forEach(field => {
        // Save on input change
        field.addEventListener('input', debounce(() => {
            saveCharacterConfigurations();
        }, 1000));

        // Save on select change
        field.addEventListener('change', () => {
            saveCharacterConfigurations();
        });
    });
}

/**
 * Debounce function to prevent excessive saving
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