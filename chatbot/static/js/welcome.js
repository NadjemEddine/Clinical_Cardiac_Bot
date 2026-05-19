// Get the patient ID from the template
const roomName = "room_123"; // Replace with the actual room name
const chatSocket = new WebSocket(
    `ws://${window.location.host}/ws/welcomeChat/${roomName}/`
);

// DOM elements
const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

// WebSocket event: Connection opened
chatSocket.onopen = (e) => {
    console.log("WebSocket connection established");
    // Optionally, send an initial message to start the conversation
    chatSocket.send(JSON.stringify({
        response: "I am a patient",
        patient_id: patient_id,
    }));
};

// WebSocket event: Message received
chatSocket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    const response = data.response; // Agent's response
    const finalData = data.final_data; // Final clinical data (if available)
    const tool = data.tool; // Tool attribute (e.g., "Check_static_clinical_data")

    // Determine the message to display based on the tool attribute
    let displayMessage = response; // Default to the agent's response



    if (tool === "Check_static_clinical_data") {
        displayMessage = "Let me check in our database, please.";
    } else if (tool === "Update_static_clinical_data") {
        displayMessage = "Thank you for the information. Let me update your status in the database.";
    }

    // Display the agent's response
    if (response && (data.sender === "agent" || data.sender === "patient")) {

        if (data.sender === "agent") {
            const messageDiv = document.createElement('div');
            messageDiv.id = 'agent-message'; // Add ID as requested
            messageDiv.classList.add('chat-agent');
            messageDiv.innerHTML = '<i class="fas fa-robot"></i> ' + " : " + displayMessage; // Use Font Awesome 5 icon
            messageDiv.classList.add('fade-in');
            chatLog.appendChild(messageDiv);
        } else {
            const messageDiv = document.createElement('div');
            messageDiv.id = 'user-message'; // Add ID as requested
            messageDiv.classList.add('chat-user');
            messageDiv.innerHTML = '<i class="fa-solid fa-user"></i> ' + " : " + displayMessage; // Use Font Awesome 5 icon
            messageDiv.classList.add('fade-in');
            chatLog.appendChild(messageDiv);

        }
        
    }
    // Display final clinical data if available
    // if (finalData) {
    //     const finalDataDiv = document.createElement('div');
    //     finalDataDiv.textContent = `Final Clinical Data: ${JSON.stringify(finalData, null, 2)}`;
    //     finalDataDiv.classList.add('fade-in'); // Add animation
    //     chatLog.appendChild(finalDataDiv);
    // }

    // Check if the response is "All your clinical data are updated."
    if (response === "All your clinical data are updated.") {
        // Disable the input field and send button
        messageInput.disabled = true;
        sendButton.disabled = true;

        // Create a congratulatory alert in the middle of the page
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

        // Append the alert to the body
        document.body.appendChild(alertDiv);
    }

    // Auto-scroll to the bottom of the chat log
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
            sender: "patient"
        }));
        // Display the user's message in the chat log
        // const messageDiv = document.createElement('div');
        // messageDiv.textContent = `You: ${message}`;
        // messageDiv.classList.add('fade-in'); // Add animation
        // chatLog.appendChild(messageDiv);
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