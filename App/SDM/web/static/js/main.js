// Global state
let currentSettings = null;
let currentStudy = null;

// View switching
document.querySelectorAll('[data-view]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const view = e.target.dataset.view;
        switchView(view);
    });
});

function switchView(view) {
    // Update navigation
    document.querySelectorAll('[data-view]').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.view === view) {
            link.classList.add('active');
        }
    });

    // Update content
    document.querySelectorAll('.view').forEach(v => {
        v.style.display = 'none';
    });
    document.getElementById(`${view}-view`).style.display = 'block';

    // Load data for the view
    if (view === 'results') {
        loadStudies();
    }
}

// Batch mode toggle
document.getElementById('batchMode').addEventListener('change', (e) => {
    const isBatch = e.target.checked;
    document.getElementById('singleFileSelection').style.display = isBatch ? 'none' : 'block';
    document.getElementById('batchFileSelection').style.display = isBatch ? 'block' : 'none';
});

// Load default settings
document.getElementById('loadDefaults').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/settings/default');
        const settings = await response.json();
        currentSettings = settings;
        populateSettings(settings);
    } catch (error) {
        showError('Failed to load default settings');
    }
});

// Start processing
document.getElementById('startProcessing').addEventListener('click', async () => {
    const isBatch = document.getElementById('batchMode').checked;
    const settings = collectSettings();

    try {
        if (isBatch) {
            await processBatch(settings);
        } else {
            await processSingle(settings);
        }
    } catch (error) {
        showError('Processing failed: ' + error.message);
    }
});

// Helper functions
function populateSettings(settings) {
    // Smooth & Impute
    document.getElementById('resetTac').checked = settings.smooth_and_impute.reset_tac;
    document.getElementById('medianSmooth').checked = settings.smooth_and_impute.median_smooth;
    document.getElementById('imputeGaps').checked = settings.smooth_and_impute.impute_gaps;

    // Curve Analysis
    document.getElementById('curveThreshold').value = settings.curve.curve_threshold;
    document.getElementById('peripheryBufferBefore').value = settings.curve.periphery_buffer_before;

    // Day Analysis
    document.getElementById('dayStartHour').value = settings.day.day_start_hour;
    document.getElementById('makeGraphs').checked = settings.day.make_graphs;

    // Gaps & Non-wear
    document.getElementById('exportExcel').checked = settings.gaps_and_non_wear.export_excel;
}

function collectSettings() {
    return {
        smooth_and_impute: {
            reset_tac: document.getElementById('resetTac').checked,
            median_smooth: document.getElementById('medianSmooth').checked,
            impute_gaps: document.getElementById('imputeGaps').checked
        },
        curve: {
            curve_threshold: document.getElementById('curveThreshold').value,
            periphery_buffer_before: parseInt(document.getElementById('peripheryBufferBefore').value)
        },
        day: {
            day_start_hour: parseInt(document.getElementById('dayStartHour').value),
            make_graphs: document.getElementById('makeGraphs').checked
        },
        gaps_and_non_wear: {
            export_excel: document.getElementById('exportExcel').checked
        }
    };
}

async function processSingle(settings) {
    const subid = document.getElementById('subid').value;
    const datasetId = document.getElementById('datasetId').value;

    if (!subid || !datasetId) {
        throw new Error('Subject ID and Dataset ID are required');
    }

    // Create study
    const studyResponse = await fetch('/api/studies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: `Study ${subid}_${datasetId}`,
            description: 'Single file processing',
            subid,
            dataset_identifier: datasetId
        })
    });

    const study = await studyResponse.json();
    if (study.error) {
        throw new Error(study.error);
    }

    // Process study
    const processResponse = await fetch(`/api/studies/${study.study_id}/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            options: {
                use_prior_save: false,
                smooth_and_impute: true,
                adjust_for_gaps_and_non_wear: true,
                analyze_days: true,
                identify_curves: true
            },
            settings
        })
    });

    const result = await processResponse.json();
    if (result.error) {
        throw new Error(result.error);
    }

    showSuccess('Processing started successfully');
    switchView('results');
}

async function processBatch(settings) {
    const inputFolder = document.getElementById('inputFolder').value;
    if (!inputFolder) {
        throw new Error('Input folder is required');
    }

    // TODO: Implement batch processing
    showError('Batch processing not implemented yet');
}

// Results view functions
async function loadStudies() {
    try {
        const response = await fetch('/api/studies');
        const studies = await response.json();
        
        const studyList = document.getElementById('studyList');
        studyList.innerHTML = studies.map(study => `
            <a href="#" class="list-group-item list-group-item-action" data-study-id="${study.id}">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${study.name}</h6>
                    <small>${study.processing_status}</small>
                </div>
                <p class="mb-1">${study.description}</p>
                <small>Subject: ${study.subid}, Dataset: ${study.dataset_identifier}</small>
            </a>
        `).join('');

        // Add click handlers
        studyList.querySelectorAll('[data-study-id]').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const studyId = e.currentTarget.dataset.studyId;
                loadStudyDetails(studyId);
            });
        });
    } catch (error) {
        showError('Failed to load studies');
    }
}

async function loadStudyDetails(studyId) {
    try {
        const response = await fetch(`/api/studies/${studyId}`);
        const study = await response.json();
        
        if (study.error) {
            throw new Error(study.error);
        }

        currentStudy = study;
        displayStudyDetails(study);
    } catch (error) {
        showError('Failed to load study details');
    }
}

function displayStudyDetails(study) {
    const details = document.getElementById('studyDetails');
    details.innerHTML = `
        <h4>${study.study_info.name}</h4>
        <p>${study.study_info.description}</p>
        <div class="row">
            <div class="col-md-6">
                <p><strong>Subject ID:</strong> ${study.study_info.subid}</p>
                <p><strong>Dataset ID:</strong> ${study.study_info.dataset_identifier}</p>
            </div>
            <div class="col-md-6">
                <p><strong>Status:</strong> ${study.study_info.processing_status}</p>
                <p><strong>Last Updated:</strong> ${new Date(study.study_info.last_updated).toLocaleString()}</p>
            </div>
        </div>
    `;

    // Load results based on study status
    if (study.study_info.processing_status === 'completed') {
        loadStudyResults(study.study_info.id);
    }
}

async function loadStudyResults(studyId) {
    try {
        // Load day results
        const dayResponse = await fetch(`/api/studies/${studyId}/days`);
        const dayData = await dayResponse.json();
        document.getElementById('dayResults').innerHTML = formatResults(dayData);

        // Load curve results
        const curveResponse = await fetch(`/api/studies/${studyId}/curves`);
        const curveData = await curveResponse.json();
        document.getElementById('curveResults').innerHTML = formatResults(curveData);

        // Load event results
        const eventResponse = await fetch(`/api/studies/${studyId}/events`);
        const eventData = await eventResponse.json();
        document.getElementById('eventResults').innerHTML = formatResults(eventData);
    } catch (error) {
        showError('Failed to load study results');
    }
}

function formatResults(data) {
    if (!data || !data.features) {
        return '<p>No results available</p>';
    }

    // Create a table for the results
    const table = document.createElement('table');
    table.className = 'table table-striped';
    
    // Add headers
    const thead = document.createElement('thead');
    thead.innerHTML = `
        <tr>
            ${Object.keys(data.features[0]).map(key => `<th>${key}</th>`).join('')}
        </tr>
    `;
    table.appendChild(thead);

    // Add rows
    const tbody = document.createElement('tbody');
    tbody.innerHTML = data.features.map(row => `
        <tr>
            ${Object.values(row).map(value => `<td>${value}</td>`).join('')}
        </tr>
    `).join('');
    table.appendChild(tbody);

    return table.outerHTML;
}

// Utility functions
function showError(message) {
    // TODO: Implement error notification
    console.error(message);
}

function showSuccess(message) {
    // TODO: Implement success notification
    console.log(message);
} 