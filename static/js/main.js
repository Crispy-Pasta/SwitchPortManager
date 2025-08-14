/**
 * Dell Switch Port Tracer - Main JavaScript Module
 * ================================================
 * 
 * Handles MAC address tracing, form validation, and UI interactions
 * for the main port tracer interface.
 * 
 * Version: 2.1.3
 * Updated: August 2025
 */

class PortTracer {
    constructor() {
        this.init();
    }

    init() {
        console.log('🚀 Port Tracer initialized');
        this.setupEventListeners();
        this.setupFormValidation();
        this.preloadSwitchData();
    }

    setupEventListeners() {
        // Site selection change
        const siteSelect = document.getElementById('site');
        if (siteSelect) {
            siteSelect.addEventListener('change', this.onSiteChange.bind(this));
        }

        // Floor selection change
        const floorSelect = document.getElementById('floor');
        if (floorSelect) {
            floorSelect.addEventListener('change', this.onFloorChange.bind(this));
        }

        // MAC input formatting
        const macInput = document.getElementById('mac');
        if (macInput) {
            macInput.addEventListener('input', this.formatMacAddress.bind(this));
            macInput.addEventListener('paste', this.handleMacPaste.bind(this));
        }

        // Trace form submission
        const traceForm = document.getElementById('trace-form');
        if (traceForm) {
            traceForm.addEventListener('submit', this.handleTraceSubmit.bind(this));
        }

        // Real-time search for switches
        const searchInput = document.getElementById('switch-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.handleSwitchSearch.bind(this));
        }
    }

    setupFormValidation() {
        // Add visual indicators for form validation
        const requiredFields = document.querySelectorAll('input[required], select[required]');
        requiredFields.forEach(field => {
            field.addEventListener('blur', this.validateField.bind(this, field));
            field.addEventListener('input', this.clearFieldError.bind(this, field));
        });
    }

    validateField(field) {
        const isValid = field.checkValidity();
        const errorElement = field.parentNode.querySelector('.field-error');

        if (!isValid) {
            field.classList.add('error');
            if (!errorElement) {
                const error = document.createElement('div');
                error.className = 'field-error';
                error.textContent = this.getFieldErrorMessage(field);
                field.parentNode.appendChild(error);
            }
        } else {
            field.classList.remove('error');
            if (errorElement) {
                errorElement.remove();
            }
        }

        return isValid;
    }

    clearFieldError(field) {
        field.classList.remove('error');
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    }

    getFieldErrorMessage(field) {
        if (field.id === 'mac') {
            return 'Please enter a valid MAC address (e.g., aa:bb:cc:dd:ee:ff)';
        }
        if (field.tagName === 'SELECT') {
            return `Please select a ${field.id}`;
        }
        return 'This field is required';
    }

    formatMacAddress(event) {
        let value = event.target.value.replace(/[^a-fA-F0-9]/g, '');
        
        // Auto-format with colons
        if (value.length > 2) {
            value = value.match(/.{1,2}/g).join(':');
        }
        
        // Limit to MAC address length
        if (value.length > 17) {
            value = value.substring(0, 17);
        }
        
        event.target.value = value.toLowerCase();
        
        // Show format hint
        this.showMacFormatHint(event.target, value);
    }

    handleMacPaste(event) {
        // Allow various MAC formats on paste
        setTimeout(() => {
            const input = event.target;
            let value = input.value;
            
            // Clean and reformat pasted MAC address
            value = value.replace(/[^a-fA-F0-9]/g, '');
            if (value.length === 12) {
                value = value.match(/.{2}/g).join(':');
            }
            
            input.value = value.toLowerCase();
            this.showMacFormatHint(input, value);
        }, 10);
    }

    showMacFormatHint(input, value) {
        const hint = input.parentNode.querySelector('.mac-hint');
        
        if (value.length > 0 && value.length < 17) {
            if (!hint) {
                const hintElement = document.createElement('div');
                hintElement.className = 'mac-hint';
                hintElement.innerHTML = '💡 MAC format: aa:bb:cc:dd:ee:ff';
                input.parentNode.appendChild(hintElement);
            }
        } else if (hint) {
            hint.remove();
        }
    }

    onSiteChange(event) {
        const siteSelect = event.target;
        const floorSelect = document.getElementById('floor');
        const selectedSite = siteSelect.value;

        // Clear floor dropdown
        floorSelect.innerHTML = '<option value="">Select Floor...</option>';
        
        if (!selectedSite) {
            return;
        }

        // Show loading indicator
        this.showLoadingIndicator(floorSelect.parentNode, 'Loading floors...');

        // Load floors for selected site
        this.loadFloors(selectedSite);
    }

    onFloorChange(event) {
        const floorSelect = event.target;
        const switchInfo = document.getElementById('switch-info');
        
        if (!floorSelect.value) {
            if (switchInfo) {
                switchInfo.style.display = 'none';
            }
            return;
        }

        // Show switch count for selected floor
        this.updateSwitchInfo();
    }

    async loadFloors(siteName) {
        try {
            // Get floors data from embedded site data or API
            const sitesData = window.sitesData || {};
            const siteData = sitesData[siteName];
            
            const floorSelect = document.getElementById('floor');
            
            if (siteData) {
                // Populate floors dropdown
                Object.keys(siteData).forEach(floorName => {
                    const option = document.createElement('option');
                    option.value = floorName;
                    option.textContent = this.formatFloorName(floorName);
                    floorSelect.appendChild(option);
                });
                
                this.hideLoadingIndicator(floorSelect.parentNode);
            } else {
                throw new Error('Site data not found');
            }
            
        } catch (error) {
            console.error('Failed to load floors:', error);
            this.showError('Failed to load floors for selected site');
            this.hideLoadingIndicator(document.getElementById('floor').parentNode);
        }
    }

    formatFloorName(floorName) {
        // Format floor names consistently (e.g., "11" -> "Floor 11", "GF" -> "Ground Floor")
        if (/^\d+$/.test(floorName)) {
            return `Floor ${floorName}`;
        }
        if (floorName === 'GF') {
            return 'Ground Floor';
        }
        if (floorName === 'PH') {
            return 'Penthouse';
        }
        return floorName;
    }

    updateSwitchInfo() {
        const siteSelect = document.getElementById('site');
        const floorSelect = document.getElementById('floor');
        const switchInfo = document.getElementById('switch-info');
        
        if (!switchInfo) return;

        const siteName = siteSelect.value;
        const floorName = floorSelect.value;
        
        if (siteName && floorName) {
            const sitesData = window.sitesData || {};
            const siteData = sitesData[siteName];
            const floorData = siteData ? siteData[floorName] : null;
            
            if (floorData && floorData.length > 0) {
                switchInfo.innerHTML = `
                    <div class="switch-count">
                        <span class="icon">🔌</span>
                        <span class="count">${floorData.length}</span>
                        <span class="label">switch${floorData.length !== 1 ? 'es' : ''} available</span>
                    </div>
                `;
                switchInfo.style.display = 'block';
            } else {
                switchInfo.innerHTML = '<div class="no-switches">⚠️ No switches found for this floor</div>';
                switchInfo.style.display = 'block';
            }
        } else {
            switchInfo.style.display = 'none';
        }
    }

    async handleTraceSubmit(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Validate form before submission
        const isValid = this.validateTraceForm(form);
        if (!isValid) {
            this.showError('Please fix the errors above and try again');
            return;
        }
        
        // Show loading state
        this.showLoadingState(true);
        
        try {
            const response = await fetch('/trace', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });
            
            const results = await response.json();
            
            if (response.ok) {
                this.displayResults(results);
                this.logTraceAttempt(data, results.length);
            } else {
                throw new Error(results.error || 'Trace request failed');
            }
            
        } catch (error) {
            console.error('Trace error:', error);
            this.showError(error.message || 'Failed to trace MAC address');
        } finally {
            this.showLoadingState(false);
        }
    }

    validateTraceForm(form) {
        const fields = form.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        fields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        // Additional MAC address validation
        const macField = form.querySelector('#mac');
        if (macField && macField.value) {
            const macRegex = /^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$/i;
            if (!macRegex.test(macField.value)) {
                this.validateField(macField); // This will show the error
                isValid = false;
            }
        }
        
        return isValid;
    }

    displayResults(results) {
        const resultsContainer = document.getElementById('results');
        if (!resultsContainer) return;
        
        resultsContainer.innerHTML = '';
        
        if (results.length === 0) {
            resultsContainer.innerHTML = `
                <div class="no-results">
                    <div class="icon">🔍</div>
                    <div class="message">No MAC address matches found</div>
                    <div class="suggestion">The device might be offline or on a different network segment</div>
                </div>
            `;
            return;
        }
        
        // Group results by status
        const foundResults = results.filter(r => r.status === 'found');
        const notFoundResults = results.filter(r => r.status !== 'found');
        
        let html = '';
        
        if (foundResults.length > 0) {
            html += '<h3 class="results-header found">✅ MAC Address Found</h3>';
            foundResults.forEach((result, index) => {
                html += this.formatResultItem(result, index, 'found');
            });
        }
        
        if (notFoundResults.length > 0) {
            html += '<h3 class="results-header not-found">🔍 Other Switches Checked</h3>';
            notFoundResults.forEach((result, index) => {
                html += this.formatResultItem(result, index, 'not-found');
            });
        }
        
        resultsContainer.innerHTML = html;
        
        // Smooth scroll to results
        setTimeout(() => {
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }

    formatResultItem(result, index, type) {
        const statusIcon = result.status === 'found' ? '✅' : '❌';
        const statusClass = result.status === 'found' ? 'found' : 'not-found';
        
        let details = '';
        if (result.status === 'found') {
            details = `
                <div class="result-details">
                    <div class="detail-item"><strong>Port:</strong> ${result.port}</div>
                    <div class="detail-item"><strong>VLAN:</strong> ${result.vlan}</div>
                    ${result.port_description ? `<div class="detail-item"><strong>Description:</strong> ${result.port_description}</div>` : ''}
                    ${result.port_mode ? `<div class="detail-item"><strong>Mode:</strong> ${result.port_mode}</div>` : ''}
                    ${result.is_uplink ? '<div class="detail-item uplink-warning">⚠️ This is an uplink port</div>' : ''}
                </div>
            `;
        } else if (result.message) {
            details = `<div class="error-message">${result.message}</div>`;
        }
        
        return `
            <div class="result-item ${statusClass}" data-index="${index}">
                <div class="result-header">
                    <span class="status-icon">${statusIcon}</span>
                    <span class="switch-name">${result.switch_name}</span>
                    <span class="switch-ip">${result.switch_ip}</span>
                </div>
                ${details}
            </div>
        `;
    }

    showLoadingState(show) {
        const button = document.querySelector('button[type="submit"]');
        const resultsContainer = document.getElementById('results');
        
        if (show) {
            if (button) {
                button.disabled = true;
                button.innerHTML = '🔄 Tracing...';
            }
            
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="loading-state">
                        <div class="spinner"></div>
                        <div class="loading-message">Searching switches for MAC address...</div>
                    </div>
                `;
            }
        } else {
            if (button) {
                button.disabled = false;
                button.innerHTML = '🔍 Trace MAC Address';
            }
        }
    }

    showLoadingIndicator(container, message) {
        const loading = document.createElement('div');
        loading.className = 'loading-indicator';
        loading.innerHTML = `<span class="spinner"></span> ${message}`;
        container.appendChild(loading);
    }

    hideLoadingIndicator(container) {
        const loading = container.querySelector('.loading-indicator');
        if (loading) {
            loading.remove();
        }
    }

    showError(message) {
        // Remove any existing error messages
        const existingError = document.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Create new error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <div class="error-content">
                <span class="error-icon">❌</span>
                <span class="error-text">${message}</span>
                <button class="error-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;
        
        // Insert after the form
        const form = document.getElementById('trace-form');
        if (form) {
            form.parentNode.insertBefore(errorDiv, form.nextSibling);
        }
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 10000);
    }

    logTraceAttempt(data, resultCount) {
        // Log trace attempt for analytics (client-side only)
        console.log('📊 Trace completed:', {
            site: data.site,
            floor: data.floor,
            mac: data.mac,
            results: resultCount,
            timestamp: new Date().toISOString()
        });
    }

    preloadSwitchData() {
        // Preload site and switch data for faster UI interactions
        if (window.sitesData) {
            console.log('📋 Switch data preloaded:', Object.keys(window.sitesData).length, 'sites');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.portTracer = new PortTracer();
});

// Additional utility functions
window.utils = {
    formatMacAddress: function(mac) {
        return mac.replace(/[^a-fA-F0-9]/g, '').match(/.{2}/g).join(':').toLowerCase();
    },
    
    isValidMacAddress: function(mac) {
        const macRegex = /^([0-9a-f]{2}[:-]){5}([0-9a-f]{2})$/i;
        return macRegex.test(mac);
    },
    
    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            console.log('📋 Copied to clipboard:', text);
        });
    }
};
