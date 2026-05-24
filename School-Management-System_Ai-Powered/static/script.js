// --- Utility Functions ---

/**
 * Displays a custom alert/message in the page structure.
 * Note: Window.alert() is forbidden in the canvas environment.
 * We'll use a simple flash-like banner at the top of the body.
 * @param {string} message - The message content.
 * @param {string} type - 'success', 'error', or 'info'.
 */
function displayCustomAlert(message, type) {
    const alertContainer = document.getElementById('custom-alert-container') || document.createElement('div');
    if (!alertContainer.id) {
        alertContainer.id = 'custom-alert-container';
        alertContainer.style.cssText = `
            position: fixed; top: 10px; left: 50%; transform: translateX(-50%); 
            z-index: 10000; width: 90%; max-width: 400px;
        `;
        document.body.appendChild(alertContainer);
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = `flash-message ${type}`;
    alertDiv.textContent = message;
    alertDiv.style.marginBottom = '10px';
    alertContainer.appendChild(alertDiv);

    // Automatically remove after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// --- Login/Signup Modal Handlers ---

document.addEventListener('DOMContentLoaded', () => {
    const loginSignupModal = document.getElementById('login-signup-modal');
    const authButton = document.getElementById('auth-button');
    const closeButtons = document.querySelectorAll('.close-modal');
    const switchLinks = document.querySelectorAll('.switch-auth');
    const loginForm = document.getElementById('login-form-container');
    const signupForm = document.getElementById('signup-form-container');

    if (authButton && loginSignupModal) {
        authButton.addEventListener('click', () => {
            loginSignupModal.style.display = 'flex';
        });

        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                loginSignupModal.style.display = 'none';
            });
        });

        switchLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                if (link.dataset.target === 'signup') {
                    loginForm.style.display = 'none';
                    signupForm.style.display = 'block';
                } else {
                    loginForm.style.display = 'block';
                    signupForm.style.display = 'none';
                }
            });
        });

        // Close when clicking outside the modal content
        window.addEventListener('click', (event) => {
            if (event.target == loginSignupModal) {
                loginSignupModal.style.display = 'none';
            }
        });
    }

    // Initialize Marks Table Listener
    initMarksTableListener();
    
    // Initialize Chatbot Logic
    initChatbot();

    // Check for existing flash messages and replace with custom alert
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        const type = msg.classList.contains('error') ? 'error' : 
                     msg.classList.contains('success') ? 'success' : 'info';
        // Only run if the message is already present on page load
        if(msg.parentElement.id !== 'custom-alert-container') {
             displayCustomAlert(msg.textContent.trim(), type);
             msg.style.display = 'none'; // Hide the original Flask message
        }
    });
});

// --- Marks Management Logic (for Teacher/Admin) ---

function initMarksTableListener() {
    const studentSelect = document.getElementById('student-select-marks');
    if (studentSelect) {
        studentSelect.addEventListener('change', fetchStudentMarks);
        // Initial load if a student is already selected
        if (studentSelect.value) {
            fetchStudentMarks();
        }
    }
}

async function fetchStudentMarks() {
    const studentId = document.getElementById('student-select-marks').value;
    const marksTableBody = document.getElementById('marks-table-body');
    const totalPercentageCell = document.getElementById('total-percentage');
    const downloadLink = document.getElementById('download-marks-link');
    
    marksTableBody.innerHTML = '<tr><td colspan="4">Loading marks...</td></tr>';
    totalPercentageCell.textContent = '...';
    downloadLink.style.display = 'none';

    if (!studentId) {
        marksTableBody.innerHTML = '<tr><td colspan="4">Please select a student.</td></tr>';
        return;
    }

    try {
        const response = await fetch(`/get_student_marks/${studentId}`);
        const data = await response.json();

        if (data.error) {
            marksTableBody.innerHTML = `<tr><td colspan="4" class="error">${data.error}</td></tr>`;
            totalPercentageCell.textContent = 'N/A';
            return;
        }

        marksTableBody.innerHTML = ''; // Clear loading message

        if (data.marks.length === 0) {
            marksTableBody.innerHTML = '<tr><td colspan="4">No marks entered yet.</td></tr>';
        } else {
            data.marks.forEach(mark => {
                const row = marksTableBody.insertRow();
                row.insertCell().textContent = mark.subject_name;
                row.insertCell().textContent = mark.marks_obtained;
                row.insertCell().textContent = mark.total_marks;
            });
            totalPercentageCell.textContent = `${data.percentage}%`;
            downloadLink.href = `/download_marks/${studentId}`;
            downloadLink.style.display = 'inline-block';
        }
        
    } catch (error) {
        console.error('Error fetching student marks:', error);
        marksTableBody.innerHTML = '<tr><td colspan="4" class="error">Failed to load marks data.</td></tr>';
        totalPercentageCell.textContent = 'Error';
    }
}

// --- Gemini Chatbot Logic ---

function initChatbot() {
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', handleChatSubmit);
    }
}

// Function to handle exponential backoff for API calls
async function fetchWithBackoff(url, options, maxRetries = 5) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                // If it's a 429 (Too Many Requests), we retry. Otherwise, throw a standard error.
                if (response.status === 429 && i < maxRetries - 1) {
                    throw new Error('429 Rate Limit - Retrying...');
                }
                const errorText = await response.text();
                throw new Error(`API Error: ${response.status} - ${errorText.substring(0, 100)}...`);
            }
            return response;
        } catch (error) {
            if (error.message.includes('429 Rate Limit')) {
                const delay = Math.pow(2, i) * 1000 + Math.random() * 1000; // 1s, 2s, 4s... + jitter
                console.warn(`Retry attempt ${i + 1} after ${delay.toFixed(0)}ms: ${error.message}`);
                await new Promise(resolve => setTimeout(resolve, delay));
            } else {
                throw error; // Throw other errors immediately
            }
        }
    }
    throw new Error('Max retries exceeded.');
}


async function handleChatSubmit(e) {
    e.preventDefault();
    
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendButton = document.getElementById('send-button');
    const loadingIndicator = document.getElementById('loading-indicator');
    const userPrompt = chatInput.value.trim();
    
    // API key is passed from Flask template (see chatbot.html)
    const apiKey = document.getElementById('gemini-api-key').dataset.key;
    if (!apiKey || apiKey === 'YOUR_GEMINI_API_KEY') {
        displayCustomAlert('Gemini API key is not configured. Please update app.py.', 'error');
        return;
    }

    if (!userPrompt) return;

    // 1. Display User Message
    appendMessage(userPrompt, 'user');
    chatInput.value = '';
    
    // Disable input and show loading
    sendButton.disabled = true;
    chatInput.disabled = true;
    loadingIndicator.style.display = 'block';

    // 2. Construct API Call
    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;
    
    const payload = {
        contents: [{ parts: [{ text: userPrompt }] }],
        tools: [{ "google_search": {} }], // Use Google Search for grounding
        systemInstruction: {
            parts: [{ text: "You are a helpful and knowledgeable school portal chatbot based on Google Gemini. Answer all questions concisely and professionally. If the question relates to school data (like marks, teachers, students), state clearly that you do not have access to real-time database information and can only answer general knowledge questions. Use your grounding sources when necessary." }]
        },
    };
    
    const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    };

    // 3. Send Request
    try {
        const response = await fetchWithBackoff(apiUrl, options);
        const result = await response.json();
        
        let geminiResponseText = "Sorry, I couldn't get a response from the model.";
        let sourcesHtml = '';

        const candidate = result.candidates?.[0];

        if (candidate && candidate.content?.parts?.[0]?.text) {
            geminiResponseText = candidate.content.parts[0].text;
            
            // Extract and format grounding sources
            const groundingMetadata = candidate.groundingMetadata;
            if (groundingMetadata && groundingMetadata.groundingAttributions) {
                const sources = groundingMetadata.groundingAttributions
                    .map(attr => ({
                        uri: attr.web?.uri,
                        title: attr.web?.title,
                    }))
                    .filter(source => source.uri && source.title);
                
                if (sources.length > 0) {
                    sourcesHtml = '<div class="text-xs mt-2 text-gray-500">Sources: ' + 
                                  sources.map((s, i) => `<a href="${s.uri}" target="_blank" class="underline hover:no-underline">${s.title} (${i + 1})</a>`).join(', ') + 
                                  '</div>';
                }
            }
        }
        
        // 4. Display Gemini Response
        appendMessage(geminiResponseText + sourcesHtml, 'gemini');

    } catch (error) {
        console.error('Chatbot API Error:', error);
        appendMessage('An error occurred while contacting the chatbot service.', 'gemini');
    } finally {
        // Re-enable input
        sendButton.disabled = false;
        chatInput.disabled = false;
        loadingIndicator.style.display = 'none';
        chatInput.focus();
    }
}

/**
 * Appends a new message to the chat history and scrolls to the bottom.
 * @param {string} text - The message content (can include HTML for sources).
 * @param {string} sender - 'user' or 'gemini'.
 */
function appendMessage(text, sender) {
    const chatHistory = document.getElementById('chat-history');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.innerHTML = text; // Use innerHTML to allow for source links
    chatHistory.appendChild(messageDiv);
    // Scroll to the latest message
    chatHistory.scrollTop = chatHistory.scrollHeight;
}