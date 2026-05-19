// Get the patient ID from the template
const roomName = "room_id"; // Replace with the actual room name
const chatSocket = new WebSocket(
    `ws://${window.location.host}/ws/chat/${roomName}/`
);

// DOM elements
const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

function parseDeepSeekResponse(text) {
    const tags = ["THINK", "EXPLAIN", "ACT", "OBSERVE", "RESPOND"];
    const result = {};

    tags.forEach(tag => {
        // Regex finds the tag and captures everything until the next tag or end of string
        const regex = new RegExp(`\\*\\*${tag}:\\*\\*\\s*([\\s\\S]*?)(?=\\s*\\*\\*|$)`, 'i');
        const match = text.match(regex);
        result[tag.toLowerCase()] = match ? match[1].trim() : null;
    });

    return result;
}

// WebSocket event: Connection opened
chatSocket.onopen = (e) => {
    console.log("WebSocket connection established");
    // Optionally, send an initial message to start the conversation
    chatSocket.send(JSON.stringify({
        response: "",
        patient_id: patient_id,
    }));
};

// WebSocket event: Message received
chatSocket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    const response = data.response;
    const tool = data.tool;

    const messageDiv = document.createElement('div');
    messageDiv.classList.add('chat-bubble', 'fade-in');

    // 1. Process the raw text through our parser
    const parsed = parseDeepSeekResponse(response);

    // 2. Determine the "Human" message
    // Priority: Tool override > RESPOND tag > Raw response
    let mainContent = "";
    if (tool === "Check_for_updates") {
        mainContent = "Checking the database for your clinical updates...";
    } else if (tool === "update_missing_clinical_data") {
        mainContent = "Updating your clinical records now.";
    } else {
        mainContent = parsed.respond || response; 
    }

    // 3. Create the UI Structure
    // Main Answer
    const textSpan = document.createElement('p');
    textSpan.className = 'main-text';
    textSpan.textContent = mainContent;
    messageDiv.appendChild(textSpan);

    // Optional: Add the "EXPLAIN" part as a subtle hint if it exists
    if (parsed.explain) {
        const infoSpan = document.createElement('span');
        infoSpan.className = 'status-hint';
        infoSpan.textContent = `ℹ️ ${parsed.explain}`;
        messageDiv.appendChild(infoSpan);
    }

    chatLog.appendChild(messageDiv);
    chatLog.scrollTop = chatLog.scrollHeight;
};

// WebSocket event: Connection closed
chatSocket.onclose = (e) => {
    console.error("WebSocket connection closed unexpectedly");
};

// Send button: Send user's message to the WebSocket
sendButton.onclick = (e) => {
    const message = messageInput.value.trim();
    if (message) {
        // Send the message along with the patient ID
        chatSocket.send(JSON.stringify({
            message: message,
            patient_id: patient_id,
        }));
        // Display the user's message in the chat log
        const messageDiv = document.createElement('div');
        messageDiv.textContent = `You: ${message}`;
        messageDiv.classList.add('fade-in'); // Add animation
        chatLog.appendChild(messageDiv);
        // Clear the input field
        messageInput.value = '';
        // Auto-scroll to the bottom of the chat log
        chatLog.scrollTop = chatLog.scrollHeight;
    }
};

// Allow pressing Enter to send the message
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendButton.click();
    }
});