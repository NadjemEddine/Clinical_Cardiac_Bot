let threadId = null;

// DOM elements
const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

async function sendMessage(message) {
    messageInput.value = '';

    // Display user message
    const userDiv = document.createElement('div');
    userDiv.id = 'user-message';
    userDiv.classList.add('chat-user', 'fade-in');
    userDiv.innerHTML = '<i class="fa-solid fa-user"></i> : ' + message;
    chatLog.appendChild(userDiv);
    chatLog.scrollTop = chatLog.scrollHeight;

    try {
        const response = await fetch('/chatbot/api/agent/welcome/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                message: message,
                thread_id: threadId,
            }),
        });

        const data = await response.json();
        threadId = data.thread_id;
        const response_text = data.response;

        // Determine display message based on tool context
        let displayMessage = response_text;

        // Display agent response
        if (response_text) {
            const agentDiv = document.createElement('div');
            agentDiv.id = 'agent-message';
            agentDiv.classList.add('chat-agent', 'fade-in');
            agentDiv.innerHTML = '<i class="fas fa-robot"></i> : ' + displayMessage;
            chatLog.appendChild(agentDiv);
        }

        chatLog.scrollTop = chatLog.scrollHeight;

        // Check if all data is collected
        if (response_text === "All your clinical data are updated.") {
            messageInput.disabled = true;
            sendButton.disabled = true;

            const alertDiv = document.createElement('div');
            alertDiv.classList.add('alert', 'alert-success', 'text-center', 'mt-4');
            alertDiv.style.position = 'fixed';
            alertDiv.style.top = '50%';
            alertDiv.style.left = '50%';
            alertDiv.style.transform = 'translate(-50%, -50%)';
            alertDiv.style.zIndex = '1000';
            alertDiv.style.width = '80%';
            alertDiv.style.maxWidth = '500px';
            alertDiv.innerHTML = `
                <h4 class="alert-heading">Congratulations!</h4>
                <p>We got the historical data which helps us to serve you better and give us a good understanding of your health status.</p>
                <hr>
                <a href="/chatbot/Dashboard/" class="btn btn-primary">Go to Dashboard</a>
            `;
            document.body.appendChild(alertDiv);
        }

    } catch (error) {
        console.error('Error sending message:', error);
    }
}

// Send button
sendButton.onclick = () => {
    const message = messageInput.value.trim();
    if (message) {
        sendMessage(message);
    }
};

// Enter key
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendButton.click();
    }
});

function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}
