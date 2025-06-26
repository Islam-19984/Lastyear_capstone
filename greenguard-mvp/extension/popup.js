const API_BASE_URL = 'http://localhost:5000/api';
let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
  console.log('🚀 GreenGuard popup initializing...');
  
  try {
    const userData = await chrome.storage.local.get(['user']);
    if (userData.user) {
      currentUser = userData.user;
      console.log('👤 User loaded:', currentUser.email);
      showDashboard();
    } else {
      console.log('👤 No user found, showing auth screen');
      showAuth();
    }
    
    await initializeResponsiveDesign();
    setupEventListeners();
    injectEnhancedStyles();
    
    if (currentUser) {
      await loadStatistics();
    }
    
    console.log('✅ GreenGuard popup initialized successfully');
  } catch (error) {
    console.error('❌ Error initializing popup:', error);
    showAuth();
    setupEventListeners();
  }
});

async function initializeResponsiveDesign() {
  const container = document.querySelector('.container');
  if (!container) return;
  
  const width = window.innerWidth;
  const height = window.innerHeight;
  
  console.log(`📱 Responsive mode: ${width}x${height}`);
  
  container.classList.remove('mobile', 'tablet', 'desktop');
  
  if (width <= 480) {
    container.classList.add('mobile');
  } else if (width <= 768) {
    container.classList.add('tablet');
  } else {
    container.classList.add('desktop');
  }
  
  window.addEventListener('resize', () => {
    const newWidth = window.innerWidth;
    container.classList.remove('mobile', 'tablet', 'desktop');
    
    if (newWidth <= 480) {
      container.classList.add('mobile');
    } else if (newWidth <= 768) {
      container.classList.add('tablet');
    } else {
      container.classList.add('desktop');
    }
  });
}

function setupEventListeners() {
  console.log('🔧 Setting up event listeners...');
  
  const tabButtons = document.querySelectorAll('.tab-btn');
  console.log('📋 Found', tabButtons.length, 'tab buttons');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', (e) => {
      const tabName = e.target.dataset.tab;
      if (tabName) {
        switchTab(tabName);
      }
    });
  });
  
  setupFormListeners();
  setupWebsiteAnalysisListeners();
  setupAuthSwitchListeners();
  setupLogoutListener();
  
  console.log('✅ Event listeners setup complete');
}

function setupFormListeners() {
  const forms = [
    'signupForm',
    'signinForm', 
    'analysisForm',
    'verificationForm',
    'communityForm',
    'websiteAnalysisForm'
  ];
  
  forms.forEach(formId => {
    const form = document.getElementById(formId);
    if (form) {
      form.addEventListener('submit', handleFormSubmit);
      console.log('📝', formId, 'listener added');
    }
  });
}

function setupWebsiteAnalysisListeners() {
  const analyzeCurrentPageBtn = document.getElementById('analyzeCurrentPageBtn');
  if (analyzeCurrentPageBtn) {
    analyzeCurrentPageBtn.addEventListener('click', handleAnalyzeCurrentPage);
    console.log('🌐 Current page analysis listener added');
  }
}

function setupAuthSwitchListeners() {
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

function setupLogoutListener() {
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
    console.log('👋 Logout listener added');
  }
}

async function handleFormSubmit(e) {
  e.preventDefault();
  const formId = e.target.id;
  
  console.log('📝 Form submitted:', formId);
  
  try {
    switch (formId) {
      case 'signupForm':
        await handleSignup(e.target);
        break;
      case 'signinForm':
        await handleSignin(e.target);
        break;
      case 'analysisForm':
        await handleAnalysis(e.target);
        break;
      case 'verificationForm':
        await handleVerification(e.target);
        break;
      case 'communityForm':
        await handleCommunitySubmission(e.target);
        break;
      case 'websiteAnalysisForm':
        await handleWebsiteAnalysis(e.target);
        break;
    }
  } catch (error) {
    console.error('❌ Form submission error:', error);
    showNotification('❌ Error: ' + error.message, 'error');
  }
}

async function handleWebsiteAnalysis(form) {
  console.log('🌐 Starting website analysis...');
  
  const urlInput = form.querySelector('#websiteUrl');
  const submitBtn = form.querySelector('button[type="submit"]');
  const resultsDiv = document.getElementById('websiteAnalysisResults');
  
  if (!urlInput.value.trim()) {
    showNotification('Please enter a website URL', 'error');
    return;
  }
  
  if (submitBtn) {
    submitBtn.innerHTML = '<span class="loading-spinner"></span>Analyzing Website...';
    submitBtn.disabled = true;
  }
  
  if (resultsDiv) {
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div class="loading">🔄 Analyzing website...</div>';
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-website`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: urlInput.value.trim(),
        user_email: currentUser?.email || 'anonymous'
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Website analysis result:', result);
    
    if (result.success) {
      displayWebsiteAnalysisResults(result);
      await loadStatistics();
      showNotification('✅ Website analysis completed!', 'success');
    } else {
      throw new Error(result.error || 'Website analysis failed');
    }
    
  } catch (error) {
    console.error('❌ Website analysis error:', error);
    showWebsiteAnalysisError(error.message);
    showNotification('❌ Website analysis failed: ' + error.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.innerHTML = '🔍 Analyze Website';
      submitBtn.disabled = false;
    }
  }
}

async function handleAnalyzeCurrentPage() {
  console.log('📄 Analyzing current page...');
  
  const btn = document.getElementById('analyzeCurrentPageBtn');
  const urlInput = document.getElementById('websiteUrl');
  const resultsDiv = document.getElementById('websiteAnalysisResults');
  
  if (btn) {
    btn.innerHTML = '<span class="loading-spinner"></span>Analyzing Current Page...';
    btn.disabled = true;
  }
  
  if (resultsDiv) {
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = '<div class="loading">🔄 Analyzing current page...</div>';
  }
  
  try {
    const tabs = await chrome.tabs.query({active: true, currentWindow: true});
    const currentUrl = tabs[0].url;
    
    if (!currentUrl || currentUrl.startsWith('chrome://') || currentUrl.startsWith('chrome-extension://')) {
      throw new Error('Cannot analyze this page type');
    }
    
    if (urlInput) {
      urlInput.value = currentUrl;
    }
    
    const response = await fetch(`${API_BASE_URL}/analyze-website`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        url: currentUrl,
        user_email: currentUser?.email || 'anonymous'
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Current page analysis result:', result);
    
    if (result.success) {
      displayWebsiteAnalysisResults(result);
      await loadStatistics();
      showNotification('✅ Current page analysis completed!', 'success');
    } else {
      throw new Error(result.error || 'Current page analysis failed');
    }
    
  } catch (error) {
    console.error('❌ Current page analysis error:', error);
    showWebsiteAnalysisError(error.message);
    showNotification('❌ Analysis failed: ' + error.message, 'error');
  } finally {
    if (btn) {
      btn.innerHTML = '📄 Analyze Current Page';
      btn.disabled = false;
    }
  }
}

function displayWebsiteAnalysisResults(data) {
  console.log('📊 Displaying website analysis results:', data);

  const resultsDiv = document.getElementById('websiteAnalysisResults');
  if (!resultsDiv) {
    console.error('websiteAnalysisResults div not found');
    return;
  }

  const analysis = data.analysis;
  
  if (!analysis.has_environmental_content) {
    resultsDiv.innerHTML = `
      <div class="website-results">
        <h4>Website: ${data.website_url}</h4>
        <div class="no-content">
          <p>❌ ${analysis.message}</p>
        </div>
      </div>
    `;
    return;
  }

  let html = `
    <div class="website-results">
      <h4>Website: ${data.website_url}</h4>
      
      <div class="result-section">
        <h5>✅ Environmental Content Found</h5>
        <p><strong>Sustainability sections:</strong> ${analysis.sustainability_sections_count}</p>
        
        ${analysis.environmental_keywords_found && analysis.environmental_keywords_found.length > 0 ? `
          <div class="keywords">
            <strong>🌱 Environmental keywords found:</strong>
            <ul>
              ${analysis.environmental_keywords_found.map(keyword => 
                `<li>${keyword}</li>`
              ).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${analysis.potential_greenwashing_indicators && analysis.potential_greenwashing_indicators.length > 0 ? `
          <div class="warnings">
            <strong>⚠️ Potential concerns:</strong>
            <ul>
              ${analysis.potential_greenwashing_indicators.map(indicator => 
                `<li>${indicator}</li>`
              ).join('')}
            </ul>
          </div>
        ` : ''}
        
        ${analysis.transparency_indicators && analysis.transparency_indicators.length > 0 ? `
          <div class="transparency">
            <strong>✅ Transparency indicators:</strong>
            <ul>
              ${analysis.transparency_indicators.map(indicator => 
                `<li>${indicator}</li>`
              ).join('')}
            </ul>
          </div>
        ` : ''}

        ${data.content_summary ? `
          <div class="content-summary">
            <h5>📝 Content Summary:</h5>
            <p><strong>Title:</strong> ${data.content_summary.title || 'Not found'}</p>
            <p><strong>Sustainability sections found:</strong> ${data.content_summary.sustainability_sections_found}</p>
            <p><strong>Content length:</strong> ${data.content_summary.total_content_length} characters</p>
          </div>
        ` : ''}

        ${analysis.blockchain_id ? `
          <div class="blockchain-info">
            <h5>🔗 Blockchain Secured</h5>
            <p>Analysis ID: ${analysis.blockchain_id}</p>
          </div>
        ` : ''}
      </div>
    </div>
  `;
  
  resultsDiv.innerHTML = html;
  resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showWebsiteAnalysisError(message) {
  const resultsDiv = document.getElementById('websiteAnalysisResults');
  if (resultsDiv) {
    resultsDiv.style.display = 'block';
    resultsDiv.innerHTML = `<div class="error">❌ ${message}</div>`;
  }
}

async function handleAnalysis(form) {
  console.log('🔍 Starting analysis...');
  
  const textInput = form.querySelector('#analysisContent') || form.querySelector('textarea[name="content"]');
  const submitBtn = form.querySelector('button[type="submit"]');
  
  if (submitBtn) {
    submitBtn.textContent = '🔍 Analyzing...';
    submitBtn.disabled = true;
  }
  
  try {
    let analysisResult;
    
    if (textInput && textInput.value.trim()) {
      console.log('📝 Analyzing provided text');
      analysisResult = await analyzeProvidedText(textInput.value.trim());
    } else {
      console.log('🌐 Requesting on-demand page analysis');
      analysisResult = await requestPageAnalysis();
    }
    
    if (analysisResult && analysisResult.success) {
      showAnalysisResults(analysisResult.data || analysisResult);
      await loadStatistics();
      showNotification('✅ Analysis completed successfully!', 'success');
    } else {
      throw new Error(analysisResult?.error || 'Analysis failed');
    }
    
  } catch (error) {
    console.error('❌ Analysis error:', error);
    showNotification('❌ Analysis failed: ' + error.message, 'error');
  } finally {
    if (submitBtn) {
      submitBtn.textContent = '🤖 Analyze Claims';
      submitBtn.disabled = false;
    }
  }
}

async function requestPageAnalysis() {
  return new Promise((resolve) => {
    console.log('📨 Requesting on-demand page analysis...');
    
    chrome.runtime.sendMessage(
      { action: 'analyze_current_page' },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error('❌ Background script error:', chrome.runtime.lastError);
          resolve({ 
            success: false, 
            error: chrome.runtime.lastError.message 
          });
        } else {
          console.log('✅ Page analysis response:', response);
          resolve(response);
        }
      }
    );
  });
}

function extractEnvironmentalClaimsFromText(text) {
  if (!text || typeof text !== 'string') {
    return [];
  }
  
  const claims = [];
  const sentences = text.split(/[.!?]+/).map(s => s.trim()).filter(s => s.length > 10);
  
  const environmentalPatterns = [
    /\b(100%|completely|fully|entirely)\s+(recyclable|biodegradable|sustainable|eco-friendly|green|renewable)\b/gi,
    /\b(carbon|co2)\s+(neutral|negative|free|zero|offset)\b/gi,
    /\bzero\s+(waste|emission|carbon|impact)\b/gi,
    /\b(renewable|clean|solar|wind|hydro)\s+(energy|power)\b/gi,
    /\b(organic|natural|chemical-free|non-toxic)\b/gi,
    /\b(sustainable|sustainably)\s+(sourced|produced|made|grown|harvested)\b/gi,
    /\benvironmentally\s+(friendly|responsible|conscious|safe)\b/gi,
    /\beco-friendly\b/gi,
    /\bbiodegradable\b/gi,
    /\brecyclable\b/gi,
    /\bcarbon\s+footprint\b/gi,
    /\bgreen\s+(technology|innovation|solution|product|manufacturing)\b/gi,
    /\b(reduce|reducing|reduces)\s+(carbon|emissions|waste|impact)\b/gi,
    /\b(protect|protecting|preservation)\s+(environment|planet|earth|nature)\b/gi,
    /\bclimate\s+(friendly|neutral|positive|action)\b/gi,
    /\benergy\s+efficient\b/gi,
    /\bwater\s+(conservation|saving|efficient)\b/gi,
    /\bwaste\s+(reduction|minimization|management)\b/gi,
    /\bsustainability\s+(commitment|initiative|program|goal)\b/gi
  ];
  
  sentences.forEach(sentence => {
    environmentalPatterns.forEach(pattern => {
      if (pattern.test(sentence)) {
        const cleanSentence = sentence.replace(/^\W+|\W+$/g, '').trim();
        if (cleanSentence.length > 20 && !claims.some(claim => claim.text === cleanSentence)) {
          claims.push({
            text: cleanSentence,
            confidence: 0.85,
            type: 'environmental_statement'
          });
        }
      }
    });
  });
  
  if (claims.length === 0) {
    const environmentalKeywords = [
      'sustainable', 'eco-friendly', 'green', 'renewable', 'biodegradable',
      'carbon neutral', 'zero waste', 'organic', 'recyclable', 'clean energy',
      'environmental', 'climate', 'planet', 'earth-friendly', 'natural',
      'emission', 'footprint', 'conservation', 'preservation'
    ];
    
    sentences.forEach(sentence => {
      const lowerSentence = sentence.toLowerCase();
      const keywordCount = environmentalKeywords.filter(keyword => 
        lowerSentence.includes(keyword.toLowerCase())
      ).length;
      
      if (keywordCount > 0 && sentence.length > 25) {
        const cleanSentence = sentence.replace(/^\W+|\W+$/g, '').trim();
        if (!claims.some(claim => claim.text === cleanSentence)) {
          claims.push({
            text: cleanSentence,
            confidence: Math.min(0.9, 0.5 + (keywordCount * 0.1)),
            type: 'environmental_mention'
          });
        }
      }
    });
  }
  
  return claims;
}

function transformApiResponse(apiResult) {
  console.log('🔄 Transforming API result:', apiResult);
  
  if (apiResult.detected_claims && Array.isArray(apiResult.detected_claims) && 
      apiResult.detected_claims.length > 0 && 
      apiResult.detected_claims[0].text && 
      !apiResult.detected_claims[0].text.includes('Environmental claim')) {
    return apiResult;
  }
  
  const transformed = {
    detected_claims: [],
    environmental_claims: [],
    risk_level: 'unknown',
    risk_percentage: 0,
    summary: '',
    keywords: [],
    greenwashing_indicators: []
  };
  
  let summaryText = '';
  if (apiResult.summary && typeof apiResult.summary === 'string') {
    summaryText = apiResult.summary;
  } else if (apiResult.analysis_summary && typeof apiResult.analysis_summary === 'string') {
    summaryText = apiResult.analysis_summary;
  } else if (apiResult.summary && typeof apiResult.summary === 'object') {
    summaryText = JSON.stringify(apiResult.summary);
  } else {
    summaryText = 'Analysis completed successfully';
  }
  transformed.summary = summaryText;
  
  let claims = [];
  
  if (apiResult.claims && Array.isArray(apiResult.claims)) {
    claims.push(...apiResult.claims);
  }
  if (apiResult.analysis_result && apiResult.analysis_result.claims && Array.isArray(apiResult.analysis_result.claims)) {
    claims.push(...apiResult.analysis_result.claims);
  }
  if (apiResult.environmental_claims && Array.isArray(apiResult.environmental_claims)) {
    claims.push(...apiResult.environmental_claims);
  }
  if (apiResult.detected_claims && Array.isArray(apiResult.detected_claims)) {
    claims.push(...apiResult.detected_claims);
  }
  
  if (apiResult.analysis_result) {
    const analysisResult = apiResult.analysis_result;
    
    if (analysisResult.detected_environmental_claims) {
      claims.push(...analysisResult.detected_environmental_claims);
    }
    if (analysisResult.environmental_statements) {
      claims.push(...analysisResult.environmental_statements);
    }
    if (analysisResult.sustainability_claims) {
      claims.push(...analysisResult.sustainability_claims);
    }
  }

  if (apiResult.content_analyzed && typeof apiResult.content_analyzed === 'string') {
    console.log('📝 Extracting claims from content_analyzed:', apiResult.content_analyzed.substring(0, 200) + '...');
    const extractedClaims = extractEnvironmentalClaimsFromText(apiResult.content_analyzed);
    console.log('🔍 Extracted claims from content_analyzed:', extractedClaims);
    claims.push(...extractedClaims);
  }
  
  if (apiResult.original_input_text && typeof apiResult.original_input_text === 'string') {
    console.log('📝 Extracting claims from original input text');
    const extractedClaims = extractEnvironmentalClaimsFromText(apiResult.original_input_text);
    console.log('🔍 Extracted claims from input text:', extractedClaims);
    claims.push(...extractedClaims);
  }
  
  if (apiResult.text && typeof apiResult.text === 'string') {
    console.log('📝 Extracting claims from original text field');
    const extractedClaims = extractEnvironmentalClaimsFromText(apiResult.text);
    console.log('🔍 Extracted claims from text field:', extractedClaims);
    claims.push(...extractedClaims);
  }
  
  const claimsCount = apiResult.claims_found || apiResult.claims_detected || 0;
  console.log(`📊 Claims found in API: ${claimsCount}, Claims extracted: ${claims.length}`);
  
  if (claims.length > 0 && claims.some(claim => 
    (typeof claim === 'string' && claim.length > 20 && !claim.includes('Environmental claim')) ||
    (typeof claim === 'object' && claim.text && claim.text.length > 20 && !claim.text.includes('Environmental claim'))
  )) {
    const realClaims = claims.filter(claim => {
      const text = typeof claim === 'string' ? claim : claim.text;
      return text && text.length > 20 && !text.includes('Environmental claim');
    });
    
    transformed.detected_claims = realClaims.map((claim, index) => {
      if (typeof claim === 'string') {
        return {
          text: claim,
          confidence: 0.8,
          type: 'environmental'
        };
      } else {
        return {
          text: claim.text || `Environmental statement ${index + 1}`,
          confidence: claim.confidence || 0.8,
          type: claim.type || 'environmental'
        };
      }
    });
  } else {
    if (claimsCount > 0) {
      transformed.detected_claims = [{
        text: `${claimsCount} environmental claims were detected in the text, but the API doesn't provide the specific claim details. The analysis identified environmental content but detailed extraction requires API enhancement.`,
        confidence: 0.7,
        type: 'api_limitation'
      }];
    } else {
      transformed.detected_claims = [{
        text: "No specific environmental claims could be extracted from the analyzed content.",
        confidence: 0.5,
        type: 'no_claims'
      }];
    }
  }
  
  let riskScore = 0;
  if (apiResult.risk_score !== undefined && apiResult.risk_score !== null) {
    riskScore = apiResult.risk_score;
  } else if (apiResult.avg_risk_score !== undefined && apiResult.avg_risk_score !== null) {
    riskScore = apiResult.avg_risk_score;
  } else if (apiResult.analysis_result && apiResult.analysis_result.risk_score !== undefined) {
    riskScore = apiResult.analysis_result.risk_score;
  } else {
    if (claimsCount > 10) {
      riskScore = 0.7;
    } else if (claimsCount > 5) {
      riskScore = 0.4;
    } else if (claimsCount > 0) {
      riskScore = 0.2;
    }
  }
  
  transformed.risk_percentage = Math.round(riskScore * 100);
  if (riskScore < 0.3) {
    transformed.risk_level = 'low';
  } else if (riskScore < 0.7) {
    transformed.risk_level = 'medium';
  } else {
    transformed.risk_level = 'high';
  }
  
  if (apiResult.keywords && Array.isArray(apiResult.keywords)) {
    transformed.keywords = apiResult.keywords;
  } else if (apiResult.analysis_result && apiResult.analysis_result.keywords) {
    transformed.keywords = apiResult.analysis_result.keywords;
  }

  if (apiResult.greenwashing_indicators && Array.isArray(apiResult.greenwashing_indicators)) {
    transformed.greenwashing_indicators = apiResult.greenwashing_indicators;
  } else if (apiResult.potential_greenwashing_indicators && Array.isArray(apiResult.potential_greenwashing_indicators)) {
    transformed.greenwashing_indicators = apiResult.potential_greenwashing_indicators;
  } else if (apiResult.analysis_result && apiResult.analysis_result.greenwashing_indicators) {
    transformed.greenwashing_indicators = apiResult.analysis_result.greenwashing_indicators;
  }
  
  console.log('✅ Transformation complete:', transformed);
  return transformed;
}

function testEnhancedDisplay() {
  const testData = {
    detected_claims: [
      {
        text: "100% recyclable packaging materials",
        confidence: 0.85,
        type: "packaging"
      },
      {
        text: "Carbon neutral manufacturing process",
        confidence: 0.92,
        type: "manufacturing"
      },
      {
        text: "Sustainably sourced raw materials",
        confidence: 0.78,
        type: "sourcing"
      },
      {
        text: "Zero waste to landfill policy",
        confidence: 0.88,
        type: "waste_management"
      }
    ],
    environmental_claims: [],
    risk_level: "low",
    risk_percentage: 15,
    summary: "Analysis found several environmental claims with good confidence levels.",
    keywords: ["recyclable", "carbon neutral", "sustainable", "zero waste"],
    greenwashing_indicators: ["Vague language used in claim 3"]
  };
  
  displayTextAnalysisResults(testData);
}

async function analyzeProvidedText(text) {
  try {
    console.log('📝 Analyzing provided text directly');
    console.log('📄 Input text:', text.substring(0, 200) + '...');
    
    const response = await fetch(`${API_BASE_URL}/claims/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: text,
        url: 'user_provided_text',
        save_to_db: true,
        timestamp: new Date().toISOString()
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const result = await response.json();
    
    console.log('🔍 FULL API RESPONSE:', JSON.stringify(result, null, 2));
    console.log('🔍 Claims detected:', result.detected_claims);
    console.log('🔍 Environmental claims:', result.environmental_claims);
    console.log('🔍 Claims found:', result.claims_found);
    console.log('🔍 Content analyzed:', result.content_analyzed);
    console.log('🔍 All properties:', Object.keys(result));

    result.original_input_text = text;

    const transformedResult = transformApiResponse(result);
    console.log('🔄 Transformed result:', transformedResult);
    
    return { success: true, data: transformedResult };

  } catch (error) {
    console.error('❌ Text analysis error:', error);
    return { success: false, error: error.message };
  }
}

function showAnalysisResults(result) {
  console.log('📊 Displaying analysis results:', result);

  const resultsDiv = document.getElementById('analysisResults');
  if (!resultsDiv) {
    console.error('analysisResults div not found');
    return;
  }

  if (result.detected_claims || result.environmental_claims) {
    displayTextAnalysisResults(result);
    return;
  }

  const analysis = result.analysis_result || result;
  const riskScore = analysis.risk_score || analysis.avg_risk_score || 0;
  const claimsCount = result.claims_found || analysis.claims_detected || analysis.environmental_claims || 0;
  const summary = analysis.summary || analysis.analysis_summary || 'Analysis completed successfully';
  
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
      
      <div class="claims-found">
        <h4>Environmental Claims Detected: ${claimsCount}</h4>
      </div>
      
      ${result.content_analyzed ? `
        <div class="content-preview">
          <h4>Content Analyzed:</h4>
          <p style="font-size: 12px; color: #666; background: #f5f5f5; padding: 8px; border-radius: 4px;">
            ${result.content_analyzed}
          </p>
        </div>
      ` : ''}
      
      <div class="summary">
        <h4>Summary:</h4>
        <p>${typeof summary === 'string' ? summary : 'Analysis completed successfully'}</p>
      </div>
      
      ${result.url ? `
        <div class="source-info">
          <h4>Source:</h4>
          <p style="font-size: 12px; color: #666;">${result.url}</p>
        </div>
      ` : ''}
      
      ${analysis.blockchain_id ? `
        <div class="blockchain-info">
          <h4>🔗 Blockchain Secured</h4>
          <p>Verification ID: ${analysis.blockchain_id}</p>
        </div>
      ` : ''}
    </div>
  `;

  resultsDiv.style.display = 'block';
  resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function displayTextAnalysisResults(analysis) {
  const resultsDiv = document.getElementById('analysisResults');
  
  if (!analysis || analysis.error) {
    resultsDiv.innerHTML = `
      <div class="error-message">
        <span class="error-icon">⚠️</span>
        ${analysis?.error || 'Analysis failed'}
      </div>
    `;
    return;
  }

  const detectedClaims = analysis.detected_claims || [];
  const environmentalClaims = analysis.environmental_claims || [];
  const allClaims = [...detectedClaims, ...environmentalClaims];

  const riskLevel = analysis.risk_level || 'unknown';
  const riskColor = getRiskColor(riskLevel);
  const riskPercentage = analysis.risk_percentage || 0;

  let claimsListHTML = '';
  
  if (allClaims.length > 0) {
    claimsListHTML = `
      <div class="claims-section">
        <h4>🔍 Environmental Claims Found:</h4>
        <div class="claims-list">
          ${allClaims.map((claim, index) => `
            <div class="claim-item">
              <span class="claim-number">${index + 1}.</span>
              <div class="claim-content">
                <div class="claim-text">"${claim.text || claim}"</div>
                ${claim.confidence ? `
                  <div class="claim-confidence">
                    <span class="confidence-label">Confidence:</span>
                    <span class="confidence-value">${(claim.confidence * 100).toFixed(1)}%</span>
                  </div>
                ` : ''}
                ${claim.type ? `
                  <div class="claim-type">
                    <span class="type-label">Type:</span>
                    <span class="type-value">${claim.type}</span>
                  </div>
                ` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  } else {
    claimsListHTML = `
      <div class="no-claims-section">
        <span class="no-claims-icon">🌱</span>
        <span class="no-claims-text">No specific environmental claims detected in this text.</span>
      </div>
    `;
  }

  resultsDiv.innerHTML = `
    <div class="analysis-results active">
      <div class="result-header">
        <span class="result-icon">🔍</span>
        <span class="result-title">Analysis Results</span>
      </div>
      
      <div class="risk-section">
        <div class="risk-level">
          <span class="risk-label">Risk Level:</span>
          <span class="risk-value" style="color: ${riskColor}; font-weight: bold;">
            ${riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)} (${riskPercentage}%)
          </span>
        </div>
      </div>

      <div class="claims-count-section">
        <div class="claims-count">
          <span class="count-icon">📊</span>
          <span class="count-text">Environmental Claims Detected: </span>
          <span class="count-number">${allClaims.length}</span>
        </div>
      </div>

      ${claimsListHTML}

      ${analysis.summary ? `
        <div class="summary-section">
          <h4>📋 Summary:</h4>
          <div class="summary-content">${analysis.summary}</div>
        </div>
      ` : ''}

      ${analysis.keywords && analysis.keywords.length > 0 ? `
        <div class="keywords-section">
          <h4>🏷️ Environmental Keywords Found:</h4>
          <div class="keywords-list">
            ${analysis.keywords.map(keyword => `
              <span class="keyword-tag">${keyword}</span>
            `).join('')}
          </div>
        </div>
      ` : ''}

      ${analysis.greenwashing_indicators && analysis.greenwashing_indicators.length > 0 ? `
        <div class="greenwashing-section">
          <h4>⚠️ Potential Greenwashing Indicators:</h4>
          <div class="indicators-list">
            ${analysis.greenwashing_indicators.map(indicator => `
              <div class="indicator-item">
                <span class="indicator-icon">⚠️</span>
                <span class="indicator-text">${indicator}</span>
              </div>
            `).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;

  resultsDiv.style.display = 'block';
  resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function getRiskColor(riskLevel) {
  switch (riskLevel.toLowerCase()) {
    case 'low': return '#22c55e';
    case 'medium': return '#f59e0b';
    case 'high': return '#ef4444';
    default: return '#6b7280';
  }
}

const enhancedAnalysisStyles = `
  .claims-section {
    margin: 15px 0;
    padding: 15px;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 4px solid #3b82f6;
  }

  .claims-section h4 {
    margin: 0 0 12px 0;
    color: #1e40af;
    font-size: 14px;
    font-weight: 600;
  }

  .claims-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .claim-item {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
    background: white;
    border-radius: 6px;
    border: 1px solid #e2e8f0;
    transition: all 0.2s ease;
  }

  .claim-item:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
  }

  .claim-number {
    background: #3b82f6;
    color: white;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: bold;
    flex-shrink: 0;
    margin-top: 2px;
  }

  .claim-content {
    flex: 1;
  }

  .claim-text {
    font-size: 13px;
    color: #374151;
    line-height: 1.4;
    margin-bottom: 6px;
    font-style: italic;
  }

  .claim-confidence, .claim-type {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    margin-bottom: 4px;
  }

  .confidence-label, .type-label {
    color: #6b7280;
    font-weight: 500;
  }

  .confidence-value {
    color: #059669;
    font-weight: 600;
  }

  .type-value {
    color: #7c3aed;
    font-weight: 600;
    text-transform: capitalize;
  }

  .no-claims-section {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 20px;
    background: #f0fdf4;
    border-radius: 8px;
    border: 1px solid #bbf7d0;
    margin: 15px 0;
  }

  .no-claims-icon {
    font-size: 18px;
  }

  .no-claims-text {
    color: #166534;
    font-size: 13px;
  }

  .claims-count-section {
    margin: 12px 0;
    padding: 12px;
    background: #eff6ff;
    border-radius: 6px;
    border: 1px solid #bfdbfe;
  }

  .claims-count {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
  }

  .count-icon {
    font-size: 14px;
  }

  .count-text {
    color: #374151;
    font-weight: 500;
  }

  .count-number {
    background: #3b82f6;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: bold;
    font-size: 12px;
  }

  .keywords-section {
    margin: 15px 0;
    padding: 12px;
    background: #fefce8;
    border-radius: 6px;
    border: 1px solid #fde047;
  }

  .keywords-section h4 {
    margin: 0 0 8px 0;
    color: #a16207;
    font-size: 12px;
    font-weight: 600;
  }

  .keywords-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .keyword-tag {
    background: #fbbf24;
    color: #92400e;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
  }

  .greenwashing-section {
    margin: 15px 0;
    padding: 12px;
    background: #fef2f2;
    border-radius: 6px;
    border: 1px solid #fecaca;
  }

  .greenwashing-section h4 {
    margin: 0 0 8px 0;
    color: #dc2626;
    font-size: 12px;
    font-weight: 600;
  }

  .indicators-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .indicator-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
  }

  .indicator-icon {
    font-size: 14px;
  }

  .indicator-text {
    color: #dc2626;
    font-weight: 500;
  }

  .summary-section {
    margin: 15px 0;
    padding: 12px;
    background: #f1f5f9;
    border-radius: 6px;
    border: 1px solid #cbd5e1;
  }

  .summary-section h4 {
    margin: 0 0 8px 0;
    color: #475569;
    font-size: 12px;
    font-weight: 600;
  }

  .summary-content {
    color: #374151;
    font-size: 12px;
    line-height: 1.4;
  }

  .error-message {
    padding: 16px;
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 8px;
    margin: 15px 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .error-icon {
    font-size: 16px;
    color: #dc2626;
  }

  .result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e2e8f0;
  }

  .result-icon {
    font-size: 16px;
  }

  .result-title {
    font-weight: 600;
    color: #374151;
  }

  .risk-section {
    margin: 15px 0;
    padding: 12px;
    background: #f9fafb;
    border-radius: 6px;
    border: 1px solid #e5e7eb;
  }

  .risk-level {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
  }

  .risk-label {
    color: #374151;
    font-weight: 500;
  }
`;

function injectEnhancedStyles() {
  const existingStyle = document.getElementById('enhanced-analysis-styles');
  if (!existingStyle) {
    const styleElement = document.createElement('style');
    styleElement.id = 'enhanced-analysis-styles';
    styleElement.textContent = enhancedAnalysisStyles;
    document.head.appendChild(styleElement);
  }
}

async function handleSignup(form) {
  console.log('👤 Handling signup...');

  const formData = new FormData(form);
  const userData = {
    email: formData.get('email'),
    password: formData.get('password'),
    confirmPassword: formData.get('confirmPassword')
  };

  if (userData.password !== userData.confirmPassword) {
    showNotification('Passwords do not match', 'error');
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
      showNotification('Account created successfully!', 'success');
      showDashboard();
    } else {
      showNotification(result.error || result.message || 'Registration failed', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Registration error:', error);
    showNotification('Network error. Please check if backend is running.', 'error');
  }
}

async function handleSignin(form) {
  console.log('🔐 Handling signin...');

  const formData = new FormData(form);
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
      showNotification('Welcome back!', 'success');
      showDashboard();
    } else {
      showNotification(result.error || result.message || 'Login failed', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Login error:', error);
    showNotification('Network error. Please check if backend is running.', 'error');
  }
}

async function handleVerification(form) {
  console.log('✅ Handling verification...');

  const formData = new FormData(form);
  const company = formData.get('company');
  const claim = formData.get('claim');

  if (!company || !company.trim() || !claim || !claim.trim()) {
    showNotification('Please enter both company name and claim', 'error');
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
        user_email: currentUser?.email || 'anonymous',
        save_to_db: true
      })
    });

    const result = await response.json();
    hideLoading();

    console.log('Verification result:', result);

    if (response.ok && result.success) {
      displayVerificationResults(result);
      await loadStatistics();
      showNotification('Verification completed!', 'success');
    } else {
      showNotification(result.error || result.message || 'Verification failed', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Verification error:', error);
    showNotification('Network error. Please check if backend is running.', 'error');
  }
}

async function handleCommunitySubmission(form) {
  console.log('📝 Handling community submission...');

  const formData = new FormData(form);
  const feedback = {
    feedback_type: formData.get('type'),
    company: formData.get('company'),
    content: formData.get('description'),
    user_id: currentUser?.id || 'anonymous'
  };

  if (!feedback.feedback_type || !feedback.company || !feedback.content) {
    showNotification('Please fill in all fields', 'error');
    return;
  }

  try {
    showLoading('Submitting feedback...');

    const response = await fetch(`${API_BASE_URL}/community/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        ...feedback,
        save_to_db: true
      })
    });

    const result = await response.json();
    hideLoading();

    console.log('Community submission result:', result);

    if (response.ok && result.success) {
      showNotification('Feedback submitted successfully!', 'success');
      form.reset();
      await loadStatistics();
    } else {
      showNotification(result.error || result.message || 'Submission failed', 'error');
    }
  } catch (error) {
    hideLoading();
    console.error('Submission error:', error);
    showNotification('Network error. Please check if backend is running.', 'error');
  }
}

function displayVerificationResults(result) {
  console.log('📊 Displaying verification results:', result);

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
        <div class="blockchain-info">
          <h4>🔗 Blockchain Secured</h4>
          <p>Verification ID: ${result.blockchain_id}</p>
          <p>Status: ${result.blockchain_secured ? '✅ Immutably Recorded' : '⚠️ Not secured'}</p>
        </div>
      ` : ''}
    </div>
  `;

  resultsDiv.style.display = 'block';
  resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function loadStatistics() {
  console.log('📊 Loading statistics...');

  try {
    const response = await fetch(`${API_BASE_URL}/statistics`);
    
    if (!response.ok) {
      throw new Error(`Statistics API error: ${response.status}`);
    }
    
    const stats = await response.json();
    console.log('📈 Statistics loaded:', stats);

    updateStatisticsDisplay(stats);
    updateConnectionStatus('Connected');

  } catch (error) {
    console.error('❌ Statistics loading error:', error);
    
    updateStatisticsDisplay({
      claims_analyzed: 0,
      companies_verified: 0,
      websites_analyzed: 0,
      community_reports: 0,
      greenwashing_detected: 0
    });
    updateConnectionStatus('Disconnected');
  }
}

function updateStatisticsDisplay(stats) {
  console.log('📈 Updating statistics display:', stats);

  const statElements = {
    claimsAnalyzed: stats.claims_analyzed || 0,
    companiesVerified: stats.companies_verified || 0,
    websitesAnalyzed: stats.websites_analyzed || 0, // New website analysis stat
    communityReports: stats.community_reports || 0,
    greenwashingDetected: stats.greenwashing_detected || 0
  };

  Object.entries(statElements).forEach(([key, value]) => {
    const element = document.getElementById(key);
    if (element) {
      animateNumber(element, parseInt(element.textContent) || 0, value);
      console.log('📊 Updated', key + ':', value);
    }
  });
}

function animateNumber(element, start, end) {
  const duration = 1000;
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    const current = Math.round(start + (end - start) * progress);
    element.textContent = current;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  requestAnimationFrame(update);
}

function updateConnectionStatus(status) {
  const statusElement = document.getElementById('connectionStatus');
  if (statusElement) {
    statusElement.textContent = status;
    statusElement.className = `connection-status ${status.toLowerCase()}`;
    console.log('🌐 Connection status:', status);
  }
}

function switchTab(tabName) {
  console.log('🔄 Switching to tab:', tabName);
  
  const tabContents = document.querySelectorAll('.tab-content');
  tabContents.forEach(content => {
    content.classList.remove('active');
  });
  
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(button => {
    button.classList.remove('active');
  });
  
  const selectedContent = document.getElementById(tabName + 'Tab');
  if (selectedContent) {
    selectedContent.classList.add('active');
    console.log('✅ Tab content shown:', tabName + 'Tab');
  }
  
  const selectedButton = document.querySelector(`[data-tab="${tabName}"]`);
  if (selectedButton) {
    selectedButton.classList.add('active');
  }
  
  if (tabName === 'dashboard') {
    loadStatistics();
  }
}

function showDashboard() {
  console.log('📊 Showing dashboard section');
  
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

function showAuth() {
  console.log('👤 Showing auth section');

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

function showSignupForm() {
  console.log('📝 Showing signup form');

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
  console.log('🔐 Showing signin form');

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
  console.log('👋 Handling logout');

  try {
    await chrome.storage.local.remove(['user']);
    currentUser = null;
    showAuth();
    showNotification('Logged out successfully', 'success');
  } catch (error) {
    console.error('Logout error:', error);
    showNotification('Logout failed', 'error');
  }
}

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  const notificationStyle = notification.style;
  notificationStyle.position = 'fixed';
  notificationStyle.top = '20px';
  notificationStyle.right = '20px';
  notificationStyle.padding = '12px 20px';
  notificationStyle.borderRadius = '8px';
  notificationStyle.zIndex = '10000';
  notificationStyle.maxWidth = '300px';
  notificationStyle.fontSize = '14px';
  notificationStyle.fontWeight = '500';
  notificationStyle.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
  
  if (type === 'success') {
    notificationStyle.backgroundColor = '#d4edda';
    notificationStyle.color = '#155724';
    notificationStyle.border = '1px solid #c3e6cb';
  } else if (type === 'error') {
    notificationStyle.backgroundColor = '#f8d7da';
    notificationStyle.color = '#721c24';
    notificationStyle.border = '1px solid #f5c6cb';
  } else {
    notificationStyle.backgroundColor = '#d1ecf1';
    notificationStyle.color = '#0c5460';
    notificationStyle.border = '1px solid #bee5eb';
  }
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    if (notification.parentNode) {
      notification.parentNode.removeChild(notification);
    }
  }, 4000);
}

function showLoading(message) {
  console.log(`⏳ Loading: ${message}`);
}

function hideLoading() {
  console.log('✅ Loading complete');
}

console.log('🚀 GreenGuard responsive popup script loaded');