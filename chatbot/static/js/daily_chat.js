let threadId = null;

// DOM elements
const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

function parseDeepSeekResponse(text) {
    const tags = ["THINK", "EXPLAIN", "ACT", "OBSERVE", "RESPOND"];
    const result = {};
    tags.forEach(tag => {
        const regex = new RegExp(`\\*\\*${tag}:\\*\\*\\s*([\\s\\S]*?)(?=\\s*\\*\\*|$)`, 'i');
        const match = text.match(regex);
        result[tag.toLowerCase()] = match ? match[1].trim() : null;
    });
    return result;
}

async function sendMessage(message) {
    console.log(`[DAILY] Sending message: "${message}"  threadId=${threadId}`);

    // Display user message
    const userDiv = document.createElement('div');
    userDiv.textContent = `You: ${message}`;
    userDiv.classList.add('fade-in');
    chatLog.appendChild(userDiv);
    chatLog.scrollTop = chatLog.scrollHeight;

    messageInput.value = '';

    try {
        const response = await fetch('/chatbot/api/agent/daily/', {
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
        console.log('[DAILY] Response:', JSON.stringify(data));
        threadId = data.thread_id;

        const parsed = parseDeepSeekResponse(data.response);
        const mainContent = parsed.respond || data.response;

        const agentDiv = document.createElement('div');
        agentDiv.classList.add('chat-bubble', 'fade-in');

        const textSpan = document.createElement('p');
        textSpan.className = 'main-text';
        textSpan.textContent = mainContent;
        agentDiv.appendChild(textSpan);

        if (parsed.explain) {
            const infoSpan = document.createElement('span');
            infoSpan.className = 'status-hint';
            infoSpan.textContent = `ℹ️ ${parsed.explain}`;
            agentDiv.appendChild(infoSpan);
        }

        chatLog.appendChild(agentDiv);
        chatLog.scrollTop = chatLog.scrollHeight;

        // Handle swap signal from daily agent -> HVR
        if (data.swap === 'hvr') {
            console.log('[DAILY] Swap to HVR agent requested');
            setTimeout(() => {
                window.location.href = '/chatbot/HVRChat/';
            }, 2000);
        }

    } catch (error) {
        console.error('[DAILY] Error:', error);
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

// Send initial greeting to start the conversation
window.addEventListener('DOMContentLoaded', async () => {
    console.log('[DAILY] DOM ready — sending initial greeting');
    const data = await fetch('/chatbot/api/agent/daily/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ message: 'Hello', thread_id: null }),
    }).then(r => r.json());
    console.log('[DAILY] Initial response:', JSON.stringify(data));
    threadId = data.thread_id;

    const parsed = parseDeepSeekResponse(data.response);
    const mainContent = parsed.respond || data.response;

    const agentDiv = document.createElement('div');
    agentDiv.classList.add('chat-bubble', 'fade-in');
    const textSpan = document.createElement('p');
    textSpan.className = 'main-text';
    textSpan.textContent = mainContent;
    agentDiv.appendChild(textSpan);
    chatLog.appendChild(agentDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
});
