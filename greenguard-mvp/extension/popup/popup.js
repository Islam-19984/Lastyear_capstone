const API_BASE_URL = 'http://localhost:5000/api';

let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    console.log('GreenGuard popup initializing...');

    try {
        const userData = await chrome.storage.local.get(['user']);
        if (userData.user) {
            currentUser = userData.user;
            showDashboard();
        } else {
            showAuth();
        }

        setupEventListeners();
        loadStatistics();

        console.log('GreenGuard popup initialized successfully');
    } catch (error) {
        console.error('Initialization error:', error);
        showAuth();
        setupEventListeners();
        loadStatistics();
    }
});

function setupEventListeners() {
    console.log('Setting up event listeners...');

    const tabButtons = document.querySelectorAll('.tab-btn');
    console.log('Found tab buttons:', tabButtons.length);

    tabButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const tabName = e.target.dataset.tab;
            console.log('Tab clicked:', tabName);
            if (tabName) {
                switchTab(tabName);
            }
        });
    });

    const signupForm = document.getElementById('signupForm');
    const signinForm = document.getElementById('signinForm');

    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
        console.log('Signup form listener added');
    }

    if (signinForm) {
        signinForm.addEventListener('submit', handleSignin);
        console.log('Signin form listener added');
    }

    const analysisForm = document.getElementById('analysisForm');
    if (analysisForm) {
        analysisForm.addEventListener('submit', handleAnalysis);
        console.log('Analysis form listener added');
    }

    const verificationForm = document.getElementById('verificationForm');
    if (verificationForm) {
        verificationForm.addEventListener('submit', handleVerification);
        console.log('Verification form listener added');
    }

    const communityForm = document.getElementById('communityForm');
    if (communityForm) {
        communityForm.addEventListener('submit', handleCommunitySubmission);
        console.log('Community form listener added');
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

    console.log('Event listeners setup complete');
}

function switchTab(tabName) {
    console.log('Switching to tab:', tabName);

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
        console.log('Tab content shown:', `${tabName}Tab`);
    } else {
        console.error('Tab content not found:', `${tabName}Tab`);
    }

    const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
    if (targetButton) {
        targetButton.classList.add('active');
        console.log('Tab button activated');
    } else {
        console.error('Tab button not found for:', tabName);
    }

    if (tabName === 'dashboard') {
        loadStatistics();
    }
}

async function handleSignup(e) {
    e.preventDefault();
    console.log('Handling signup...');

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

        console.log('Signup response:', result);

        if (response.ok && result.success) {
            currentUser = result.user;
            await chrome.storage.local.set({ user: currentUser });
            showMessage('Account created successfully!', 'success');
            showDashboard();
        } else {
            showMessage(result.error || result.message || 'Registration failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Registration error:', error);
        showMessage('Network error. Please check if backend is running.', 'error');
    }
}

async function handleSignin(e) {
    e.preventDefault();
    console.log('Handling signin...');

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

        console.log('Signin response:', result);

        if (response.ok && result.success) {
            currentUser = result.user;
            await chrome.storage.local.set({ user: currentUser });
            showMessage('Welcome back!', 'success');
            showDashboard();
        } else {
            showMessage(result.error || result.message || 'Login failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Login error:', error);
        showMessage('Network error. Please check if backend is running.', 'error');
    }
}

async function handleAnalysis(e) {
    e.preventDefault();
    console.log('Handling analysis...');

    const formData = new FormData(e.target);
    const content = formData.get('content');

    if (!content || !content.trim()) {
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
            body: JSON.stringify({
                text: content,
                content: content,
                user_email: currentUser?.email || 'anonymous'
            })
        });

        const result = await response.json();
        hideLoading();

        console.log('Analysis result:', result);

        if (response.ok && result.success) {
            displayAnalysisResults(result);
            loadStatistics(); // Refresh stats
        } else {
            showMessage(result.error || result.message || 'Analysis failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Analysis error:', error);
        showMessage('Network error. Please check if backend is running.', 'error');
    }
}

async function handleVerification(e) {
    e.preventDefault();
    console.log('Handling verification...');

    const formData = new FormData(e.target);
    const company = formData.get('company');
    const claim = formData.get('claim');

    if (!company || !company.trim() || !claim || !claim.trim()) {
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
            body: JSON.stringify({
                company_name: company,
                claim_text: claim,
                user_email: currentUser?.email || 'anonymous'
            })
        });

        const result = await response.json();
        hideLoading();

        console.log('Verification result:', result);

        if (response.ok && result.success) {
            displayVerificationResults(result);
            loadStatistics(); // Refresh stats
        } else {
            showMessage(result.error || result.message || 'Verification failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Verification error:', error);
        showMessage('Network error. Please check if backend is running.', 'error');
    }
}

async function handleCommunitySubmission(e) {
    e.preventDefault();
    console.log('Handling community submission...');

    const formData = new FormData(e.target);
    const feedback = {
        feedback_type: formData.get('type'),
        company: formData.get('company'),
        content: formData.get('description'),
        user_id: currentUser?.id || 'anonymous'
    };

    if (!feedback.feedback_type || !feedback.company || !feedback.content) {
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

        console.log('Community submission result:', result);

        if (response.ok && result.success) {
            showMessage('Feedback submitted successfully!', 'success');
            e.target.reset();
            loadStatistics();
        } else {
            showMessage(result.error || result.message || 'Submission failed', 'error');
        }
    } catch (error) {
        hideLoading();
        console.error('Submission error:', error);
        showMessage('Network error. Please check if backend is running.', 'error');
    }
}

function displayAnalysisResults(result) {
    console.log('Displaying analysis results:', result);

    const resultsDiv = document.getElementById('analysisResults');
    if (!resultsDiv) {
        console.error('analysisResults div not found');
        return;
    }

    const riskScore = result.risk_score || 0;
    let riskLevel = 'Low';
    let riskColor = '#2ecc71';

    if (riskScore > 0.7) {
        riskLevel = 'High';
        riskColor = '#e74c3c';
    } else if (riskScore > 0.4) {
        riskLevel = 'Medium';
        riskColor = '#f39c12';
    }

    resultsDiv.innerHTML = `
        <div class="result-card">
            <h3>🔍 Analysis Results</h3>
            <div class="risk-indicator">
                <span>Risk Level: </span>
                <span style="color: ${riskColor}; font-weight: bold;">${riskLevel}</span>
                <span>(${Math.round(riskScore * 100)}%)</span>
            </div>
            <div class="summary">
                <h4>Summary:</h4>
                <p>${result.summary || 'Analysis completed successfully'}</p>
            </div>
            <div class="claims-found">
                <h4>Claims Detected: ${result.claims_count || 0}</h4>
            </div>
            ${result.blockchain_id ? `
                <div class="blockchain-info">
                    <h4>🔗 Blockchain Secured</h4>
                    <p>Verification ID: ${result.blockchain_id}</p>
                </div>
            ` : ''}
        </div>
    `;

    resultsDiv.style.display = 'block';
}

function displayVerificationResults(result) {
    console.log('Displaying verification results:', result);

    const resultsDiv = document.getElementById('verificationResults');
    if (!resultsDiv) {
        console.error('verificationResults div not found');
        return;
    }

    const verification = result.verification || {};
    const trustColor = result.trustworthy ? '#2ecc71' : '#e74c3c';
    const trustText = result.trustworthy ? 'Trustworthy' : 'Questionable';
    const score = verification.verification_score || 0;
    const scorePercentage = Math.round(score * 100);

    resultsDiv.innerHTML = `
        <div class="result-card">
            <h3>🔍 Verification Results</h3>
            <div class="trust-indicator">
                <span>Status: </span>
                <span style="color: ${trustColor}; font-weight: bold;">${trustText}</span>
                <span>(${scorePercentage}%)</span>
            </div>
            <div class="verification-summary">
                <h4>Analysis:</h4>
                <p>${result.analysis || 'Verification completed successfully'}</p>
            </div>
            <div class="evidence">
                <h4>Evidence:</h4>
                <ul>
                    ${(result.evidence || []).map(item => `<li>${item}</li>`).join('')}
                </ul>
            </div>
            ${result.blockchain_id ? `
                <div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 5px;">
                    <h4>🔗 Blockchain Secured</h4>
                    <p>Verification ID: ${result.blockchain_id}</p>
                    <p>Status: ${result.blockchain_secured ? '✅ Immutably Recorded' : '⚠️ Not secured'}</p>
                </div>
            ` : ''}
        </div>
    `;

    resultsDiv.style.display = 'block';
}

async function loadStatistics() {
    console.log('Loading statistics...');

    try {
        const response = await fetch(`${API_BASE_URL}/analytics/stats`);
        const stats = await response.json();

        console.log('Statistics loaded:', stats);

        if (response.ok && stats.success) {
            updateStatisticsDisplay(stats);
        } else {
            console.warn('Failed to load statistics:', stats);
            updateStatisticsDisplay({
                total_claims_analyzed: 0,
                companies_verified: 0,
                community_reports: 0,
                greenwashing_detected: 0
            });
        }
    } catch (error) {
        console.error('Statistics loading error:', error);
        updateStatisticsDisplay({
            total_claims_analyzed: 0,
            companies_verified: 0,
            community_reports: 0,
            greenwashing_detected: 0
        });
    }
}

function updateStatisticsDisplay(stats) {
    console.log('Updating statistics display:', stats);

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
            console.log(`Updated ${id}: ${value}`);
        } else {
            console.warn(`Element not found: ${id}`);
        }
    });
}

function showAuth() {
    console.log('Showing auth section');

    const authSection = document.getElementById('authSection');
    const dashboardSection = document.getElementById('dashboardSection');
    const userInfo = document.getElementById('userInfo');

    if (authSection) {
        authSection.style.display = 'block';
        console.log('Auth section shown');
    }

    if (dashboardSection) {
        dashboardSection.style.display = 'none';
    }

    if (userInfo) {
        userInfo.style.display = 'none';
    }

    showSignupForm();
}

function showDashboard() {
    console.log('Showing dashboard section');

    const authSection = document.getElementById('authSection');
    const dashboardSection = document.getElementById('dashboardSection');
    const userInfo = document.getElementById('userInfo');

    if (authSection) {
        authSection.style.display = 'none';
    }

    if (dashboardSection) {
        dashboardSection.style.display = 'block';
        console.log('Dashboard section shown');
    }

    if (userInfo && currentUser) {
        userInfo.style.display = 'flex';
        const userEmailSpan = document.getElementById('userEmail');
        if (userEmailSpan) {
            userEmailSpan.textContent = currentUser.email;
        }
    }

    switchTab('analyzer');

    loadStatistics();
}

function showSignupForm() {
    console.log('Showing signup form');

    const signupForm = document.getElementById('signupFormContainer');
    const signinForm = document.getElementById('signinFormContainer');

    if (signupForm) {
        signupForm.style.display = 'block';
    }

    if (signinForm) {
        signinForm.style.display = 'none';
    }
}

function showSigninForm() {
    console.log('Showing signin form');

    const signupForm = document.getElementById('signupFormContainer');
    const signinForm = document.getElementById('signinFormContainer');

    if (signupForm) {
        signupForm.style.display = 'none';
    }

    if (signinForm) {
        signinForm.style.display = 'block';
    }
}

async function handleLogout() {
    console.log('Handling logout');

    try {
        await chrome.storage.local.remove(['user']);
        currentUser = null;
        showAuth();
        showMessage('Logged out successfully', 'success');
    } catch (error) {
        console.error('Logout error:', error);
        showMessage('Logout failed', 'error');
    }
}

function showLoading(message) {
    console.log(`Loading: ${message}`);
}

function hideLoading() {
    console.log('Loading complete');
}

function showMessage(message, type) {
    console.log(`${type.toUpperCase()}: ${message}`);

    if (type === 'error') {
        alert(`Error: ${message}`);
    } else {
        alert(message);
    }
}

setInterval(loadStatistics, 30000);
