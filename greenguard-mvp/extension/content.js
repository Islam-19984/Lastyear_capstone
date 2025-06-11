class GreenGuardAnalyzer {
    constructor() {
      this.isEnabled = true;
      this.sensitivity = 'medium';
      this.detectedClaims = new Set();
      this.widgets = new Map();
      
      this.environmentalKeywords = [
        'sustainable', 'eco-friendly', 'green', 'carbon neutral',
        'renewable', 'biodegradable', 'organic', 'recycled',
        'zero waste', 'climate positive', 'earth friendly',
        'environmentally responsible', 'natural', 'clean energy',
        'carbon negative', 'net zero', 'climate friendly'
      ];
      
      this.init();
    }
    
    async init() {
      const response = await this.sendMessage({ action: 'getSettings' });
      if (response.success) {
        this.isEnabled = response.data.enabled !== false;
        this.sensitivity = response.data.sensitivity || 'medium';
      }
      
      if (!this.isEnabled) return;
      
      this.startAnalysis();
      
      this.observeChanges();
    }
    
    startAnalysis() {
      const textContent = this.extractPageContent();
      
      if (textContent.length > 100) {
        this.analyzeContent(textContent);
      }
      
      this.findEnvironmentalClaims();
    }
    
    extractPageContent() {
      const contentSelectors = [
        'main', 'article', '.content', '.product-description',
        '.product-details', '.about', '.sustainability'
      ];
      
      let content = '';
      
      for (const selector of contentSelectors) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          content += el.textContent + ' ';
        });
      }
      
      if (content.length < 100) {
        content = document.body.textContent;
      }
      
      return content.trim();
    }
    
    findEnvironmentalClaims() {
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode: (node) => {
            const text = node.textContent.toLowerCase();
            return this.environmentalKeywords.some(keyword => 
              text.includes(keyword)
            ) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
          }
        }
      );
      
      const claimElements = [];
      let node;
      
      while (node = walker.nextNode()) {
        const parent = node.parentElement;
        if (parent && !this.isIgnoredElement(parent)) {
          claimElements.push(parent);
        }
      }
      
      claimElements.forEach(element => {
        this.processClaim(element);
      });
    }
    
    isIgnoredElement(element) {
      const ignoredTags = ['SCRIPT', 'STYLE', 'NOSCRIPT'];
      const ignoredClasses = ['navigation', 'nav', 'menu', 'footer', 'header'];
      
      if (ignoredTags.includes(element.tagName)) return true;
      
      const className = element.className.toLowerCase();
      return ignoredClasses.some(cls => className.includes(cls));
    }
    
    async processClaim(element) {
      const claimText = element.textContent.trim();
      
      const claimId = this.hashString(claimText);
      if (this.detectedClaims.has(claimId)) return;
      
      this.detectedClaims.add(claimId);
      
      this.highlightClaim(element, 'analyzing');
      
      try {
        const response = await this.sendMessage({
          action: 'analyzeClaims',
          data: {
            text: claimText,
            url: window.location.href
          }
        });
        
        if (response.success && response.data.claims.length > 0) {
          const claim = response.data.claims[0];
          this.displayClaimAnalysis(element, claim);
        } else {
          this.removeHighlight(element);
        }
        
      } catch (error) {
        console.error('Error analyzing claim:', error);
        this.removeHighlight(element);
      }
    }
    
    highlightClaim(element, status = 'detected') {
      element.classList.add('greenguard-claim');
      element.classList.add(`greenguard-${status}`);
      
      element.addEventListener('click', (e) => {
        e.preventDefault();
        this.showDetailedAnalysis(element);
      });
    }
    
    removeHighlight(element) {
      element.classList.remove('greenguard-claim', 'greenguard-analyzing', 'greenguard-detected');
    }
    
    displayClaimAnalysis(element, claimData) {
      this.removeHighlight(element);
      this.highlightClaim(element, this.getRiskLevel(claimData.greenwashing_risk));
      
      this.createAnalysisWidget(element, claimData);
    }
    
    getRiskLevel(risk) {
      if (risk >= 0.7) return 'high-risk';
      if (risk >= 0.4) return 'medium-risk';
      return 'low-risk';
    }
    
    createAnalysisWidget(element, claimData) {
      const widget = document.createElement('div');
      widget.className = 'greenguard-widget';
      widget.innerHTML = `
        <div class="greenguard-header">
          <span class="greenguard-logo">🛡️ GreenGuard</span>
          <button class="greenguard-close">×</button>
        </div>
        <div class="greenguard-content">
          <div class="greenguard-score">
            <span class="score-label">Greenwashing Risk:</span>
            <span class="score-value ${this.getRiskLevel(claimData.greenwashing_risk)}">
              ${this.formatRiskScore(claimData.greenwashing_risk)}
            </span>
          </div>
          <div class="greenguard-confidence">
            <span class="confidence-label">Detection Confidence:</span>
            <span class="confidence-value">
              ${Math.round(claimData.confidence_score * 100)}%
            </span>
          </div>
          <div class="greenguard-actions">
            <button class="btn-details">View Details</button>
            <button class="btn-alternatives">Find Alternatives</button>
          </div>
        </div>
      `;
      
      this.positionWidget(widget, element);
      
      this.setupWidgetEvents(widget, claimData);
      
      this.widgets.set(element, widget);
      
      document.body.appendChild(widget);
    }
    
    formatRiskScore(risk) {
      if (risk >= 0.7) return 'HIGH';
      if (risk >= 0.4) return 'MEDIUM';
      return 'LOW';
    }
    
    positionWidget(widget, element) {
      const rect = element.getBoundingClientRect();
      const scrollTop = window.pageYOffset;
      const scrollLeft = window.pageXOffset;
      
      widget.style.position = 'absolute';
      widget.style.top = (rect.bottom + scrollTop + 10) + 'px';
      widget.style.left = (rect.left + scrollLeft) + 'px';
      widget.style.zIndex = '10000';
    }
    
    setupWidgetEvents(widget, claimData) {
      widget.querySelector('.greenguard-close').addEventListener('click', () => {
        widget.remove();
      });
      
      widget.querySelector('.btn-details').addEventListener('click', () => {
        this.showDetailedAnalysis(claimData);
      });
      
      widget.querySelector('.btn-alternatives').addEventListener('click', () => {
        this.showAlternatives(claimData);
      });
    }
    
    showDetailedAnalysis(claimData) {
      const modal = this.createModal('Detailed Claim Analysis', `
        <div class="analysis-details">
          <h3>Claim: "${claimData.claim_text}"</h3>
          <div class="analysis-metrics">
            <div class="metric">
              <label>Greenwashing Risk:</label>
              <div class="risk-bar">
                <div class="risk-fill" style="width: ${claimData.greenwashing_risk * 100}%"></div>
              </div>
              <span>${Math.round(claimData.greenwashing_risk * 100)}%</span>
            </div>
            <div class="metric">
              <label>Detection Confidence:</label>
              <span>${Math.round(claimData.confidence_score * 100)}%</span>
            </div>
            <div class="metric">
              <label>Keyword Detected:</label>
              <span class="keyword-tag">${claimData.keyword}</span>
            </div>
          </div>
          <div class="verification-status">
            <h4>Verification Status</h4>
            <div class="verification-sources">
              <div class="source">
                <span class="source-name">Carbon Disclosure Project</span>
                <span class="source-status pending">Checking...</span>
              </div>
              <div class="source">
                <span class="source-name">Science-Based Targets</span>
                <span class="source-status pending">Checking...</span>
              </div>
              <div class="source">
                <span class="source-name">Community Reports</span>
                <span class="source-status pending">Checking...</span>
              </div>
            </div>
          </div>
          <div class="recommendations">
            <h4>Recommendations</h4>
            <ul>
              <li>Look for third-party certifications</li>
              <li>Check company sustainability reports</li>
              <li>Consider verified alternatives</li>
            </ul>
          </div>
        </div>
      `);
      
      document.body.appendChild(modal);
    }
    
    async showAlternatives(claimData) {
      try {
        const response = await this.sendMessage({
          action: 'getAlternatives',
          data: {
            companyName: this.extractCompanyName(),
            category: this.detectProductCategory()
          }
        });
        
        if (response.success) {
          this.displayAlternatives(response.data.alternatives);
        }
      } catch (error) {
        console.error('Error getting alternatives:', error);
      }
    }
    
    extractCompanyName() {
      const domain = window.location.hostname.replace('www.', '');
      return domain.split('.')[0];
    }
    
    detectProductCategory() {
      const url = window.location.href.toLowerCase();
      const content = document.title.toLowerCase();
      
      if (url.includes('fashion') || url.includes('clothing') || content.includes('fashion')) {
        return 'fashion';
      }
      if (url.includes('food') || content.includes('food')) {
        return 'food';
      }
      if (url.includes('tech') || content.includes('technology')) {
        return 'technology';
      }
      
      return 'general';
    }
    
    displayAlternatives(alternatives) {
      const modal = this.createModal('Sustainable Alternatives', `
        <div class="alternatives-list">
          ${alternatives.map(alt => `
            <div class="alternative-item">
              <h4>${alt.name}</h4>
              <p>${alt.product}</p>
              <div class="certifications">
                ${alt.certifications.map(cert => 
                  `<span class="cert-badge">${cert}</span>`
                ).join('')}
              </div>
              <div class="sustainability-score">
                Sustainability Score: ${Math.round(alt.sustainability_score * 100)}%
              </div>
              <div class="price-range">
                Price Range: ${alt.price_range}
              </div>
              <a href="${alt.url}" target="_blank" class="btn-visit">Visit Website</a>
            </div>
          `).join('')}
        </div>
      `);
      
      document.body.appendChild(modal);
    }
    
    createModal(title, content) {
      const modal = document.createElement('div');
      modal.className = 'greenguard-modal';
      modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-content">
          <div class="modal-header">
            <h2>${title}</h2>
            <button class="modal-close">×</button>
          </div>
          <div class="modal-body">
            ${content}
          </div>
        </div>
      `;
      
      modal.querySelector('.modal-close').addEventListener('click', () => {
        modal.remove();
      });
      
      modal.querySelector('.modal-backdrop').addEventListener('click', () => {
        modal.remove();
      });
      
      return modal;
    }
    
    observeChanges() {
      const observer = new MutationObserver((mutations) => {
        let hasNewContent = false;
        
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            hasNewContent = true;
          }
        });
        
        if (hasNewContent) {
          clearTimeout(this.analysisTimeout);
          this.analysisTimeout = setTimeout(() => {
            this.findEnvironmentalClaims();
          }, 1000);
        }
      });
      
      observer.observe(document.body, {
        childList: true,
        subtree: true
      });
    }
    
    sendMessage(message) {
      return new Promise((resolve) => {
        chrome.runtime.sendMessage(message, resolve);
      });
    }
    
    hashString(str) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
      }
      return hash.toString();
    }
  }
  
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      new GreenGuardAnalyzer();
    });
  } else {
    new GreenGuardAnalyzer();
  }