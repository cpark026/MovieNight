let isLoginMode = true;

const authForm = document.getElementById('authForm');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');
const submitBtn = document.getElementById('submitBtn');
const formTitle = document.getElementById('formTitle');
const toggleLink = document.getElementById('toggleLink');
const toggleDiv = document.getElementById('toggleDiv');

function toggleForms(e) {
    e.preventDefault();
    isLoginMode = !isLoginMode;
    
    clearMessages();
    authForm.reset();
    
    if (isLoginMode) {
        formTitle.textContent = 'Login';
        submitBtn.textContent = 'Login';
        toggleDiv.innerHTML = '<p>Don\'t have an account? <a href="#" id="toggleLink" onclick="toggleForms(event)">Register</a></p>';
    } else {
        formTitle.textContent = 'Register';
        submitBtn.textContent = 'Register';
        toggleDiv.innerHTML = '<p>Already have an account? <a href="#" id="toggleLink" onclick="toggleForms(event)">Login</a></p>';
    }
}

authForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    clearMessages();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        showError('Please fill in all fields');
        return;
    }

    if (password.length < 6) {
        showError('Password must be at least 6 characters');
        return;
    }

    try {
        const endpoint = isLoginMode ? '/api/login' : '/api/register';
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });

        const data = await response.json();

        if (response.ok) {
            showSuccess(isLoginMode ? 'Login successful!' : 'Registration successful!');
            
            // Store cached recommendations in sessionStorage so index.js can use them
            if (data.cached_recommendations) {
                sessionStorage.setItem('cachedRecommendations', JSON.stringify(data.cached_recommendations));
                console.log('[LOGIN] Cached recommendations stored:', data.cached_recommendations);
            }
            
            setTimeout(() => {
                window.location.href = '/';
            }, 1500);
        } else {
            showError(data.message || (isLoginMode ? 'Login failed' : 'Registration failed'));
        }
    } catch (error) {
        showError('An error occurred. Please try again.');
        console.error('Auth error:', error);
    }
});

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.style.color = 'white';
    successMessage.style.display = 'none';
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    successMessage.style.color = 'white';
    errorMessage.style.display = 'none';
}

function clearMessages() {
    errorMessage.style.display = 'none';
    successMessage.style.display = 'none';
}

usernameInput.addEventListener('input', clearMessages);
passwordInput.addEventListener('input', clearMessages);