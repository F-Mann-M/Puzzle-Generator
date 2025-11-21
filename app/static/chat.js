const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatContainer = document.getElementById('chat-container');

// Function to display a message in the chat window
function displayMessage(sender, text) {
    const msgDiv = document.createElement('div');
    msgDiv.className = sender === 'user' ? 'user-msg' : 'ai-msg';
    msgDiv.textContent = `${sender === 'user' ? 'You' : 'AI'}: ${text}`;
    chatContainer.appendChild(msgDiv);
    // Scroll to the latest message
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault(); // Prevent the default form submission (page reload)
    const message = userInput.value.trim();
    if (!message) return;

    displayMessage('user', message);
    userInput.value = ''; // Clear input

    // --- 1. Send the message to the FastAPI endpoint ---
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({message: message})
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // --- 2. Display the AI response ---
        displayMessage('ai', data.response);

    } catch (error) {
        console.error('Error sending message:', error);
        displayMessage('ai', 'Error: Could not connect to the AI service.');
    }
});