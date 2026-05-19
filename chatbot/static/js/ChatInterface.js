// Ensure the conversationUid is available globally or passed dynamically
// const conversationUid = document.getElementById('chat-interface').dataset.conversationUid;

document.getElementById('send-button').addEventListener('click', () => sendMessage(conversationUid));

// Function to send a message
async function sendMessage() {
    const inputElement = document.getElementById('chat-input');
    const message = inputElement.value.trim();

    if (!message) return;

    const chatMessages = document.getElementById('chat-messages');

    chatMessages.innerHTML += `<div class="message human-message p-2 mb-2 bg-light rounded">${message}</div>`;
    inputElement.value = ''; // Clear input


    try {
        const response = await fetch(`/chatbot/api/conversations/${conversationUid}/messages/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({source: "human" ,content: message })
        });

        if (response.ok) {
            const data = await response.json();
            const aiMessage = data.reply;

            // Display AI response
            chatMessages.innerHTML += `<div class="message ai-message p-2 mb-2 bg-info text-white rounded">${aiMessage}</div>`;
            chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
        } else {
            chatMessages.innerHTML += `<div class="error-message">Error: Could not get AI response.</div>`;
        }
    } catch (error) {
        console.error('Error sending message:', error);
        chatMessages.innerHTML += `<div class="error-message text-danger">Error: Could not get AI response.</div>`;
    }
}

// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


// Function to fetch the latest messages (optional)
async function fetchLatestMessages(conversationUid) {
    const chatMessages = document.getElementById('chat-messages');

    try {
        const response = await fetch(`/chatbot/api/conversations/${conversationUid}/messages/`);
        if (response.ok) {
            const messages = await response.json();
            chatMessages.innerHTML = ''; // Clear existing messages

            messages.forEach(msg => {
                const messageClass = msg.source === 'human' ? 'human-message' : 'ai-message';
                chatMessages.innerHTML += `<div class="message ${messageClass}">${escapeHtml(msg.content)}</div>`;
            });
        } else {
            chatMessages.innerHTML += `<div class="error-message">Error: Could not load messages.</div>`;
        }
    } catch (error) {
        console.error('Error fetching messages:', error);
        chatMessages.innerHTML += `<div class="error-message">Error: Network issue while fetching messages.</div>`;
    }
}

// Function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


document.getElementById('complete-collection-button').addEventListener('click', completeClinicalDataCollection);

async function completeClinicalDataCollection() {
    const responseElement = document.getElementById('completion-response');
    responseElement.innerHTML = 'Processing...';

    try {
        const response = await fetch(`/chatbot/api/conversations/${conversationUid}/complete-collection/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.ok) {
            const data = await response.json();
            responseElement.innerHTML = `<div class="message ai-message">${data.message}</div>`;
        } else {
            responseElement.innerHTML = `<div class="error-message">Error: Could not complete the clinical data collection.</div>`;
        }
    } catch (error) {
        console.error('Error completing clinical data collection:', error);
        responseElement.innerHTML = `<div class="error-message">Error: Network issue.</div>`;
    }
}
