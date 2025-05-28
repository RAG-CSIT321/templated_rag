// Global flag to prevent multiple redirections
let authCheckInProgress = false;

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    // Only run auth check if not already in progress
    if (!authCheckInProgress) {
        authCheckInProgress = true;
        
        // Check for both token formats for compatibility
        const token = localStorage.getItem('accessToken') || localStorage.getItem('auth_token');
        console.log("Found token:", token ? "Yes" : "No");
        
        if (!token) {
            console.log("No token found, redirecting to login");
            // No token, redirect to login
            window.location.replace('/');
            return;
        }
        
        // Verify token and role
        fetch('/api/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })
        .then(response => {
            console.log("Auth check response status:", response.status);
            if (!response.ok) {
                throw new Error('Invalid token');
            }
            return response.json();
        })
        .then(data => {
            console.log("Auth check response data:", data);
            // Auth check complete
            authCheckInProgress = false;
            
            if (data && data.role === 'client') {
                // Valid client, update username
                document.getElementById('username').textContent = data.username || 'Client';
            } else {
                // Not a client, redirect to main page
                console.log('User is not a client, redirecting to main page');
                window.location.replace('/');
            }
        })
        .catch(error => {
            // Auth check failed
            authCheckInProgress = false;
            console.error('Auth error:', error);
            
            // Clear token and redirect
            localStorage.removeItem('accessToken');
            localStorage.removeItem('auth_token');
            localStorage.removeItem('userRole');
            localStorage.removeItem('userId');
            window.location.replace('/');
        });
    }
});

function showTab(tabName) {
    // Hide all tab content
    document.querySelectorAll('.upload-section, .database-section, .status-section').forEach(section => {
        section.style.display = 'none';
    });

    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });

    // Show the selected tab content and set the tab as active
    if (tabName === 'files') {
        document.getElementById('files-tab').style.display = 'block';
    } else if (tabName === 'database') {
        document.getElementById('database-tab').style.display = 'block';
    } else if (tabName === 'status') {
        document.getElementById('status-tab').style.display = 'block';
    }
    document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
}

// File upload handling
const dropArea = document.getElementById('drop-area');
const fileInput = document.getElementById('fileInput');

// Add event listeners for drag and drop
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, unhighlight, false);
});

function highlight() {
    dropArea.style.borderColor = '#1A3C34';
    dropArea.style.backgroundColor = 'rgba(26, 60, 52, 0.1)';
}

function unhighlight() {
    dropArea.style.borderColor = '#CCCCCC';
    dropArea.style.backgroundColor = 'transparent';
}

dropArea.addEventListener('drop', handleDrop, false);
fileInput.addEventListener('change', handleFiles, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles({ target: { files } });
}

function handleFiles(e) {
    const files = e.target.files;
    for (const file of files) {
        uploadFile(file);
    }
}

function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('accessToken');
    
    // Show processing status
    document.getElementById('processing-status').textContent = `Processing file ${file.name}...`;
    
    fetch('/api/upload_file', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            loadFiles();
            document.getElementById('processing-status').textContent = `File ${file.name} uploaded and processed successfully.`;
            // Clear the status message after 5 seconds
            setTimeout(() => {
                document.getElementById('processing-status').textContent = 'No data is currently being processed.';
            }, 5000);
        } else {
            document.getElementById('processing-status').textContent = `Upload failed: ${data.detail}`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('processing-status').textContent = `Upload failed: ${error}`;
    });
}

// Add these variables at the top of your script
let selectedFiles = new Set();
let fileToDelete = null;

// Add these functions to your existing JavaScript
function updateDeleteButton() {
    const deleteButton = document.getElementById('delete-selected');
    deleteButton.disabled = selectedFiles.size === 0;
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.file-checkbox');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        const filename = checkbox.getAttribute('data-filename');
        if (selectAllCheckbox.checked) {
            selectedFiles.add(filename);
        } else {
            selectedFiles.delete(filename);
        }
    });
    
    updateDeleteButton();
}

function toggleFileSelection(checkbox) {
    const filename = checkbox.getAttribute('data-filename');
    if (checkbox.checked) {
        selectedFiles.add(filename);
    } else {
        selectedFiles.delete(filename);
    }
    
    // Update select all checkbox
    const selectAllCheckbox = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('.file-checkbox');
    selectAllCheckbox.checked = Array.from(checkboxes).every(cb => cb.checked);
    
    updateDeleteButton();
}

function showDeleteConfirmation(filename = null) {
    if (filename) {
        fileToDelete = filename;
        document.getElementById('delete-confirm-message').textContent = 
            'Are you sure you want to delete this file? This action cannot be undone.';
    } else {
        fileToDelete = Array.from(selectedFiles);
        document.getElementById('delete-confirm-message').textContent = 
            `Are you sure you want to delete ${selectedFiles.size} selected file(s)? This action cannot be undone.`;
    }
    document.getElementById('delete-confirm-dialog').style.display = 'block';
}

function deleteSelectedFiles() {
    if (!fileToDelete) return;
    
    const token = localStorage.getItem('accessToken');
    const filesToDelete = Array.isArray(fileToDelete) ? fileToDelete : [fileToDelete];
    
    // Show processing status
    document.getElementById('processing-status').textContent = 'Deleting files...';
    
    // Create an array of promises for all delete operations
    const deletePromises = filesToDelete.map(filename => 
        fetch(`/api/delete_file/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        }).then(response => response.json())
    );
    
    // Execute all delete operations
    Promise.all(deletePromises)
        .then(results => {
            const allSuccessful = results.every(result => result.status === 'success');
            if (allSuccessful) {
                // Show embedding update status
                document.getElementById('processing-status').textContent = 'Clearing embeddings and updating with remaining files...';
                
                // Wait a moment to show the status message
                setTimeout(() => {
                    loadFiles(); // Refresh the file list
                    hideDeleteConfirmation();
                    selectedFiles.clear();
                    updateDeleteButton();
                    document.getElementById('processing-status').textContent = 'Files deleted and embeddings updated successfully.';
                    // Clear the status message after 5 seconds
                    setTimeout(() => {
                        document.getElementById('processing-status').textContent = 'No data is currently being processed.';
                    }, 5000);
                }, 1000);
            } else {
                document.getElementById('processing-status').textContent = 'Error: Some files could not be deleted. Please try again.';
            }
        })
        .catch(error => {
            console.error('Error deleting files:', error);
            document.getElementById('processing-status').textContent = 'Error deleting files. Please try again.';
        });
}

// Update your loadFiles function
function loadFiles() {
    const token = localStorage.getItem('accessToken');
    fetch('/api/list_files', {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => response.json())
    .then(data => {
        const fileList = document.getElementById('file-list');
        fileList.innerHTML = '';
        
        data.files.forEach(file => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <input type="checkbox" class="file-checkbox" data-filename="${file.filename}" 
                        onchange="toggleFileSelection(this)">
                </td>
                <td>${file.filename}</td>
                <td>${formatFileSize(file.size)}</td>
                <td>${formatDate(file.uploaded_at)}</td>
                <td>
                    <button class="delete-btn" onclick="showDeleteConfirmation('${file.filename}')">Delete</button>
                </td>
            `;
            fileList.appendChild(row);
        });
        
        // Reset select all checkbox
        document.getElementById('select-all').checked = false;
    })
    .catch(error => {
        console.error('Error loading files:', error);
    });
}

// Add event listeners
document.addEventListener('DOMContentLoaded', function() {
    loadFiles();
    
    // Add event listener for select all checkbox
    document.getElementById('select-all').addEventListener('change', toggleSelectAll);
    
    // Add event listener for delete selected button
    document.getElementById('delete-selected').addEventListener('click', () => showDeleteConfirmation());
    
    // Update existing event listeners
    document.getElementById('confirm-delete').addEventListener('click', deleteSelectedFiles);
    document.getElementById('cancel-delete').addEventListener('click', hideDeleteConfirmation);
});

function hideDeleteConfirmation() {
    document.getElementById('delete-confirm-dialog').style.display = 'none';
    fileToDelete = null;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Database connection handling
function connectToDatabase() {
    const host = document.getElementById('db-host').value;
    const dbName = document.getElementById('db-name').value;
    const username = document.getElementById('db-username').value;
    const password = document.getElementById('db-password').value;
    const port = document.getElementById('db-port').value;

    if (!host || !dbName || !username || !password || !port) {
        showConnectionStatus('error', 'All fields are required');
        return;
    }

    const connectBtn = document.getElementById('connect-btn');
    connectBtn.disabled = true;
    connectBtn.textContent = 'Connecting...';
    showConnectionStatus('pending', 'Attempting to connect to database...');

    const token = localStorage.getItem('accessToken');
    
    fetch('/api/connect_database', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            host,
            database: dbName,
            username,
            password,
            port
        })
    })
    .then(response => response.json())
    .then(data => {
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect Database';
        
        if (data.status === 'success') {
            document.getElementById('db-status').textContent = 'Connected';
            document.getElementById('db-status').className = 'status-connected';
            document.getElementById('db-details').textContent = `Connected to ${dbName} on ${host}`;
            document.getElementById('processing-status').textContent = 'Database data is being processed and indexed. This may take a few minutes depending on the size of your database.';
            showConnectionStatus('success', data.message || 'Database connected successfully.');
        } else {
            document.getElementById('db-status').textContent = 'Error';
            document.getElementById('db-status').className = 'status-error';
            showConnectionStatus('error', data.detail || 'Connection failed');
        }
    })
    .catch(error => {
        connectBtn.disabled = false;
        connectBtn.textContent = 'Connect Database';
        document.getElementById('db-status').textContent = 'Error';
        document.getElementById('db-status').className = 'status-error';
        showConnectionStatus('error', error.toString());
        console.error('Error:', error);
    });
}

function showConnectionStatus(type, message) {
    const statusElement = document.getElementById('connection-status');
    statusElement.textContent = message;
    
    // Clear all classes
    statusElement.className = 'connection-status';
    
    // Add appropriate class
    if (type === 'error') {
        statusElement.classList.add('status-error');
    } else if (type === 'success') {
        statusElement.classList.add('status-success');
    } else if (type === 'pending') {
        statusElement.classList.add('status-pending');
    }
    
    // Display the status
    statusElement.style.display = 'block';
}

function logout() {
    // Clear tokens in both formats
    localStorage.removeItem('accessToken');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('userRole');
    localStorage.removeItem('userId');
    // Use replace to avoid history issues
    window.location.replace('/');
}

// Initialize with files tab active
showTab('files');