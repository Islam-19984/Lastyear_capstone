const API_BASE_URL = 'http://localhost:5000/api';

let currentUser = null;
let currentSection = 'hero';

document.addEventListener('DOMContentLoaded', async () => {
    console.log('GreenGuard popup initializing...');
    
    const userData = await chrome.storage.local.get(['user']);
    if (userData.user) {
        currentUser = userData.user;
        showDashboard();
    } else {
        showAuth();
    }
    
    setupEventListeners();
    
    loadStatistics();
});

function setupEventListeners() {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = e.target.dataset.section;
            if (section) {
                navigateToSection(section);
            }
        });
    });
    
    const signupForm = document.getElementById('signupForm');
    const signinForm = document.getElementById('signinForm');
    
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }
    
    if (signinForm) {
        signinForm.addEventListener('submit', handleSignin);
    }
    
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabName = e.target.dataset.tab;
            if (tabName) {
                switchTab(tabName);
            }
        });
    });
    
    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        analysisForm.addEventListener('submit', handleAnalysis);
    }
    
    const verificationForm = document.getElementById('verificationForm');
    if (verificationForm) {
        verificationForm.addEventListener('submit', handleVerification);
    }
    
    const communityForm = document.getElementById('communityForm');
    if (communityForm) {
        communityForm.addEventListener('submit', handleCommunitySubmission);
    }
    
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    const switchToSignin = document.getElementById('switchToSignin');
    const switchToSignup = document.getElementById('switchToSignup');
    
    if (switchToSignin) {
        switchToSignin.addEventListener('click', (e) => {
            e.preventDefault();
            showSigninForm();
        });
    }
    
    if (switchToSignup) {
        switchToSignup.addEventListener('click', (e) => {
            e.preventDefault();
            showSignupForm();
        });
    }
}

function navigateToSection(section) {
    currentSection = section;
    
    const sections = document.querySelectorAll('.section');
    sections.forEach(s => s.style.display = 'none');
    
    const targetSection = document.getElementById(`${section}Section`);
    if (targetSection) {
        targetSection.style.display = 'block';
    }
    
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.dataset.section === section) {
            link.classList.add('active');
        }
    });
}

function switchTab(tabName) {
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    
    const targetContent = document.getElementById(`${tabName}Tab`);
    if (targetContent) {
        targetContent.classList.add('active');
    }
    
    const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (targetButton) {
        targetButton.classList.add('active');
    }
}

async function handleSignup(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const userData = {
        email: formData.get('email'),
        password: formData.get('password'),
        confirmPassword: formData.get('confirmPassword')
    };
    
    if (userData.password !== userData.confirmPassword) {
        showMessage('Passwords do not match', 'error');
        return;
    }
    
    try {
        showLoading('Creating account...');
        
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: userData.email,
                password: userData.password
            })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            currentUser = result.user;
            await chrome.storage.local.set({ user: currentUser });
            showMessage('Account created successfully!', 'success');
            showDashboard();
        } else {
            showMessage(result.message || 'Registration failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Registration error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleSignin(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const credentials = {
        email: formData.get('email'),
        password: formData.get('password')
    };
    
    try {
        showLoading('Signing in...');
        
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(credentials)
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            currentUser = result.user;
            await chrome.storage.local.set({ user: currentUser });
            showMessage('Welcome back!', 'success');
            showDashboard();
        } else {
            showMessage(result.message || 'Login failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Login error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleAnalysis(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const content = formData.get('content');
    
    if (!content.trim()) {
        showMessage('Please enter content to analyze', 'error');
        return;
    }
    
    try {
        showLoading('Analyzing content...');
        
        const response = await fetch(`${API_BASE_URL}/claims/detect`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            displayAnalysisResults(result);
        } else {
            showMessage(result.message || 'Analysis failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Analysis error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleVerification(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const company = formData.get('company');
    const claim = formData.get('claim');
    
    if (!company.trim() || !claim.trim()) {
        showMessage('Please enter both company name and claim', 'error');
        return;
    }
    
    try {
        showLoading('Verifying claim...');
        
        const response = await fetch(`${API_BASE_URL}/claims/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ company, claim })
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            displayVerificationResults(result);
        } else {
            showMessage(result.message || 'Verification failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Verification error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

async function handleCommunitySubmission(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const feedback = {
        type: formData.get('type'),
        company: formData.get('company'),
        description: formData.get('description')
    };
    
    if (!feedback.type || !feedback.company || !feedback.description) {
        showMessage('Please fill in all fields', 'error');
        return;
    }
    
    try {
        showLoading('Submitting feedback...');
        
        const response = await fetch(`${API_BASE_URL}/community/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(feedback)
        });
        
        const result = await response.json();
        hideLoading();
        
        if (response.ok) {
            showMessage('Feedback submitted successfully!', 'success');
            e.target.reset();
        } else {
            showMessage(result.message || 'Submission failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Submission error:', error);
        showMessage('Network error. Please try again.', 'error');
    }
}

function displayAnalysisResults(result) {
    const resultsDiv = document.getElementById('analysisResults');
    if (!resultsDiv) return;
    
    let riskLevel = 'Low';
    let riskColor = '#2ecc71';
    
    if (result.risk_score > 0.7) {
        riskLevel = 'High';
        riskColor = '#e74c3c';
    } else if (result.risk_score > 0.4) {
        riskLevel = 'Medium';
        riskColor = '#f39c12';
    }
    
    resultsDiv.innerHTML = `
        <div class="result-card">
            <h3>Analysis Results</h3>
            <div class="risk-indicator">
                <span>Risk Level: </span>
                <span style="color: ${riskColor}; font-weight: bold;">${riskLevel}</span>
                <span>(${Math.round(result.risk_score * 100)}%)</span>
            </div>
            <div class="summary">
                <h4>Summary:</h4>
                <p>${result.summary}</p>
            </div>
            <div class="claims-found">
                <h4>Claims Detected: ${result.claims_count}</h4>
            </div>
        </div>
    `;
    
    resultsDiv.style.display = 'block';
}

function displayVerificationResults(result) {
    const resultsDiv = document.getElementById('verificationResults');
    if (!resultsDiv) return;
    
    const trustColor = result.trustworthy ? '#2ecc71' : '#e74c3c';
    const trustText = result.trustworthy ? 'Trustworthy' : 'Questionable';
    
    resultsDiv.innerHTML = `
        <div class="result-card">
            <h3>Verification Results</h3>
            <div class="trust-indicator">
                <span>Status: </span>
                <span style="color: ${trustColor}; font-weight: bold;">${trustText}</span>
            </div>
            <div class="verification-summary">
                <h4>Analysis:</h4>
                <p>${result.analysis}</p>
            </div>
            <div class="evidence">
                <h4>Evidence:</h4>
                <ul>
                    ${result.evidence.map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
    
    resultsDiv.style.display = 'block';
}

async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/analytics/stats`);
        const stats = await response.json();
        
        if (response.ok) {
            updateStatisticsDisplay(stats);
        }
    } catch (error) {
        updateStatisticsDisplay({
            total_claims_analyzed: 0,
            companies_verified: 0,
            community_reports: 0,
            greenwashing_detected: 0
        });
    }
}

function updateStatisticsDisplay(stats) {
    const elements = {
        'claimsAnalyzed': stats.total_claims_analyzed || 0,
        'companiesVerified': stats.companies_verified || 0,
        'communityReports': stats.community_reports || 0,
        'greenwashingDetected': stats.greenwashing_detected || 0
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value.toLocaleString();
        }
    });
}

function showAuth() {
    const authSection = document.getElementById('authSection');
    const dashboardSection = document.getElementById('dashboardSection');
    
    if (authSection) authSection.style.display = 'block';
    if (dashboardSection) dashboardSection.style.display = 'none';
    
    showSignupForm();
}

function showDashboard() {
    const authSection = document.getElementById('authSection');
    const dashboardSection = document.getElementById('dashboardSection');
    
    if (authSection) authSection.style.display = 'none';
    if (dashboardSection) dashboardSection.style.display = 'block';
    
    switchTab('analyzer');
    
    const userEmailSpan = document.getElementById('userEmail');
    if (userEmailSpan && currentUser) {
        userEmailSpan.textContent = currentUser.email;
    }
}

function showSignupForm() {
    const signupForm = document.getElementById('signupFormContainer');
    const signinForm = document.getElementById('signinFormContainer');
    
    if (signupForm) signupForm.style.display = 'block';
    if (signinForm) signinForm.style.display = 'none';
}

function showSigninForm() {
    const signupForm = document.getElementById('signupFormContainer');
    const signinForm = document.getElementById('signinFormContainer');
    
    if (signupForm) signupForm.style.display = 'none';
    if (signinForm) signinForm.style.display = 'block';
}

async function handleLogout() {
    await chrome.storage.local.remove(['user']);
    currentUser = null;
    showAuth();
    showMessage('Logged out successfully', 'success');
}

function showLoading(message) {
    console.log(`Loading: ${message}`);
}

function hideLoading() {
    console.log('Loading complete');
}

function showMessage(message, type) {
    if (type === 'error') {
        alert(`Error: ${message}`);
    } else {
        alert(message);
    }
}