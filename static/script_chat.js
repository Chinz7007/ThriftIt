
// Initialize socket connection
const socket = io();
const statusDisplay = document.getElementById('connectionStatus');
const currentUserId = {{ current_user.id }};
const otherUserId = {{ other_user.id }};

// DOM elements
const chat = document.getElementById("chat");
const input = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");

// Auto-resize textarea
input.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    updateSendButton();
});

// Connection handling
socket.on('connect', () => {
    statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Connected and secure!';
    statusDisplay.className = 'status-indicator connected';
    
    // Join personal room
    socket.emit('join', { user_id: currentUserId });
    
    // Load conversation history
    loadConversation(otherUserId);
    
    // Hide status after 2 seconds
    setTimeout(() => {
    statusDisplay.classList.add('hidden');
    }, 2000);
});

socket.on('disconnect', () => {
    statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Connection lost. Reconnecting...';
    statusDisplay.className = 'status-indicator error';
    statusDisplay.classList.remove('hidden');
});

// Send message function
function sendMessage() {
    const content = input.value.trim();
    if (!content) return;
    
    const data = {
    sender_id: currentUserId,
    receiver_id: otherUserId,
    content: content
    };
    
    // Disable input temporarily to prevent double-sending
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
    sendBtn.disabled = !hasContent;
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);

input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
    }
});

// Load conversation history from API
function loadConversation(userId) {
    fetch(`/api/conversations/${userId}`)
    .then(response => response.json())
    .then(messages => {
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
        
        // Focus input
        input.focus();
    })
    .catch(error => {
        console.error('Error loading conversation:', error);
        showErrorState();
    });
}

// Handle incoming messages
socket.on('new_message', msg => {
    console.log('Received message:', msg);
    
    // If the message is from the other user in this chat
    if (msg.sender_id == otherUserId) {
    appendMessage('received', msg.content, '{{ other_user.student_id }}', msg.timestamp);
    }
});

// Handle sent message confirmation
socket.on('message_sent', msg => {
    console.log('Message sent confirmation:', msg);
    
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
    <div>${text}</div>
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
    </div>
    `;
}
