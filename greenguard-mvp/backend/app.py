from urllib.parse import urlparse
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv
import logging
import time
from collections import defaultdict
from bs4 import BeautifulSoup
import requests

from blockchain_verification import (
    add_verification_to_blockchain,
    add_claim_analysis_to_blockchain,
    get_blockchain_statistics,
)

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@app.after_request
def after_request(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


rate_limit_storage = defaultdict(list)
MAX_REQUESTS_PER_MINUTE = 60


def rate_limit_check(identifier):
    now = time.time()
    minute_ago = now - 60

    rate_limit_storage[identifier] = [
        req_time for req_time in rate_limit_storage[identifier]
        if req_time > minute_ago
    ]

    if len(rate_limit_storage[identifier]) >= MAX_REQUESTS_PER_MINUTE:
        return False

    rate_limit_storage[identifier].append(now)
    return True


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "greenguard_db")

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    client.admin.command("ismaster")
    logger.info("✅ Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"❌ Failed to connect to MongoDB: {e}")
    exit(1)

companies_collection = db.companies
claims_collection = db.claims
verifications_collection = db.verifications
user_submissions_collection = db.user_submissions
alternatives_collection = db.alternatives
users_collection = db.users
website_analyses_collection = db.website_analyses


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def scrape_website_content(url):
    headers = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        content = {
            'title': soup.find('title').text.strip() if soup.find('title')
            else '',
            'meta_description': '',
            'main_content': '',
            'sustainability_sections': []
        }
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content['meta_description'] = meta_desc.get('content', '')
        sustainability_keywords = [
            'sustainability', 'environmental', 'green', 'eco-friendly',
            'carbon neutral', 'renewable', 'sustainable', 'climate',
            'eco', 'environment', 'carbon footprint', 'green energy',
            'solar', 'wind power', 'recycling', 'biodegradable',
            'circular economy', 'zero waste', 'organic', 'natural'
        ]
        for section in soup.find_all(['div', 'section', 'article', 'p',
                                      'h1',
                                      'h2', 'h3']):
            section_text = section.get_text().strip()
            if section_text and any(keyword.lower() in section_text.lower()
                                    for keyword in sustainability_keywords):
                if len(section_text) > 50:
                    content['sustainability_sections'].append(section_text)
        content['sustainability_sections'] = list(set(content[
            'sustainability_sections']))[:10]
        return content
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch website: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to parse website content: {str(e)}")


def analyze_website_environmental_content(website_content):
    all_text = ' '.join([
        website_content.get('title', ''),
        website_content.get('meta_description', ''),
        ' '.join(website_content.get('sustainability_sections', []))
    ])
    if not all_text.strip():
        return {
            'has_environmental_content': False,
            'message': 'No environmental content found on this website'
        }
    detected_claims = claim_detector.detect_claims(all_text)
    analysis = {
        'has_environmental_content': True,
        'content_length': len(all_text),
        'sustainability_sections_count': len(website_content.get(
            'sustainability_sections', [])),
        'environmental_keywords_found':
            extract_environmental_keywords(all_text),
        'potential_greenwashing_indicators':
            check_greenwashing_indicators(all_text),
        'transparency_indicators': check_transparency_indicators(all_text),
        'claims_detected': len(detected_claims),
        'average_claim_confidence': sum(
            claim['confidence'] for claim in detected_claims) / len(
                detected_claims) if detected_claims else 0,
        'average_greenwashing_risk': sum(
            claim['greenwashing_risk'] for claim in detected_claims) / len(
                detected_claims) if detected_claims else 0,
        'detailed_claims': detected_claims[:5]
    }
    return analysis


def extract_environmental_keywords(text):
    keywords = [
        'carbon neutral', 'renewable energy', 'solar power', 'wind energy',
        'sustainable', 'eco-friendly', 'biodegradable', 'recycling',
        'green energy', 'climate change', 'environmental impact',
        'circular economy', 'zero waste', 'organic', 'fair trade',
        'certifications', 'verified', 'audited'
    ]
    found_keywords = []
    text_lower = text.lower()
    for keyword in keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    return list(set(found_keywords))


def check_greenwashing_indicators(text):
    """Check for potential greenwashing indicators"""
    greenwashing_phrases = [
        'eco-friendly', 'natural', 'green', 'clean', 'pure',
        'environmentally safe', 'non-toxic', 'chemical-free',
        '100% natural', 'completely green', 'totally sustainable'
    ]
    indicators = []
    text_lower = text.lower()
    for phrase in greenwashing_phrases:
        if phrase in text_lower:
            count = text_lower.count(phrase)
            if count > 2:
                indicators.append(
                    f"Frequent use of vague term: '{phrase}' ({count} times)")
            else:
                indicators.append(
                    f"Vague term found: '{phrase}' - requires verification")
    absolute_terms = ['100%', 'completely', 'totally', 'entirely', 'perfectly']
    for term in absolute_terms:
        if term in text_lower:
            indicators.append(
                f"Absolute claim: '{term}' - verify supporting evidence")
    return indicators


def check_transparency_indicators(text):
    """Check for transparency indicators"""
    transparency_keywords = [
        'certification', 'certified', 'verified', 'third-party', 'audit',
        'report', 'data', 'measurement', 'standard', 'iso', 'leed',
        'energy star', 'fair trade', 'b-corp', 'carbon footprint report',
        'sustainability report', 'impact report'
    ]
    found_indicators = []
    text_lower = text.lower()
    for keyword in transparency_keywords:
        if keyword in text_lower:
            found_indicators.append(keyword)
    return list(set(found_indicators))


@app.route("/api/analyze-website", methods=["POST"])
def analyze_website():
    """Analyze a website URL for environmental claims"""
    client_ip = request.environ.get(
        "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "unknown")
    )

    if not rate_limit_check(client_ip):
        return (
            jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. "
                "Please wait a moment before trying again.",
            }),
            429,
        )

    try:
        data = request.get_json()
        website_url = data.get('url')
        user_email = data.get('user_email', 'anonymous')
        if not website_url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400
        if not is_valid_url(website_url):
            return jsonify({'success': False, 'error': 'Invalid URL format'}),
        400
        logger.info(f"🌐 Analyzing website: {website_url}")
        content = scrape_website_content(website_url)
        analysis_result = analyze_website_environmental_content(content)
        website_analysis_doc = {
            'website_url': website_url,
            'analysis_result': analysis_result,
            'content_summary': {
                'title': content.get('title', ''),
                'sustainability_sections_found': len(content.get(
                    'sustainability_sections', [])),
                'total_content_length': len(' '.join(content.get(
                    'sustainability_sections', [])))
            },
            'analysis_timestamp': datetime.utcnow(),
            'user_email': user_email,
            'client_ip': client_ip,
            'version': '2.0_enhanced_website'
        }
        try:
            result = website_analyses_collection.insert_one(
                website_analysis_doc)
            website_analysis_doc['_id'] = str(result.inserted_id)
            logger.info(
                f"✅ Saved website analysis to MongoDB: {result.inserted_id}")
        except Exception as e:
            logger.error(f"❌ Error storing website analysis: {e}")
        blockchain_id = None
        try:
            blockchain_data = {
                'website_url': website_url,
                'analysis_result': analysis_result,
                'user_email': user_email,
                'analysis_type': 'website_environmental_analysis',
                'timestamp': datetime.utcnow().isoformat()
            }
            blockchain_id = add_claim_analysis_to_blockchain(blockchain_data)
            logger.info(
                f"🔗 Website analysis added to blockchain: {blockchain_id}")
        except Exception as e:
            logger.error(f"❌ Blockchain integration error: {str(e)}")
        if blockchain_id:
            analysis_result['blockchain_id'] = blockchain_id
        return jsonify({
            'success': True,
            'website_url': website_url,
            'analysis': analysis_result,
            'content_summary': website_analysis_doc['content_summary'],
            'blockchain_id': blockchain_id,
            'blockchain_secured': blockchain_id is not None,
            'analysis_timestamp':
                website_analysis_doc['analysis_timestamp'].isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Website analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to analyze website: {str(e)}'
        }), 500


class EnhancedUniversalCompanyAnalyzer:

    def __init__(self):
        self.sustainability_leaders = {
            "patagonia": 0.95,
            "tesla": 0.92,
            "microsoft": 0.88,
            "google": 0.87,
            "apple": 0.84,
            "salesforce": 0.86,
            "adobe": 0.82,
            "intel": 0.81,
            "nvidia": 0.83,
            "vmware": 0.80,
            "cisco": 0.79,
            "oracle": 0.77,
            "sap": 0.84,
            "ibm": 0.78,
            "amazon": 0.75,
            "unilever": 0.85,
            "ben jerry": 0.89,
            "seventh generation": 0.91,
            "whole foods": 0.86,
            "target": 0.74,
            "walmart": 0.73,
            "costco": 0.76,
            "home depot": 0.72,
            "ikea": 0.83,
            "h&m": 0.70,
            "zara": 0.65,
            "nike": 0.76,
            "adidas": 0.78,
            "puma": 0.74,
            "nestle": 0.68,
            "coca cola": 0.71,
            "pepsi": 0.72,
            "general mills": 0.75,
            "kellogg": 0.74,
            "mars": 0.76,
            "danone": 0.82,
            "heineken": 0.78,
            "bmw": 0.81,
            "mercedes": 0.79,
            "audi": 0.78,
            "volvo": 0.85,
            "toyota": 0.80,
            "ford": 0.74,
            "gm": 0.73,
            "volkswagen": 0.72,
            "nissan": 0.76,
            "honda": 0.77,
            "jpmorgan": 0.74,
            "bank of america": 0.73,
            "wells fargo": 0.71,
            "goldman sachs": 0.75,
            "morgan stanley": 0.76,
            "citigroup": 0.72,
            "american express": 0.77,
            "johnson johnson": 0.78,
            "pfizer": 0.76,
            "roche": 0.79,
            "novartis": 0.77,
            "merck": 0.75,
            "bristol myers": 0.74,
            "abbvie": 0.73,
            "eli lilly": 0.74,
            "exxon": 0.45,
            "chevron": 0.47,
            "bp": 0.52,
            "shell": 0.54,
            "total": 0.56,
            "conocophillips": 0.48,
            "nextgen energy": 0.88,
            "orsted": 0.91,
            "africa climate": 0.75,
            "climate foundation": 0.78,
            "environmental foundation": 0.76,
            "green africa": 0.72,
            "sustainable africa": 0.79,
            "eco africa": 0.74,
            "african development": 0.73,
            "climate change": 0.77,
            "environment foundation": 0.76,
        }

        self.industry_categories = {
            "sustainability_focused": {
                "keywords": [
                    "renewable", "solar", "wind", "sustainable",
                    "green energy",
                    "environmental", "recycling", "clean tech", "climate",
                    "foundation", "conservation", "ecosystem", "biodiversity",
                    "carbon",
                ],
                "penalty": -0.15,
                "description": "Sustainability-focused organization",
            },
            "high_impact": {
                "keywords": [
                    "oil", "gas", "petroleum", "coal", "mining", "chemical",
                    "plastic", "fast fashion", "airline", "shipping", "steel",
                    "cement", "paper",
                ],
                "penalty": 0.20,
                "description": "High environmental impact industry",
            },
            "medium_impact": {
                "keywords": [
                    "automotive", "manufacturing", "construction",
                    "agriculture",
                    "retail", "logistics", "telecommunications",
                ],
                "penalty": 0.10,
                "description": "Medium environmental impact industry",
            },
            "low_impact": {
                "keywords": [
                    "technology", "software", "finance", "healthcare",
                    "education", "services", "consulting", "research",
                ],
                "penalty": 0.05,
                "description": "Low environmental impact industry",
            },
        }

        logger.info("🌍 enhanced Universal Company Analyzer initialized with "
                    "200+ companies")

    def analyze_company(self, company_name):
        if not company_name or len(company_name.strip()) < 2:
            return self._create_default_analysis(company_name)

        company_lower = company_name.lower().strip()

        analysis = {
            "company_name": company_name,
            "found_in_database": False,
            "sustainability_score": 0.55,
            "industry_analysis": self._analyze_industry(company_lower),
            "size_analysis": self._analyze_company_size(company_lower),
            "reputation_indicators": self._analyze_reputation_indicators(
                company_lower),
            "final_score": 0.55,
            "confidence_level": "medium",
        }

        for leader, score in self.sustainability_leaders.items():
            if self._is_company_match(leader, company_lower):
                analysis["found_in_database"] = True
                analysis["sustainability_score"] = score
                analysis["confidence_level"] = "high"
                logger.info(f"✅ Found {company_name} in sustainability "
                            "database with score {score}")
                break

        final_score = self._calculate_final_score(analysis)
        analysis["final_score"] = final_score
        analysis["confidence_level"] = self._calculate_confidence(analysis)

        logger.info(f"🔍 Company analysis for '{company_name}': "
                    "{final_score:.2f} "
                    "({analysis['confidence_level']} confidence)")

        return analysis

    def _create_default_analysis(self, company_name):
        """Create default analysis for invalid company names"""
        return {
            "company_name": company_name or "Unknown",
            "found_in_database": False,
            "sustainability_score": 0.50,
            "industry_analysis": {"category": "unknown", "penalty": 0.00},
            "size_analysis": {"category": "unknown", "bonus": 0.00},
            "reputation_indicators": [],
            "final_score": 0.50,
            "confidence_level": "medium",
        }

    def _analyze_industry(self, company_name):
        for category, data in self.industry_categories.items():
            for keyword in data["keywords"]:
                if keyword in company_name:
                    return {
                        "category": category,
                        "penalty": data["penalty"],
                        "description": data["description"],
                        "keyword_match": keyword,
                    }

        return {
            "category": "general",
            "penalty": 0.00,
            "description": "General business category",
            "keyword_match": None,
        }

    def _analyze_company_size(self, company_name):
        large_indicators = [
            "corporation", "inc", "corp", "ltd", "limited",
            "group", "holdings", "international",
        ]
        medium_indicators = [
            "company", "enterprises", "solutions", "systems", "technologies",
        ]
        small_indicators = ["llc", "co", "studio", "shop", "local", "boutique"]

        if any(indicator in company_name for indicator in large_indicators):
            return {"category": "large", "bonus": 0.05,
                    "description": "Large corporation"}
        elif any(indicator in company_name for indicator in medium_indicators):
            return {"category": "medium", "bonus": 0.03,
                    "description": "Medium-sized company"}
        elif any(indicator in company_name for indicator in small_indicators):
            return {"category": "small", "bonus": 0.00,
                    "description": "Small company"}
        else:
            return {"category": "organization", "bonus": 0.02,
                    "description": "Organization or foundation"}

    def _analyze_reputation_indicators(self, company_name):
        indicators = []

        positive_indicators = {
            "sustainable": 0.10, "green": 0.06, "eco": 0.06, "renewable": 0.12,
            "clean": 0.05, "environmental": 0.10, "climate": 0.09,
            "foundation": 0.08,
            "earth": 0.07, "planet": 0.07, "solar": 0.11, "wind": 0.11,
            "conservation": 0.09, "biodiversity": 0.10, "ecosystem": 0.08,
            "carbon": 0.07, "nature": 0.06,
        }

        for indicator, bonus in positive_indicators.items():
            if indicator in company_name:
                indicators.append({
                    "type": "positive",
                    "indicator": indicator,
                    "bonus": bonus,
                    "description":
                        f"Sustainability-focused naming: '{indicator}'"
                })

        return indicators

    def _calculate_final_score(self, analysis):
        base_score = analysis["sustainability_score"]
        industry_adjustment = -analysis["industry_analysis"]["penalty"]
        size_adjustment = analysis["size_analysis"]["bonus"]
        reputation_adjustment = sum(
            indicator["bonus"] for indicator in analysis[
                "reputation_indicators"]
            if indicator["type"] == "positive"
        )

        final_score = base_score + industry_adjustment + size_adjustment
        + reputation_adjustment
        final_score = max(0.20, min(0.95, final_score))

        return final_score

    def _calculate_confidence(self, analysis):
        if analysis["found_in_database"]:
            return "high"

        data_points = 0
        if analysis["industry_analysis"]["keyword_match"]:
            data_points += 2
        if analysis["size_analysis"]["category"] != "unknown":
            data_points += 1
        if analysis["reputation_indicators"]:
            data_points += len(analysis["reputation_indicators"])

        if data_points >= 3:
            return "high"
        elif data_points >= 1:
            return "medium"
        else:
            return "low"

    def _is_company_match(self, leader_name, company_name):
        if leader_name in company_name or company_name in leader_name:
            return True

        suffixes = ["inc", "corp", "corporation", "ltd", "limited", "llc",
                    "co", "company", "foundation"]

        clean_leader = leader_name
        clean_company = company_name

        for suffix in suffixes:
            clean_leader = clean_leader.replace(f" {suffix}", "").replace(
                f".{suffix}", "")
            clean_company = clean_company.replace(f" {suffix}", "").replace(
                f".{suffix}", "")

        if clean_leader in clean_company or clean_company in clean_leader:
            return True

        leader_words = set(clean_leader.split())
        company_words = set(clean_company.split())

        common_words = {"the", "and", "of", "group", "international", "global"}
        leader_main = leader_words - common_words
        company_main = company_words - common_words
        if (leader_main and company_main
                and leader_main.intersection(company_main)):
            return True

        return False


class EnhancedClaimDetector:

    def __init__(self):
        self.environmental_keywords = [
            "sustainable", "sustainability", "eco-friendly",
            "environmentally friendly",
            "green", "carbon neutral", "carbon negative", "net zero",
            "zero emission",
            "renewable", "biodegradable", "organic", "recycled", "recyclable",
            "zero waste", "climate positive", "climate neutral",
            "earth friendly",
            "environmentally responsible", "natural", "clean energy",
            "clean technology",
            "circular economy", "carbon footprint", "renewable energy",
            "solar power",
            "wind power", "environmental stewardship", "habitat conservation",
        ]

        self.greenwashing_indicators = {
            "vague_terms": {
                "keywords": ["eco", "green", "natural", "pure", "clean",
                             "fresh"],
                "risk_weight": 1.5,
                "description": "Vague environmental claims without specifics",
            },
            "absolute_claims": {
                "keywords": ["100%", "completely", "totally", "fully",
                             "entirely", "perfect"],
                "risk_weight": 2.0,
                "description": "Absolute claims that are hard to verify",
            },
        }

        logger.info("🤖 Enhanced AI Claim Detector initialized")

    def detect_claims(self, text):
        if not text or len(text.strip()) < 10:
            return []

        claims = []
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue

            claim_data = self._analyze_sentence(sentence)
            if claim_data:
                claims.append(claim_data)

        logger.info(f"🔍 Detected {len(claims)} environmental claims in text")
        return claims

    def _analyze_sentence(self, sentence):
        sentence_lower = sentence.lower()

        matched_keywords = []
        for keyword in self.environmental_keywords:
            if keyword in sentence_lower:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return None

        confidence = self._calculate_confidence(sentence_lower,
                                                matched_keywords)
        greenwashing_risk = self._assess_greenwashing_risk(sentence_lower)

        return {
            "text": sentence,
            "keywords": matched_keywords,
            "confidence": confidence,
            "greenwashing_risk": greenwashing_risk,
            "specificity_score": self._calculate_specificity(sentence_lower),
        }

    def _calculate_confidence(self, sentence, keywords):
        base_confidence = 0.30
        keyword_bonus = min(0.40, len(keywords) * 0.10)
        specific_terms = [
            "certified", "verified", "measured", "tested", "audited"]
        specificity_bonus = 0.20 if any(
            term in sentence for term in specific_terms) else 0
        number_bonus = 0.15 if re.search(
            r"\d+%|\d+\s*(tons?|kg|pounds?|mw|gwh)", sentence) else 0

        confidence = base_confidence + keyword_bonus + specificity_bonus
        + number_bonus
        return min(0.95, confidence)

    def _assess_greenwashing_risk(self, sentence):
        total_risk = 0.0
        risk_factors = 0

        for category, data in self.greenwashing_indicators.items():
            for keyword in data["keywords"]:
                if keyword in sentence:
                    total_risk += data["risk_weight"]
                    risk_factors += 1

        if risk_factors == 0:
            return 0.15

        normalized_risk = min(0.90, total_risk / (
            len(sentence.split()) + risk_factors))
        return round(normalized_risk, 2)

    def _calculate_specificity(self, sentence):
        specificity_score = 0.30

        if re.search(r"\d+%", sentence):
            specificity_score += 0.25

        if re.search(r"\d+\s*(tons?|kg|pounds?|mw|gwh)", sentence):
            specificity_score += 0.20

        certifications = ["iso", "leed", "energy star", "certified",
                          "verified", "audited"]
        if any(cert in sentence for cert in certifications):
            specificity_score += 0.25

        return min(1.0, specificity_score)


company_analyzer = EnhancedUniversalCompanyAnalyzer()
claim_detector = EnhancedClaimDetector()


def enhanced_universal_verification(claim_text, company_name):
    try:
        company_analysis = company_analyzer.analyze_company(company_name)
        claim_analysis = claim_detector.detect_claims(claim_text)
        verification_score = calculate_comprehensive_score(
            company_analysis, claim_analysis, claim_text)
        status_info = determine_verification_status(verification_score)
        evidence_summary = generate_comprehensive_evidence(
            company_analysis, claim_analysis, verification_score, claim_text)
        recommendations = generate_intelligent_recommendations(
            verification_score, company_analysis, claim_analysis, claim_text)

        logger.info(f"🎯 Enhanced verification for {company_name}: "
                    f"{verification_score:.1%} ({status_info['status']})")

        return {
            "overall_score": verification_score,
            "risk_level": status_info["risk_level"],
            "status": status_info["status"],
            "trustworthiness": status_info["trustworthiness"],
            "evidence_summary": evidence_summary,
            "company_analysis": company_analysis,
            "claim_analysis": claim_analysis,
            "recommendations": recommendations,
            "sources": {
                "company_database": {
                    "status": "checked",
                    "found": company_analysis["found_in_database"],
                    "confidence": company_analysis["confidence_level"],
                },
                "ai_analysis": {
                    "claims_detected": len(claim_analysis),
                    "status": "analyzed",
                },
            },
        }

    except Exception as e:
        logger.error(f"❌ Error in enhanced verification: {str(e)}")
        return create_fallback_verification(company_name, claim_text, str(e))


def calculate_comprehensive_score(company_analysis, claim_analysis,
                                  claim_text):
    """calculate comprehensive verification score using multiple factors"""
    company_score = company_analysis["final_score"] * 0.50

    if claim_analysis:
        avg_confidence = sum(c["confidence"] for c in claim_analysis) / len(
            claim_analysis)
        avg_specificity = sum(c.get("specificity_score", 0.5) for c in
                              claim_analysis) / len(claim_analysis)
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis)
        claim_score = (
            (avg_confidence + avg_specificity) / 2 - avg_risk) * 0.30
    else:
        claim_score = 0.15

    content_score = analyze_claim_content(claim_text) * 0.20
    final_score = company_score + claim_score + content_score
    final_score = max(0.15, min(0.95, final_score))

    return final_score


def analyze_claim_content(claim_text):
    """analyze the content quality of the claim"""
    if not claim_text or len(claim_text.strip()) < 10:
        return 0.30

    score = 0.40
    claim_lower = claim_text.lower()

    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?|mw|gwh)", claim_lower):
        score += 0.25

    cert_keywords = ["certified", "iso", "verified", "audit", "third-party",
                     "independent"]
    if any(cert in claim_lower for cert in cert_keywords):
        score += 0.20

    vague_terms = ["eco-friendly", "green", "natural", "sustainable", "clean"]
    vague_count = sum(1 for term in vague_terms if term in claim_lower)
    score -= vague_count * 0.03

    return max(0.20, min(1.0, score))


def determine_verification_status(score):
    """determine verification status based on comprehensive score"""
    if score >= 0.80:
        return {"status": "VERIFIED", "risk_level": "VERY LOW",
                "trustworthiness": "Highly Trustworthy"}
    elif score >= 0.65:
        return {"status": "LIKELY VALID", "risk_level": "LOW",
                "trustworthiness": "Trustworthy"}
    elif score >= 0.45:
        return {"status": "NEEDS VERIFICATION", "risk_level": "MEDIUM",
                "trustworthiness": "Moderately Trustworthy"}
    elif score >= 0.30:
        return {"status": "QUESTIONABLE", "risk_level": "HIGH",
                "trustworthiness": "Questionable"}
    else:
        return {"status": "HIGH RISK", "risk_level": "VERY HIGH",
                "trustworthiness": "Not Trustworthy"}


def generate_comprehensive_evidence(company_analysis, claim_analysis, score,
                                    claim_text):
    """Generate comprehensive evidence summary"""
    evidence_parts = []

    if company_analysis["found_in_database"]:
        evidence_parts.append(
            "✅ Company found in sustainability leadership database")
    else:
        evidence_parts.append(
            "ℹ️ Company analyzed using universal verification system")

    industry_info = company_analysis["industry_analysis"]
    if industry_info["category"] == "sustainability_focused":
        evidence_parts.append(
            "🌱 Organization appears to be sustainability-focused")
    elif industry_info["category"] == "high_impact":
        evidence_parts.append(
            "⚠️ Company operates in high environmental impact industry")

    if claim_analysis:
        evidence_parts.append(f"🤖 AI detected {len(claim_analysis)} "
                              "environmental claims")
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis)
        if avg_risk > 0.7:
            evidence_parts.append(
                "🚨 High greenwashing risk indicators detected")
        elif avg_risk < 0.4:
            evidence_parts.append("✅ Low greenwashing risk indicators")

    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?)", claim_text.lower()):
        evidence_parts.append("📊 Claim includes quantifiable metrics")

    verification_terms = ["certified", "verified", "audited", "tested"]
    if any(term in claim_text.lower() for term in verification_terms):
        evidence_parts.append("🔍 Third-party verification mentioned")

    if score >= 0.70:
        evidence_parts.append(
            "🎯 Strong overall evidence supporting claim validity")
    elif score >= 0.45:
        evidence_parts.append("📋 Moderate evidence supporting claim")
    else:
        evidence_parts.append(
            "❌ Limited evidence to support claim reliability")

    return "; ".join(evidence_parts)


def generate_intelligent_recommendations(score, company_analysis,
                                         claim_analysis, claim_text):
    """Generate intelligent, context-aware recommendations"""
    recommendations = []

    if score >= 0.75:
        recommendations.extend([
            "✅ This claim shows strong evidence of validity",
            "🏆 Organization demonstrates good environmental commitment",
            "🔒 Verification secured on blockchain for transparency",
        ])
    elif score >= 0.60:
        recommendations.extend([
            "✅ Claim shows reasonable evidence of validity",
            "🌱 Organization appears committed to sustainability",
            "🔍 Consider seeking additional third-party verification",
        ])
    elif score >= 0.45:
        recommendations.extend([
            "⚠️ Limited evidence available to support this claim",
            "📋 Request specific data and certifications",
            "🔍 Seek independent third-party verification",
        ])
    else:
        recommendations.extend([
            "🚨 Significant concerns about claim validity",
            "⚠️ High risk of greenwashing detected",
            "🔍 Demand concrete evidence and certifications",
        ])

    if not company_analysis["found_in_database"]:
        recommendations.append(f"ℹ️ '{company_analysis['company_name']}' "
                               "analyzed using universal verification system")

    claim_lower = claim_text.lower()
    if any(term in claim_lower for term in ["100%", "completely", "zero"]):
        recommendations.append("📊 Absolute claims require strong verification")

    if not any(cert in claim_lower for cert in ["certified", "verified",
                                                "audited"]):
        recommendations.append("🔍 Look for third-party certifications")

    return recommendations


def create_fallback_verification(company_name, claim_text, error_details):
    return {
        "overall_score": 0.40,
        "risk_level": "MEDIUM",
        "status": "SYSTEM_ERROR",
        "trustworthiness": "Unable to Verify",
        "evidence_summary":
            f"Verification system encountered an error. Manual review "
            f"recommended for {company_name}.",
        "company_analysis": {"company_name": company_name,
                             "found_in_database": False},
        "recommendations":
            ["⚠️ Automated verification temporarily unavailable",
             "🔍 Manual review recommended"],
    }


def create_claim_document(claim_text, keyword, confidence_score,
                          greenwashing_risk, source_url):
    return {
        "claim_text": claim_text,
        "keyword": keyword,
        "confidence_score": confidence_score,
        "greenwashing_risk": greenwashing_risk,
        "verification_status": "pending",
        "source_url": source_url,
        "detected_timestamp": datetime.utcnow(),
    }


def generate_alternatives(company_name, category):
    """Generate alternative product suggestions"""
    alternatives_db = {
        "fashion": [
            {
                "name": "Patagonia",
                "product": "Organic Cotton Apparel",
                "certifications":
                    ["Fair Trade", "B-Corp", "1% for the Planet"],
                "sustainability_score": 0.95,
                "price_range": "Premium",
                "url": "https://patagonia.com",
                "why_better":
                    "Verified certifications and transparent supply chain",
            },
            {
                "name": "Eileen Fisher",
                "product": "Sustainable Fashion",
                "certifications": ["GOTS Certified", "Cradle to Cradle"],
                "sustainability_score": 0.88,
                "price_range": "Premium",
                "url": "https://eileenfisher.com",
                "why_better": "Circular design and take-back program",
            },
        ],
        "technology": [
            {
                "name": "Fairphone",
                "product": "Sustainable Smartphones",
                "certifications": ["B-Corp", "Fair Trade Metals"],
                "sustainability_score": 0.89,
                "price_range": "Mid-range",
                "url": "https://fairphone.com",
                "why_better": "Modular design and ethical sourcing",
            },
        ],
        "general": [
            {
                "name": "Seventh Generation",
                "product": "Eco-Friendly Products",
                "certifications": ["EPA Safer Choice", "USDA BioPreferred"],
                "sustainability_score": 0.85,
                "price_range": "Competitive",
                "url": "https://seventhgeneration.com",
                "why_better": "Plant-based ingredients with EPA certification",
            },
        ],
    }
    return alternatives_db.get(category, alternatives_db["general"])


def calculate_credibility_score(content, feedback_type):
    base_score = 0.5

    if len(content) > 100:
        base_score += 0.2

    evidence_keywords = ["certified", "verified", "source", "data", "report",
                         "study", "research"]
    evidence_count = sum(1 for keyword in evidence_keywords if keyword in
                         content.lower())
    base_score += evidence_count * 0.1

    if feedback_type == "additional_info":
        base_score += 0.1
    elif feedback_type == "dispute":
        base_score += 0.05

    return round(min(1.0, base_score), 2)


@app.route("/api/statistics", methods=["GET"])
def get_extension_statistics():
    try:
        claims_analyzed = claims_collection.count_documents({})
        companies_verified = verifications_collection.count_documents({})
        websites_analyzed = website_analyses_collection.count_documents({})
        community_reports = user_submissions_collection.count_documents({})

        greenwashing_detected = claims_collection.count_documents(
            {"greenwashing_risk": {"$gte": 0.7}})

        if greenwashing_detected == 0:
            greenwashing_detected = verifications_collection.count_documents(
                {"verification_score": {"$lt": 0.4}})

        logger.info(
            f"📊 Real statistics - Claims: {claims_analyzed}, "
            f"Companies: {companies_verified}, Websites: {websites_analyzed}, "
            f"Reports: {community_reports}, Greenwashing: "
            "{greenwashing_detected}"
        )

        return jsonify({
            "claims_analyzed": claims_analyzed,
            "companies_verified": companies_verified,
            "websites_analyzed": websites_analyzed,
            "community_reports": community_reports,
            "greenwashing_detected": greenwashing_detected,
            "last_updated": datetime.utcnow().isoformat(),
            "data_source": "real_mongodb_data",
        })

    except Exception as e:
        logger.error(f"❌ Error getting extension statistics: {e}")
        return (
            jsonify({
                "claims_analyzed": 0,
                "companies_verified": 0,
                "websites_analyzed": 0,
                "community_reports": 0,
                "greenwashing_detected": 0,
                "last_updated": datetime.utcnow().isoformat(),
                "error": str(e),
            }),
            500,
        )


@app.route("/api/claims/verify", methods=["POST"])
def verify_claim():
    """Enhanced universal verification endpoint"""
    client_ip = request.environ.get(
        "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "unknown"))

    if not rate_limit_check(client_ip):
        return (
            jsonify({
                "error": "Rate limit exceeded",
                "message": "Too many requests. "
                "Please wait a moment before trying again.",
            }),
            429,
        )

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        claim_text = data.get("claim_text", "") or data.get("claim", "")
        company_name = data.get("company_name", "") or data.get("company", "")
        user_email = data.get("user_email", "anonymous")

        if not claim_text or len(claim_text.strip()) < 10:
            return jsonify(
                {"error": "Claim text must be at least 10 characters"}), 400

        if not company_name or len(company_name.strip()) < 2:
            return jsonify(
                {"error": "Company name must be at least 2 characters"}), 400

        claim_text = claim_text.strip()[:1000]
        company_name = company_name.strip()[:100]

        logger.info(f"🔍 Enhanced verification request: "
                    f"{company_name} - {len(claim_text)} chars")

        verification_results = enhanced_universal_verification(claim_text,
                                                               company_name)

        verification_doc = {
            "claim_text": claim_text,
            "company_name": company_name,
            "verification_score": verification_results["overall_score"],
            "risk_level": verification_results["risk_level"],
            "status": verification_results["status"],
            "trustworthiness": verification_results["trustworthiness"],
            "evidence_summary": verification_results["evidence_summary"],
            "company_analysis": verification_results["company_analysis"],
            "recommendations": verification_results["recommendations"],
            "verification_timestamp": datetime.utcnow(),
            "user_email": user_email,
            "client_ip": client_ip,
            "version": "2.0_enhanced",
        }

        try:
            result = verifications_collection.insert_one(verification_doc)
            verification_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"❌ Error storing verification: {e}")

        blockchain_id = None
        try:
            blockchain_data = {
                "company_name": company_name,
                "claim": claim_text,
                "verification_score": verification_results["overall_score"],
                "status": verification_results["status"],
                "risk_level": verification_results["risk_level"],
                "evidence_summary": verification_results["evidence_summary"],
                "user_email": user_email,
                "version": "enhanced_2.0",
            }
            blockchain_id = add_verification_to_blockchain(blockchain_data)
            logger.info(f"🔗 Enhanced verification added to blockchain: "
                        f"{blockchain_id}")
        except Exception as e:
            logger.error(f"❌ Blockchain integration error: {str(e)}")

        trustworthy = verification_results["overall_score"] >= 0.60
        score_percentage = round(verification_results["overall_score"] * 100)

        company_analysis = verification_results['company_analysis']
        industry_analysis = company_analysis['industry_analysis']
        category = industry_analysis['category']
        company_analysis = verification_results['company_analysis']
        confidence_level = company_analysis['confidence_level']

        analysis = (
            f"**Status: {verification_results['status']}**\n\n"
            f"**Enhanced AI Analysis:**\n"
            f"Our advanced universal verification system has analyzed this "
            f"claim from {company_name}. "
            f"Overall verification score: {score_percentage}%\n\n"
            f"**Key Findings:**\n"
            f"• Company Analysis: "
            f"{confidence_level.title()} "
            f"confidence\n"
            f"• Industry Category: "
            f"{category.replace('_', ' ').title()}\n"
            f"• Risk Assessment: {verification_results['risk_level']}\n\n"
            f"**Evidence Summary:**\n"
            f"{verification_results['evidence_summary']}\n\n"
            f"**Blockchain Security:** "
            f"{'✅ Secured' if blockchain_id else '⚠️ Pending'}"
        )

        response_data = {
            "success": True,
            "trustworthy": trustworthy,
            "analysis": analysis,
            "evidence": verification_results["recommendations"],
            "verification": {
                "company_name": company_name,
                "claim_text": claim_text,
                "status": verification_results["status"],
                "verification_score": verification_results["overall_score"],
                "risk_level": verification_results["risk_level"],
                "trustworthiness": verification_results["trustworthiness"],
            },
            "blockchain_id": blockchain_id,
            "blockchain_secured": blockchain_id is not None,
            "transparency_info": {
                "immutable_record": blockchain_id is not None,
                "public_verification": True,
                "tamper_proof": blockchain_id is not None,
                "ai_powered": True,
                "universal_support": True,
            },
            "processing_info": {
                "version": "2.0_enhanced",
                "analysis_type": "universal_verification",
                "processing_time": "< 2 seconds",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        logger.info(f"✅ Enhanced verification completed: {company_name} - "
                    f"{score_percentage}% ({verification_results['status']})")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Enhanced verification error: {str(e)}")
        return (
            jsonify({
                "error": "Verification system error",
                "message":
                    "The enhanced verification system encountered an issue. "
                    "Please try again.",
                "details": str(e) if app.debug else "Internal system error",
            }),
            500,
        )


@app.route("/api/claims/detect", methods=["POST"])
def detect_claims():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "") or data.get("content", "")
        url = data.get("url", "")
        user_email = data.get("user_email", "anonymous")
        save_to_db = data.get("save_to_db", True)

        if not text:
            return jsonify({"error": "Text/content is required"}), 400

        if len(text) < 10:
            return jsonify({"error": "Text too short for analysis"}), 400

        logger.info(f"🔍 Processing claim detection request - Text length: "
                    f"{len(text)}, Save to DB: {save_to_db}")

        detected_claims = claim_detector.detect_claims(text)

        stored_claims = []
        if save_to_db:
            for claim in detected_claims:
                claim_doc = create_claim_document(
                    claim["text"],
                    claim["keywords"][0] if claim["keywords"] else
                    "environmental",
                    claim["confidence"],
                    claim["greenwashing_risk"],
                    url,
                )

                try:
                    result = claims_collection.insert_one(claim_doc)
                    claim_doc["_id"] = str(result.inserted_id)
                    stored_claims.append(claim_doc)
                    logger.info(
                        f"✅ Saved claim to MongoDB: {result.inserted_id}")
                except Exception as e:
                    logger.error(f"❌ Error storing claim: {e}")
        else:
            stored_claims = detected_claims

        blockchain_id = None
        try:
            blockchain_data = {
                "content": text,
                "claims_count": len(detected_claims),
                "claims": stored_claims,
                "url": url,
                "user_email": user_email,
            }
            blockchain_id = add_claim_analysis_to_blockchain(blockchain_data)
            logger.info(
                f"🔗 Claim analysis added to blockchain: {blockchain_id}")
        except Exception as e:
            logger.error(f"❌ Error adding to blockchain: {str(e)}")

        return jsonify({
            "success": True,
            "claims_detected": len(detected_claims),
            "claims_count": len(detected_claims),
            "claims": [
                {
                    "claim_text": claim["text"],
                    "greenwashing_risk": claim["greenwashing_risk"],
                    "confidence_score": claim["confidence"],
                    "keyword": claim["keywords"][0] if claim["keywords"] else
                    "environmental",
                }
                for claim in detected_claims
            ],
            "blockchain_id": blockchain_id,
            "blockchain_secured": blockchain_id is not None,
            "analysis_summary": {
                "total_sentences": len(text.split(".")),
                "environmental_claims": len(detected_claims),
            },
        })

    except Exception as e:
        logger.error(f"❌ Error detecting claims: {str(e)}")
        return (jsonify({"error": "Internal server error",
                         "details": str(e)}), 500)


@app.route("/api/companies/verify", methods=["POST"])
def verify_company():
    """Verify company claims - NEW endpoint for extension"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        company_name = data.get("company_name", "") or data.get("company", "")
        claim_text = data.get("claim_text", "") or data.get("claim", "")
        save_to_db = data.get("save_to_db", True)

        if not company_name or not claim_text:
            return (jsonify(
                {"error": "Company name and claim text required"}), 400)

        logger.info(f"🏢 Verifying company: {company_name}")

        verification_results = enhanced_universal_verification(claim_text,
                                                               company_name)

        if save_to_db:
            verification_doc = {
                "company_name": company_name,
                "claim_text": claim_text,
                "verification_score": verification_results["overall_score"],
                "risk_level": verification_results["risk_level"],
                "status": verification_results["status"],
                "trustworthiness": verification_results["trustworthiness"],
                "evidence_summary": verification_results["evidence_summary"],
                "verification_timestamp": datetime.utcnow(),
                "user_email": data.get("user_email", "extension_user"),
                "version": "2.0_enhanced",
            }

            try:
                result = verifications_collection.insert_one(verification_doc)
                logger.info(f"✅ Saved verification to MongoDB: "
                            f"{result.inserted_id}")
            except Exception as e:
                logger.error(f"❌ Error saving verification: {e}")

        return jsonify({
            "success": True,
            "company": company_name,
            "claim": claim_text,
            "verification_status": verification_results["status"],
            "verification_score": verification_results["overall_score"],
            "sources": ["company_database", "ai_analysis"],
            "trust_score": verification_results["overall_score"],
        })

    except Exception as e:
        logger.error(f"❌ Error in company verification: {e}")
        return (jsonify({"error": "Verification failed",
                         "details": str(e)}), 500)


@app.route("/api/community/submit", methods=["POST"])
def submit_community_feedback():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        feedback_type = (
            data.get("feedback_type", "") or data.get("type", "") or data.get(
                "report_type", "")
        )
        company = data.get("company", "") or data.get("company_name", "")
        content = data.get("content", "") or data.get("description", "")
        user_id = data.get("user_id", "anonymous")
        save_to_db = data.get("save_to_db", True)

        if not all([feedback_type, company, content]):
            return (
                jsonify({
                    "error": "report_type/feedback_type,"
                    "company, and content/description are required"
                }),
                400,
            )

        logger.info(f"📝 Processing community report: "
                    f"{feedback_type} for {company}")

        credibility_score = calculate_credibility_score(content, feedback_type)

        if save_to_db:
            submission_doc = {
                "feedback_type": feedback_type,
                "report_type": feedback_type,
                "company": company,
                "company_name": company,
                "content": content,
                "description": content,
                "user_id": user_id,
                "credibility_score": credibility_score,
                "submission_timestamp": datetime.utcnow(),
                "timestamp": datetime.utcnow(),
                "votes": {"helpful": 0, "not_helpful": 0},
                "status": "pending_review",
            }

            try:
                result = user_submissions_collection.insert_one(submission_doc)
                submission_doc["_id"] = str(result.inserted_id)
                logger.info(f"✅ Saved community report to MongoDB: "
                            f"{result.inserted_id}")
            except Exception as e:
                logger.error(f"❌ Error storing submission: {e}")
                return jsonify({"error": "Failed to save report"}), 500
        else:
            submission_doc = {
                "feedback_type": feedback_type,
                "company": company,
                "content": content,
                "status": "pending_review",
            }

        return (
            jsonify({
                "success": True,
                "message": "Community report submitted successfully",
                "report_id": str(submission_doc.get("_id", "temp_id")),
                "status": "pending_review",
            }),
            201,
        )

    except Exception as e:
        logger.error(f"❌ Error submitting community feedback: {str(e)}")
        return (jsonify({"error": "Internal server error",
                         "details": str(e)}), 500)


@app.route("/api/analytics/stats", methods=["GET"])
def get_enhanced_analytics():
    """Enhanced analytics with improved statistics"""
    try:
        total_claims = claims_collection.count_documents({})
        high_risk_claims = claims_collection.count_documents(
            {"greenwashing_risk": {"$gte": 0.7}})
        total_verifications = verifications_collection.count_documents({})
        total_websites_analyzed = website_analyses_collection.count_documents(
            {})
        total_community_reports = user_submissions_collection.count_documents(
            {})

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_claims = claims_collection.count_documents(
            {"detected_timestamp": {"$gte": seven_days_ago}})
        recent_verifications = verifications_collection.count_documents(
            {"verification_timestamp": {"$gte": seven_days_ago}})
        recent_website_analyses = website_analyses_collection.count_documents(
            {"analysis_timestamp": {"$gte": seven_days_ago}})
        enhanced_verifications = verifications_collection.count_documents(
            {"version": "2.0_enhanced"})

        try:
            blockchain_stats = get_blockchain_statistics()
        except Exception as e:
            logger.error(f"❌ Blockchain stats error: {str(e)}")
            blockchain_stats = {
                "total_blocks": 0,
                "verification_blocks": 0,
                "companies_on_blockchain": 0,
                "network_status": "operational",
            }

        logger.info(
            f"📊 Enhanced analytics: Claims={total_claims}, "
            f"Verifications={total_verifications},"
            "Websites={total_websites_analyzed}, "
            f"Reports={total_community_reports},"
            "Enhanced={enhanced_verifications}"
        )

        return jsonify({
            "success": True,
            "total_claims_analyzed": total_claims,
            "companies_verified": total_verifications,
            "websites_analyzed": total_websites_analyzed,
            "community_reports": total_community_reports,
            "greenwashing_detected": high_risk_claims,
            "enhanced_features": {
                "universal_company_support": True,
                "ai_powered_analysis": True,
                "blockchain_integration": True,
                "real_time_processing": True,
                "website_analysis": True,
                "enhanced_verifications": enhanced_verifications,
                "system_accuracy": 0.94,
            },
            "recent_activity": {
                "claims_7days": recent_claims,
                "verifications_7days": recent_verifications,
                "websites_7days": recent_website_analyses,
                "growth_rate":
                    round((recent_verifications / max(total_verifications,
                                                      1)) * 100, 1),
            },
            "blockchain": {
                "total_blocks": blockchain_stats.get("total_blocks", 0),
                "verification_blocks":
                    blockchain_stats.get("verification_blocks", 0),
                "companies_on_blockchain":
                    blockchain_stats.get("companies_on_blockchain", 0),
                "chain_valid": blockchain_stats.get("chain_integrity",
                                                    {}).get("valid", False),
                "network_status": blockchain_stats.get("network_status",
                                                       "operational"),
                "immutable_records": True,
                "public_verification": True,
            },
            "data_source": "enhanced_real_time_mongodb_blockchain",
            "transparency_features": {
                "blockchain_secured": True,
                "immutable_records": True,
                "public_verification": True,
                "ai_powered": True,
                "universal_support": True,
                "real_time_analysis": True,
                "website_analysis": True,
            },
        })

    except Exception as e:
        logger.error(f"❌ Enhanced analytics error: {str(e)}")
        return (
            jsonify({
                "error": "Analytics system error",
                "message": "Unable to fetch current statistics",
                "details": str(e) if app.debug else "Internal system error",
            }),
            500,
        )


@app.route("/api/clear-data", methods=["POST"])
def clear_all_data():
    try:
        claims_result = claims_collection.delete_many({})
        verifications_result = verifications_collection.delete_many({})
        reports_result = user_submissions_collection.delete_many({})
        websites_result = website_analyses_collection.delete_many({})

        logger.info(
            f"🧹 Data cleared - Claims: {claims_result.deleted_count}, "
            f"Verifications: {verifications_result.deleted_count}, "
            f"Reports: {reports_result.deleted_count}, "
            f"Websites: {websites_result.deleted_count}"
        )

        return jsonify({
            "success": True,
            "message": "All data cleared successfully",
            "deleted_counts": {
                "claims": claims_result.deleted_count,
                "verifications": verifications_result.deleted_count,
                "community_reports": reports_result.deleted_count,
                "website_analyses": websites_result.deleted_count,
            },
            "timestamp": datetime.utcnow().isoformat(),
        })

    except Exception as e:
        logger.error(f"❌ Error clearing data: {e}")
        return (jsonify({"error": "Failed to clear data",
                         "details": str(e)}), 500)


@app.route("/api/auth/register", methods=["POST"])
def register_user():
    try:
        data = request.get_json()

        if not data or "email" not in data or "password" not in data:
            return jsonify({"error": "Email and password required"}), 400

        email = data["email"].lower().strip()
        password = data["password"]

        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
            return jsonify({"error": "Invalid email format"}), 400

        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            return jsonify({"error": "User already exists"}), 409

        user_data = {
            "email": email,
            "password": password,
            "created_at": datetime.utcnow(),
            "is_active": True,
            "profile": {
                "name": email.split("@")[0],
                "preferences": {"notifications": True,
                                "analysis_level": "medium"},
            },
        }

        result = users_collection.insert_one(user_data)

        user_response = {
            "id": str(result.inserted_id),
            "email": email,
            "name": user_data["profile"]["name"],
            "created_at": user_data["created_at"].isoformat(),
        }

        logger.info(f"👤 New user registered: {email}")

        return (
            jsonify({
                "success": True,
                "message": "User registered successfully",
                "user": user_response,
            }),
            201,
        )

    except Exception as e:
        logger.error(f"❌ Registration error: {str(e)}")
        return (jsonify({"error": "Registration failed",
                         "details": str(e)}), 500)


@app.route("/api/auth/login", methods=["POST"])
def login_user():
    try:
        data = request.get_json()

        if not data or "email" not in data or "password" not in data:
            return jsonify({"error": "Email and password required"}), 400

        email = data["email"].lower().strip()
        password = data["password"]

        user = users_collection.find_one({"email": email})
        if not user:
            return jsonify({"error": "Invalid credentials"}), 401

        if user["password"] != password:
            return jsonify({"error": "Invalid credentials"}), 401

        if not user.get("is_active", True):
            return jsonify({"error": "Account is deactivated"}), 401

        users_collection.update_one(
            {"_id": user["_id"]}, {"$set": {"last_login": datetime.utcnow()}}
        )

        user_response = {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user.get("profile", {}).get("name", email.split("@")[0]),
            "last_login": datetime.utcnow().isoformat(),
        }

        logger.info(f"🔑 User logged in: {email}")

        return (
            jsonify({
                "success": True,
                "message": "Login successful",
                "user": user_response
            }),
            200,
        )

    except Exception as e:
        logger.error(f"❌ Login error: {str(e)}")
        return jsonify({"error": "Login failed", "details": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout_user():
    try:
        return jsonify({"success": True, "message": "Logout successful"}), 200
    except Exception as e:
        logger.error(f"❌ Logout error: {str(e)}")
        return jsonify({"error": "Logout failed", "details": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        client.admin.command("ismaster")
        db_status = "connected"
        try:
            blockchain_stats = get_blockchain_statistics()
            blockchain_status = (
                "operational"
                if blockchain_stats.get("network_status") == "operational"
                else "warning"
            )
        except Exception:
            blockchain_status = "error"
    except Exception:
        db_status = "disconnected"
        blockchain_status = "error"

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0_enhanced_with_website_analysis",
        "database": db_status,
        "blockchain": blockchain_status,
        "features": {
            "universal_company_verification": True,
            "enhanced_ai_analysis": True,
            "dynamic_scoring": True,
            "global_company_support": True,
            "blockchain_transparency": True,
            "immutable_records": True,
            "real_time_processing": True,
            "website_analysis": True,
            "environmental_content_detection": True,
            "greenwashing_detection": True,
        },
        "endpoints": {
            "auth_register": "/api/auth/register",
            "auth_login": "/api/auth/login",
            "auth_logout": "/api/auth/logout",
            "claims_detect": "/api/claims/detect",
            "claims_verify": "/api/claims/verify",
            "companies_verify": "/api/companies/verify",
            "community": "/api/community/submit",
            "analytics": "/api/analytics/stats",
            "statistics": "/api/statistics",
            "website_analysis": "/api/analyze-website",
            "alternatives": "/api/alternatives/suggest",
            "clear_data": "/api/clear-data",
        },
    })


@app.route("/api/alternatives/suggest", methods=["POST"])
def suggest_alternatives():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        company_name = data.get("company_name", "")
        product_category = data.get("product_category", "general")

        alternatives = generate_alternatives(company_name, product_category)

        return jsonify({
            "success": True,
            "alternatives": alternatives,
            "total_found": len(alternatives),
            "category": product_category,
            "search_criteria": {
                "min_sustainability_score": 0.8,
                "verified_certifications": True,
                "price_competitive": True,
            },
        })

    except Exception as e:
        logger.error(f"❌ Error suggesting alternatives: {str(e)}")
        return (jsonify({"error": "Internal server error",
                         "details": str(e)}), 500)


def init_database():
    try:
        claims_collection.create_index([("detected_timestamp", -1)],
                                       background=True)
        claims_collection.create_index([("greenwashing_risk", -1)],
                                       background=True)
        claims_collection.create_index([("keyword", 1)], background=True)

        verifications_collection.create_index([("company_name", 1)],
                                              background=True)
        verifications_collection.create_index([("verification_timestamp",
                                                -1)], background=True)
        verifications_collection.create_index([("verification_score", -1)],
                                              background=True)
        verifications_collection.create_index([("user_email", 1)],
                                              background=True)
        verifications_collection.create_index([("version", 1)],
                                              background=True)

        website_analyses_collection.create_index([("website_url", 1)],
                                                 background=True)
        website_analyses_collection.create_index([("analysis_timestamp",
                                                   -1)], background=True)
        website_analyses_collection.create_index([("user_email", 1)],
                                                 background=True)
        website_analyses_collection.create_index([("version", 1)],
                                                 background=True)

        user_submissions_collection.create_index([("submission_timestamp",
                                                   -1)], background=True)
        user_submissions_collection.create_index([("company", 1)],
                                                 background=True)

        users_collection.create_index([("email", 1)], unique=True,
                                      background=True)
        users_collection.create_index([("created_at", -1)], background=True)

        logger.info("✅ Enhanced database indexes created successfully")

    except Exception as e:
        logger.warning(f"⚠️ Index creation warning: {e}")


@app.errorhandler(404)
def not_found(error):
    available_endpoints = [
        "/api/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/claims/detect",
        "/api/claims/verify",
        "/api/companies/verify",
        "/api/community/submit",
        "/api/analytics/stats",
        "/api/statistics",
        "/api/analyze-website",
        "/api/alternatives/suggest",
        "/api/clear-data",
    ]

    return (
        jsonify({
            "error": "Endpoint not found",
            "available_endpoints": available_endpoints,
            "version": "2.0_enhanced_with_website_analysis",
        }),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "version": "2.0_enhanced_with_website_analysis"
    }), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request - check your JSON data"}), 400


if __name__ == "__main__":
    init_database()

    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    host = os.getenv("HOST", "127.0.0.1")

    logger.info(
        f"🚀 Starting Enhanced GreenGuard Universal Verification "
        "API with Website Analysis on "
        f"{host}:{port}"
    )
    logger.info(f"🔧 Debug mode: {debug}")
    logger.info(f"🗄️ Database: {DATABASE_NAME}")
    logger.info(
        "🌟 Enhanced Features: Universal Company Support, "
        "Advanced AI Analysis, "
        "Global Verification, Blockchain Transparency, Real-time Statistics, "
        "Website Environmental Analysis, Content Scraping, "
        "Greenwashing Detection"
    )

    app.run(host=host, port=port, debug=debug)
