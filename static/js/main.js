// Global variables
let extractedData = [];
let currentFiles = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeDragAndDrop();
    initializeButtons();
});

function initializeButtons() {
    document.getElementById('extractButton').addEventListener('click', processFiles);
    document.getElementById('downloadCSV').addEventListener('click', downloadCSV);
    document.getElementById('clearButton').addEventListener('click', clearAll);
}

function initializeDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

function handleFiles(files) {
    currentFiles = Array.from(files);
    updateFileList();
    previewFile(currentFiles[0]);
    document.getElementById('extractButton').disabled = false;
}

function updateFileList() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';

    currentFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>${file.name}</span>
            <span class="status">Pending</span>
        `;
        fileItem.addEventListener('click', () => previewFile(file));
        fileList.appendChild(fileItem);
    });
}

function previewFile(file) {
    const previewContainer = document.getElementById('previewContainer');
    previewContainer.innerHTML = '';

    if (!file) {
        previewContainer.innerHTML = '<p class="no-preview">No document selected</p>';
        return;
    }

    if (file.type.startsWith('image/')) {
        const img = document.createElement('img');
        img.className = 'preview-image';
        img.src = URL.createObjectURL(file);
        previewContainer.appendChild(img);
    } else if (file.type === 'application/pdf') {
        const embed = document.createElement('embed');
        embed.className = 'preview-pdf';
        embed.src = URL.createObjectURL(file);
        embed.type = 'application/pdf';
        previewContainer.appendChild(embed);
    } else {
        previewContainer.innerHTML = '<p class="no-preview">Preview not available for this file type</p>';
    }
}

async function processFiles() {
    const extractButton = document.getElementById('extractButton');
    const downloadButton = document.getElementById('downloadCSV');

    extractButton.disabled = true;
    showLoading();

    try {
        for (const file of currentFiles) {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                extractedData.push(result);
                updateFileStatus(file.name, 'Processed');
            } else {
                updateFileStatus(file.name, `Error: ${result.error}`);
            }
        }

        updateResultsTable();
        downloadButton.disabled = false;
    } catch (error) {
        console.error('Error:', error);
        alert('Error processing files. Please try again.');
    } finally {
        hideLoading();
        extractButton.disabled = false;
    }
}

function updateFileStatus(fileName, status) {
    const fileItems = document.querySelectorAll('.file-item');
    for (const item of fileItems) {
        if (item.querySelector('span').textContent === fileName) {
            item.querySelector('.status').textContent = status;
            break;
        }
    }
}

function updateResultsTable() {
    const tableContainer = document.getElementById('tableContainer');
    if (extractedData.length === 0) {
        tableContainer.innerHTML = '<p>No data available</p>';
        return;
    }

    // Create table headers
    const headers = new Set();
    extractedData.forEach(data => {
        Object.keys(data).forEach(key => headers.add(key));
    });

    let html = '<table class="results-table">';
    html += '<tr>' + Array.from(headers).map(h => `<th>${h}</th>`).join('') + '</tr>';

    // Add data rows
    extractedData.forEach(data => {
        html += '<tr>';
        Array.from(headers).forEach(header => {
            const value = data[header] || '';
            html += `<td>${Array.isArray(value) ? JSON.stringify(value) : value}</td>`;
        });
        html += '</tr>';
    });

    html += '</table>';
    tableContainer.innerHTML = html;
}

function downloadCSV() {
    if (extractedData.length === 0) {
        alert('No data available to download');
        return;
    }

    // Convert data to CSV
    const headers = Object.keys(extractedData[0]);
    let csv = headers.join(',') + '\n';

    extractedData.forEach(row => {
        const values = headers.map(header => {
            const value = row[header] || '';
            const stringValue = Array.isArray(value) ? JSON.stringify(value) : value;
            return `"${stringValue.toString().replace(/"/g, '""')}"`;
        });
        csv += values.join(',') + '\n';
    });

    // Create and trigger download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', 'invoice_data.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function clearAll() {
    extractedData = [];
    currentFiles = [];
    document.getElementById('fileList').innerHTML = '';
    document.getElementById('tableContainer').innerHTML = '<p>No data available</p>';
    document.getElementById('previewContainer').innerHTML = '<p class="no-preview">No document selected</p>';
    document.getElementById('extractButton').disabled = true;
    document.getElementById('downloadCSV').disabled = true;
    document.getElementById('fileInput').value = '';
}

function showLoading() {
    document.getElementById('loadingSpinner').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loadingSpinner').style.display = 'none';
}
