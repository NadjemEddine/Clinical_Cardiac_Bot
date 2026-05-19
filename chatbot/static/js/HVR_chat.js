function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

import { executeTool } from './executor.js';

const roomName = "456789"; // Replace with the actual room name

function parseAgentReasoning(text) {
    if (!text || typeof text !== 'string') return text;
    
    // We prioritize the RESPOND tag as the main UI message
    const respondMatch = text.match(/\*\*RESPOND:\*\*\s*([\s\S]*?)(?=\s*\*\*|$)/i);
    const explainMatch = text.match(/\*\*EXPLAIN:\*\*\s*([\s\S]*?)(?=\s*\*\*|$)/i);

    return {
        main: respondMatch ? respondMatch[1].trim() : text,
        hint: explainMatch ? explainMatch[1].trim() : null
    };
}

let activeSocket; // Declare outside to ensure global scope

if (record && NullFields === 'True') {
    activeSocket = new WebSocket(
        `ws://${window.location.host}/ws/EHR/${roomName}/` // Start with chat WebSocket
    );
} else {
    activeSocket = new WebSocket(
        `ws://${window.location.host}/ws/chat/${roomName}/` // Start with EHR WebSocket
    );
}


// DOM elements
const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

// Function to initialize WebSocket event handlers
function setupWebSocket(socket) {
    socket.onopen = (e) => {
        console.log(`${socket.url.includes('/ws/EHR/') ? 'EHR' : 'chat'} WebSocket connection established`);
        socket.send(JSON.stringify({
            response: "",
            patient_id: patient_id,
            sender: "patient",
        }));
    };

    socket.onmessage = async (e) => {
        const data = JSON.parse(e.data);
        const response = data.response;
        const tool = data.tool;
        const type = data.type;
        let displayMessage = response;

        if (type === 'call_js_function') {
            await executeTool(activeSocket, data, record);
            console.log(`record is:`, record);
        } else if (type === "swap_webSocket") {
            swapWebSocket();
        } else if (type === "swap_webSocket2") {
            swapWebSocket2();
        } else {
            // Display the agent's response
            if (response && (data.sender === "agent" || data.sender === "patient")) {

                if (data.sender === "agent") {
                    // --- START PARSING LOGIC ---
                    const parsed = parseAgentReasoning(response);

                    const messageDiv = document.createElement('div');
                    messageDiv.id = 'agent-message';
                    messageDiv.classList.add('chat-agent', 'fade-in');

                    // Main Message (from RESPOND)
                    let htmlContent = `<i class="fas fa-robot"></i> : ${parsed.main}`;

                    // Optional Sub-text (from EXPLAIN)
                    if (parsed.hint) {
                        htmlContent += `<div class="agent-explain-subtext">${parsed.hint}</div>`;
                    }

                    messageDiv.innerHTML = htmlContent;
                    chatLog.appendChild(messageDiv);
                    // --- END PARSING LOGIC ---
                } else {
                    const messageDiv = document.createElement('div');
                    messageDiv.id = 'user-message'; // Add ID as requested
                    messageDiv.classList.add('chat-user');
                    messageDiv.innerHTML = '<i class="fa-solid fa-user"></i> ' + " : " + displayMessage; // Use Font Awesome 5 icon
                    messageDiv.classList.add('fade-in');
                    chatLog.appendChild(messageDiv);

                }
            }
            chatLog.scrollTop = chatLog.scrollHeight;
        }
    };

    socket.onclose = (e) => {
        console.error("WebSocket connection closed unexpectedly");
    };
}

// Function to swap WebSocket to EHR
function swapWebSocket() {
    // Close the current WebSocket (chatSocket)
    activeSocket.close();
    console.log("Chat WebSocket closed, switching to EHR WebSocket...");

    // Open the new WebSocket (ehrSocket)

    activeSocket = new WebSocket(
        `ws://${window.location.host}/ws/EHR/${roomName}/`
    );

    // Reassign event handlers to the new WebSocket

    setupWebSocket(activeSocket);


}

// Function to swap WebSocket to EHR
function swapWebSocket2() {
    // Close the current WebSocket (chatSocket)
    activeSocket.close();
    console.log("Chat WebSocket closed, switching to Imaging WebSocket...");

    // Open the new WebSocket (ehrSocket)

    activeSocket = new WebSocket(
        `ws://${window.location.host}/ws/imaging/${roomName}/`
    );

    // Reassign event handlers to the new WebSocket

    setupWebSocket(activeSocket);


}

// Initialize the first WebSocket (chatSocket)
setupWebSocket(activeSocket);

// Send button: Send user's message to the active WebSocket
sendButton.onclick = (e) => {
    const message = messageInput.value.trim();
    if (message) {
        activeSocket.send(JSON.stringify({
            message: message,
            patient_id: patient_id,
            sender: "patient",
        }));

        messageInput.value = '';
        chatLog.scrollTop = chatLog.scrollHeight;
    }
};

// Allow pressing Enter to send the message
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendButton.click();
    }
});