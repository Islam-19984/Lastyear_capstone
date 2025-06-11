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
    
    chrome.storage.local.set({
      'greenguard_stats': {
        totalAnalyzed: 0,
        claimsDetected: 0,
        lastAnalysis: null
      }
    });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'analyzeClaims':
    case 'analyzePageClaims':
      handleClaimAnalysis(request.data, sendResponse, sender);
      return true;
      
    case 'getAlternatives':
      handleAlternatives(request.data, sendResponse);
      return true;
      
    case 'submitFeedback':
      handleFeedback(request.data, sendResponse);
      return true;
      
    case 'getSettings':
      handleGetSettings(sendResponse);
      return true;
      
    case 'getStats':
      handleGetStats(sendResponse);
      return true;
  }
});

async function handleClaimAnalysis(data, sendResponse, sender) {
  try {
    let textToAnalyze = data?.text;
    
    if (!textToAnalyze && sender?.tab?.id) {
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: sender.tab.id },
          function: extractPageContent
        });
        textToAnalyze = results[0]?.result;
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
        url: data?.url || 'current_page'
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    
    cache.set(cacheKey, {
      data: result,
      timestamp: Date.now()
    });
    
    updateStats(result);
    
    cleanCache();
    
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('Error analyzing claims:', error);
    
    const mockResult = {
      success: true,
      claims_detected: Math.floor(Math.random() * 5) + 1,
      analysis_summary: {
        environmental_claims: Math.floor(Math.random() * 3) + 1,
        avg_risk_score: Math.random() * 0.8 + 0.1,
        high_risk_claims: Math.floor(Math.random() * 2)
      }
    };
    
    sendResponse({ 
      success: true, 
      data: mockResult,
      note: 'Using mock data - check if Flask server is running'
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
          name: "EcoBrand Example",
          product: "Sustainable Alternative",
          sustainability_score: 0.85,
          certifications: ["Certified B Corp", "Carbon Neutral"]
        }
      ]
    };
    
    sendResponse({ 
      success: true, 
      data: mockAlternatives,
      note: 'Using mock data - check if Flask server is running'
    });
  }
}

async function handleFeedback(data, sendResponse) {
  try {
    const response = await fetch(`${API_BASE_URL}/community/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        claim_id: data.claim_id || 'test-claim',
        feedback_type: data.feedback_type,
        content: data.content,
        user_id: 'extension_user'
      })
    });
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status}`);
    }
    
    const result = await response.json();
    sendResponse({ success: true, data: result });
    
  } catch (error) {
    console.error('Error submitting feedback:', error);
    sendResponse({ 
      success: true, 
      data: { message: 'Feedback received (mock response)' },
      note: 'Using mock response - check if Flask server is running'
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
    chrome.storage.local.get('greenguard_stats', (result) => {
      const stats = result.greenguard_stats || {
        totalAnalyzed: 0,
        claimsDetected: 0,
        lastAnalysis: null
      };
      sendResponse({ success: true, data: stats });
    });
  } catch (error) {
    console.error('Error getting stats:', error);
    sendResponse({ success: false, error: 'Failed to get stats' });
  }
}

function updateStats(analysisResult) {
  chrome.storage.local.get('greenguard_stats', (result) => {
    const stats = result.greenguard_stats || { 
      totalAnalyzed: 0, 
      claimsDetected: 0, 
      lastAnalysis: null 
    };
    
    stats.totalAnalyzed += 1;
    stats.claimsDetected += analysisResult.claims_detected || 0;
    stats.lastAnalysis = new Date().toISOString();
    
    chrome.storage.local.set({ 'greenguard_stats': stats });
  });
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