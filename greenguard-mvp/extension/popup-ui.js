document.addEventListener('DOMContentLoaded', function() {
    console.log('Popup UI initializing...');

    function setupPasswordToggles() {
        const passwordToggles = document.querySelectorAll('.password-toggle');
        console.log('Found password toggles:', passwordToggles.length);
        
        passwordToggles.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const container = this.closest('.password-input-container');
                const input = container.querySelector('input[type="password"], input[type="text"]');
                
                if (input) {
                    const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
                    input.setAttribute('type', type);
                    
                    this.textContent = type === 'password' ? '👁️' : '🙈';
                    console.log('Password visibility toggled:', type);
                }
            });
        });
    }

    function setupTabNavigation() {
        const tabBtns = document.querySelectorAll('.tab-btn');
        console.log('Found tab buttons:', tabBtns.length);
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                
                btn.classList.add('active');
                const tabId = btn.getAttribute('data-tab') + 'Tab';
                const targetTab = document.getElementById(tabId);
                if (targetTab) {
                    targetTab.classList.add('active');
                    console.log('Switched to tab:', tabId);
                }
            });
        });
    }

    function setupAuthSwitching() {
        const switchToSignin = document.getElementById('switchToSignin');
        const switchToSignup = document.getElementById('switchToSignup');

        if (switchToSignin) {
            switchToSignin.addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('signupFormContainer').style.display = 'none';
                document.getElementById('signinFormContainer').style.display = 'block';
                console.log('Switched to signin form');
            });
        }

        if (switchToSignup) {
            switchToSignup.addEventListener('click', (e) => {
                e.preventDefault();
                document.getElementById('signinFormContainer').style.display = 'none';
                document.getElementById('signupFormContainer').style.display = 'block';
                console.log('Switched to signup form');
            });
        }
    }

    function setupFormSubmissions() {
        const signupForm = document.getElementById('signupForm');
        const signinForm = document.getElementById('signinForm');

        if (signupForm) {
            signupForm.addEventListener('submit', (e) => {
                e.preventDefault();
                console.log('Signup form submitted');
                
                const email = document.getElementById('signupEmail').value;
                const password = document.getElementById('signupPassword').value;
                const confirmPassword = document.getElementById('confirmPassword').value;
                
                if (password !== confirmPassword) {
                    alert('Passwords do not match!');
                    return;
                }
                
                showDashboard(email);
            });
        }

        if (signinForm) {
            signinForm.addEventListener('submit', (e) => {
                e.preventDefault();
                console.log('Signin form submitted');
                
                const email = document.getElementById('signinEmail').value;
                const password = document.getElementById('signinPassword').value;
                
                showDashboard(email);
            });
        }
    }

    function showDashboard(email) {
        document.getElementById('authSection').style.display = 'none';
        document.getElementById('dashboardSection').style.display = 'block';
        
        const userInfo = document.getElementById('userInfo');
        const userEmail = document.getElementById('userEmail');
        
        if (userInfo && userEmail) {
            userInfo.style.display = 'flex';
            userEmail.textContent = email;
        }
        
        console.log('Dashboard shown for user:', email);
    }

    function setupLogout() {
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                document.getElementById('dashboardSection').style.display = 'none';
                document.getElementById('authSection').style.display = 'flex';
                document.getElementById('userInfo').style.display = 'none';
                
                document.getElementById('signupForm').reset();
                document.getElementById('signinForm').reset();
                
                console.log('User logged out');
            });
        }
    }

    function initializeUI() {
        setupPasswordToggles();
        setupTabNavigation();
        setupAuthSwitching();
        setupFormSubmissions();
        setupLogout();
        
        const authSection = document.getElementById('authSection');
        if (authSection) {
            authSection.style.display = 'flex';
            console.log('Auth section shown by default');
        }
        
        console.log('Popup UI initialized successfully');
    }

    initializeUI();
});

function checkPasswordStrength(password) {
    const strength = {
        score: 0,
        feedback: []
    };
    
    if (password.length >= 8) strength.score++;
    else strength.feedback.push('Use at least 8 characters');
    
    if (/[A-Z]/.test(password)) strength.score++;
    else strength.feedback.push('Include uppercase letter');
    
    if (/[a-z]/.test(password)) strength.score++;
    else strength.feedback.push('Include lowercase letter');
    
    if (/[0-9]/.test(password)) strength.score++;
    else strength.feedback.push('Include number');
    
    if (/[^A-Za-z0-9]/.test(password)) strength.score++;
    else strength.feedback.push('Include special character');
    
    return strength;
}