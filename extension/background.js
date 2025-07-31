const API_BASE_URL = 'http://localhost:5000/api';

const cache = new Map();
const CACHE_DURATION = 5 * 60 * 1000;

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('GreenGuard extension installed successfully');
    
    chrome.storage.sync.set({
      enabled: true,
      sensitivity: 'medium',
      showAlternatives: true,
      communityFeatures: true
    });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request.action);
  
  switch (request.action) {
    case 'analyzeClaims':
    case 'analyzePageClaims':
    case 'analyzePage':
      handleClaimAnalysis(request.data, sendResponse, sender);
      return true;
      
    case 'analyze_current_page':
      handleAnalyzeCurrentPage(sendResponse, sender);
      return true;
      
    case 'verifyClaims':
      handleVerification(request.data, sendResponse);
      return true;
      
    case 'getAlternatives':
      handleAlternatives(request.data, sendResponse);
      return true;
      
    case 'submitFeedback':
    case 'submitCommunityReport':
      handleFeedback(request.data, sendResponse);
      return true;
      
    case 'getSettings':
      handleGetSettings(sendResponse);
      return true;
      
    case 'getStats':
    case 'getStatistics':
      handleGetStats(sendResponse);
      return true;
  }
});

async function handleAnalyzeCurrentPage(sendResponse, sender) {
  try {
    console.log('🔍 Starting on-demand page analysis...');
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab) {
      sendResponse({ success: false, error: 'No active tab found' });
      return;
    }
    
    if (!tab.url.startsWith('http') && !tab.url.startsWith('https')) {
      sendResponse({ 
        success: false, 
        error: 'Cannot analyze special pages (chrome://, about:, etc.)' 
      });
      return;
    }
    
    console.log('📄 Analyzing tab:', tab.url);
    
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      files: ['content.js']
    });
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: executeOnDemandAnalysis
    });
    
    const analysisResult = results[0].result;
    
    if (analysisResult && analysisResult.success) {
      console.log('✅ On-demand analysis complete:', analysisResult);
      sendResponse(analysisResult);
    } else {
      console.log('❌ Analysis failed:', analysisResult);
      sendResponse({ 
        success: false, 
        error: analysisResult?.error || 'Analysis failed' 
      });
    }
    
  } catch (error) {
    console.error('❌ Error in on-demand analysis:', error);
    sendResponse({ 
      success: false, 
      error: error.message || 'Failed to analyze page' 
    });
  }
}

function executeOnDemandAnalysis() {
  return new Promise((resolve) => {
    try {
      if (typeof window.GreenGuardAnalyzer === 'undefined') {
        resolve({ 
          success: false, 
          error: 'GreenGuard analyzer not loaded' 
        });
        return;
      }
      
      const analyzer = new window.GreenGuardAnalyzer(true);
      
      const pageContent = analyzer.extractPageContent();
      
      if (pageContent.length < 10) {
        resolve({ 
          success: false, 
          error: 'Not enough content to analyze' 
        });
        return;
      }
      
      analyzer.analyzeContent(pageContent).then((result) => {
        resolve({
          success: true,
          data: {
            content_analyzed: pageContent.substring(0, 200) + '...',
            url: window.location.href,
            title: document.title,
            analysis_result: result?.data || {},
            claims_found: analyzer.detectedClaims.size
          }
        });
      }).catch((error) => {
        resolve({ 
          success: false, 
          error: error.message || 'Analysis failed' 
        });
      });
      
    } catch (error) {
      resolve({ 
        success: false, 
        error: error.message || 'Failed to execute analysis' 
      });
    }
  });
}

async function handleClaimAnalysis(data, sendResponse, sender) {
  try {
    console.log('🔍 Analyzing individual claims...');
    
    let textToAnalyze = data?.text;
    let sourceUrl = data?.url;
    
    if (!textToAnalyze && sender?.tab?.id) {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: sender.tab.id },
          function: extractPageContent
        });
        textToAnalyze = results[0]?.result;
        sourceUrl = sender.tab.url;
      } catch (error) {
        console.error('Error extracting page content:', error);
        textToAnalyze = 'Sample environmental content for testing';
      }
    }
    
    if (!textToAnalyze || textToAnalyze.length < 10) {
      sendResponse({ 
        success: false, 
        error: 'Not enough content to analyze' 
      });
      return;
    }
    const cacheKey = `claims_${hashString(textToAnalyze)}`;
    if (cache.has(cacheKey)) {
      const cached = cache.get(cacheKey);
      if (Date.now() - cached.timestamp < CACHE_DURATION) {
        console.log(' Returning cached analysis result');
        sendResponse({ success: true, data: cached.data });
        return;
      }
    }
    
    const response = await fetch(`${API_BASE_URL}/claims/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: textToAnalyze,
        url: sourceUrl || 'current_page',
        save_to_db: true
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    console.log(' Analysis result from Flask:', result);
    
    cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });
    
    cleanCache();
    
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('❌ Error analyzing claims:', error);
    
    const mockResult = createMockAnalysisResult(textToAnalyze);
    
    sendResponse({ 
      success: true, 
      data: mockResult,
      note: 'Using mock data - Flask server may be offline'
    });
  }
}

async function handleVerification(data, sendResponse) {
  try {
    console.log('🏢 Verifying company claims...');
    
    const response = await fetch(`${API_BASE_URL}/companies/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_name: data.company,
        claim_text: data.claim,
        save_to_db: true
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ Verification result:', result);
    
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('❌ Error verifying claims:', error);
    
    const mockResult = {
      success: true,
      company: data.company,
      claim: data.claim,
      verification_status: 'pending',
      sources: ['example.com']
    };
    
    sendResponse({ 
      success: true, 
      data: mockResult,
      note: 'Using mock data - Flask server may be offline'
    });
  }
}

async function handleFeedback(data, sendResponse) {
  try {
    console.log('📝 Submitting community report...');
    
    const response = await fetch(`${API_BASE_URL}/community/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        report_type: data.type || data.feedback_type,
        company_name: data.company,
        description: data.description || data.content,
        user_id: 'extension_user',
        save_to_db: true
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    console.log('✅ Community report result:', result);
    
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('❌ Error submitting feedback:', error);
    sendResponse({ 
      success: true, 
      data: { message: 'Report submitted successfully (mock response)' },
      note: 'Using mock response - Flask server may be offline'
    });
  }
}

async function handleAlternatives(data, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/alternatives/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        company_name: data.companyName,
        product_category: data.category || 'general'
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('Error getting alternatives:', error);
    const mockAlternatives = {
      success: true,
      alternatives: [
        {
          name: "EcoChoice",
          product: "Sustainable alternative product",
          sustainability_score: 0.85,
          certifications: ["Certified B Corp", "Carbon Neutral"],
          price_range: "$$",
          url: "https://example.com"
        }
      ]
    };
    
    sendResponse({ 
      success: true, 
      data: mockAlternatives,
      note: 'Using mock data - Flask server may be offline'
    });
  }
}

async function handleGetSettings(sendResponse) {
  try {
    const settings = await chrome.storage.sync.get([
      'enabled', 'sensitivity', 'showAlternatives', 'communityFeatures'
    ]);
    sendResponse({ success: true, data: settings });
  } catch (error) {
    console.error('Error getting settings:', error);
    sendResponse({ success: false, error: 'Failed to get settings' });
  }
}

async function handleGetStats(sendResponse) {
  try {
    console.log('📊 Fetching statistics from Flask MongoDB...');
    
    const response = await fetch(`${API_BASE_URL}/statistics`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (response.ok) {
      const flaskStats = await response.json();
      console.log('✅ Real Flask MongoDB stats:', flaskStats);
      
      sendResponse({ 
        success: true, 
        data: flaskStats,
        source: 'flask_mongodb'
      });
    } else {
      console.log('❌ Flask stats API not available');
      sendResponse({ 
        success: false, 
        error: 'Flask server not available',
        data: {
          claims_analyzed: 0,
          companies_verified: 0,
          community_reports: 0,
          greenwashing_detected: 0
        }
      });
    }
    
  } catch (error) {
    console.error('❌ Error getting stats:', error);
    sendResponse({ 
      success: false, 
      error: 'Failed to get stats',
      data: {
        claims_analyzed: 0,
        companies_verified: 0,
        community_reports: 0,
        greenwashing_detected: 0
      }
    });
  }
}

function extractPageContent() {
  const scripts = document.querySelectorAll('script, style, nav, footer');
  scripts.forEach(el => el.remove());
  
  const contentSelectors = [
    'main', 'article', '[role="main"]', '.content', '#content',
  ];
  
  let content = '';
  
  for (const selector of contentSelectors) {
    const element = document.querySelector(selector);
    if (element) {
      content = element.innerText;
      break;
    }
  }
  
  if (!content) {
    content = document.body.innerText;
  }
  
  return content
    .replace(/\s+/g, ' ')
    .replace(/\n+/g, '. ')
    .trim()
    .substring(0, 5000);
}

function createMockAnalysisResult(text) {
  return {
    success: true,
    claims_detected: 1,
    analysis_summary: {
      environmental_claims: 1,
      avg_risk_score: Math.random() * 0.5 + 0.3,
      high_risk_claims: Math.random() > 0.7 ? 1 : 0
    },
    claims: [{
      claim_text: text.substring(0, 100) + '...',
      greenwashing_risk: Math.random() * 0.5 + 0.3,
      confidence_score: Math.random() * 0.3 + 0.6,
      keyword: 'sustainable'
    }]
  };
}

function hashString(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString();
}

function cleanCache() {
  const now = Date.now();
  for (const [key, value] of cache.entries()) {
    if (now - value.timestamp > CACHE_DURATION) {
      cache.delete(key);
    }
  }
}

console.log('🚀 GreenGuard background script loaded - On-demand injection mode');