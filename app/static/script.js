
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


// Handle Enter key to submit form, Shift+Enter for new line
document.addEventListener('DOMContentLoaded', function() {
    const textarea = document.getElementById('user-input');
    const chatForm = document.getElementById('chat-form');
    
    if (textarea && chatForm) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                // Trigger HTMX form submission
                htmx.trigger(chatForm, 'submit');
            }
            // Shift+Enter will create a new line (default behavior)
        });
    }
});

// Re-bind after HTMX swaps (in case the form is recreated)
document.body.addEventListener('htmx:afterSwap', function(event) {
    const textarea = document.getElementById('user-input');
    const chatForm = document.getElementById('chat-form');
    
    if (textarea && chatForm) {
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                htmx.trigger(chatForm, 'submit');
            }
        });
    }
});

// Resizable divider logic
document.addEventListener('DOMContentLoaded', function() {
    const resizer = document.getElementById('drag-resizer');
    const leftSide = document.getElementById('chat-main');
    const rightSide = document.getElementById('puzzle-visualization');

    if (!resizer || !leftSide || !rightSide) return;

    let x = 0;
    let leftWidth = 0;

    const mouseDownHandler = function(e) {
        x = e.clientX;
        leftWidth = leftSide.getBoundingClientRect().width;

        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
        
        // Add a class to body to prevent text selection during drag
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    };

    const mouseMoveHandler = function(e) {
        const dx = e.clientX - x;
        const newLeftWidth = leftWidth + dx;
        
        // Use percentage for flexibility or pixels for precision
        // Here we'll use flex-basis to control the 50/50 split
        const containerWidth = resizer.parentElement.getBoundingClientRect().width;
        const leftPercent = (newLeftWidth / containerWidth) * 100;
        const rightPercent = 100 - leftPercent;

        if (leftPercent > 10 && leftPercent < 90) {
            leftSide.style.flex = `0 0 ${leftPercent}%`;
            rightSide.style.flex = `0 0 ${rightPercent}%`;
        }
    };

    const mouseUpHandler = function() {
        document.removeEventListener('mousemove', mouseMoveHandler);
        document.removeEventListener('mouseup', mouseUpHandler);
        
        document.body.style.removeProperty('cursor');
        document.body.style.removeProperty('user-select');
    };

    resizer.addEventListener('mousedown', mouseDownHandler);
});


// handel Streaming Updates ///
async function handleChatSubmit(event) {
    event.preventDefault();
    const form = event.target;

    // 1. DYNAMIC TARGET: Read the selector from the HTML attribute
    const targetSelector = form.getAttribute("data-target");
    const chatContainer = document.querySelector(targetSelector);

    if (!chatContainer) {
        console.error(`Target element ${targetSelector} not found`);
        return;
    }

    const formData = new FormData(form);
    const input = form.querySelector("#user-input"); // Find input inside this specific form
    const jsonBody = JSON.stringify(Object.fromEntries(formData));

    // Clear input
    if (input) input.value = "";

    try {
        const response = await fetch("/puzzles/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonBody
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });

            // 2. Stream to the dynamic target
            chatContainer.insertAdjacentHTML('beforeend', chunk);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

    } catch (error) {
        console.error("Stream error:", error);
    }
}