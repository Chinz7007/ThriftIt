// Fixed script_send_message.js

// Debug logging function
function debugLog(message, data = null) {
    console.log(`[Send Message Debug] ${message}`, data || '');
}

// Global variables - FIXED: Remove template literals since this is a static file
const currentUserId = parseInt(document.querySelector('meta[name="current-user-id"]').content);
let selectedRecipient = null;
let socket = null;
let isConnected = false;

// DOM elements
const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const recipient = document.getElementById("recipient");
const sendBtn = document.getElementById("sendBtn");
const statusDisplay = document.getElementById('connectionStatus');

// Initialize Socket.IO connection
function initializeSocket() {
    try {
        debugLog('Initializing Socket.IO connection...');
        
        // Create socket connection with enhanced configuration
        socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true,
            timeout: 20000,
            forceNew: true,
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionAttempts: 5,
            maxReconnectionAttempts: 5
        });

        // Connection event handlers
        socket.on('connect', handleConnect);
        socket.on('connect_error', handleConnectError);
        socket.on('disconnect', handleDisconnect);
        socket.on('reconnect', handleReconnect);
        socket.on('reconnect_error', handleReconnectError);
        socket.on('reconnect_failed', handleReconnectFailed);

        // Chat event handlers
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

// Event handlers
function handleConnect() {
    debugLog('Socket connected successfully', socket.id);
    isConnected = true;
    
    statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Connected and ready!';
    statusDisplay.className = 'status-indicator connected';
    
    // Join personal room
    debugLog('Joining room for user', currentUserId);
    socket.emit('join', { user_id: currentUserId });
    
    // Hide status after 2 seconds
    setTimeout(() => {
        statusDisplay.style.display = 'none';
    }, 2000);
}

function handleConnectError(error) {
    debugLog('Connection error', error);
    isConnected = false;
    statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Connection failed. Retrying...';
    statusDisplay.className = 'status-indicator error';
    statusDisplay.style.display = 'block';
    showConnectionError();
}

function handleDisconnect(reason) {
    debugLog('Socket disconnected', reason);
    isConnected = false;
    statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Connection lost. Reconnecting...';
    statusDisplay.className = 'status-indicator error';
    statusDisplay.style.display = 'block';
}

function handleReconnect(attemptNumber) {
    debugLog('Reconnected after attempts', attemptNumber);
    statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Reconnected!';
    statusDisplay.className = 'status-indicator connected';
    
    socket.emit('join', { user_id: currentUserId });
}

function handleReconnectError(error) {
    debugLog('Reconnection error', error);
}

function handleReconnectFailed() {
    debugLog('Reconnection failed completely');
    statusDisplay.innerHTML = '<i class="fas fa-times-circle"></i> Connection failed. Please refresh the page.';
    statusDisplay.className = 'status-indicator error';
    showConnectionError();
}

function handleJoined(data) {
    debugLog('Successfully joined room', data.room);
}

function handleSocketError(data) {
    debugLog('Server error', data);
    showNotification(data.message || 'An error occurred', 'error');
}

function handleNewMessage(msg) {
    debugLog('Received new message', msg);
    if (selectedRecipient && msg.sender_id == selectedRecipient) {
        const senderName = recipient.options[recipient.selectedIndex]?.text || 'User';
        appendMessage('received', msg.content, senderName, msg.timestamp);
    }
}

function handleMessageSent(msg) {
    debugLog('Message sent confirmation', msg);
    if (selectedRecipient && msg.receiver_id == selectedRecipient) {
        appendMessage('sent', msg.content, 'You', msg.timestamp);
    }
}

// Auto-resize textarea
input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    updateSendButton();
});

// Update selected recipient when dropdown changes
recipient.addEventListener('change', () => {
    selectedRecipient = recipient.value;
    
    if (selectedRecipient) {
        // Enable input and send button
        input.disabled = false;
        input.placeholder = `Message ${recipient.options[recipient.selectedIndex].text}...`;
        updateSendButton();
        
        // Clear chat and load conversation
        loadConversation(selectedRecipient);
        input.focus();
    } else {
        // Disable input and send button
        input.disabled = true;
        input.placeholder = "Select a contact first...";
        sendBtn.disabled = true;
        showEmptyState();
    }
});

// Send message function
function sendMessage() {
    const content = input.value.trim();
    if (!content || !selectedRecipient) {
        debugLog('Cannot send message - missing content or recipient');
        return;
    }

    if (!isConnected || !socket) {
        debugLog('Cannot send message - not connected');
        showNotification('Not connected to chat server. Please wait...', 'error');
        return;
    }
    
    const data = {
        sender_id: currentUserId,
        receiver_id: parseInt(selectedRecipient),
        content: content
    };
    
    debugLog('Sending message', data);
    
    // Disable input temporarily
    input.disabled = true;
    sendBtn.disabled = true;
    
    // Send via socket
    socket.emit('send_message', data);
    
    // Clear input field
    input.value = '';
    input.style.height = 'auto';
    
    // Re-enable input
    setTimeout(() => {
        input.disabled = false;
        updateSendButton();
        input.focus();
    }, 100);
}

// Update send button state
function updateSendButton() {
    const hasContent = input.value.trim().length > 0;
    const hasRecipient = selectedRecipient !== null && selectedRecipient !== '';
    const canSend = hasContent && hasRecipient && isConnected;
    sendBtn.disabled = !canSend;
    
    if (!isConnected) {
        sendBtn.title = "Not connected to chat server";
    } else if (!hasRecipient) {
        sendBtn.title = "Select a contact first";
    } else if (!hasContent) {
        sendBtn.title = "Enter a message to send";
    } else {
        sendBtn.title = "Send message";
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Load conversation history
function loadConversation(userId) {
    debugLog('Loading conversation with user', userId);
    showLoadingState();
    
    fetch(`/api/conversations/${userId}`)
        .then(response => {
            debugLog('Conversation API response status', response.status);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(messages => {
            debugLog('Loaded messages', `${messages.length} messages`);
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
            
            if (isConnected) {
                input.focus();
            }
        })
        .catch(error => {
            debugLog('Error loading conversation', error);
            console.error('Error loading conversation:', error);
            showErrorState();
        });
}

// Message display functions
function appendMessage(type, text, senderName, timestamp) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = senderName.charAt(0).toUpperCase();
    
    const content = document.createElement("div");
    content.className = "message-content";
    
    const formattedTime = new Date(timestamp).toLocaleTimeString([], {
        hour: '2-digit', 
        minute: '2-digit'
    });
    
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

// Utility functions
function scrollToBottom() {
    setTimeout(() => {
        chat.scrollTop = chat.scrollHeight;
    }, 100);
}

function showEmptyState() {
    chat.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-comments"></i>
            <h3>Start a Conversation</h3>
            <p>Select a contact above to begin chatting</p>
        </div>
    `;
}

function showEmptyConversation() {
    chat.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-paper-plane"></i>
            <h3>No messages yet</h3>
            <p>Send the first message to start this conversation!</p>
        </div>
    `;
}

function showLoadingState() {
    chat.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-circle-notch fa-spin"></i>
            <h3>Loading conversation...</h3>
            <p>Please wait while we fetch your messages</p>
        </div>
    `;
}

function showErrorState() {
    chat.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Error loading messages</h3>
            <p>Please refresh the page and try again</p>
            <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 15px;">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

function showConnectionError() {
    chat.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-wifi" style="opacity: 0.3;"></i>
            <h3>Connection Problem</h3>
            <p>Unable to connect to chat server. Please check your internet connection and refresh the page.</p>
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
        debugLog('Connection timeout - not connected after 10 seconds');
        showConnectionError();
    }
}, 10000);

// Update send button state periodically
setInterval(updateSendButton, 1000);

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Page loaded, initializing socket...');
    initializeSocket();
});

debugLog('Send message script loaded');