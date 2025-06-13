// Enhanced Socket.IO Configuration for chat.html
// Replace the existing socket initialization in your chat.html

// Debug logging function
function debugLog(message, data = null) {
    console.log(`[Socket.IO Debug] ${message}`, data || '');
}

// Enhanced Socket.IO initialization with debugging
const socket = io({
    // Explicit configuration for better compatibility
    transports: ['websocket', 'polling'], // Try websocket first, fallback to polling
    upgrade: true,
    rememberUpgrade: true,
    timeout: 20000, // 20 second timeout
    forceNew: true, // Force new connection
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 5,
    maxReconnectionAttempts: 5
});

const statusDisplay = document.getElementById('connectionStatus');
const currentUserId = {{ current_user.id }};
const otherUserId = {{ other_user.id }};

// DOM elements
const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// Connection state tracking
let isConnected = false;
let conversationLoaded = false;

// Auto-resize textarea
input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    updateSendButton();
});

// Enhanced connection handling with detailed logging
socket.on('connect', () => {
    debugLog('Socket connected successfully', socket.id);
    isConnected = true;
    
    statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Connected and secure!';
    statusDisplay.className = 'status-indicator connected';
    
    // Join personal room
    debugLog('Joining room for user', currentUserId);
    socket.emit('join', { user_id: currentUserId });
    
    // Load conversation history
    debugLog('Loading conversation with user', otherUserId);
    loadConversation(otherUserId);
    
    // Hide status after 2 seconds
    setTimeout(() => {
        statusDisplay.classList.add('hidden');
    }, 2000);
});

socket.on('connect_error', (error) => {
    debugLog('Connection error', error);
    isConnected = false;
    statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Connection failed. Retrying...';
    statusDisplay.className = 'status-indicator error';
    statusDisplay.classList.remove('hidden');
    
    // Show fallback message in chat
    showConnectionError();
});

socket.on('disconnect', (reason) => {
    debugLog('Socket disconnected', reason);
    isConnected = false;
    statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Connection lost. Reconnecting...';
    statusDisplay.className = 'status-indicator error';
    statusDisplay.classList.remove('hidden');
});

socket.on('reconnect', (attemptNumber) => {
    debugLog('Reconnected after attempts', attemptNumber);
    statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Reconnected!';
    statusDisplay.className = 'status-indicator connected';
    
    // Rejoin room and reload conversation
    socket.emit('join', { user_id: currentUserId });
    if (!conversationLoaded) {
        loadConversation(otherUserId);
    }
});

socket.on('reconnect_error', (error) => {
    debugLog('Reconnection error', error);
});

socket.on('reconnect_failed', () => {
    debugLog('Reconnection failed completely');
    statusDisplay.innerHTML = '<i class="fas fa-times-circle"></i> Connection failed. Please refresh the page.';
    statusDisplay.className = 'status-indicator error';
    showConnectionError();
});

// Handle join confirmation
socket.on('joined', (data) => {
    debugLog('Successfully joined room', data.room);
});

// Handle errors from server
socket.on('error', (data) => {
    debugLog('Server error', data);
    showNotification(data.message || 'An error occurred', 'error');
});

// Send message function with enhanced error handling
function sendMessage() {
    const content = input.value.trim();
    if (!content) {
        debugLog('Cannot send empty message');
        return;
    }

    if (!isConnected) {
        debugLog('Cannot send message - not connected');
        showNotification('Not connected to chat server. Please wait...', 'error');
        return;
    }
    
    const data = {
        sender_id: currentUserId,
        receiver_id: otherUserId,
        content: content
    };
    
    debugLog('Sending message', data);
    
    // Disable input temporarily to prevent double-sending
    input.disabled = true;
    sendBtn.disabled = true;
    
    // Send via socket
    socket.emit('send_message', data);
    
    // Clear input field
    input.value = '';
    input.style.height = 'auto';
    
    // Re-enable input after a short delay
    setTimeout(() => {
        input.disabled = false;
        updateSendButton();
        input.focus();
    }, 100);
}

// Update send button state
function updateSendButton() {
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
sendBtn.addEventListener('click', sendMessage);

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Enhanced conversation loading with better error handling
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
            conversationLoaded = true;
            chat.innerHTML = ''; // Clear existing messages
            
            if (messages.length === 0) {
                showEmptyConversation();
            } else {
                // Group messages by date and display
                let currentDate = null;
                messages.forEach(msg => {
                    const msgDate = new Date(msg.timestamp).toDateString();
                    
                    // Add date divider if this is a new date
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
                
                // Scroll to bottom
                scrollToBottom();
            }
            
            // Focus input if connected
            if (isConnected) {
                input.focus();
            }
        })
        .catch(error => {
            debugLog('Error loading conversation', error);
            console.error('Error loading conversation:', error);
            showErrorState();
            conversationLoaded = false;
        });
}

// Handle incoming messages
socket.on('new_message', msg => {
    debugLog('Received new message', msg);
    
    // If the message is from the other user in this chat
    if (msg.sender_id == otherUserId) {
        appendMessage('received', msg.content, '{{ other_user.student_id }}', msg.timestamp);
    }
});

// Handle sent message confirmation
socket.on('message_sent', msg => {
    debugLog('Message sent confirmation', msg);
    
    // If this is for the current conversation
    if (msg.receiver_id == otherUserId) {
        appendMessage('sent', msg.content, 'You', msg.timestamp);
    }
});

function appendMessage(type, text, senderName, timestamp) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = senderName.charAt(0).toUpperCase();
    
    const content = document.createElement("div");
    content.className = "message-content";
    
    // Format timestamp
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

function showEmptyConversation() {
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-comments"></i>
            <h3>Start your conversation</h3>
            <p>Send the first message to {{ other_user.student_id }}!</p>
        </div>
    `;
}

function showErrorState() {
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>Error loading messages</h3>
            <p>Please refresh the page and try again</p>
            <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 15px;">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

function showLoadingState() {
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-circle-notch fa-spin"></i>
            <h3>Loading conversation...</h3>
            <p>Please wait while we fetch your messages</p>
        </div>
    `;
}

function showConnectionError() {
    chat.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-wifi" style="opacity: 0.3;"></i>
            <h3>Connection Problem</h3>
            <p>Unable to connect to chat server. Please check your internet connection and refresh the page.</p>
            <button onclick="location.reload()" class="btn btn-primary" style="margin-top: 15px;">
                <i class="fas fa-refresh"></i> Refresh Page
            </button>
        </div>
    `;
}

// HTML escape function for security
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Notification function
function showNotification(message, type = 'info') {
    // Create notification element if it doesn't exist
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
    
    // Set message and style
    notification.textContent = message;
    notification.className = `notification ${type}`;
    
    // Style based on type
    const colors = {
        success: '#28a745',
        error: '#dc3545',
        info: '#17a2b8',
        warning: '#ffc107'
    };
    notification.style.backgroundColor = colors[type] || colors.info;
    
    // Show notification
    notification.style.transform = 'translateX(0)';
    
    // Hide after 3 seconds
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
}, 10000); // 10 second timeout

// Update send button state periodically
setInterval(updateSendButton, 1000);

debugLog('Chat initialization complete');
