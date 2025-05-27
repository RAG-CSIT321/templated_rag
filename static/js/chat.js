// Authentication state
let currentToken = null;
let currentUserId = null;
let currentUsername = null;
let currentSessionId = null;
let isSidebarVisible = true;
let pendingDeleteSessionId = null;
let authCheckInProgress = false;

// DOM elements
const chatbox = document.getElementById('chatbox');
const promptInput = document.getElementById('prompt');
const statusText = document.getElementById('status');
const historyList = document.getElementById('history-list');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const chatTitle = document.getElementById('chat-title');
const sendButton = document.getElementById('send-button');
const welcomeScreen = document.getElementById('welcome-screen');

// Auth DOM Elements
const authModal = document.getElementById('auth-modal');
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const loginError = document.getElementById('login-error');
const signupError = document.getElementById('signup-error');
const authTitle = document.getElementById('auth-title');

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Always show auth modal first, hide rest of UI
    showAuthModal();
    
    // Hide main content until authenticated
    document.querySelector('.main-content').style.visibility = 'hidden';
    document.querySelector('.sidebar').style.visibility = 'hidden';
    
    // Set up enter key for prompt (shift+enter for new line)
    promptInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    promptInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Initialize the welcome screen content if needed
    if (!welcomeScreen || welcomeScreen.children.length === 0) {
        // Create welcome screen content
        chatbox.innerHTML = `
            <div id="welcome-screen">
                <h1 class="welcome-title">Hello!</h1>
                <h2 class="welcome-subtitle">How can I help you today?</h2>
                <div class="welcome-prompts">
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Which gaming laptop should I buy?')">Which gaming laptop should I buy?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('What is the latest Iphone right now?')">What is the latest Iphone right now?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Compare between Dell and Macbook? Which one is better?')">Compare between Dell and Macbook? Which one is better?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Which laptop is the most suitable for Computer Science?')">Which laptop is the most suitable for Computer Science?</div>
                </div>
            </div>
        `;
    }
    
    // Check screen size for sidebar
    checkScreenSize();
    window.addEventListener('resize', checkScreenSize);
    
    // Check for stored auth token and try to authenticate automatically
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
        checkAuthStatus();
    }
    
    // Restore sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed) {
        document.getElementById('sidebar').classList.add('collapsed');
    }

    // Load saved settings
    loadSavedSettings();
});

function checkScreenSize() {
    if (window.innerWidth <= 768) {
        isSidebarVisible = false;
        sidebar.classList.remove('visible');
    } else {
        isSidebarVisible = true;
        sidebar.classList.add('visible');
    }
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    
    // Save the state to localStorage
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}

// Auth Functions
function showAuthModal() {
    authModal.style.display = 'flex';
    showLogin();
}

function hideAuthModal() {
    authModal.style.display = 'none';
}

function showLogin() {
    loginForm.style.display = 'block';
    signupForm.style.display = 'none';
    authTitle.textContent = 'Login';
    loginError.textContent = '';
    if (document.getElementById('signup-username')) document.getElementById('login-username').value = document.getElementById('signup-username').value;
}

function showSignup() {
    loginForm.style.display = 'none';
    signupForm.style.display = 'block';
    authTitle.textContent = 'Sign up';
    signupError.textContent = '';
    if (document.getElementById('login-username')) document.getElementById('signup-username').value = document.getElementById('login-username').value;
}

function showUserInfo() {
    hideAuthModal();
    
    if (currentUsername) {
        document.getElementById('user-initial').textContent = currentUsername.charAt(0).toUpperCase();
    }
    
    document.querySelector('.main-content').style.visibility = 'visible';
    document.querySelector('.sidebar').style.visibility = 'visible';
    
    showWelcomeScreen();
}

async function checkAuthStatus() {
    if (authCheckInProgress) return;
    
    authCheckInProgress = true;
    
    const token = localStorage.getItem('auth_token');
    if (token) {
        try {
            let response = await fetch('http://localhost:5000/api/me', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.status === 401) {
                const refreshSuccess = await attemptTokenRefresh();
                if (refreshSuccess) {
                    response = await fetch('http://localhost:5000/api/me', {
                        headers: {
                            'Authorization': `Bearer ${currentToken}`
                        }
                    });
                }
            }
            
            if (response.ok) {
                const user = await response.json();
                currentToken = token;
                currentUserId = user.user_id;
                currentUsername = user.username;
                
                if (user.role === 'client') {
                    console.log("User is a client, redirecting to client dashboard");
                    localStorage.setItem('userRole', user.role);
                    localStorage.setItem('accessToken', token);
                    window.location.replace('/client');
                    return;
                }
                
                showUserInfo();
                listChatHistory();
                authCheckInProgress = false;
                return;
            }
        } catch (error) {
            console.error("Auth check failed:", error);
        }
    }
    authCheckInProgress = false;
    showAuthModal();
}

function sendWelcomePrompt(promptText) {
    if (!currentToken) {
        showAuthModal();
        return;
    }
    promptInput.value = promptText;
    sendMessage();
}

async function login() {
    if (authCheckInProgress) return;
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    if (!username || !password) {
        loginError.textContent = 'Please enter both username and password';
        return;
    }
    
    try {
        authCheckInProgress = true;
        
        const requestBody = {
            username: username,
            password: password
        };
        
        const response = await fetch('http://localhost:5000/api/token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }));
            const errorMessage = errorData.detail || 'Login failed';
            if (response.status === 401) {
                loginError.textContent = 'Incorrect username or password';
            } else {
                loginError.textContent = errorMessage;
            }
            authCheckInProgress = false;
            return;
        }
        
        const data = await response.json();
        console.log("Login response data:", data);
        currentToken = data.access_token;
        currentUserId = data.user_id;
        currentUsername = username;
        
        localStorage.setItem('auth_token', currentToken);
        localStorage.setItem('accessToken', currentToken);
        
        if (data.role === 'client') {
            console.log("User is a client, redirecting to client dashboard after login");
            localStorage.setItem('userRole', data.role);
            window.location.replace('/client');
            return;
        }
        
        showUserInfo();
        chatbox.innerHTML = '';
        historyList.innerHTML = '';
        listChatHistory();
        showWelcomeScreen();
        await createNewSession();
        
        authCheckInProgress = false;
    } catch (error) {
        console.error('Login error:', error);
        loginError.textContent = error.message;
        authCheckInProgress = false;
    }
}

async function signup() {
    const username = document.getElementById('signup-username').value;
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const keycode = document.getElementById('signup-keycode').value;
    
    if (!username || !password) {
        signupError.textContent = 'Username and password are required';
        return;
    }

    // Validate keycode if provided
    if (keycode && keycode !== 'CLOCK') {
        signupError.textContent = 'Invalid client access key';
        return;
    }
    
    try {
        const response = await fetch('http://localhost:5000/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                email: email || null,
                password: password,
                role: keycode === 'CLOCK' ? 'client' : 'user'
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Signup failed');
        }
        
        showLogin();
        document.getElementById('login-username').value = username;
        signupError.textContent = '';
        loginError.textContent = 'Account created! Please login.';
    } catch (error) {
        signupError.textContent = error.message;
        console.error("Signup error:", error);
    }
}

function logout() {
    currentToken = null;
    currentUserId = null;
    currentUsername = null;
    currentSessionId = null;
    localStorage.removeItem('auth_token');
    
    const welcomeScreen = document.getElementById('welcome-screen');
    const messages = Array.from(chatbox.children).filter(child => child.id !== 'welcome-screen');
    messages.forEach(msg => msg.remove());
    if (welcomeScreen) {
        welcomeScreen.style.display = 'flex';
    }
    chatTitle.textContent = "ChatWithMe";

    historyList.innerHTML = '';
    
    document.querySelector('.main-content').style.visibility = 'hidden';
    document.querySelector('.sidebar').style.visibility = 'hidden';
    showAuthModal();
}

function toggleUserDropdown() {
    const dropdown = document.getElementById('user-dropdown');
    dropdown.classList.toggle('visible');
    
    document.addEventListener('click', function closeDropdown(e) {
        const isClickInside = document.getElementById('user-profile-icon').contains(e.target) || 
                             document.getElementById('user-dropdown').contains(e.target);
        if (!isClickInside) {
            dropdown.classList.remove('visible');
            document.removeEventListener('click', closeDropdown);
        }
    });
}

// Chat Functions
function appendMessage(role, content) {
    hideWelcomeScreen();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role === 'user' ? 'user-message' : 'assistant-message'}`;
    
    const displayName = role === 'user' ? (currentUsername || 'User') : 'Assistant';
        
    messageDiv.innerHTML = `
        <div class="message-content">
            ${formatMessageContent(content)}
        </div>
    `;
    
    chatbox.appendChild(messageDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
}

function formatMessageContent(content) {
    let formatted = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>');
    
    formatted = formatted.split('\n\n').map(para => {
        if (para.trim() === '') return '';
        return `<p>${para.replace(/\n/g, '<br>')}</p>`;
    }).join('');
    
    return formatted;
}

function showLoadingIndicator() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message assistant-message loading-message';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="loading-dots"></div>
        </div>
    `;
    chatbox.appendChild(loadingDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
    return loadingDiv;
}

async function createNewSession() {
    if (!currentUserId) return;
    
    currentSessionId = null;
    chatbox.innerHTML = '';
    showWelcomeScreen();
    await listChatHistory();
}

async function sendMessage() {
    if (!currentToken) {
        showAuthModal();
        return;
    }
    
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    hideWelcomeScreen();

    appendMessage('user', prompt);
    promptInput.value = '';
    promptInput.style.height = 'auto';
    
    sendButton.disabled = true;
    
    const loadingDiv = showLoadingIndicator();
    
    try {
        const requestBody = {
            user_id: currentUserId,
            session_id: currentSessionId || null,
            role: 'user',
            content: prompt
        };

        let saveResponse = await fetch('http://localhost:5000/api/save_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentToken}`
            },
            body: JSON.stringify(requestBody)
        });
        
        if (saveResponse.status === 401) {
            await attemptTokenRefresh();
            saveResponse = await fetch('http://localhost:5000/api/save_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${currentToken}`
                },
                body: JSON.stringify(requestBody)
            });
        }

        if (!saveResponse.ok) {
            throw new Error(`Failed to save message: ${saveResponse.status}`);
        }

        const saveData = await saveResponse.json();
        currentSessionId = saveData.session_id;
        
        if (saveData.session_id && !currentSessionId) {
            currentSessionId = saveData.session_id;
            await listChatHistory();
        } else if (saveData.session_id && saveData.session_id !== currentSessionId) {
            currentSessionId = saveData.session_id;
            await listChatHistory();
        }
        
        let response = await fetch('http://localhost:5000/api/interact_with_agent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${currentToken}`
            },
            body: JSON.stringify({
                prompt, 
                session_id: currentSessionId,
                user_id: currentUserId  
            })
        });

        if (response.status === 401) {
            await attemptTokenRefresh();
            response = await fetch('http://localhost:5000/api/interact_with_agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${currentToken}`
                },
                body: JSON.stringify({
                    prompt, 
                    session_id: currentSessionId,
                    user_id: currentUserId  
                })
            });
        }

        loadingDiv.remove();

        const data = await response.json();
        if (data.messages && data.messages.length > 0) {
            const assistantMessage = data.messages[0].content;
            appendMessage('assistant', assistantMessage);
            
            await fetch('http://localhost:5000/api/save_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${currentToken}`
                },
                body: JSON.stringify({
                    user_id: currentUserId,
                    session_id: currentSessionId,
                    role: 'assistant',
                    content: assistantMessage
                })
            });
        } else {
            throw new Error('Invalid response format');
        }
        
        await listChatHistory();
    } catch (error) {
        console.error('Error:', error);
        
        if (loadingDiv && loadingDiv.parentNode) {
            loadingDiv.remove();
        }
        
        appendMessage('system', `Error: ${error.message}`);
        if (error.message.includes('401')) {
            alert("Session expired. Please login again.");
            logout();
        }
    } finally {
        sendButton.disabled = false;
    }
}

async function attemptTokenRefresh() {
    try {
        const refreshResponse = await fetch('http://localhost:5000/api/refresh_token', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });

        if (refreshResponse.ok) {
            const refreshData = await refreshResponse.json();
            currentToken = refreshData.access_token;
            localStorage.setItem('auth_token', currentToken);
            return true;
        } else {
            throw new Error('Token refresh failed');
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        throw error;
    }
}

async function listChatHistory() {
    if (!currentUserId || !currentToken) return;
    
    try {
        const response = await fetch(`http://localhost:5000/api/list_chat_sessions/${currentUserId}`, {
            headers: {
                'Authorization': `Bearer ${currentToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const result = await response.json();
        const sessions = result.data || [];
        historyList.innerHTML = '';

        if (sessions.length === 0) {
            historyList.innerHTML = '<div class="history-item" style="color: var(--text-color-sidebar); font-style: italic;">No chat history</div>';
            if (!currentSessionId) {
                showWelcomeScreen();
            }
            return;
        }

        sessions.forEach(session => {
            const sessionDiv = document.createElement('div');
            sessionDiv.className = `history-item ${session.session_id === currentSessionId ? 'active' : ''}`;
            
            const sessionName = session.session_name || (session.first_message_summary ? (session.first_message_summary.length > 25 ? session.first_message_summary.substring(0,22) + "..." : session.first_message_summary) : 'New Chat');

            sessionDiv.innerHTML = `
                <div class="history-item-content" onclick="loadChatHistory('${session.session_id}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#AAAAAA" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                        <path d="M22 4L12 14.01l-3-3"/>
                    </svg>
                    <span>${sessionName}</span>
                </div>
                <button class="delete-chat-btn" onclick="showDeleteModal('${session.session_id}', event)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="#ff4d4d">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                    </svg>
                </button>
            `;
            
            historyList.appendChild(sessionDiv);
        });
        
    } catch (error) {
        console.error("Error loading sessions:", error);
        historyList.innerHTML = `
            <div class="history-item" style="color: var(--error-color);">
                Failed to load chat history
            </div>
        `;
        
        if (!currentSessionId) {
            showWelcomeScreen();
        }
    }
}

function showDeleteModal(sessionId, event) {
    if (event) {
        event.stopPropagation();
    }
    pendingDeleteSessionId = sessionId;
    document.getElementById('delete-modal').style.display = 'flex';
}

function hideDeleteModal() {
    document.getElementById('delete-modal').style.display = 'none';
    pendingDeleteSessionId = null;
}

async function confirmDelete() {
    if (pendingDeleteSessionId) {
        try {
            const response = await fetch(
                `http://localhost:5000/api/delete_session/${currentUserId}/${pendingDeleteSessionId}`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${currentToken}`
                    }
                });
            
            if (!response.ok) {
                throw new Error(`Delete failed: ${response.status}`);
            }
            
            if (currentSessionId === pendingDeleteSessionId) {
                chatbox.innerHTML = '';
                currentSessionId = null;
                chatTitle.textContent = 'ChatWithMe';
                showWelcomeScreen();
            }
            
            await listChatHistory();
            
        } catch (error) {
            console.error("Delete error:", error);
            appendMessage('system', `Failed to delete session: ${error.message}`);
        }
        hideDeleteModal();
    }
}

async function loadChatHistory(sessionId) {
    if (!currentUserId || !currentToken) return;
    
    try {
        hideWelcomeScreen();
        
        currentSessionId = sessionId;
        const response = await fetch(
            `http://localhost:5000/api/load_chat_history/${currentUserId}/${sessionId}`, {
                headers: {
                    'Authorization': `Bearer ${currentToken}`
                }
            });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log("Chat history loaded:", result);
        
        chatbox.innerHTML = '';
        
        if (result.messages && result.messages.length > 0) {
            result.messages.forEach(msg => {
                if (msg.content && msg.content.trim() !== '') {
                    appendMessage(msg.role, msg.content);
                }
            });
            
            if (result.session_name) {
                chatTitle.textContent = result.session_name;
            } else {
                const firstUserMessage = result.messages.find(m => m.role === 'user' && m.content);
                if (firstUserMessage) {
                    chatTitle.textContent = firstUserMessage.content.length > 30 ? 
                        firstUserMessage.content.substring(0, 30) + '...' : 
                        firstUserMessage.content;
                } else {
                    chatTitle.textContent = "Chat";
                }
            }
        } else {
            showWelcomeScreen();
            chatTitle.textContent = "New Chat";
        }
        
        await listChatHistory();
        chatbox.scrollTop = chatbox.scrollHeight;
    } catch (error) {
        console.error("Load error:", error);
        appendMessage('system', `Failed to load chat: ${error.message}`);
    }
}

// Modal Functions
function showHelp() {
    document.getElementById('help-modal').style.display = 'flex';
}

function hideHelp() {
    document.getElementById('help-modal').style.display = 'none';
}

function showActivity() {
    alert('Activity tracking will be implemented in future versions');
}

function showSettings() {
    document.getElementById('settings-modal').style.display = 'flex';
}

function hideSettings() {
    document.getElementById('settings-modal').style.display = 'none';
}

function updateSettings(setting, value) {
    localStorage.setItem(setting, value);
    applySettings(setting, value);
}

function applySettings(setting, value) {
    switch(setting) {
        case 'messageDisplay':
            document.body.setAttribute('data-message-display', value);
            break;
        case 'fontSize':
            document.body.setAttribute('data-font-size', value);
            break;
        case 'sendBehavior':
            break;
        case 'autoScroll':
            break;
        case 'soundEnabled':
            break;
        case 'desktopNotifications':
            if (value) {
                Notification.requestPermission();
            }
            break;
        case 'saveHistory':
            break;
    }
}

function loadSavedSettings() {
    const settings = [
        'messageDisplay',
        'fontSize',
        'sendBehavior',
        'autoScroll',
        'soundEnabled',
        'desktopNotifications',
        'saveHistory'
    ];

    settings.forEach(setting => {
        const value = localStorage.getItem(setting);
        if (value !== null) {
            const element = document.getElementById(setting.replace(/([A-Z])/g, '-$1').toLowerCase());
            if (element) {
                if (element.type === 'checkbox') {
                    element.checked = value === 'true';
                } else {
                    element.value = value;
                }
                applySettings(setting, value);
            }
        }
    });
}

function showWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    const messagesContainer = document.getElementById('chatbox');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'flex';
        if (!chatbox.contains(welcomeScreen)) {
            chatbox.innerHTML = '';
            chatbox.appendChild(welcomeScreen);
        }
    } else {
        chatbox.innerHTML = `
            <div id="welcome-screen">
                <h1 class="welcome-title">Hello!</h1>
                <h2 class="welcome-subtitle">How can I help you today?</h2>
                <div class="welcome-prompts">
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Which gaming laptop should I buy?')">Which gaming laptop should I buy?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('What is the latest Iphone right now?')">What is the latest Iphone right now?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Compare between Dell and Macbook? Which one is better?')">Compare between Dell and Macbook? Which one is better?</div>
                    <div class="welcome-prompt-box" onclick="sendWelcomePrompt('Which laptop is the most suitable for Computer Science?')">Which laptop is the most suitable for Computer Science?</div>
                </div>
            </div>
        `;
    }
    const messages = Array.from(messagesContainer.children).filter(child => child.id !== 'welcome-screen');
    messages.forEach(msg => {
        msg.style.display = 'none';
    });
    chatTitle.textContent = 'ChatWithMe';
}

function hideWelcomeScreen() {
    const welcomeScreen = document.getElementById('welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'none';
    }
    const messages = Array.from(chatbox.children).filter(child => child.id !== 'welcome-screen');
    messages.forEach(msg => {
        msg.style.display = '';
    });
} 