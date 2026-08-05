// Main App Actions
document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle Handler
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
    }
    
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            document.body.classList.toggle('light-theme');
            const theme = document.body.classList.contains('light-theme') ? 'light' : 'dark';
            localStorage.setItem('theme', theme);
            const icon = themeBtn.querySelector('i');
            if (icon) {
                icon.className = theme === 'light' ? 'fas fa-moon' : 'fas fa-sun';
            }
        });
    }

    // Initialize dropzone if on upload page
    initDropzone();

    // Setup Preview triggers for file lists
    initPreviews();
});

// CSV Dataset Previews Loader
function initPreviews() {
    document.querySelectorAll('.file-preview-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const filename = btn.dataset.filename;
            const container = document.getElementById(`preview-${CSS.escape(filename)}`);
            
            if (!container) return;

            // If already open, toggle hide
            if (container.style.display === 'block') {
                container.style.display = 'none';
                btn.innerHTML = '<i class="fas fa-eye me-1"></i>Preview';
                return;
            }

            // Fetch table rows
            container.innerHTML = '<div class="text-center py-3"><i class="fas fa-spinner fa-spin text-muted me-2"></i>Loading Preview...</div>';
            container.style.display = 'block';
            btn.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Preview';

            fetch(`/profile-preview/${encodeURIComponent(filename)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.error) {
                        container.innerHTML = `<div class="text-danger small py-2"><i class="fas fa-exclamation-triangle me-2"></i>${data.error}</div>`;
                        return;
                    }
                    
                    let tableHtml = `
                        <div class="table-responsive">
                            <table class="table table-sm table-dark text-secondary small align-middle mb-0" style="font-size:0.75rem;">
                                <thead>
                                    <tr>
                                        ${data.columns.map(c => `<th>${c}</th>`).join('')}
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.rows.map(r => `
                                        <tr>
                                            ${data.columns.map(c => `<td>${r[c]}</td>`).join('')}
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    `;
                    container.innerHTML = tableHtml;
                })
                .catch(err => {
                    container.innerHTML = `<div class="text-danger small py-2">Failed to load preview data.</div>`;
                });
        });
    });

    // Delete handler
    document.querySelectorAll('.file-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const filename = btn.dataset.filename;
            if (!confirm(`Are you sure you want to permanently delete "${filename}"?`)) return;

            fetch(`/api/delete-file/${encodeURIComponent(filename)}`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.message) {
                        // Remove element
                        const card = btn.closest('.file-item');
                        if (card) card.remove();
                        // Optional reload
                        window.location.reload();
                    } else {
                        alert(data.error || 'Failed to delete file');
                    }
                })
                .catch(err => alert('Network error deleting dataset'));
        });
    });
}

// File Drag & Drop handler
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    if (!dropzone) return;

    const fileInput = document.getElementById('csvFileInput');
    const uploadForm = document.getElementById('uploadForm');
    const fileList = document.getElementById('uploadedFilesList');
    
    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        uploadFiles(dt.files);
    });

    fileInput.addEventListener('change', (e) => {
        uploadFiles(e.target.files);
    });

    function uploadFiles(files) {
        if (files.length === 0) return;

        // Process files one-by-one
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (!file.name.endsWith('.csv')) {
                alert(`File "${file.name}" is not a valid CSV.`);
                continue;
            }
            
            // Create a progress item
            const pItem = document.createElement('div');
            pItem.className = 'file-item';
            pItem.innerHTML = `
                <div class="file-item-header">
                    <div class="file-info">
                        <i class="fas fa-spinner fa-spin text-primary fa-lg"></i>
                        <strong>${file.name}</strong>
                    </div>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar-fill" style="width: 0%"></div>
                </div>
            `;
            fileList.appendChild(pItem);

            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('file', file);
            
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    pItem.querySelector('.progress-bar-fill').style.width = percent + '%';
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    pItem.innerHTML = `
                        <div class="file-item-header">
                            <div class="file-info">
                                <i class="fas fa-file-csv text-success fa-lg"></i>
                                <div>
                                    <strong>${file.name}</strong>
                                    <small class="text-muted d-block">${(file.size/1024).toFixed(1)} KB</small>
                                </div>
                            </div>
                            <span class="text-success small"><i class="fas fa-check-circle me-1"></i>Uploaded</span>
                        </div>
                    `;
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    const errRes = JSON.parse(xhr.responseText);
                    pItem.innerHTML = `
                        <div class="file-item-header">
                            <div class="file-info">
                                <i class="fas fa-times-circle text-danger fa-lg"></i>
                                <strong>${file.name}</strong>
                            </div>
                            <span class="text-danger small">Failed</span>
                        </div>
                        <div class="text-danger small mt-2">${errRes.error || 'Upload error'}</div>
                    `;
                }
            });
            
            xhr.open('POST', '/upload', true);
            xhr.send(formData);
        }
    }
}

// Chart.js helper functions
function renderQualityChart(ctxId, dataA, dataB, labels) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Dataset A',
                    data: dataA,
                    backgroundColor: 'rgba(59, 130, 246, 0.75)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1
                },
                {
                    label: 'Dataset B',
                    data: dataB,
                    backgroundColor: 'rgba(16, 185, 129, 0.75)',
                    borderColor: 'rgb(16, 185, 129)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(156, 163, 175, 0.1)' }
                },
                x: { grid: { display: false } }
            },
            plugins: {
                legend: {
                    labels: { color: getComputedStyle(document.body).getPropertyValue('--text-primary') }
                }
            }
        }
    });
}

function renderCompatibilityChart(ctxId, scores, labels) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;

    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Compatibility',
                data: scores,
                fill: true,
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: 'rgb(59, 130, 246)',
                pointBackgroundColor: 'rgb(59, 130, 246)',
                pointBorderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: 'rgba(156, 163, 175, 0.1)' },
                    grid: { color: 'rgba(156, 163, 175, 0.1)' },
                    pointLabels: { color: getComputedStyle(document.body).getPropertyValue('--text-primary') },
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            }
        }
    });
}

function renderDashboardTrend(ctxId, labels, data) {
    const ctx = document.getElementById(ctxId);
    if (!ctx) return;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Dataset Quality Trend',
                data: data,
                borderColor: 'rgb(59, 130, 246)',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: 'rgba(156, 163, 175, 0.1)' }
                },
                x: { grid: { display: false } }
            }
        }
    });
}
