
    // Initialize socket connection
    const socket = io();
    const statusDisplay = document.getElementById('connectionStatus');
    const currentUserId = {{ current_user.id }};
    let selectedRecipient = null;
    
    // DOM elements
    const chat = document.getElementById("chat");
    const input = document.getElementById("messageInput");
    const recipient = document.getElementById("recipient");
    const sendBtn = document.getElementById("sendBtn");
    
    // Auto-resize textarea
    input.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
    
    // Connection handling
    socket.on('connect', () => {
      statusDisplay.innerHTML = '<i class="fas fa-check-circle"></i> Connected and ready!';
      statusDisplay.className = 'status-indicator connected';
      
      // Join personal room
      socket.emit('join', { user_id: currentUserId });
      
      setTimeout(() => {
        statusDisplay.style.display = 'none';
      }, 2000);
    });
    
    socket.on('disconnect', () => {
      statusDisplay.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Disconnected. Trying to reconnect...';
      statusDisplay.className = 'status-indicator error';
      statusDisplay.style.display = 'block';
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
      if (!content || !selectedRecipient) return;
      
      const data = {
        sender_id: currentUserId,
        receiver_id: parseInt(selectedRecipient),
        content: content
      };
      
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
      sendBtn.disabled = !(hasContent && hasRecipient);
    }
    
    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    
    input.addEventListener('input', updateSendButton);
    
    // Load conversation history
    function loadConversation(userId) {
      showLoadingState();
      
      fetch(`/api/conversations/${userId}`)
        .then(response => response.json())
        .then(messages => {
          chat.innerHTML = '';
          
          if (messages.length === 0) {
            showEmptyConversation();
          } else {
            messages.forEach(msg => {
              appendMessage(
                msg.is_sender ? 'sent' : 'received',
                msg.content,
                msg.sender_name,
                msg.timestamp
              );
            });
            scrollToBottom();
          }
        })
        .catch(error => {
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
        <div>${text}</div>
        <div class="message-time">${formattedTime}</div>
      `;
      
      messageDiv.appendChild(avatar);
      messageDiv.appendChild(content);
      
      chat.appendChild(messageDiv);
      scrollToBottom();
    }
    
    // Handle incoming messages
    socket.on('new_message', msg => {
      if (msg.sender_id == selectedRecipient) {
        appendMessage('received', msg.content, 'They', msg.timestamp);
      }
    });
    
    // Handle sent message confirmation
    socket.on('message_sent', msg => {
      if (msg.receiver_id == selectedRecipient) {
        appendMessage('sent', msg.content, 'You', msg.timestamp);
      }
    });
    
    // Utility functions
    function scrollToBottom() {
      chat.scrollTop = chat.scrollHeight;
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
        </div>
      `;
    }
    
    function showErrorState() {
      chat.innerHTML = `
        <div class="empty-state">
          <i class="fas fa-exclamation-triangle"></i>
          <h3>Error loading messages</h3>
          <p>Please refresh the page and try again</p>
        </div>
      `;
    }
