// Static/js/auth.js

async function logout() {
    // const refreshToken = getCookie('refresh_token');

    try {
        const response = await fetch('/accounts/api/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(), // Include the CSRF token for security
            },
            body: JSON.stringify({ 
                // refresh: refreshToken
             }),
        });

        if (response.ok) {
            // deleteCookie('access_token');
            // deleteCookie('refresh_token');
            window.location.href = '/';
        } else {
            alert('Logout failed.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred during logout.');
    }
}

// Utility functions for cookies
function getCookie(name) {
    let nameEQ = name + "=";
    let ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i].trim();
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

function deleteCookie(name) {
    document.cookie = name + "=; Max-Age=-99999999; path=/;";
}

// Function to get the CSRF token from cookies
function getCSRFToken() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
}

document.getElementById('logout-button').addEventListener('click', logout);



async function createConversation() {
    try {
        const response = await fetch('/chatbot/api/conversations/create/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),  // Correct
            },
            body: JSON.stringify({ patient : patient ,tokens_consumed: 0 })  // Default tokens_consumed to 0
        });

        if (response.ok) {
            const data = await response.json();
            const conversationUid = data.uid;  // Assuming the API returns the conversation UID
            window.location.href = `/chatbot/chat/${conversationUid}/`;  // Redirect to the chat page
        } else {
            alert('Failed to create conversation. Please try again.');
        }
    } catch (error) {
        console.error('Error creating conversation:', error);
        alert('An error occurred. Please try again.');
    }
}

document.getElementById('start-conversation-button').addEventListener('click', () => {
    createConversation();
});