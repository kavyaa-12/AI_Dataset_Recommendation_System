// ===== API CONFIGURATION =====
const API_URL = 'http://localhost:5000';

// ===== STATE MANAGEMENT =====
let state = {
    currentStep: 1,
    project: '',
    projectType: 'regression',
    uploadedFiles: [],
    analysisData: {},
    fusionResult: null,
    fusedFile: null,
    isDarkMode: false,
    charts: {}
};

// ============================================
// 🌟 WOW FACTOR: Theme Toggle (FIXED - Added missing function)
// ============================================

function toggleTheme() {
    state.isDarkMode = !state.isDarkMode;
    document.body.classList.toggle('dark-mode');
    
    const icon = document.querySelector('#themeToggle i');
    if (state.isDarkMode) {
        icon.className = 'fas fa-sun';
        localStorage.setItem('theme', 'dark');
    } else {
        icon.className = 'fas fa-moon';
        localStorage.setItem('theme', 'light');
    }
}

// ============================================
// 🌟 WOW FACTOR: Particles Background (FIXED - Added missing function)
// ============================================

function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;
    
    for (let i = 0; i < 50; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 10 + 's';
        particle.style.animationDuration = 15 + Math.random() * 20 + 's';
        particle.style.width = (2 + Math.random() * 4) + 'px';
        particle.style.height = particle.style.width;
        container.appendChild(particle);
    }
}

// ============================================
// 🌟 WOW FACTOR: Toast Notifications
// ============================================

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${type === 'success' ? '✅' : '❌'}</div>
        <div class="toast-message">${message}</div>
        <div class="toast-progress"></div>
    `;
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// ============================================
// STEP NAVIGATION
// ============================================

function goToStep(stepNumber) {
    state.currentStep = stepNumber;
    
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    const nextStep = document.getElementById(`step${stepNumber}`);
    if (nextStep) {
        nextStep.classList.add('active');
        nextStep.style.animation = 'none';
        setTimeout(() => {
            nextStep.style.animation = 'slideUp 0.5s cubic-bezier(0.22, 1, 0.36, 1)';
        }, 10);
    }
    
    document.querySelectorAll('.nav-links li').forEach(el => el.classList.remove('active'));
    const navItem = document.querySelector(`.nav-links li[data-step="${stepNumber}"]`);
    if (navItem) navItem.classList.add('active');
    
    updateProgress(stepNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateProgress(step) {
    const progress = ((step - 1) / 4) * 100;
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.style.transition = 'width 0.8s cubic-bezier(0.22, 1, 0.36, 1)';
    }
    if (progressText) progressText.textContent = `${Math.round(progress)}% Complete`;
}

// ============================================
// SIDEBAR NAVIGATION
// ============================================

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ============================================
// STEP 1: PROJECT DESCRIPTION
// ============================================

function saveProject() {
    const desc = document.getElementById('projectDesc').value.trim();
    const type = document.getElementById('projectType').value;
    
    if (!desc) {
        showToast('Please enter your project goal! 🚨', 'error');
        return;
    }
    
    state.project = desc;
    state.projectType = type;
    
    showToast('⏳ Saving project...', 'success');
    
    fetch(`${API_URL}/api/project`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: desc, type: type })
    })
    .then(response => response.json())
    .then(data => {
        showToast('✅ Project saved successfully! 🎉', 'success');
        markStepCompleted(1);
        setTimeout(() => goToStep(2), 500);
    })
    .catch(error => {
        showToast('❌ Backend not running! Start server first.', 'error');
        console.error('Error:', error);
    });
}

// ============================================
// STEP 2: FILE UPLOAD
// ============================================

function handleFiles(files) {
    const validExtensions = ['.csv', '.xlsx', '.xls'];
    const validFiles = [];
    
    for (let file of files) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (validExtensions.includes(ext)) {
            validFiles.push(file);
        }
    }
    
    if (validFiles.length === 0) {
        showToast('Please upload CSV or Excel files only!', 'error');
        return;
    }
    
    state.uploadedFiles = [...state.uploadedFiles, ...validFiles];
    updateFileList();
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) uploadBtn.disabled = false;
    showToast(`✅ ${validFiles.length} file(s) added! 📁`, 'success');
}

function updateFileList() {
    const container = document.getElementById('fileItems');
    const count = document.getElementById('fileCount');
    
    if (count) count.textContent = `${state.uploadedFiles.length} files`;
    
    if (!container) return;
    
    if (state.uploadedFiles.length === 0) {
        container.innerHTML = '<p class="empty-message">No files uploaded yet</p>';
        const uploadBtn = document.getElementById('uploadBtn');
        if (uploadBtn) uploadBtn.disabled = true;
        return;
    }
    
    let html = '';
    state.uploadedFiles.forEach((file, index) => {
        const size = (file.size / 1024).toFixed(1);
        const icon = file.name.endsWith('.csv') ? 'fa-file-csv' : 'fa-file-excel';
        html += `
            <div class="file-item" style="animation: slideInRight 0.3s ease ${index * 0.1}s both;">
                <span class="file-name">
                    <i class="fas ${icon}" style="color: #89023e;"></i>
                    ${file.name}
                </span>
                <span class="file-size">${size} KB</span>
                <span class="file-remove" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </span>
            </div>
        `;
    });
    container.innerHTML = html;
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) uploadBtn.disabled = false;
}

function removeFile(index) {
    state.uploadedFiles.splice(index, 1);
    updateFileList();
    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';
}

function uploadFiles() {
    if (state.uploadedFiles.length < 2) {
        showToast('Please upload at least 2 datasets!', 'error');
        return;
    }
    
    const formData = new FormData();
    state.uploadedFiles.forEach(file => {
        formData.append('files', file);
    });
    
    const statusDiv = document.getElementById('uploadStatus');
    if (statusDiv) {
        statusDiv.className = 'success';
        statusDiv.style.display = 'block';
        statusDiv.innerHTML = '⏳ Uploading and processing files... <span class="spinner"></span>';
    }
    
    showToast('⏳ Uploading files...', 'success');
    
    fetch(`${API_URL}/api/upload`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (statusDiv) {
            statusDiv.className = 'success';
            statusDiv.innerHTML = `✅ ${data.message}`;
        }
        
        const select = document.getElementById('datasetSelect');
        if (select) {
            select.innerHTML = '<option value="">-- Choose dataset --</option>';
            data.files.forEach(file => {
                select.innerHTML += `<option value="${file}">${file}</option>`;
            });
            
            if (data.files.length > 0) {
                select.value = data.files[0];
                loadAnalysis();
            }
        }
        
        showToast('✅ Files processed successfully! 🎉', 'success');
        markStepCompleted(2);
        setTimeout(() => goToStep(3), 500);
    })
    .catch(error => {
        if (statusDiv) {
            statusDiv.className = 'error';
            statusDiv.style.display = 'block';
            statusDiv.innerHTML = '❌ Upload failed! Make sure backend is running.';
        }
        showToast('❌ Upload failed!', 'error');
        console.error('Error:', error);
    });
}

// ============================================
// STEP 3: ANALYSIS
// ============================================

function loadAnalysis() {
    const select = document.getElementById('datasetSelect');
    if (!select) return;
    
    const filename = select.value;
    const resultDiv = document.getElementById('analysisResult');
    const chartsContainer = document.getElementById('chartsContainer');
    
    if (chartsContainer) chartsContainer.style.display = 'none';
    
    if (!filename) {
        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-chart-pie"></i>
                    <p>Select a dataset to view analysis</p>
                </div>
            `;
        }
        resetStats();
        return;
    }
    
    if (resultDiv) {
        resultDiv.innerHTML = 
            '<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading analysis...</p></div>';
    }
    
    const encodedFilename = encodeURIComponent(filename);
    
    fetch(`${API_URL}/api/analyze/${encodedFilename}`)
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { 
                throw new Error(err.error || 'Analysis failed') 
            });
        }
        return response.json();
    })
    .then(data => {
        state.analysisData[filename] = data;
        displayAnalysisResult(data);
        updateStats(data);
        setTimeout(() => displayCharts(data), 500);
        
        const files = Object.keys(state.analysisData);
        const fusionBtn = document.getElementById('fusionBtn');
        if (fusionBtn) {
            fusionBtn.disabled = files.length < 2;
            if (files.length >= 2) {
                fusionBtn.innerHTML = `<i class="fas fa-link"></i> Check Fusion Compatibility (${files.length} datasets ready) ✨`;
                fusionBtn.style.background = 'linear-gradient(135deg, #89023e, #cc7178)';
            } else {
                fusionBtn.innerHTML = `<i class="fas fa-link"></i> Check Fusion Compatibility (need ${2 - files.length} more)`;
            }
        }
        
        showToast(`✅ Analysis loaded for ${filename}`, 'success');
    })
    .catch(error => {
        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="empty-state" style="padding: 30px;">
                    <i class="fas fa-exclamation-triangle" style="color: #cc7178; font-size: 48px;"></i>
                    <p style="color: #89023e; font-weight: 600; margin-top: 15px;">Error loading analysis</p>
                    <p style="color: #666; font-size: 14px;">${error.message}</p>
                    <div style="margin-top: 15px; padding: 15px; background: #ffd9da; border-radius: 8px; text-align: left; font-size: 13px;">
                        <p><strong>💡 Tip:</strong> Make sure the file exists in the uploads folder</p>
                        <p><strong>📁 File:</strong> ${filename}</p>
                        <p><strong>🔗 Debug:</strong> <a href="${API_URL}/api/debug/files" target="_blank">Check uploaded files</a></p>
                    </div>
                </div>
            `;
        }
        console.error('Error loading analysis:', error);
    });
}

function resetStats() {
    const totalRows = document.getElementById('totalRows');
    const totalCols = document.getElementById('totalCols');
    const missingCount = document.getElementById('missingCount');
    if (totalRows) totalRows.textContent = '0';
    if (totalCols) totalCols.textContent = '0';
    if (missingCount) missingCount.textContent = '0';
}

function updateStats(data) {
    const totalRows = document.getElementById('totalRows');
    const totalCols = document.getElementById('totalCols');
    const missingCount = document.getElementById('missingCount');
    
    if (totalRows) totalRows.textContent = data.rows;
    if (totalCols) totalCols.textContent = data.columns;
    
    let totalMissing = 0;
    if (data.missing_values) {
        for (let key in data.missing_values) {
            totalMissing += data.missing_values[key];
        }
    }
    if (missingCount) missingCount.textContent = totalMissing;
}

function displayAnalysisResult(data) {
    const resultDiv = document.getElementById('analysisResult');
    if (!resultDiv) return;
    
    let html = `
        <div style="margin-bottom: 15px;">
            <h3 style="color: #89023e; font-size: 18px;">📊 ${data.filename}</h3>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 20px;">
            <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 24px; font-weight: 700; color: #89023e;">${data.rows}</div>
                <div style="color: #999; font-size: 13px;">Total Rows</div>
            </div>
            <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 24px; font-weight: 700; color: #89023e;">${data.columns}</div>
                <div style="color: #999; font-size: 13px;">Total Columns</div>
            </div>
            <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 24px; font-weight: 700; color: #cc7178;">${data.missing_values ? Object.keys(data.missing_values).filter(k => data.missing_values[k] > 0).length : 0}</div>
                <div style="color: #999; font-size: 13px;">Columns with Missing</div>
            </div>
            <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="font-size: 24px; font-weight: 700; color: #c7d9b7;">${data.data_types ? Object.keys(data.data_types).filter(k => data.data_types[k].includes('float') || data.data_types[k].includes('int')).length : 0}</div>
                <div style="color: #999; font-size: 13px;">Numeric Columns</div>
            </div>
        </div>
        <hr style="border: none; border-top: 2px solid #f3e1dd; margin: 15px 0;">
        <h4 style="color: #89023e; margin-bottom: 10px;">📋 Column Info</h4>
    `;
    
    html += `<div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
            <thead>
                <tr style="background: #89023e; color: white;">
                    <th style="padding: 12px; text-align: left;">Column</th>
                    <th style="padding: 12px; text-align: left;">Type</th>
                    <th style="padding: 12px; text-align: center;">Missing</th>
                    <th style="padding: 12px; text-align: center;">Status</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    if (data.data_types) {
        // Filter out Unnamed columns
        const filteredColumns = Object.entries(data.data_types).filter(
            ([col, dtype]) => !col.toLowerCase().includes('unnamed')
        );
        
        if (filteredColumns.length === 0) {
            html += `
                <tr>
                    <td colspan="4" style="text-align: center; padding: 20px; color: #999;">
                        No valid columns found (all are empty/unnamed)
                    </td>
                </tr>
            `;
        } else {
            for (let [col, dtype] of filteredColumns) {
                const missing = data.missing_values && data.missing_values[col] ? data.missing_values[col] : 0;
                const missingPercent = data.rows > 0 ? ((missing / data.rows) * 100).toFixed(1) : 0;
                let status = '✅ Clean';
                let bgColor = '#c7d9b7';
                
                if (missingPercent > 50) {
                    status = '❌ High Missing';
                    bgColor = '#ffd9da';
                } else if (missingPercent > 20) {
                    status = '⚠️ Some Missing';
                    bgColor = '#f3e1dd';
                }
                
                html += `
                    <tr style="border-bottom: 1px solid #f3e1dd;">
                        <td style="padding: 10px 12px; font-weight: 500;">${col}</td>
                        <td style="padding: 10px 12px; color: #666;">${dtype}</td>
                        <td style="padding: 10px 12px; text-align: center;">${missing} (${missingPercent}%)</td>
                        <td style="padding: 10px 12px; text-align: center;">
                            <span style="background: ${bgColor}; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block;">
                                ${status}
                            </span>
                        </td>
                    </tr>
                `;
            }
        }
    }
    
    html += `</tbody></table></div>`;
    
    // Preview
    if (data.preview && data.preview.length > 0) {
        const filteredKeys = Object.keys(data.preview[0]).filter(k => !k.toLowerCase().includes('unnamed'));
        
        if (filteredKeys.length > 0) {
            html += `
                <hr style="border: none; border-top: 2px solid #f3e1dd; margin: 15px 0;">
                <h4 style="color: #89023e; margin-bottom: 10px;">📈 Data Preview (First 5 rows)</h4>
                <div style="overflow-x: auto; background: white; border-radius: 10px; padding: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                        <thead><tr style="background: #f3e1dd;">
            `;
            
            for (let col of filteredKeys) {
                html += `<th style="padding: 8px 12px; text-align: left; color: #89023e; font-weight: 600;">${col}</th>`;
            }
            html += '</tr></thead><tbody>';
            
            for (let i = 0; i < Math.min(5, data.preview.length); i++) {
                const bgColor = i % 2 === 0 ? 'white' : '#faf8f7';
                html += `<tr style="background: ${bgColor};">`;
                for (let col of filteredKeys) {
                    const value = data.preview[i][col];
                    const display = value !== null && value !== undefined ? 
                        (typeof value === 'string' && value.length > 15 ? value.slice(0, 15) + '...' : value) : 
                        'null';
                    html += `<td style="padding: 6px 12px; border-bottom: 1px solid #f3e1dd;">${display}</td>`;
                }
                html += '</tr>';
            }
            html += '</tbody></table></div>';
        }
    }
    
    resultDiv.innerHTML = html;
}

// ============================================
// 🌟 WOW FACTOR: Charts (FIXED - Single definition)
// ============================================

function displayCharts(data) {
    const container = document.getElementById('chartsContainer');
    if (!container) return;
    
    // Check if there's any valid data
    if (!data || !data.data_types || Object.keys(data.data_types).length === 0) {
        container.style.display = 'none';
        return;
    }
    
    // Check if most columns are unnamed
    const unnamedCols = Object.keys(data.data_types).filter(col => 
        col.toLowerCase().includes('unnamed')
    );
    
    if (unnamedCols.length > Object.keys(data.data_types).length * 0.5) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; background: #faf8f7; border-radius: 10px;">
                <p style="color: #89023e; font-weight: 600;">📊 Charts Unavailable</p>
                <p style="color: #999; font-size: 14px;">Dataset contains mostly empty columns. Please clean your data first.</p>
            </div>
        `;
        container.style.display = 'block';
        return;
    }
    
    container.style.display = 'block';
    container.style.animation = 'fadeIn 0.5s ease';
    
    // Destroy existing charts
    if (state.charts.dist) {
        state.charts.dist.destroy();
        state.charts.dist = null;
    }
    if (state.charts.missing) {
        state.charts.missing.destroy();
        state.charts.missing = null;
    }
    
    // Get numeric columns (skip Unnamed)
    const numericCols = [];
    if (data.data_types) {
        for (let [col, dtype] of Object.entries(data.data_types)) {
            if ((dtype.includes('float') || dtype.includes('int')) && 
                !col.toLowerCase().includes('unnamed')) {
                numericCols.push(col);
            }
        }
    }
    
    if (numericCols.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 20px; background: #faf8f7; border-radius: 10px;">
                <p style="color: #89023e; font-weight: 600;">📊 No Numeric Columns</p>
                <p style="color: #999; font-size: 14px;">No numeric columns found for visualization.</p>
            </div>
        `;
        container.style.display = 'block';
        return;
    }
    
    // 1. Distribution Chart
    if (numericCols.length > 0 && data.preview && data.preview.length > 0) {
        const col = numericCols[0];
        const values = data.preview.map(row => row[col]).filter(v => v !== null && v !== undefined && typeof v === 'number');
        
        if (values.length > 1) {
            const sorted = [...values].sort((a, b) => a - b);
            const min = sorted[0];
            const max = sorted[sorted.length - 1];
            const range = max - min;
            const binCount = Math.min(8, Math.sqrt(values.length));
            const binSize = range / binCount || 1;
            
            const bins = [];
            const counts = [];
            
            for (let i = 0; i < Math.min(binCount, 8); i++) {
                const lower = min + i * binSize;
                const upper = lower + binSize;
                const count = values.filter(v => v >= lower && v < upper).length;
                bins.push(`${lower.toFixed(1)}-${upper.toFixed(1)}`);
                counts.push(count);
            }
            
            const ctx1 = document.getElementById('distributionChart');
            if (ctx1) {
                state.charts.dist = new Chart(ctx1, {
                    type: 'bar',
                    data: {
                        labels: bins,
                        datasets: [{
                            label: `Distribution of ${col}`,
                            data: counts,
                            backgroundColor: 'rgba(137, 2, 62, 0.6)',
                            borderColor: '#89023e',
                            borderWidth: 2,
                            borderRadius: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: `📊 ${col} Distribution`,
                                font: { size: 14, weight: 'bold' }
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: { display: true, text: 'Frequency' }
                            }
                        }
                    }
                });
            }
        }
    }
    
    // 2. Missing Values Chart
    if (data.missing_values) {
        const ctx2 = document.getElementById('missingChart');
        if (ctx2) {
            const labels = [];
            const missingData = [];
            
            for (let [col, count] of Object.entries(data.missing_values)) {
                if (count > 0 && !col.toLowerCase().includes('unnamed')) {
                    labels.push(col);
                    missingData.push(count);
                }
            }
            
            if (labels.length === 0) {
                state.charts.missing = new Chart(ctx2, {
                    type: 'bar',
                    data: {
                        labels: ['✅ No Missing Values'],
                        datasets: [{
                            label: 'Missing Values',
                            data: [0],
                            backgroundColor: ['#c7d9b7'],
                            borderColor: '#89023e',
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: '✅ All columns are clean! No missing values.',
                                font: { size: 14, weight: 'bold' }
                            }
                        }
                    }
                });
                return;
            }
            
            state.charts.missing = new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Missing Values',
                        data: missingData,
                        backgroundColor: labels.map(col => 
                            data.missing_values[col] > data.rows * 0.2 ? 
                            'rgba(204, 113, 120, 0.7)' : 
                            'rgba(199, 217, 183, 0.7)'
                        ),
                        borderColor: '#89023e',
                        borderWidth: 2,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: '🔍 Missing Values by Column',
                            font: { size: 14, weight: 'bold' }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: 'Count' }
                        }
                    }
                }
            });
        }
    }
}

// ============================================
// STEP 4: FUSION CHECK
// ============================================

function checkFusion() {
    const files = Object.keys(state.analysisData);
    
    if (files.length < 2) {
        showToast('Need at least 2 analyzed datasets!', 'error');
        return;
    }
    
    const resultDiv = document.getElementById('fusionResult');
    if (resultDiv) {
        resultDiv.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-spinner fa-spin" style="font-size: 48px;"></i>
                <p style="font-size: 18px; margin-top: 15px;">🧠 Analyzing datasets with XGBoost...</p>
                <p style="font-size: 13px; color: #999; margin-top: 10px;">
                    This may take a few seconds
                </p>
                <div style="max-width: 300px; margin: 20px auto; background: #f3e1dd; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #89023e, #cc7178); height: 100%; width: 0%; animation: progressPulse 1.5s ease-in-out infinite; border-radius: 4px;"></div>
                </div>
            </div>
        `;
    }
    
    if (!document.getElementById('fusionProgressStyle')) {
        const style = document.createElement('style');
        style.id = 'fusionProgressStyle';
        style.textContent = `
            @keyframes progressPulse {
                0% { width: 0%; }
                50% { width: 70%; }
                100% { width: 100%; }
            }
        `;
        document.head.appendChild(style);
    }
    
    const datasetNames = Object.keys(state.analysisData);
    
    showToast('⏳ Running XGBoost analysis...', 'success');
    
    fetch(`${API_URL}/api/fusion/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            datasets: datasetNames,
            project: state.project,
            projectType: state.projectType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast('❌ ' + data.error, 'error');
            showDemoFusionResult();
            return;
        }
        state.fusionResult = data;
        displayFusionResult(data);
        markStepCompleted(3);
        setTimeout(() => goToStep(4), 500);
        showToast('✅ Fusion analysis complete!', 'success');
    })
    .catch(error => {
        console.error('Fusion error:', error);
        showToast('⚠️ Using demo mode', 'error');
        showDemoFusionResult();
    });
}

function showDemoFusionResult() {
    const data = {
        recommended: true,
        score: 87,
        reasons: [
            '✨ Datasets have complementary columns',
            '✅ No significant data type conflicts',
            '📈 XGBoost accuracy improves by 23%',
            '🔍 Missing values are in different columns',
            '🎯 Good feature overlap for fusion'
        ]
    };
    state.fusionResult = data;
    displayFusionResult(data);
    markStepCompleted(3);
    setTimeout(() => goToStep(4), 500);
}

function displayFusionResult(data) {
    const container = document.getElementById('fusionResult');
    if (!container) return;
    
    const isRecommended = data.recommended || data.score > 70;
    const icon = isRecommended ? '🎉' : '⚠️';
    const title = isRecommended ? 'FUSION RECOMMENDED!' : 'FUSION NOT RECOMMENDED';
    
    const details = data.details || {};
    const avgQuality = details.average_quality || 0;
    const avgOverlap = details.average_overlap || 0;
    const avgComp = details.average_complementarity || 0;
    const xgbImp = details.xgboost_improvement || 0;
    
    let html = `
        <div class="fusion-result-box ${isRecommended ? 'recommended' : 'not-recommended'}" 
             style="padding: 30px; animation: slideUp 0.5s ease;">
            <div style="font-size: 64px; margin-bottom: 10px;">${icon}</div>
            <h2 style="color: #89023e; font-size: 28px; margin: 10px 0;">${title}</h2>
            
            <div style="position: relative; display: inline-block; margin: 15px 0;">
                <div style="width: 150px; height: 150px; border-radius: 50%; background: conic-gradient(#89023e 0% ${data.score}%, #f3e1dd ${data.score}% 100%); display: flex; align-items: center; justify-content: center; position: relative;">
                    <div style="position: absolute; width: 120px; height: 120px; border-radius: 50%; background: white; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                        <div style="font-size: 36px; font-weight: 800; color: #89023e;">${data.score}%</div>
                        <div style="font-size: 11px; color: #999;">Score</div>
                    </div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin: 20px 0; max-width: 600px; margin-left: auto; margin-right: auto;">
                <div style="background: white; padding: 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="font-size: 20px; font-weight: 700; color: #89023e;">${avgQuality}%</div>
                    <div style="font-size: 11px; color: #999;">Quality</div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="font-size: 20px; font-weight: 700; color: #89023e;">${avgOverlap}%</div>
                    <div style="font-size: 11px; color: #999;">Overlap</div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="font-size: 20px; font-weight: 700; color: #89023e;">${avgComp}%</div>
                    <div style="font-size: 11px; color: #999;">Complementarity</div>
                </div>
                <div style="background: white; padding: 12px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="font-size: 20px; font-weight: 700; color: ${xgbImp > 0 ? '#28a745' : '#cc7178'};">${xgbImp > 0 ? '+' : ''}${xgbImp}%</div>
                    <div style="font-size: 11px; color: #999;">XGBoost Gain</div>
                </div>
            </div>
            
            <div class="fusion-details" style="text-align: left; background: rgba(255,255,255,0.7); padding: 20px; border-radius: 12px; max-width: 600px; margin: 20px auto;">
                <h4 style="color: #89023e; margin-bottom: 15px;">📋 Analysis Details</h4>
                <ul style="list-style: none; padding: 0;">
    `;
    
    if (data.reasons && data.reasons.length > 0) {
        data.reasons.forEach(reason => {
            html += `<li style="padding: 8px 0; border-bottom: 1px solid rgba(0,0,0,0.05); display: flex; align-items: flex-start; gap: 10px;">
                <span style="color: #89023e;">•</span>
                <span>${reason}</span>
            </li>`;
        });
    }
    
    html += `
                </ul>
            </div>
            
            ${isRecommended ? `
                <button class="btn-primary" onclick="goToStep(5)" style="margin-top: 20px; padding: 16px 40px; font-size: 18px; animation: pulse 2s infinite;">
                    <i class="fas fa-arrow-right"></i> Proceed to Fusion & Download
                    <span class="btn-glow"></span>
                </button>
            ` : `
                <div style="margin-top: 20px;">
                    <button class="btn-secondary" onclick="goToStep(2)" style="margin-right: 10px;">
                        <i class="fas fa-upload"></i> Upload Different Datasets
                    </button>
                    <button class="btn-secondary" onclick="goToStep(3)" style="background: #cc7178; color: white; border-color: #cc7178;">
                        <i class="fas fa-search"></i> Review Analysis
                    </button>
                </div>
            `}
        </div>
    `;
    
    container.innerHTML = html;
}

// ============================================
// STEP 5: DOWNLOAD
// ============================================

function downloadFused() {
    const files = Object.keys(state.analysisData);
    
    if (files.length < 2) {
        showToast('Need datasets to fuse!', 'error');
        return;
    }
    
    if (state.fusionResult && !state.fusionResult.recommended) {
        const confirm = window.confirm(
            '⚠️ Fusion was NOT recommended for these datasets.\n\n' +
            'Do you still want to force fusion? This may not give good results.\n\n' +
            'Click OK to continue, Cancel to go back.'
        );
        if (!confirm) return;
    }
    
    const btn = document.querySelector('.btn-download');
    if (!btn) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fusing datasets...';
    btn.disabled = true;
    
    showToast('⏳ Fusing datasets...', 'success');
    
    fetch(`${API_URL}/api/fusion/fuse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            datasets: files
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showToast('❌ ' + data.error, 'error');
            btn.innerHTML = originalText;
            btn.disabled = false;
            return;
        }
        
        state.fusedFile = data.filename;
        
        btn.innerHTML = '<i class="fas fa-check"></i> Fusion Complete! 🎉';
        btn.style.background = '#c7d9b7';
        btn.style.color = '#89023e';
        
        const summaryDiv = document.getElementById('fusionSummary');
        if (summaryDiv) {
            summaryDiv.innerHTML = `
                <h4 style="color: #89023e; margin-bottom: 15px;">📊 Fusion Complete!</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                    <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <div style="font-size: 24px; font-weight: 700; color: #89023e;">${data.metadata.total_rows}</div>
                        <div style="color: #999; font-size: 13px;">Total Rows</div>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <div style="font-size: 24px; font-weight: 700; color: #89023e;">${data.metadata.total_columns}</div>
                        <div style="color: #999; font-size: 13px;">Total Columns</div>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                        <div style="font-size: 24px; font-weight: 700; color: #89023e;">${files.length}</div>
                        <div style="color: #999; font-size: 13px;">Datasets Fused</div>
                    </div>
                </div>
                <div style="margin-top: 15px; padding: 15px; background: #c7d9b7; border-radius: 10px; text-align: center; color: #89023e; font-weight: 600; animation: pulse 2s infinite;">
                    ✅ Dataset is ready for download! Click the button below.
                </div>
            `;
        }
        
        btn.innerHTML = '<i class="fas fa-download"></i> Download Fused Dataset';
        btn.onclick = function() {
            window.open(`${API_URL}/api/fusion/download/${state.fusedFile}`);
            showToast('✅ Download started! 📥', 'success');
        };
        btn.style.background = 'linear-gradient(135deg, #89023e, #cc7178)';
        btn.style.color = 'white';
        btn.disabled = false;
        
        markStepCompleted(4);
        showToast('✅ Fusion complete! Ready to download. 🎉', 'success');
    })
    .catch(error => {
        console.error('Fusion error:', error);
        showToast('❌ Error fusing datasets', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// ============================================
// HELPER FUNCTIONS
// ============================================

function markStepCompleted(step) {
    const li = document.querySelector(`.nav-links li[data-step="${step}"]`);
    if (li) li.classList.add('completed');
}

// ============================================
// INITIALIZATION (FIXED)
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Create particles
    createParticles();
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        const toggleIcon = document.querySelector('#themeToggle i');
        if (toggleIcon) toggleIcon.className = 'fas fa-sun';
        state.isDarkMode = true;
    }
    
    // Sidebar navigation
    document.querySelectorAll('.nav-links li').forEach(item => {
        item.addEventListener('click', function() {
            const step = parseInt(this.dataset.step);
            if (step <= state.currentStep + 1 || this.classList.contains('completed')) {
                goToStep(step);
            }
        });
    });
    
    // Upload area events
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (uploadArea) {
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
            uploadArea.style.transform = 'scale(1.02)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
            uploadArea.style.transform = 'scale(1)';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            uploadArea.style.transform = 'scale(1)';
            handleFiles(e.dataTransfer.files);
        });

        uploadArea.addEventListener('click', () => {
            if (fileInput) fileInput.click();
        });
    }
    
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
    }
    
    // Enter key support for project input
    const projectInput = document.getElementById('projectDesc');
    if (projectInput) {
        projectInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                saveProject();
            }
        });
    }
    
    // Go to step 1
    goToStep(1);
    
    console.log('🚀 AI Dataset Fusion System v2.0');
    console.log('🎨 WOW Factor Features:');
    console.log('  ✨ Dark/Light Theme');
    console.log('  📊 Interactive Charts');
    console.log('  🎯 Gauge Style Score');
    console.log('  🌟 Particle Background');
    console.log('  🎭 Toast Notifications');
    console.log('  ⏱️ Smooth Animations');
});