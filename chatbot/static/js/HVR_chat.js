let threadId = null;
let currentEndpoint = '';
let _flowBroken = false; // set to true when user clicks Break
const record = (typeof recordID !== 'undefined') ? recordID : null;

// Determine starting agent based on whether clinical data exists
if (typeof NullFields !== 'undefined' && NullFields === 'True') {
    console.log('[FLOW] All daily fields filled → starting with HVR agent');
    currentEndpoint = '/chatbot/api/agent/hvr/';
} else {
    console.log('[FLOW] Daily fields missing or no record → starting with daily agent');
    currentEndpoint = '/chatbot/api/agent/daily/';
}

const chatLog = document.querySelector('#chat-log');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-button');

function parseAgentReasoning(text) {
    if (!text || typeof text !== 'string') return { main: text, hint: null };
    const respondMatch = text.match(/\*\*RESPOND:\*\*\s*([\s\S]*?)(?=\s*\*\*|$)/i);
    const explainMatch = text.match(/\*\*EXPLAIN:\*\*\s*([\s\S]*?)(?=\s*\*\*|$)/i);
    return {
        main: respondMatch ? respondMatch[1].trim() : text,
        hint: explainMatch ? explainMatch[1].trim() : null
    };
}

async function fetchAgent(data) {
    console.log(`[FLOW] POST to ${currentEndpoint} | message="${data.message}" | thread_id=${data.thread_id}`);
    const response = await fetch(currentEndpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({
            message: data.message,
            thread_id: data.thread_id,
        }),
    });
    const result = await response.json();
    console.log('[FLOW] Response:', JSON.stringify(result));
    return result;
}

function addChatMessage(html, extraClass) {
    const div = document.createElement('div');
    div.classList.add('chat-agent', 'fade-in');
    if (extraClass) div.classList.add(extraClass);
    div.innerHTML = html;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
    return div;
}

function addStatusMessage(text) {
    const div = document.createElement('div');
    div.style.cssText = 'color:#6c757d; font-style:italic; font-size:0.9em; margin:4px 0; text-align:center;';
    div.textContent = text;
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
    return div;
}

async function processAndDisplay(data) {
    threadId = data.thread_id;
    const responseText = data.response;

    // Display agent message
    if (responseText) {
        const parsed = parseAgentReasoning(responseText);
        let html = `<i class="fas fa-robot"></i> : ${parsed.main}`;
        if (parsed.hint) {
            html += `<div class="agent-explain-subtext">${parsed.hint}</div>`;
        }
        addChatMessage(html);
    }

    // Handle swap signals (switch to next agent in the pipeline)
    if (data.swap) {
        await handleSwap(data.swap);
        return;
    }

    // Handle action signals
    if (data.action) {
        const feedbackActions = ['checkBluetoothConnection', 'pairBluetoothDevice', 'startECGRecording'];
        const isFeedback = feedbackActions.includes(data.action);

        // Show a brief status so user sees what's happening
        const statusEl = addStatusMessage(`⏳ Executing: ${data.action}...`);

        // Small delay so user can read the agent message before action executes
        await sleep(2000);

        // Check if user hit Break during the delay
        if (_flowBroken) {
            _flowBroken = false;
            statusEl.remove();
            enableInput();
            return;
        }

        // Execute the tool
        let result = await executeTool(data.action, null, record);
        statusEl.remove();

        if (isFeedback && result !== null) {
            addStatusMessage(`✅ ${data.action} → ${result}`);
            await sleep(800);

            // Check Break again before auto-POSTing
            if (_flowBroken) {
                _flowBroken = false;
                enableInput();
                return;
            }

            // POST result back to agent
            const nextData = await fetchAgent({ message: result, thread_id: threadId });
            await processAndDisplay(nextData);
            return;
        }
    }

    // No action → enable input for user to reply
    enableInput();
}

async function handleSwap(target) {
    if (target === 'hvr') {
        currentEndpoint = '/chatbot/api/agent/hvr/';
        addChatMessage('<i class="fas fa-robot"></i> : 🔄 Switching to ECG recording assistant...', 'text-info');
        await sleep(1500);
        const nextData = await fetchAgent({ message: 'hello', thread_id: null });
        await processAndDisplay(nextData);
    } else if (target === 'imaging') {
        currentEndpoint = '/chatbot/api/agent/imaging/';
        addChatMessage('<i class="fas fa-robot"></i> : 🔄 Switching to imaging collection assistant...', 'text-info');
        await sleep(1500);
        const nextData = await fetchAgent({ message: 'hello', thread_id: null });
        await processAndDisplay(nextData);
    }
}

function enableInput() {
    messageInput.disabled = false;
    sendButton.disabled = false;
    messageInput.focus();
}

function disableInput() {
    messageInput.disabled = true;
    sendButton.disabled = true;
}

function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
}

// Break button handler — breaks the current action loop
function breakFlow() {
    _flowBroken = true;
    breakCurrentAction();
    hideRecordingControls();
    enableInput();
    addStatusMessage('⏹ Flow interrupted. You can now type a response.');
}

// Send button handler
sendButton.onclick = async () => {
    const message = messageInput.value.trim();
    if (!message) return;

    // Display user message
    const userDiv = document.createElement('div');
    userDiv.id = 'user-message';
    userDiv.classList.add('chat-user', 'fade-in');
    userDiv.innerHTML = '<i class="fa-solid fa-user"></i> : ' + message;
    chatLog.appendChild(userDiv);
    messageInput.value = '';
    chatLog.scrollTop = chatLog.scrollHeight;

    disableInput();

    try {
        const data = await fetchAgent({ message, thread_id: threadId });
        await processAndDisplay(data);
    } catch (error) {
        console.error('Error:', error);
        enableInput();
    }
};

// Enter key
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendButton.click();
});

// Global Break button in the UI
(function addBreakBtn() {
    const btn = document.createElement('button');
    btn.id = 'global-break-btn';
    btn.innerHTML = '⏹ Break';
    btn.style.cssText = 'position:fixed; bottom:20px; right:20px; padding:10px 20px; background:#dc3545; color:white; border:none; border-radius:8px; font-size:14px; font-weight:bold; cursor:pointer; z-index:9998; box-shadow:0 4px 12px rgba(220,53,69,0.4); display:none;';
    btn.onclick = breakFlow;
    document.body.appendChild(btn);

    // Show break button whenever input is disabled (action in progress)
    const origDisable = disableInput;
    disableInput = function() {
        origDisable();
        btn.style.display = 'block';
    };
    const origEnable = enableInput;
    enableInput = function() {
        origEnable();
        btn.style.display = 'none';
    };
})();

function getCSRFToken() {
    return document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1] || '';
}

// Send initial greeting to start the conversation
window.addEventListener('DOMContentLoaded', async () => {
    console.log('[FLOW] DOM ready — starting conversation');
    disableInput();
    try {
        const data = await fetchAgent({ message: 'Hello', thread_id: null });
        await processAndDisplay(data);
    } catch (error) {
        console.error('[FLOW] Error starting conversation:', error);
        enableInput();
    }
});
