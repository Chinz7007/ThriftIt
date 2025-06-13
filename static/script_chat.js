// Fixed client-side JavaScript for Render deployment

// Debug logging function
function debugLog(message, data = null) {
    console.log(`[Chat Debug] ${message}`, data || '');
}

// Get current user ID from meta tag or URL
function getCurrentUserId() {
    const metaTag = document.querySelector('meta[name="current-user-id"]');
    if (metaTag) {
        return parseInt(metaTag.content);
    }
    
    // Fallback: extract from URL path /chat/1
    const pathParts = window.location.pathname.split('/');
    const otherUserId = pathParts[pathParts.length - 1];
    
    // This is a workaround - you'll need to pass current user ID properly
    debugLog('Warning: Using URL fallback for user ID detection');
    return 1; // Default fallback - replace with proper user detection
}

function getOtherUserId() {
    const pathParts = window.location.pathname.split('/');
    return parseInt(pathParts[pathParts.length - 1]);
}

// Global variables
const currentUserId = getCurrentUserId();
const otherUserId = getOtherUserId();

debugLog('User IDs detected', { currentUserId, otherUserId });

// DOM elements
const statusDisplay = document.getElementById('connectionStatus');
const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// Connection state tracking
let isConnected = false;
let conversationLoaded = false;
let socket = null;
let connectionAttempts = 0;
const maxConnectionAttempts = 5;

// Initialize Socket.IO connection with Render-specific configuration
function initializeSocket() {
    try {
        debugLog('Initializing Socket.IO connection for Render...');
        
        // IMPORTANT: Render-specific configuration
        const socketConfig = {
            // Use polling first, then upgrade to websocket
            transports: ['polling', 'websocket'],
            upgrade: true,
            rememberUpgrade: false, // Don't remember upgrades for Render
            timeout: 30000, // Longer timeout for Render
            forceNew: true,
            reconnection: true,
            reconnectionDelay: 2000, // Longer delay
            reconnectionAttempts: maxConnectionAttempts,
            maxReconnectionAttempts: maxConnectionAttempts,
            
            // Render-specific settings
            autoConnect: true,
            rejectUnauthorized: true, // Use true for production
            
            // Query parameters for debugging
            query: {
                user_id: currentUserId,
                timestamp: Date.now()
            }
        };

        debugLog('Socket configuration', socketConfig);
        
        // Create socket connection
        socket = io(socketConfig);

        // Connection event handlers
        socket.on('connect', handleConnect);
        socket.on('connect_error', handleConnectError);
        socket.on('disconnect', handleDisconnect);
        socket.on('reconnect', handleReconnect);
        socket.on('reconnect_error', handleReconnectError);
        socket.on('reconnect_failed', handleReconnectFailed);

        // Application event handlers
        socket.on('connection_confirmed', handleConnectionConfirmed);
        socket.on('joined', handleJoined);
        socket.on('error', handleSocketError);
        socket.on('new_message', handleNewMessage);
        socket.on('message_sent', handleMessageSent);

        debugLog('Socket.IO initialized successfully');
        
    } catch (error) {
        debugLog('Error initializing Socket.IO', error);
        showConnectionError();
    }
}

// Enhanced event handlers
function handleConnect() {
    debugLog('Socket connected successfully', socket.id);
    isConnected = true;
    connectionAttempts = 0;
    
    updateStatusDisplay('connected', '<i class="fas fa-check-circle"></i> Connected to chat server!');
    
    // Join personal room
    debugLog('Joining room for user', currentUserId);
    socket.emit('join', { 
        user_id: currentUserId,
        timestamp: Date.now()
    });
    
    // Load conversation history if not already loaded
    if (!conversationLoaded) {
        debugLog('Loading conversation with user', otherUserId);
        loadConversation(otherUserId);
    }
    
    // Hide status after 3 seconds
    setTimeout(() => {
        if (statusDisplay) {
            statusDisplay.classList.add('hidden');
        }
    }, 3000);
}

function handleConnectionConfirmed(data) {
    debugLog('Connection confirmed by server', data);
    showNotification('Connected to chat server', 'success');
}

function handleConnectError(error) {
    debugLog('Connection error', error);
    connectionAttempts++;
    isConnected = false;
    
    let message = `Connection failed (attempt ${connectionAttempts}/${maxConnectionAttempts})`;
    
    if (error.type === 'TransportError') {
        message += ' - Network issue detected';
    } else if (error.description) {
        message += ` - ${error.description}`;
    }
    
    updateStatusDisplay('error', `<i class="fas fa-exclamation-triangle"></i> ${message}`);
    
    if (connectionAttempts >= maxConnectionAttempts) {
        showConnectionError();
    }
}

function handleDisconnect(reason) {
    debugLog('Socket disconnected', reason);
    isConnected = false;
    
    let message = 'Connection lost';
    if (reason === 'transport close') {
        message += ' - Network interruption';
    } else if (reason === 'ping timeout') {
        message += ' - Server timeout';
    }
    
    updateStatusDisplay('error', `<i class="fas fa-exclamation-triangle"></i> ${message}. Reconnecting...`);
}

function handleReconnect(attemptNumber) {
    debugLog('Reconnected after attempts', attemptNumber);
    updateStatusDisplay('connected', '<i class="fas fa-check-circle"></i> Reconnected!');
    
    socket.emit('join', { user_id: currentUserId });
    
    if (!conversationLoaded) {
        loadConversation(otherUserId);
    }
}

function handleReconnectError(error) {
    debugLog('Reconnection error', error);
}

function handleReconnectFailed() {
    debugLog('Reconnection failed completely');
    updateStatusDisplay('error', '<i class="fas fa-times-circle"></i> Connection failed. Please refresh the page.');
    showConnectionError();
}

function handleJoined(data) {
    debugLog('Successfully joined room', data);
    if (data.message) {
        showNotification(data.message, 'success');
    }
}

function handleSocketError(data) {
    debugLog('Server error', data);
    showNotification(data.message || 'Server error occurred', 'error');
}

function handleNewMessage(msg) {
    debugLog('Received new message', msg);
    if (msg.sender_id == otherUserId) {
        appendMessage('received', msg.content, msg.sender_name || 'User', msg.timestamp);
    }
}

function handleMessageSent(msg) {
    debugLog('Message sent confirmation', msg);
    if (msg.receiver_id == otherUserId) {
        appendMessage('sent', msg.content, 'You', msg.timestamp);
    }
}

// Utility functions
function updateStatusDisplay(type, message) {
    if (!statusDisplay) return;
    
    statusDisplay.innerHTML = message;
    statusDisplay.className = `status-indicator ${type}`;
    statusDisplay.classList.remove('hidden');
}

// Load conversation history with enhanced error handling
function loadConversation(userId) {
    debugLog('Loading conversation with user', userId);
    showLoadingState();
    
    const apiUrl = `/api/conversations/${userId}`;
    debugLog('Fetching conversation from', apiUrl);
    
    fetch(apiUrl, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin' // Include cookies
    })
    .then(response => {
        debugLog('Conversation API response', { 
            status: response.status, 
            statusText: response.statusText,
            url: response.url
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(messages => {
        debugLog('Loaded messages', `${messages.length} messages`);
        conversationLoaded = true;
        chat.innerHTML = '';
        
        if (messages.length === 0) {
            showEmptyConversation();
        } else {
            let currentDate = null;
            messages.forEach(msg => {
                const msgDate = new Date(msg.timestamp).toDateString();
                
                if (msgDate !== currentDate) {
                    addDateDivider(msgDate);
                    currentDate = msgDate;
                }
                
                appendMessage(
                    msg.is_sender ? 'sent' : 'received',
                    msg.content,
                    msg.sender_name,
                    msg.timestamp
                );
            });
            
            scrollToBottom();
        }
        
        // Enable input if connected
        if (isConnected && input) {
            input.focus();
        }
    })
    .catch(error => {
        debugLog('Error loading conversation', error);
        console.error('Error loading conversation:', error);
        showErrorState(error.message);
        conversationLoaded = false;
    });
}

// Auto-resize textarea
if (input) {
    input.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        updateSendButton();
    });
}

// Send message function with enhanced validation
function sendMessage() {
    const content = input ? input.value.trim() : '';
    if (!content) {
        debugLog('Cannot send empty message');
        return;
    }

    if (!isConnected || !socket) {
        debugLog('Cannot send message - not connected');
        showNotification('Not connected to chat server. Please wait...', 'error');
        return;
    }
    
    const data = {
        sender_id: currentUserId,
        receiver_id: otherUserId,
        content: content,
        timestamp: Date.now()
    };
    
    debugLog('Sending message', data);
    
    // Disable input temporarily
    if (input) {
        input.disabled = true;
        input.value = '';
        input.style.height = 'auto';
    }
    if (sendBtn) {
        sendBtn.disabled = true;
    }
    
    // Send via socket
    socket.emit('send_message', data);
    
    // Re-enable input after a delay
    setTimeout(() => {
        if (input) {
            input.disabled = false;
            input.focus();
        }
        updateSendButton();
    }, 100);
}

// Update send button state
function updateSendButton() {
    if (!sendBtn || !input) return;
    
    const hasContent = input.value.trim().length > 0;
    const canSend = hasContent && isConnected;
    sendBtn.disabled = !canSend;
    
    if (!isConnected) {
        sendBtn.title = "Not connected to chat server";
    } else if (!hasContent) {
        sendBtn.title = "Enter a message to send";
    } else {
        sendBtn.title = "Send message";
    }
}

// Event listeners
if (sendBtn) {
    sendBtn.addEventListener('click', sendMessage);
}

if (input) {
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// Message display functions
function appendMessage(type, text, senderName, timestamp) {
    if (!chat) return;
    
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = senderName.charAt(0).toUpperCase();
    
    const content = document.createElement("div");
    content.className = "message-content";
    
    const date = new Date(timestamp);
    const formattedTime = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    content.innerHTML = `
        <div>${escapeHtml(text)}</div>
        <div class="message-time">${formattedTime}</div>
    `;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    chat.appendChild(messageDiv);
    scrollToBottom();
}

function addDateDivider(dateString) {
    if (!chat) return;
    
    const today = new Date().toDateString();
    const yesterday = new Date(Date.now() - 86400000).toDateString();
    
    let displayDate;
    if (dateString === today) {
        displayDate = 'Today';
    } else if (dateString === yesterday) {
        displayDate = 'Yesterday';
    } else {
        displayDate = new Date(dateString).toLocaleDateString('en-US', { 
            weekday: 'long', 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    }
    
    const divider = document.createElement("div");
    divider.className = "date-divider";
    divider.textContent = displayDate;
    chat.appendChild(divider);
}

// State display functions
function scrollToBottom() {
    if (!chat) return;
    setTimeout(() => {
        chat.scrollTop = chat.scrollHeight;
    }, 100);
}

function showEmptyConversation() {
    if (!chat) return;
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-comments"></i>
            <h3>Start your conversation</h3>
            <p>Send the first message to start chatting!</p>
        </div>
    `;
}

function showErrorState(errorDetails = '') {
    if (!chat) return;
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Error loading messages</h3>
            <p>There was a problem loading the conversation${errorDetails ? ': ' + errorDetails : ''}.</p>
            <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 15px;">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

function showLoadingState() {
    if (!chat) return;
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-circle-notch fa-spin"></i>
            <h3>Loading conversation...</h3>
            <p>Please wait while we fetch your messages</p>
        </div>
    `;
}

function showConnectionError() {
    if (!chat) return;
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-wifi" style="opacity: 0.3;"></i>
            <h3>Connection Problem</h3>
            <p>Unable to connect to chat server. This might be due to:</p>
            <ul style="text-align: left; margin: 10px 0;">
                <li>Network connectivity issues</li>
                <li>Server configuration problems</li>
                <li>Firewall or proxy blocking WebSocket connections</li>
            </ul>
            <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 15px;">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

// HTML escape function
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Notification function
function showNotification(message, type = 'info') {
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            color: white;
            font-weight: 600;
            z-index: 1000;
            transform: translateX(400px);
            transition: transform 0.3s ease;
        `;
        document.body.appendChild(notification);
    }
    
    notification.textContent = message;
    notification.className = `notification ${type}`;
    
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    notification.style.transform = 'translateX(0)';
    
    setTimeout(() => {
        notification.style.transform = 'translateX(400px)';
    }, 3000);
}

// Initialize connection status check
setTimeout(() => {
    if (!isConnected) {
        debugLog('Connection timeout - not connected after 15 seconds');
        showConnectionError();
    }
}, 15000);

// Update send button state periodically
setInterval(updateSendButton, 1000);

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Page loaded, initializing socket...');
    debugLog('Current URL:', window.location.href);
    debugLog('DOM elements found:', {
        chat: !!chat,
        input: !!input,
        sendBtn: !!sendBtn,
        statusDisplay: !!statusDisplay
    });
    
    initializeSocket();
});

debugLog('Chat script loaded successfully');