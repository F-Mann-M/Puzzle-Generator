
// Burger menu toggle
document.addEventListener('DOMContentLoaded', function() {
  // Scroll to bottom on initial load
  scrollChatToBottom();

  const burgerBtn = document.getElementById('burger-btn');
  const burgerDropdown = document.getElementById('burger-dropdown');
  
  if (burgerBtn && burgerDropdown) {
      burgerBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          burgerDropdown.classList.toggle('show');
      });
      
      // Close dropdown when clicking outside
      document.addEventListener('click', function(e) {
          if (!burgerBtn.contains(e.target) && !burgerDropdown.contains(e.target)) {
              burgerDropdown.classList.remove('show');
          }
      });
  }
});

// Scroll to bottom when HTMX swaps content into chat-container
document.body.addEventListener('htmx:afterSwap', function(event) {
  if (event.detail.target.id === 'chat-container') {
      scrollChatToBottom();
  }
});

// Also handle afterSettle for cases where content might render asynchronously
document.body.addEventListener('htmx:afterSettle', function(event) {
  if (event.detail.target.id === 'chat-container') {
      scrollChatToBottom();
  }
});

// Clear chat container when clearChat event is triggered
    document.body.addEventListener('clearChat', function() {
        const chatContainer = document.getElementById('chat-container');
        const sessionInput = document.getElementById('session_id_input');

        if (chatContainer) {
            chatContainer.innerHTML = '<div class="ai_response"><strong>Rudolfo:</strong> Hello! How can I help you?</div>';
        }

        if (sessionInput) {
            sessionInput.value = '';
        }
    });