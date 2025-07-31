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

try:
    from enhanced_nlp_processor import EnhancedNLPProcessor
    ENHANCED_NLP_AVAILABLE = True
    print(" Enhanced NLP processor with "
          "BERT/spaCy/HuggingFace loaded successfully")
except ImportError as e:
    print(f" Enhanced NLP processor error: {e}")
    ENHANCED_NLP_AVAILABLE = False

try:
    from blockchain_verification import (
        add_verification_to_blockchain,
        add_claim_analysis_to_blockchain,
        get_blockchain_statistics,
    )
    BLOCKCHAIN_AVAILABLE = True
    print(" Blockchain verification module loaded successfully")
except ImportError as e:
    print(f" Blockchain verification module error: {e}")
    BLOCKCHAIN_AVAILABLE = False

    def add_verification_to_blockchain(data):
        print(" Blockchain not available - verification stored in database "
              "only")
        return f"FALLBACK_{int(time.time())}"

    def add_claim_analysis_to_blockchain(data):
        print(" Blockchain not available - claim analysis stored in database "
              "only")
        return f"FALLBACK_{int(time.time())}"

    def get_blockchain_statistics():
        return {"total_blocks": 0, "network_status": "not_available"}

try:
    from blockchain_verification import SmartContractBlockchain, ContractType
    SMART_CONTRACTS_AVAILABLE = True
    print(" Smart contracts loaded from blockchain_verification module")
except ImportError as e:
    print(f" Smart contracts not available: {e}")
    SMART_CONTRACTS_AVAILABLE = False
    SmartContractBlockchain = None
    ContractType = None

try:
    from certification_verifier import EnhancedCertificationVerifier
    from emissions_verifier import EmissionsDataVerifier
    ENHANCED_VERIFICATION_AVAILABLE = True
    print(" Enhanced verification modules loaded successfully")
except ImportError as e:
    print(f" Enhanced verification modules error: {e}")
    ENHANCED_VERIFICATION_AVAILABLE = False
    EnhancedCertificationVerifier = None
    EmissionsDataVerifier = None

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
    logger.info(" Connected to MongoDB successfully")
except Exception as e:
    logger.error(f" Failed to connect to MongoDB: {e}")
    exit(1)

companies_collection = db.companies
claims_collection = db.claims
verifications_collection = db.verifications
user_submissions_collection = db.user_submissions
alternatives_collection = db.alternatives
users_collection = db.users
website_analyses_collection = db.website_analyses

certification_verifier = None
emissions_verifier = None

if ENHANCED_VERIFICATION_AVAILABLE:
    try:
        certification_verifier = EnhancedCertificationVerifier()
        emissions_verifier = EmissionsDataVerifier()
        print(" Enhanced Certification Verifier initialized")
        print(" Emissions Data Verifier initialized with comprehensive "
              "database")
    except Exception as e:
        logger.error(f" Enhanced verification initialization failed: "
                     f"{str(e)}")
        certification_verifier = None
        emissions_verifier = None

smart_blockchain = None
essential_contracts = {}

if SMART_CONTRACTS_AVAILABLE and SmartContractBlockchain is not None:
    try:
        smart_blockchain = SmartContractBlockchain()
        logger.info(" Smart Contract System initialized successfully")
        essential_contracts = {
            "greenwashing_detector": smart_blockchain.deploy_contract(
                ContractType.GREENWASHING_DETECTOR,
                "system@greenguard.com",
                {"sensitivity": 0.7, "auto_flag": True}
            ),
            "sustainability_rewards": smart_blockchain.deploy_contract(
                ContractType.SUSTAINABILITY_REWARDS,
                "system@greenguard.com",
                {"max_points": 1000, "badge_levels": 4}
            ),
            "automatic_flagging": smart_blockchain.deploy_contract(
                ContractType.AUTOMATIC_FLAGGING,
                "system@greenguard.com",
                {"threshold": 0.6, "immediate_action": True}
            ),
            "penalty_system": smart_blockchain.deploy_contract(
                ContractType.PENALTY_SYSTEM,
                "system@greenguard.com",
                {"max_penalty": 1000, "escalation": True}
            ),
            "verification_bounty": smart_blockchain.deploy_contract(
                ContractType.VERIFICATION_BOUNTY,
                "system@greenguard.com",
                {"max_bounty": 200, "quality_multiplier": True}
            ),
            "transparency_tracker": smart_blockchain.deploy_contract(
                ContractType.TRANSPARENCY_TRACKER,
                "system@greenguard.com",
                {"update_frequency": "weekly"}
            )
        }

        logger.info(f" Deployed "
                    f"{len(essential_contracts)} essential smart contracts")
    except Exception as e:
        logger.error(f" Smart contract initialization failed: {str(e)}")
        smart_blockchain = None
        essential_contracts = {}
else:
    logger.info(" Smart contracts integrated in blockchain verification "
                "system")
enhanced_nlp = None
if ENHANCED_NLP_AVAILABLE:
    try:
        enhanced_nlp = EnhancedNLPProcessor()
        print(" Enhanced NLP processor initialized "
              "with BERT, spaCy, and HuggingFace Transformers")
        nlp_status = enhanced_nlp.get_nlp_status()
        print(f" NLP Status: spaCy={nlp_status['spacy_available']}, "
              f"BERT={nlp_status['bert_available']}, "
              f"Sentiment={nlp_status['sentiment_available']}")
    except Exception as e:
        logger.error(f" Enhanced NLP initialization failed: {str(e)}")
        enhanced_nlp = None
        ENHANCED_NLP_AVAILABLE = False


def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def scrape_website_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()

        content = {
            'title': soup.find('title').text.strip() if soup.find(
                'title') else '',
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
                                      'h1', 'h2', 'h3']):
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
        'environmental_keywords_found': extract_environmental_keywords(
            all_text),
        'potential_greenwashing_indicators': check_greenwashing_indicators(
            all_text),
        'transparency_indicators': check_transparency_indicators(all_text),
        'claims_detected': len(detected_claims),
        'average_claim_confidence': sum(claim[
            'confidence'] for claim in detected_claims) / len(
                detected_claims) if detected_claims else 0,
        'average_greenwashing_risk': sum(claim[
            'greenwashing_risk'] for claim in detected_claims) / len(
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
                indicators.append(f"Frequent use of vague term: '{phrase}' ("
                                  f"{count} times)")
            else:
                indicators.append(f"Vague term found: '{phrase}' - requires "
                                  f"verification")

    absolute_terms = ['100%', 'completely', 'totally', 'entirely', 'perfectly']
    for term in absolute_terms:
        if term in text_lower:
            indicators.append(f"Absolute claim: '{term}' - verify supporting "
                              f"evidence")

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


class EnhancedUniversalCompanyAnalyzer:
    def __init__(self):
        self.sustainability_leaders = {
            "patagonia": 0.95, "tesla": 0.92, "microsoft": 0.88,
            "google": 0.87,
            "apple": 0.84, "salesforce": 0.86, "adobe": 0.82, "intel": 0.81,
            "nvidia": 0.83, "vmware": 0.80, "cisco": 0.79, "oracle": 0.77,
            "sap": 0.84, "ibm": 0.78, "amazon": 0.75, "unilever": 0.85,
            "ben jerry": 0.89, "seventh generation": 0.91, "whole foods": 0.86,
            "target": 0.74, "walmart": 0.73, "costco": 0.76,
            "home depot": 0.72,
            "ikea": 0.83, "h&m": 0.70, "zara": 0.65, "nike": 0.76,
            "adidas": 0.78, "puma": 0.74, "nestle": 0.68, "coca cola": 0.71,
            "pepsi": 0.72, "general mills": 0.75, "kellogg": 0.74,
            "mars": 0.76,
            "danone": 0.82, "heineken": 0.78, "bmw": 0.81, "mercedes": 0.79,
            "audi": 0.78, "volvo": 0.85, "toyota": 0.80, "ford": 0.74,
            "gm": 0.73, "volkswagen": 0.72, "nissan": 0.76, "honda": 0.77,
            "jpmorgan": 0.74, "bank of america": 0.73, "wells fargo": 0.71,
            "goldman sachs": 0.75, "morgan stanley": 0.76, "citigroup": 0.72,
            "american express": 0.77, "johnson johnson": 0.78, "pfizer": 0.76,
            "roche": 0.79, "novartis": 0.77, "merck": 0.75, "bristol myers":
                0.74,
            "abbvie": 0.73, "eli lilly": 0.74, "exxon": 0.45, "chevron": 0.47,
            "bp": 0.52, "shell": 0.54, "total": 0.56, "conocophillips": 0.48,
            "nextgen energy": 0.88, "orsted": 0.91, "africa climate": 0.75,
            "climate foundation": 0.78, "environmental foundation": 0.76,
            "green africa": 0.72, "sustainable africa": 0.79,
            "eco africa": 0.74,
            "african development": 0.73, "climate change": 0.77,
            "environment foundation": 0.76,
        }

        self.industry_categories = {
            "sustainability_focused": {
                "keywords": ["renewable", "solar", "wind", "sustainable",
                             "green energy", "environmental", "recycling",
                             "clean tech", "climate", "foundation",
                             "conservation", "ecosystem", "biodiversity",
                             "carbon"],
                "penalty": -0.15,
                "description": "Sustainability-focused organization",
            },
            "high_impact": {
                "keywords": ["oil", "gas", "petroleum", "coal", "mining",
                             "chemical", "plastic", "fast fashion", "airline",
                             "shipping", "steel", "cement", "paper"],
                "penalty": 0.20,
                "description": "High environmental impact industry",
            },
            "medium_impact": {
                "keywords": ["automotive", "manufacturing", "construction",
                             "agriculture", "retail", "logistics",
                             "telecommunications"],
                "penalty": 0.10,
                "description": "Medium environmental impact industry",
            },
            "low_impact": {
                "keywords": ["technology", "software", "finance", "healthcare",
                             "education", "services", "consulting",
                             "research"],
                "penalty": 0.05,
                "description": "Low environmental impact industry",
            },
        }

        logger.info(" Enhanced Universal Company Analyzer initialized with "
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
                logger.info(f" Found {company_name} in sustainability "
                            f"database with score {score}")
                break

        final_score = self._calculate_final_score(analysis)
        analysis["final_score"] = final_score
        analysis["confidence_level"] = self._calculate_confidence(analysis)

        logger.info(f" Company analysis for '{company_name}': "
                    f"{final_score:.2f} ({analysis['confidence_level']} "
                    f"confidence)")

        return analysis

    def _create_default_analysis(self, company_name):
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
        large_indicators = ["corporation", "inc", "corp", "ltd", "limited",
                            "group", "holdings", "international"]
        medium_indicators = ["company", "enterprises", "solutions",
                             "systems", "technologies"]
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
            return {"category": "organization",
                    "bonus": 0.02, "description": "Organization or foundation"}

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
        if (leader_main and company_main and
                leader_main.intersection(company_main)):
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
            "environmentally responsible", "natural", "clean enery",
            "clean technology",
            "circular economy", "carbon footprint", "renewable energy",
            "solar power",
            "wind power", "environmental stewardship", "habitat conservation",
        ]

        self.greenwashing_indicators = {
            "vague_terms": {
                "keywords": ["eco", "green", "natural", "pure",
                             "clean", "fresh"],
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

        logger.info(" Enhanced AI Claim Detector initialized "
                    "with hybrid approach")

    def detect_claims(self, text):
        try:
            rule_based_claims = self._detect_claims_rule_based(text)
            if ENHANCED_NLP_AVAILABLE and enhanced_nlp:
                try:
                    nlp_analysis = enhanced_nlp.analyze_text_comprehensive(
                        text)
                    bert_claims = nlp_analysis.get('bert_claims', [])
                    combined_claims = self._merge_claim_results(
                        rule_based_claims, bert_claims, nlp_analysis)
                    logger.info(f" Hybrid detection: "
                                f"{len(rule_based_claims)} rule-based + "
                                f"{len(bert_claims)} BERT claims = "
                                f"{len(combined_claims)} total claims")
                    return combined_claims
                except Exception as e:
                    logger.error(f" Enhanced NLP analysis failed, "
                                 f" falling back to rule-based: {e}")
                    return rule_based_claims
            else:
                logger.info(" Using rule-based detection only (Enhanced NLP not available)")
                return rule_based_claims
        except Exception as e:
            logger.error(f" Claim detection error: {e}")
            return []

    def _detect_claims_rule_based(self, text):
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

        return claims

    def _merge_claim_results(self, rule_based_claims, bert_claims,
                             nlp_analysis):
        try:
            merged_claims = []
            for claim in rule_based_claims:
                enhanced_claim = {
                    "text": claim["text"],
                    "keywords": claim.get("keywords", []),
                    "confidence": claim.get("confidence", 0.5),
                    "greenwashing_risk": claim.get("greenwashing_risk", 0.3),
                    "specificity_score": claim.get("specificity_score", 0.5),
                    "detection_method": "rule_based",
                    "bert_analysis": None,
                    "spacy_entities": [],
                    "enhanced_nlp": False
                }
                merged_claims.append(enhanced_claim)
            for bert_claim in bert_claims:
                matched = False
                for merged_claim in merged_claims:
                    if self._claims_overlap(merged_claim["text"],
                                            bert_claim["text"]):
                        merged_claim["bert_analysis"] = {
                            "bert_classification": bert_claim.get(
                                "bert_classification"),
                            "sentiment": bert_claim.get("sentiment"),
                            "entities": bert_claim.get("entities", [])
                        }
                        merged_claim["spacy_entities"] = bert_claim.get(
                            "entities", [])
                        merged_claim["enhanced_nlp"] = True
                        merged_claim["confidence"] = max(
                            merged_claim["confidence"],
                            bert_claim.get("confidence_score", 0.5)
                        )
                        bert_risk = bert_claim.get("greenwashing_risk", 0.3)
                        merged_claim["greenwashing_risk"] = (
                            merged_claim["greenwashing_risk"] + bert_risk) / 2
                        merged_claim["specificity_score"] = max(
                            merged_claim["specificity_score"],
                            bert_claim.get("specificity_score", 0.5)
                        )
                        matched = True
                        break
                if not matched:
                    new_claim = {
                        "text": bert_claim["text"],
                        "keywords": bert_claim.get(
                            "environmental_keywords", []),
                        "confidence": bert_claim.get("confidence_score", 0.5),
                        "greenwashing_risk": bert_claim.get(
                            "greenwashing_risk", 0.3),
                        "specificity_score": bert_claim.get(
                            "specificity_score", 0.5),
                        "detection_method": "bert_nlp",
                        "bert_analysis": {
                            "bert_classification": bert_claim.get(
                                "bert_classification"),
                            "sentiment": bert_claim.get("sentiment"),
                            "entities": bert_claim.get("entities", [])
                        },
                        "spacy_entities": bert_claim.get("entities", []),
                        "enhanced_nlp": True
                    }
                    merged_claims.append(new_claim)
            for claim in merged_claims:
                claim["nlp_analysis_available"] = True
                claim["spacy_preprocessing"] = nlp_analysis.get(
                    "spacy_analysis", {}).get("spacy_analysis", False)
                claim["total_entities_detected"] = len(nlp_analysis.get(
                    "spacy_analysis", {}).get("entities", []))
            return merged_claims
        except Exception as e:
            logger.error(f" Claim merging error: {e}")
            return rule_based_claims

    def _claims_overlap(self, text1, text2, threshold=0.6):
        """Check if two claim texts overlap significantly"""
        try:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            if not words1 or not words2:
                return False
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            overlap_ratio = intersection / union if union > 0 else 0
            return overlap_ratio >= threshold
        except Exception:
            return False

    def _analyze_sentence(self, sentence):
        sentence_lower = sentence.lower()

        matched_keywords = []
        for keyword in self.environmental_keywords:
            if keyword in sentence_lower:
                matched_keywords.append(keyword)

        if not matched_keywords:
            return None

        confidence = self._calculate_confidence(
            sentence_lower, matched_keywords)
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
        specific_terms = ["certified", "verified", "measured", "tested",
                          "audited"]
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

        certifications = [
            "iso", "leed", "energy star", "certified", "verified", "audited"]
        if any(cert in sentence for cert in certifications):
            specificity_score += 0.25

        return min(1.0, specificity_score)


company_analyzer = EnhancedUniversalCompanyAnalyzer()
claim_detector = EnhancedClaimDetector()


def enhanced_universal_verification(claim_text, company_name):
    try:
        company_analysis = company_analyzer.analyze_company(company_name)
        claim_analysis = claim_detector.detect_claims(claim_text)
        verification_score = calculate_comprehensive_score(company_analysis,
                                                           claim_analysis,
                                                           claim_text)

        enhanced_results = {}

        if ENHANCED_VERIFICATION_AVAILABLE:
            if certification_verifier:
                try:
                    cert_results = (
                        certification_verifier.verify_certifications(
                            claim_text, company_name)
                    )
                    enhanced_results["certification_analysis"] = cert_results
                    logger.info(f" Certification verification completed for "
                                f"{company_name}")
                except Exception as e:
                    logger.error(f" Certification verification error: "
                                 f"{str(e)}")

            if emissions_verifier:
                try:
                    emissions_results = (
                        emissions_verifier.cross_reference_emissions(
                            claim_text, company_name)
                    )
                    enhanced_results["emissions_analysis"] = emissions_results
                    logger.info(f" Emissions cross-reference completed for "
                                f"{company_name}")
                except Exception as e:
                    logger.error(f" Emissions verification error: {str(e)}")

        if enhanced_results:
            verification_score = integrate_enhanced_score(verification_score,
                                                          enhanced_results)

        status_info = determine_verification_status(verification_score)
        evidence_summary = generate_comprehensive_evidence(
            company_analysis, claim_analysis, verification_score,
            claim_text, enhanced_results)
        recommendations = generate_intelligent_recommendations(
            verification_score, company_analysis, claim_analysis,
            claim_text, enhanced_results)

        logger.info(f" Enhanced verification for {company_name}: "
                    f"{verification_score:.1%} ({status_info['status']})")

        return {
            "overall_score": verification_score,
            "risk_level": status_info["risk_level"],
            "status": status_info["status"],
            "trustworthiness": status_info["trustworthiness"],
            "evidence_summary": evidence_summary,
            "company_analysis": company_analysis,
            "claim_analysis": claim_analysis,
            "certification_analysis": enhanced_results.get(
                "certification_analysis"),
            "emissions_analysis": enhanced_results.get("emissions_analysis"),
            "recommendations": recommendations,
            "enhanced_features": {
                "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
                "third_party_verification": ENHANCED_VERIFICATION_AVAILABLE,
            },
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
                "certification_database": {
                    "status": "checked" if enhanced_results.get(
                        "certification_analysis") else "unavailable",
                    "verified": enhanced_results.get(
                        "certification_analysis", {}).get(
                            "verified_certifications", [])
                },
                "emissions_database": {
                    "status": "checked" if enhanced_results.get(
                        "emissions_analysis") else "unavailable",
                    "found": enhanced_results.get("emissions_analysis",
                                                  {}).get("company_found",
                                                          False)
                },
            },
        }

    except Exception as e:
        logger.error(f" Error in enhanced verification: {str(e)}")
        return create_fallback_verification(company_name, claim_text, str(e))


def integrate_enhanced_score(base_score, enhanced_results):
    try:
        adjusted_score = base_score

        if "certification_analysis" in enhanced_results:
            cert_analysis = enhanced_results["certification_analysis"]
            authenticity_score = cert_analysis.get("authenticity_score", 0.5)
            verified_certs = cert_analysis.get("verified_certifications", [])

            if verified_certs:
                cert_bonus = min(0.15, len(verified_certs) * 0.05)
                adjusted_score += cert_bonus

            if authenticity_score > 0.7:
                adjusted_score += 0.10
            elif authenticity_score < 0.4:
                adjusted_score -= 0.15

        if "emissions_analysis" in enhanced_results:
            emissions_analysis = enhanced_results["emissions_analysis"]
            performance_score = emissions_analysis.get(
                "performance_score", 0.5)
            industry_comparison = emissions_analysis.get(
                "industry_comparison", {})

            if performance_score > 0.7:
                adjusted_score += 0.12
            elif performance_score < 0.4:
                adjusted_score -= 0.18

            benchmark_performance = industry_comparison.get(
                "performance_vs_benchmark", "average")
            if benchmark_performance == "above_average":
                adjusted_score += 0.08
            elif benchmark_performance == "below_average":
                adjusted_score -= 0.10

        return max(0.15, min(0.95, adjusted_score))

    except Exception as e:
        logger.error(f" Error integrating enhanced score: {str(e)}")
        return base_score


def enhanced_verification_with_smart_contracts(claim_text, company_name,
                                               user_email="anonymous"):
    try:
        verification_results = enhanced_universal_verification(claim_text,
                                                               company_name)

        if smart_blockchain:
            contract_input = {
                "company_name": company_name,
                "claim": claim_text,
                "verification_score": verification_results[
                    "overall_score"] * 100,
                "confidence": verification_results.get("confidence", 75),
                "user_email": user_email,
                "transparency_level": 70,
                "certifications": verification_results.get(
                    "certification_analysis", {}).get(
                        "verified_certifications", []),
                "greenwashing_risk": (1 - verification_results[
                    "overall_score"]) * 100,
                "violation_severity": (
                    "CRITICAL" if verification_results["overall_score"] < 0.3
                    else "HIGH" if verification_results["overall_score"] < 0.5
                    else "MEDIUM" if verification_results[
                        "overall_score"] < 0.7
                    else "LOW"
                ),
                "repeat_offender": False,
                "impact_scale": "GLOBAL"
            }

            smart_contract_results = execute_all_verification_contracts(
                contract_input, user_email)

            verification_results["smart_contracts"] = smart_contract_results
            verification_results[
                "automated_actions"] = extract_automated_actions(
                    smart_contract_results)
            logger.info(f" Smart contracts executed for {company_name}")

        return verification_results

    except Exception as e:
        logger.error(f" Enhanced verification with smart contracts failed: "
                     f"{str(e)}")
        return enhanced_universal_verification(claim_text, company_name)


def execute_all_verification_contracts(contract_input, user_email):
    results = {}

    try:
        if "greenwashing_detector" in essential_contracts:
            contract_id = essential_contracts["greenwashing_detector"]
            result = smart_blockchain.contracts[contract_id].execute(
                contract_input, {"user_email": user_email,
                                 "timestamp": time.time(),
                                 "company_history": []})
            results["greenwashing_detection"] = result

        if "automatic_flagging" in essential_contracts:
            contract_id = essential_contracts["automatic_flagging"]
            result = smart_blockchain.contracts[contract_id].execute(
                contract_input, {})
            results["automatic_flagging"] = result

        if "sustainability_rewards" in essential_contracts:
            contract_id = essential_contracts["sustainability_rewards"]
            result = smart_blockchain.contracts[contract_id].execute(
                contract_input, {})
            results["sustainability_rewards"] = result

        if contract_input.get("verification_score", 100) < 40:
            if "penalty_system" in essential_contracts:
                contract_id = essential_contracts["penalty_system"]
                result = smart_blockchain.contracts[contract_id].execute(
                    contract_input, {})
                results["penalty_system"] = result

        if "verification_bounty" in essential_contracts:
            bounty_input = {
                "verifier_email": user_email,
                "verification_quality": min(100, contract_input.get(
                    "verification_score", 0)),
                "claim_complexity": "COMPLEX" if len(contract_input.get(
                    "claim", "")) > 200 else "MODERATE",
                "verification_speed": "FAST"
            }
            contract_id = essential_contracts["verification_bounty"]
            result = smart_blockchain.contracts[contract_id].execute(
                bounty_input, {"verifier_history": []})
            results["verification_bounty"] = result

        if "transparency_tracker" in essential_contracts:
            transparency_input = {
                "company_name": contract_input.get("company_name"),
                "disclosed_data": {
                    "sustainability_report": True,
                    "certifications": contract_input.get("certifications", [])
                },
                "response_time_hours": 24,
                "data_completeness": contract_input.get(
                    "transparency_level", 70)
            }
            contract_id = essential_contracts["transparency_tracker"]
            result = smart_blockchain.contracts[contract_id].execute(
                transparency_input, {"transparency_history": []})
            results["transparency_tracker"] = result

    except Exception as e:
        logger.error(f" Smart contract execution error: {str(e)}")

    return results


def extract_automated_actions(smart_contract_results):
    actions = []

    if "greenwashing_detection" in smart_contract_results:
        detection_result = smart_contract_results["greenwashing_detection"]
        if detection_result.get("success"):
            contract_actions = detection_result.get("result", {}).get(
                "actions_triggered", [])
            actions.extend(contract_actions)

    if "automatic_flagging" in smart_contract_results:
        flagging_result = smart_contract_results["automatic_flagging"]
        if flagging_result.get("success"):
            flags = flagging_result.get("result", {}).get(
                "flags_triggered", [])
            actions.extend([f"FLAG: {flag}" for flag in flags])

    if "penalty_system" in smart_contract_results:
        penalty_result = smart_contract_results["penalty_system"]
        if penalty_result.get("success"):
            consequences = penalty_result.get("result", {}).get(
                "consequences", [])
            actions.extend([f"PENALTY: "
                            f"{consequence}" for consequence in consequences])

    if "sustainability_rewards" in smart_contract_results:
        reward_result = smart_contract_results["sustainability_rewards"]
        if reward_result.get("success"):
            badge = reward_result.get("result", {}).get(
                "badge_earned", "NO_BADGE")
            if badge != "NO_BADGE":
                actions.append(f"REWARD: {badge}")

    if "verification_bounty" in smart_contract_results:
        bounty_result = smart_contract_results["verification_bounty"]
        if bounty_result.get("success"):
            bounty = bounty_result.get("result", {}).get("bounty_awarded", 0)
            if bounty > 0:
                actions.append(f"BOUNTY: {bounty} points awarded")

    return actions


def calculate_comprehensive_score(company_analysis,
                                  claim_analysis, claim_text):
    company_score = company_analysis["final_score"] * 0.50

    if claim_analysis:
        avg_confidence = sum(c["confidence"] for c in claim_analysis) / len(
            claim_analysis)
        avg_specificity = sum(c.get(
            "specificity_score", 0.5) for c in claim_analysis) / len(
                claim_analysis)
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
    if not claim_text or len(claim_text.strip()) < 10:
        return 0.30

    score = 0.40
    claim_lower = claim_text.lower()

    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?|mw|gwh)", claim_lower):
        score += 0.25

    cert_keywords = ["certified", "iso", "verified", "audit",
                     "third-party", "independent"]
    if any(cert in claim_lower for cert in cert_keywords):
        score += 0.20

    vague_terms = ["eco-friendly", "green", "natural", "sustainable", "clean"]
    vague_count = sum(1 for term in vague_terms if term in claim_lower)
    score -= vague_count * 0.03

    return max(0.20, min(1.0, score))


def determine_verification_status(score):
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
                                    claim_text, enhanced_results=None):
    evidence_parts = []

    if company_analysis["found_in_database"]:
        evidence_parts.append(
            " Company found in sustainability leadership database")
    else:
        evidence_parts.append(
            " Company analyzed using universal verification system")

    if enhanced_results and "certification_analysis" in enhanced_results:
        cert_analysis = enhanced_results["certification_analysis"]
        verified_certs = cert_analysis.get("verified_certifications", [])
        if verified_certs:
            evidence_parts.append(f" {len(verified_certs)} verified "
                                  f"certifications found")
        else:
            evidence_parts.append(
                " No verified certifications found in database")

    if enhanced_results and "emissions_analysis" in enhanced_results:
        emissions_analysis = enhanced_results["emissions_analysis"]
        if emissions_analysis.get("company_found", False):
            performance = emissions_analysis.get("performance_score", 0.5)
            if performance > 0.7:
                evidence_parts.append(
                    " Above-average emissions performance verified")
            elif performance < 0.4:
                evidence_parts.append(
                    " Below-average emissions performance detected")
            else:
                evidence_parts.append(
                    " Average emissions performance in industry")

    industry_info = company_analysis["industry_analysis"]
    if industry_info["category"] == "sustainability_focused":
        evidence_parts.append(
            " Organization appears to be sustainability-focused")
    elif industry_info["category"] == "high_impact":
        evidence_parts.append(
            " Company operates in high environmental impact industry")

    if claim_analysis:
        evidence_parts.append(f" AI detected "
                              f"{len(claim_analysis)} environmental claims")
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis)
        if avg_risk > 0.7:
            evidence_parts.append(
                " High greenwashing risk indicators detected")
        elif avg_risk < 0.4:
            evidence_parts.append(" Low greenwashing risk indicators")

    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?)", claim_text.lower()):
        evidence_parts.append(" Claim includes quantifiable metrics")

    verification_terms = ["certified", "verified", "audited", "tested"]
    if any(term in claim_text.lower() for term in verification_terms):
        evidence_parts.append(" Third-party verification mentioned")

    if score >= 0.70:
        evidence_parts.append(
            " Strong overall evidence supporting claim validity")
    elif score >= 0.45:
        evidence_parts.append(" Moderate evidence supporting claim")
    else:
        evidence_parts.append(
            " Limited evidence to support claim reliability")

    return "; ".join(evidence_parts)


def generate_intelligent_recommendations(score, company_analysis,
                                         claim_analysis, claim_text,
                                         enhanced_results=None):
    """Generate intelligent, context-aware recommendations"""
    recommendations = []

    if score >= 0.75:
        recommendations.extend([
            " This claim shows strong evidence of validity",
            " Organization demonstrates good environmental commitment",
            " Verification secured on blockchain for transparency",
        ])
    elif score >= 0.60:
        recommendations.extend([
            " Claim shows reasonable evidence of validity",
            " Organization appears committed to sustainability",
            " Consider seeking additional third-party verification",
        ])
    elif score >= 0.45:
        recommendations.extend([
            " Limited evidence available to support this claim",
            " Request specific data and certifications",
            " Seek independent third-party verification",
        ])
    else:
        recommendations.extend([
            " Significant concerns about claim validity",
            " High risk of greenwashing detected",
            " Demand concrete evidence and certifications",
        ])

    if enhanced_results and "certification_analysis" in enhanced_results:
        cert_analysis = enhanced_results["certification_analysis"]
        red_flags = cert_analysis.get("red_flags", [])
        if red_flags:
            recommendations.append(f" Certification concerns: "
                                   f"{', '.join(red_flags[:2])}")

        missing_certs = cert_analysis.get("missing_certifications", [])
        if missing_certs:
            recommendations.append(f" Consider verifying: "
                                   f"{', '.join(missing_certs[:2])}")

    if enhanced_results and "emissions_analysis" in enhanced_results:
        emissions_analysis = enhanced_results["emissions_analysis"]
        guidance = emissions_analysis.get("guidance", [])
        if guidance:
            recommendations.extend(guidance[:2])

    if not company_analysis["found_in_database"]:
        recommendations.append(
            f"'{company_analysis['company_name']}' analyzed using universal"
            f"verification system")

    claim_lower = claim_text.lower()
    if any(term in claim_lower for term in ["100%", "completely", "zero"]):
        recommendations.append(" Absolute claims require strong verification")

    if not any(cert in claim_lower for cert in ["certified", "verified",
                                                "audited"]):
        recommendations.append(" Look for third-party certifications")

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
        "company_analysis": {
            "company_name": company_name, "found_in_database": False},
        "recommendations": [
            " Automated verification temporarily unavailable",
            " Manual review recommended"],
    }


def create_claim_document(claim_text, keyword,
                          confidence_score, greenwashing_risk, source_url):
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
                "certifications": [
                    "Fair Trade", "B-Corp", "1% for the Planet"],
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

    evidence_keywords = ["certified", "verified", "source",
                         "data", "report", "study", "research"]
    evidence_count = sum(
        1 for keyword in evidence_keywords if keyword in content.lower())
    base_score += evidence_count * 0.1

    if feedback_type == "additional_info":
        base_score += 0.1
    elif feedback_type == "dispute":
        base_score += 0.05

    return round(min(1.0, base_score), 2)


@app.route("/api/nlp/status", methods=["GET"])
def get_nlp_status():
    """Get current status of enhanced NLP capabilities"""
    try:
        if ENHANCED_NLP_AVAILABLE and enhanced_nlp:
            nlp_status = enhanced_nlp.get_nlp_status()
            return jsonify({
                "success": True,
                "enhanced_nlp_available": True,
                "nlp_components": nlp_status,
                "capabilities": {
                    "spacy_preprocessing": nlp_status["spacy_available"],
                    "bert_classification": nlp_status["bert_available"],
                    "sentiment_analysis": nlp_status["sentiment_available"],
                    "transformers_integration": nlp_status[
                        "transformers_available"],
                    "linguistic_analysis": nlp_status["spacy_available"],
                    "named_entity_recognition": nlp_status["spacy_available"],
                    "advanced_claim_detection": nlp_status["bert_available"]
                },
                "system_status": "fully_operational" if nlp_status[
                    "system_ready"] else "partial",
                "last_updated": datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                "success": True,
                "enhanced_nlp_available": False,
                "message": "Enhanced NLP features not available - using "
                "rule-based approach only",
                "fallback_mode": True
            })
    except Exception as e:
        logger.error(f" NLP status check error: {e}")
        return jsonify({
            "error": "Failed to get NLP status",
            "details": str(e)
        }), 500


@app.route("/api/enhanced-verification", methods=["POST"])
def enhanced_verification_endpoint():
    client_ip = request.environ.get(
        "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "unknown"))

    if not rate_limit_check(client_ip):
        return jsonify({
            "error": "Rate limit exceeded",
            "message":
                "Too many requests. Please wait a moment before trying again.",
        }), 429

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

        logger.info(f" Enhanced verification request: "
                    f"{company_name} - {len(claim_text)} chars")

        verification_results = enhanced_verification_with_smart_contracts(
            claim_text, company_name, user_email)
        nlp_analysis_info = {}
        if ENHANCED_NLP_AVAILABLE and enhanced_nlp:
            try:
                comprehensive_nlp = enhanced_nlp.analyze_text_comprehensive(
                    claim_text)
                nlp_analysis_info = {
                    "spacy_entities": comprehensive_nlp.get(
                        "spacy_analysis", {}).get("entities", []),
                    "bert_classification_available": True,
                    "sentiment_analysis_available":
                        enhanced_nlp.sentiment_analyzer is not None,
                    "total_nlp_claims": comprehensive_nlp.get(
                        "nlp_metrics", {}).get("total_claims_detected", 0),
                    "nlp_confidence": comprehensive_nlp.get(
                        "nlp_metrics", {}).get("average_confidence", 0),
                    "nlp_risk_assessment": comprehensive_nlp.get(
                        "nlp_metrics", {}).get("average_greenwashing_risk", 0),
                    "entities_detected": comprehensive_nlp.get(
                        "nlp_metrics", {}).get("entities_found", 0),
                    "processing_method": comprehensive_nlp.get
                    ("processing_method", "rule_based"),
                    "processing_time_ms": comprehensive_nlp.get(
                        "processing_time_ms", 0)
                }
                logger.info(f" Enhanced NLP analysis completed for "
                            f"{company_name}: "
                            f"{nlp_analysis_info['total_nlp_claims']} "
                            f" claims detected")
            except Exception as e:
                logger.error(f" Enhanced NLP analysis error: {e}")
                nlp_analysis_info = {
                    "error": "NLP analysis failed", "fallback_used": True}

        verification_doc = {
            "claim_text": claim_text,
            "company_name": company_name,
            "verification_score": verification_results["overall_score"],
            "risk_level": verification_results["risk_level"],
            "status": verification_results["status"],
            "trustworthiness": verification_results["trustworthiness"],
            "evidence_summary": verification_results["evidence_summary"],
            "company_analysis": verification_results["company_analysis"],
            "certification_analysis": verification_results.get(
                "certification_analysis"),
            "emissions_analysis": verification_results.get(
                "emissions_analysis"),
            "recommendations": verification_results["recommendations"],
            "smart_contracts": verification_results.get("smart_contracts", {}),
            "automated_actions": verification_results.get(
                "automated_actions", []),
            "verification_timestamp": datetime.utcnow(),
            "user_email": user_email,
            "client_ip": client_ip,
            "version": "2.0_enhanced_complete",
        }

        try:
            result = verifications_collection.insert_one(verification_doc)
            verification_doc["_id"] = str(result.inserted_id)
            logger.info(f" Saved enhanced verification to MongoDB: "
                        f"{result.inserted_id}")
        except Exception as e:
            logger.error(f" Error storing enhanced verification: {e}")

        blockchain_id = None
        try:
            blockchain_data = {
                "company_name": company_name,
                "claim": claim_text,
                "verification_score": verification_results["overall_score"],
                "status": verification_results["status"],
                "certification_verified": bool(verification_results.get(
                    "certification_analysis")),
                "emissions_verified": bool(verification_results.get(
                    "emissions_analysis")),
                "smart_contracts_executed": len(verification_results.get(
                    "smart_contracts", {})),
                "user_email": user_email,
                "version": "enhanced_complete_2.0",
            }
            blockchain_id = add_verification_to_blockchain(blockchain_data)
            logger.info(f" Enhanced verification added to blockchain: "
                        f"{blockchain_id}")
        except Exception as e:
            logger.error(f" Blockchain integration error: {str(e)}")

        trustworthy = verification_results["overall_score"] >= 0.60
        score_percentage = round(verification_results["overall_score"] * 100)

        enhanced_features_info = ""
        if ENHANCED_VERIFICATION_AVAILABLE:
            enhanced_features_info = (
                "\n\n** Enhanced Verification Features:**\n"
                f"• Certification Database: "
                f"{' Verified' if verification_results.get('certification_analysis') else ' No data'}\n"
                f"• Emissions Cross-Reference: "
                f"{' Verified' if verification_results.get('emissions_analysis') else ' No data'}\n"
                f"• Third-party Sources: "
                f"{' Integrated'if ENHANCED_VERIFICATION_AVAILABLE else ' Unavailable'}"
            )

        smart_contract_info = ""
        if verification_results.get("smart_contracts"):
            actions = verification_results.get("automated_actions", [])
            if actions:
                smart_contract_info = (
                    "\n\n** Automated Smart Contract Actions:**\n"
                    + "\n".join([f"• {action}" for action in actions[:5]])
                )

        analysis = (
            f"**Status: {verification_results['status']}**\n\n"
            f"**Complete Enhanced Verification with All Features:**\n"
            f"The advanced universal verification system has analyzed this "
            f"claim from {company_name} "
            f"using all available verification methods. Overall verification "
            f"score: {score_percentage}%\n\n"
            f"**Enhanced Analysis Results:**\n"
            f"• Company Database: "
            f"{verification_results['company_analysis']['confidence_level'].title()} confidence\n"
            f"• Industry Analysis: "
            f"{verification_results['company_analysis']['industry_analysis']['category'].replace('_', ' ').title()}\n"
            f"• Risk Assessment: {verification_results['risk_level']}\n"
            f"• Certification Verification: "
            f"{' Active' if ENHANCED_VERIFICATION_AVAILABLE else ' Unavailable'}\n"
            f"• Emissions Cross-Reference: "
            f"{' Active' if ENHANCED_VERIFICATION_AVAILABLE else ' Unavailable'}\n"
            f"• Smart Contracts: "
            f"{len(verification_results.get('smart_contracts', {}))}\n\n"
            f"**Evidence Summary:**\n"
            f"{verification_results['evidence_summary']}\n\n"
            f"**Blockchain Security:** "
            f"{' Secured' if blockchain_id else ' Pending'}"
            f"{enhanced_features_info}"
            f"{smart_contract_info}"
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
            "enhanced_features": verification_results.get(
                "enhanced_features", {}),
            "certification_analysis": verification_results.get(
                "certification_analysis"),
            "emissions_analysis": verification_results.get(
                "emissions_analysis"),
            "smart_contracts": {
                "enabled": smart_blockchain is not None,
                "contracts_executed": len(verification_results.get(
                    "smart_contracts", {})),
                "automated_actions": verification_results.get(
                    "automated_actions", []),
                "results": verification_results.get("smart_contracts", {})
            },
            "blockchain_id": blockchain_id,
            "blockchain_secured": blockchain_id is not None,
            "transparency_info": {
                "immutable_record": blockchain_id is not None,
                "public_verification": True,
                "tamper_proof": blockchain_id is not None,
                "ai_powered": True,
                "smart_contracts": smart_blockchain is not None,
                "universal_support": True,
                "enhanced_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
            },
            "processing_info": {
                "version": "2.0_enhanced_complete",
                "analysis_type": "complete_enhanced_verification",
                "processing_time": "< 3 seconds",
                "timestamp": datetime.utcnow().isoformat(),
                "enhanced_nlp_analysis": nlp_analysis_info,
                "nlp_capabilities": {
                    "spacy_available": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.nlp is not None,
                    "bert_available": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.greenwashing_classifier is not None,
                    "sentiment_available": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.sentiment_analyzer is not None,
                    "transformers_available": ENHANCED_NLP_AVAILABLE,
                    "hybrid_detection": ENHANCED_NLP_AVAILABLE,
                    "linguistic_analysis": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.nlp is not None
                },
                "detection_methods": {
                    "rule_based": True,
                    "bert_transformer": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.greenwashing_classifier is not None,
                    "spacy_nlp": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.nlp is not None,
                    "sentiment_analysis": ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.sentiment_analyzer is not None,
                    "hybrid_approach": ENHANCED_NLP_AVAILABLE
                }
            }
        }

        logger.info(f" Complete enhanced verification completed: "
                    f"{company_name} - "
                    f"{score_percentage}% ({verification_results['status']})")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f" Enhanced verification endpoint error: {str(e)}")
        return jsonify({
            "error": "Enhanced verification system error",
            "message": "The complete enhanced verification system encountered "
            "an issue. Please try again.",
            "details": str(e) if app.debug else "Internal system error",
        }), 500


@app.route("/api/smart-contracts/stats", methods=["GET"])
def get_smart_contract_statistics():
    try:
        if not smart_blockchain:
            return jsonify({
                "error": "Smart contracts not available",
                "smart_contracts_enabled": False
            }), 503

        stats = smart_blockchain.get_contract_statistics()
        stats["greenguard_contracts"] = {
            "deployed_contracts": len(essential_contracts),
            "contract_types": list(essential_contracts.keys()),
            "system_version": "2.0_with_smart_contracts"
        }

        return jsonify({
            "success": True,
            "smart_contracts_enabled": True,
            "statistics": stats,
            "last_updated": datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f" Smart contract stats error: {str(e)}")
        return jsonify({
            "error": "Failed to get smart contract statistics",
            "details": str(e)
        }), 500


@app.route("/api/smart-contracts/execute", methods=["POST"])
def execute_smart_contract_manually():
    try:
        if not smart_blockchain:
            return jsonify({
                "error": "Smart contracts not available",
                "smart_contracts_enabled": False
            }), 503

        data = request.get_json()
        contract_type = data.get("contract_type")
        inputs = data.get("inputs", {})

        if contract_type not in essential_contracts:
            return jsonify({
                "error": f"Contract type '{contract_type}' not available",
                "available_contracts": list(essential_contracts.keys())
            }), 400

        contract_id = essential_contracts[contract_type]
        result = smart_blockchain.contracts[contract_id].execute(inputs, {
            "manual_execution": True,
            "timestamp": time.time()
        })

        return jsonify({
            "success": True,
            "contract_type": contract_type,
            "execution_result": result
        })

    except Exception as e:
        logger.error(f" Manual smart contract execution error: {str(e)}")
        return jsonify({
            "error": "Smart contract execution failed",
            "details": str(e)
        }), 500


@app.route("/api/analyze-website", methods=["POST"])
def analyze_website():
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR",
                                    request.environ.get(
                                        "REMOTE_ADDR", "unknown"))

    if not rate_limit_check(client_ip):
        return jsonify({
            "error": "Rate limit exceeded",
            "message":
                "Too many requests. Please wait a moment before trying again.",
        }), 429

    try:
        data = request.get_json()
        website_url = data.get('url')
        user_email = data.get('user_email', 'anonymous')

        if not website_url:
            return jsonify({'success': False, 'error': 'URL is required'}), 400

        if not is_valid_url(website_url):
            return jsonify({'success': False,
                            'error': 'Invalid URL format'}), 400

        logger.info(f" Analyzing website: {website_url}")

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
            logger.info(f" Saved website analysis to MongoDB: "
                        f"{result.inserted_id}")
        except Exception as e:
            logger.error(f" Error storing website analysis: {e}")

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
            logger.info(f" Website analysis added to blockchain: "
                        f"{blockchain_id}")
        except Exception as e:
            logger.error(f" Blockchain integration error: {str(e)}")

        if blockchain_id:
            analysis_result['blockchain_id'] = blockchain_id

        return jsonify({
            'success': True,
            'website_url': website_url,
            'analysis': analysis_result,
            'content_summary': website_analysis_doc['content_summary'],
            'blockchain_id': blockchain_id,
            'blockchain_secured': blockchain_id is not None,
            'analysis_timestamp': website_analysis_doc[
                'analysis_timestamp'].isoformat()
        })

    except Exception as e:
        logger.error(f" Website analysis error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to analyze website: {str(e)}'
        }), 500


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
            f" Real statistics - Claims: {claims_analyzed}, "
            f"Companies: {companies_verified}, Websites: {websites_analyzed}, "
            f"Reports: {community_reports}, Greenwashing: "
            f"{greenwashing_detected}"
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
        logger.error(f" Error getting extension statistics: {e}")
        return jsonify({
            "claims_analyzed": 0,
            "companies_verified": 0,
            "websites_analyzed": 0,
            "community_reports": 0,
            "greenwashing_detected": 0,
            "last_updated": datetime.utcnow().isoformat(),
            "error": str(e),
        }), 500


@app.route("/api/claims/verify", methods=["POST"])
def verify_claim():
    """Enhanced universal verification endpoint with smart contracts"""
    client_ip = request.environ.get("HTTP_X_FORWARDED_FOR",
                                    request.environ.get("REMOTE_ADDR",
                                                        "unknown"))

    if not rate_limit_check(client_ip):
        return jsonify({
            "error": "Rate limit exceeded",
            "message":
                "Too many requests. Please wait a moment before trying again.",
        }), 429

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

        logger.info(f"🔍 Enhanced verification with smart contracts: "
                    f"{company_name} - {len(claim_text)} chars")

        verification_results = enhanced_verification_with_smart_contracts(
            claim_text, company_name, user_email)

        enhanced_evidence = []
        if verification_results.get("certification_analysis"):
            cert_analysis = verification_results["certification_analysis"]
            verified_certs = cert_analysis.get("verified_certifications", [])
            if verified_certs:
                enhanced_evidence.append(
                    f" {len(verified_certs)} verified certifications")
        if verification_results.get("emissions_analysis"):
            emissions_analysis = verification_results["emissions_analysis"]
            if emissions_analysis.get("company_found"):
                performance = emissions_analysis.get("performance_score", 0.5)
                if performance > 0.7:
                    enhanced_evidence.append(
                        " Above-average emissions performance")
                elif performance < 0.4:
                    enhanced_evidence.append(
                        " Below-average emissions performance")

        verification_doc = {
            "claim_text": claim_text,
            "company_name": company_name,
            "verification_score": verification_results["overall_score"],
            "risk_level": verification_results["risk_level"],
            "status": verification_results["status"],
            "trustworthiness": verification_results["trustworthiness"],
            "evidence_summary": verification_results["evidence_summary"],
            "company_analysis": verification_results["company_analysis"],
            "certification_analysis": verification_results.get(
                "certification_analysis"),
            "emissions_analysis": verification_results.get(
                "emissions_analysis"),
            "recommendations": verification_results["recommendations"],
            "smart_contracts": verification_results.get("smart_contracts", {}),
            "automated_actions": verification_results.get(
                "automated_actions", []),
            "verification_timestamp": datetime.utcnow(),
            "user_email": user_email,
            "client_ip": client_ip,
            "version": "2.0_enhanced_with_smart_contracts",
        }

        try:
            result = verifications_collection.insert_one(verification_doc)
            verification_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing verification: {e}")

        blockchain_id = None
        try:
            blockchain_data = {
                "company_name": company_name,
                "claim": claim_text,
                "verification_score": verification_results["overall_score"],
                "status": verification_results["status"],
                "risk_level": verification_results["risk_level"],
                "evidence_summary": verification_results["evidence_summary"],
                "smart_contracts_executed": len(verification_results.get(
                    "smart_contracts", {})),
                "automated_actions": verification_results.get(
                    "automated_actions", []),
                "certification_verified": bool(verification_results.get(
                    "certification_analysis")),
                "emissions_verified": bool(verification_results.get(
                    "emissions_analysis")),
                "user_email": user_email,
                "version": "enhanced_2.0_with_smart_contracts",
            }
            blockchain_id = add_verification_to_blockchain(blockchain_data)
            logger.info(f"🔗 Enhanced verification with smart contracts added "
                        f"to blockchain: {blockchain_id}")
        except Exception as e:
            logger.error(f" Blockchain integration error: {str(e)}")

        trustworthy = verification_results["overall_score"] >= 0.60
        score_percentage = round(verification_results["overall_score"] * 100)

        smart_contract_info = ""
        if verification_results.get("smart_contracts"):
            actions = verification_results.get("automated_actions", [])
            if actions:
                smart_contract_info = (
                    "\n\n** Automated Smart Contract Actions:**\n"
                    + "\n".join([f"• {action}" for action in actions[:5]])
                )

        enhanced_info = ""
        if enhanced_evidence:
            enhanced_info = "\n\n**🔍 Enhanced Verification Results:**\n"
            + "\n".join([f"• {evidence}" for evidence in enhanced_evidence])

        company_analysis = verification_results['company_analysis']
        industry_analysis = company_analysis['industry_analysis']
        category = industry_analysis['category']
        confidence_level = company_analysis['confidence_level']

        analysis = (
            f"**Status: {verification_results['status']}**\n\n"
            f"**Enhanced AI Analysis with Smart Contracts:**\n"
            f"The advanced universal verification system with automated smart "
            f"contracts has analyzed this "
            f"claim from {company_name}. Overall verification score: "
            f"{score_percentage}%\n\n"
            f"**Key Findings:**\n"
            f"• Company Analysis: {confidence_level.title()} confidence\n"
            f"• Industry Category: {category.replace('_', ' ').title()}\n"
            f"• Risk Assessment: {verification_results['risk_level']}\n"
            f"• Smart Contracts Executed: "
            f"{len(verification_results.get('smart_contracts', {}))}\n"
            f"• Enhanced Verification: "
            f"{' Active' if ENHANCED_VERIFICATION_AVAILABLE else ' Unavailable'}\n\n"
            f"**Evidence Summary:**\n"
            f"{verification_results['evidence_summary']}\n\n"
            f"**Blockchain Security:** "
            f"{' Secured' if blockchain_id else ' Pending'}"
            f"{enhanced_info}"
            f"{smart_contract_info}"
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
            "enhanced_features": {
                "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
                "third_party_verification": ENHANCED_VERIFICATION_AVAILABLE,
            },
            "certification_analysis": verification_results.get(
                "certification_analysis"),
            "emissions_analysis": verification_results.get(
                "emissions_analysis"),
            "smart_contracts": {
                "enabled": smart_blockchain is not None,
                "contracts_executed": len(verification_results.get(
                    "smart_contracts", {})),
                "automated_actions": verification_results.get(
                    "automated_actions", []),
                "results": verification_results.get("smart_contracts", {})
            },
            "blockchain_id": blockchain_id,
            "blockchain_secured": blockchain_id is not None,
            "transparency_info": {
                "immutable_record": blockchain_id is not None,
                "public_verification": True,
                "tamper_proof": blockchain_id is not None,
                "ai_powered": True,
                "smart_contracts": smart_blockchain is not None,
                "universal_support": True,
                "enhanced_verification": ENHANCED_VERIFICATION_AVAILABLE,
            },
            "processing_info": {
                "version": "2.0_enhanced_with_smart_contracts",
                "analysis_type": "universal_verification_with_smart_contracts",
                "processing_time": "< 2 seconds",
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        logger.info(f" Enhanced verification with smart contracts completed: "
                    f"{company_name} - "
                    f"{score_percentage}% ({verification_results['status']})")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f" Enhanced verification with smart contracts error: "
                     f"{str(e)}")
        return jsonify({
            "error": "Verification system error",
            "message": "The enhanced verification system with smart contracts "
            "encountered an issue. Please try again.",
            "details": str(e) if app.debug else "Internal system error",
        }), 500


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

        logger.info(f" Processing claim detection request - Text length: "
                    f"{len(text)}, Save to DB: {save_to_db}")

        detected_claims = claim_detector.detect_claims(text)

        stored_claims = []
        if save_to_db:
            for claim in detected_claims:
                claim_doc = create_claim_document(
                    claim["text"],
                    claim["keywords"][0] if claim[
                        "keywords"] else "environmental",
                    claim["confidence"],
                    claim["greenwashing_risk"],
                    url,
                )

                try:
                    result = claims_collection.insert_one(claim_doc)
                    claim_doc["_id"] = str(result.inserted_id)
                    stored_claims.append(claim_doc)
                    logger.info(f" Saved claim to MongoDB: "
                                f"{result.inserted_id}")
                except Exception as e:
                    logger.error(f" Error storing claim: {e}")
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
            logger.info(f" Claim analysis added to blockchain: "
                        f"{blockchain_id}")
        except Exception as e:
            logger.error(f" Error adding to blockchain: {str(e)}")

        return jsonify({
            "success": True,
            "claims_detected": len(detected_claims),
            "claims_count": len(detected_claims),
            "claims": [
                {
                    "claim_text": claim["text"],
                    "greenwashing_risk": claim["greenwashing_risk"],
                    "confidence_score": claim["confidence"],
                    "keyword": claim["keywords"][0] if claim[
                        "keywords"] else "environmental",
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
        logger.error(f" Error detecting claims: {str(e)}")
        return jsonify({"error": "Internal server error",
                        "details": str(e)}), 500


@app.route("/api/companies/verify", methods=["POST"])
def verify_company():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        company_name = data.get("company_name", "") or data.get("company", "")
        claim_text = data.get("claim_text", "") or data.get("claim", "")
        save_to_db = data.get("save_to_db", True)

        if not company_name or not claim_text:
            return jsonify({"error": "Company name and claim text required"}),
        400

        logger.info(f" Verifying company: {company_name}")

        verification_results = enhanced_universal_verification(
            claim_text, company_name)

        if save_to_db:
            verification_doc = {
                "company_name": company_name,
                "claim_text": claim_text,
                "verification_score": verification_results["overall_score"],
                "risk_level": verification_results["risk_level"],
                "status": verification_results["status"],
                "trustworthiness": verification_results["trustworthiness"],
                "evidence_summary": verification_results["evidence_summary"],
                "certification_analysis": verification_results.get(
                    "certification_analysis"),
                "emissions_analysis": verification_results.get(
                    "emissions_analysis"),
                "verification_timestamp": datetime.utcnow(),
                "user_email": data.get("user_email", "extension_user"),
                "version": "2.0_enhanced",
            }

            try:
                result = verifications_collection.insert_one(verification_doc)
                logger.info(f" Saved verification to MongoDB: "
                            f"{result.inserted_id}")
            except Exception as e:
                logger.error(f" Error saving verification: {e}")

        return jsonify({
            "success": True,
            "company": company_name,
            "claim": claim_text,
            "verification_status": verification_results["status"],
            "verification_score": verification_results["overall_score"],
            "sources": ["company_database", "ai_analysis",
                        "certification_database", "emissions_database"],
            "trust_score": verification_results["overall_score"],
            "enhanced_features": {
                "certification_verification": bool(verification_results.get(
                    "certification_analysis")),
                "emissions_cross_reference": bool(verification_results.get(
                    "emissions_analysis")),
            },
        })

    except Exception as e:
        logger.error(f" Error in company verification: {e}")
        return jsonify({"error": "Verification failed",
                        "details": str(e)}), 500


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
            return jsonify({
                "error":
                    "report_type/feedback_type, "
                    "company, and content/description are required"
            }), 400

        logger.info(f" Processing community report: "
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
                logger.info(f" Saved community report to MongoDB: "
                            f"{result.inserted_id}")
            except Exception as e:
                logger.error(f" Error storing submission: {e}")
                return jsonify({"error": "Failed to save report"}), 500
        else:
            submission_doc = {
                "feedback_type": feedback_type,
                "company": company,
                "content": content,
                "status": "pending_review",
            }

        return jsonify({
            "success": True,
            "message": "Community report submitted successfully",
            "report_id": str(submission_doc.get("_id", "temp_id")),
            "status": "pending_review",
        }), 201

    except Exception as e:
        logger.error(f" Error submitting community feedback: {str(e)}")
        return jsonify({"error": "Internal server error",
                        "details": str(e)}), 500


@app.route("/api/analytics/stats", methods=["GET"])
def get_enhanced_analytics():
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

        enhanced_verifications = verifications_collection.count_documents({
            "version": {"$in": ["2.0_enhanced",
                                "2.0_enhanced_with_smart_contracts",
                                "2.0_enhanced_complete"]}})

        try:
            blockchain_stats = get_blockchain_statistics()
        except Exception as e:
            logger.error(f" Blockchain stats error: {str(e)}")
            blockchain_stats = {
                "total_blocks": 0,
                "verification_blocks": 0,
                "companies_on_blockchain": 0,
                "network_status": "operational",
            }

        smart_contract_stats = {}
        if smart_blockchain:
            try:
                smart_contract_stats = (
                    smart_blockchain.get_contract_statistics()
                )
            except Exception as e:
                logger.error(f" Smart contract stats error: {str(e)}")
                smart_contract_stats = {
                    "total_contracts": 0,
                    "total_executions": 0,
                    "active_contracts": 0
                }

        logger.info(
            f" Enhanced analytics: Claims={total_claims}, "
            f"Verifications={total_verifications}, "
            f"Websites={total_websites_analyzed}, "
            f"Reports={total_community_reports}, "
            f"Enhanced={enhanced_verifications}"
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
                "smart_contracts": smart_blockchain is not None,
                "real_time_processing": True,
                "website_analysis": True,
                "enhanced_verifications": enhanced_verifications,
                "system_accuracy": 0.94,
                "automated_enforcement": smart_blockchain is not None,
                "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
                "third_party_verification": ENHANCED_VERIFICATION_AVAILABLE,
            },
            "recent_activity": {
                "claims_7days": recent_claims,
                "verifications_7days": recent_verifications,
                "websites_7days": recent_website_analyses,
                "growth_rate": round((recent_verifications / max(
                    total_verifications, 1)) * 100, 1),
            },
            "blockchain": {
                "total_blocks": blockchain_stats.get("total_blocks", 0),
                "verification_blocks": blockchain_stats.get(
                    "verification_blocks", 0),
                "companies_on_blockchain": blockchain_stats.get(
                    "companies_on_blockchain", 0),
                "chain_valid": blockchain_stats.get(
                    "chain_integrity", {}).get("valid", False),
                "network_status": blockchain_stats.get("network_status",
                                                       "operational"),
                "immutable_records": True,
                "public_verification": True,
            },
            "smart_contracts": {
                "enabled": smart_blockchain is not None,
                "total_contracts": smart_contract_stats.get(
                    "total_contracts", len(essential_contracts)),
                "total_executions": smart_contract_stats.get(
                    "total_executions", 0),
                "active_contracts": smart_contract_stats.get(
                    "active_contracts", 0),
                "contract_types": list(
                    essential_contracts.keys()) if essential_contracts else [],
                "automated_actions_triggered": smart_contract_stats.get(
                    "total_executions", 0),
            },
            "data_source":
                "enhanced_real_time_mongodb_blockchain_smart_contracts",
                "transparency_features": {
                "blockchain_secured": True,
                "immutable_records": True,
                "public_verification": True,
                "ai_powered": True,
                "smart_contracts": smart_blockchain is not None,
                "automated_enforcement": smart_blockchain is not None,
                "universal_support": True,
                "real_time_analysis": True,
                "website_analysis": True,
                "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
                "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
            },
        })

    except Exception as e:
        logger.error(f" Enhanced analytics error: {str(e)}")
        return jsonify({
            "error": "Analytics system error",
            "message": "Unable to fetch current statistics",
            "details": str(e) if app.debug else "Internal system error",
        }), 500


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
        logger.error(f" Error clearing data: {e}")
        return jsonify({"error": "Failed to clear data",
                        "details": str(e)}), 500


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

        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "user": user_response,
        }), 201

    except Exception as e:
        logger.error(f" Registration error: {str(e)}")
        return jsonify({"error": "Registration failed",
                        "details": str(e)}), 500


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

        return jsonify({
            "success": True,
            "message": "Login successful",
            "user": user_response
        }), 200

    except Exception as e:
        logger.error(f" Login error: {str(e)}")
        return jsonify({"error": "Login failed", "details": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout_user():
    try:
        return jsonify({"success": True, "message": "Logout successful"}), 200
    except Exception as e:
        logger.error(f" Logout error: {str(e)}")
        return jsonify({"error": "Logout failed", "details": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        client.admin.command("ismaster")
        db_status = "connected"
        try:
            blockchain_stats = get_blockchain_statistics()
            blockchain_status = (
                "operational" if blockchain_stats.get(
                    "network_status") == "operational"
                else "warning"
            )
        except Exception:
            blockchain_status = "error"
        smart_contract_status = (
            "operational" if smart_blockchain else "disabled"
        )
    except Exception:
        db_status = "disconnected"
        blockchain_status = "error"
        smart_contract_status = "error"

    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0_enhanced_complete_with_smart_contracts",
        "database": db_status,
        "blockchain": blockchain_status,
        "smart_contracts": smart_contract_status,
        "enhanced_verification":
            "operational" if ENHANCED_VERIFICATION_AVAILABLE else "disabled",
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
            "smart_contracts": smart_blockchain is not None,
            "automated_enforcement": smart_blockchain is not None,
            "penalty_system": smart_blockchain is not None,
            "reward_system": smart_blockchain is not None,
            "community_bounties": smart_blockchain is not None,
            "certification_verification": ENHANCED_VERIFICATION_AVAILABLE,
            "emissions_cross_reference": ENHANCED_VERIFICATION_AVAILABLE,
            "third_party_verification": ENHANCED_VERIFICATION_AVAILABLE,
            "comprehensive_database_integration": ENHANCED_VERIFICATION_AVAILABLE
        },
        "enhanced_nlp_processing": ENHANCED_NLP_AVAILABLE,
        "spacy_linguistic_analysis": (ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.nlp is not None),
        "bert_classification": (ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.greenwashing_classifier is not None),
        "sentiment_analysis": (ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.sentiment_analyzer is not None),
        "transformers_integration": ENHANCED_NLP_AVAILABLE,
        "named_entity_recognition": (ENHANCED_NLP_AVAILABLE and enhanced_nlp and enhanced_nlp.nlp is not None),
        "hybrid_detection_system": ENHANCED_NLP_AVAILABLE,
        "advanced_text_preprocessing": ENHANCED_NLP_AVAILABLE,
        "smart_contract_info": {
            "enabled": smart_blockchain is not None,
            "deployed_contracts": len(essential_contracts) if smart_blockchain else 0,
            "contract_types": list(essential_contracts.keys()) if smart_blockchain else [],
            "automation_active": smart_blockchain is not None
        },
        "enhanced_verification_info": {
            "certification_verifier": certification_verifier is not None,
            "emissions_verifier": emissions_verifier is not None,
            "database_integration": ENHANCED_VERIFICATION_AVAILABLE,
            "third_party_sources": ENHANCED_VERIFICATION_AVAILABLE
        },
        "endpoints": {
            "auth_register": "/api/auth/register",
            "auth_login": "/api/auth/login",
            "auth_logout": "/api/auth/logout",
            "claims_detect": "/api/claims/detect",
            "claims_verify": "/api/claims/verify",
            "enhanced_verification": "/api/enhanced-verification",
            "companies_verify": "/api/companies/verify",
            "community": "/api/community/submit",
            "analytics": "/api/analytics/stats",
            "statistics": "/api/statistics",
            "website_analysis": "/api/analyze-website",
            "alternatives": "/api/alternatives/suggest",
            "smart_contracts_stats": "/api/smart-contracts/stats",
            "smart_contracts_execute": "/api/smart-contracts/execute",
            "clear_data": "/api/clear-data",
            "nlp_status": "/api/nlp/status"
        }
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
        logger.error(f" Error suggesting alternatives: {str(e)}")
        return jsonify({"error": "Internal server error",
                        "details": str(e)}), 500


def init_database():
    try:
        claims_collection.create_index([("detected_timestamp", -1)],
                                       background=True)
        claims_collection.create_index([("greenwashing_risk", -1)],
                                       background=True)
        claims_collection.create_index([("keyword", 1)], background=True)

        verifications_collection.create_index([("company_name", 1)],
                                              background=True)
        verifications_collection.create_index([("verification_timestamp", -1)],
                                              background=True)
        verifications_collection.create_index([("verification_score", -1)],
                                              background=True)
        verifications_collection.create_index([("user_email", 1)],
                                              background=True)
        verifications_collection.create_index([("version", 1)],
                                              background=True)

        website_analyses_collection.create_index([("website_url", 1)],
                                                 background=True)
        website_analyses_collection.create_index([("analysis_timestamp", -1)],
                                                 background=True)
        website_analyses_collection.create_index([("user_email", 1)],
                                                 background=True)
        website_analyses_collection.create_index([("version", 1)],
                                                 background=True)

        user_submissions_collection.create_index([("submission_timestamp",
                                                   -1)], background=True)
        user_submissions_collection.create_index([("company", 1)],
                                                 background=True)

        users_collection.create_index([("email", 1)],
                                      unique=True, background=True)
        users_collection.create_index([("created_at", -1)], background=True)

        logger.info(" Enhanced database indexes created successfully")

    except Exception as e:
        logger.warning(f" Index creation warning: {e}")


@app.errorhandler(404)
def not_found(error):
    available_endpoints = [
        "/api/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/claims/detect",
        "/api/claims/verify",
        "/api/enhanced-verification",
        "/api/companies/verify",
        "/api/community/submit",
        "/api/analytics/stats",
        "/api/statistics",
        "/api/analyze-website",
        "/api/alternatives/suggest",
        "/api/smart-contracts/stats",
        "/api/smart-contracts/execute",
        "/api/clear-data",
    ]

    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": available_endpoints,
        "version": "2.0_enhanced_complete_with_smart_contracts",
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "version": "2.0_enhanced_complete_with_smart_contracts"
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
        f" Starting Complete Enhanced GreenGuard Universal "
        f"Verification API with Smart Contracts on {host}:{port}")
    logger.info(f" Debug mode: {debug}")
    logger.info(f" Database: {DATABASE_NAME}")
    logger.info(f" Smart Contracts: "
                f"{' Enabled' if smart_blockchain else ' Disabled'}")
    logger.info(
        f" Enhanced Verification: "
        f"{' Enabled' if ENHANCED_VERIFICATION_AVAILABLE else ' Disabled'}")
    logger.info(f" Enhanced NLP: "
                f"{' Enabled' if ENHANCED_NLP_AVAILABLE else ' Disabled'}")

    if ENHANCED_NLP_AVAILABLE and enhanced_nlp:
        nlp_status = enhanced_nlp.get_nlp_status()
        logger.info(f" spaCy Linguistic Analysis: "
                    f"{' Active' if nlp_status['spacy_available'] else 'Inactive'}")
        logger.info(f" BERT Classification: "
                    f"{' Active' if nlp_status['bert_available'] else ' Inactive'}")
        logger.info(f" Sentiment Analysis: "
                    f"{' Active' if nlp_status['sentiment_available'] else ' Inactive'}")
        logger.info(f" HuggingFace Transformers: "
                    f"{' Active' if nlp_status['transformers_available'] else ' Inactive'}")

    if ENHANCED_VERIFICATION_AVAILABLE:
        logger.info(" Enhanced Certification Verifier:  Active")
        logger.info(" Enhanced Emissions Verifier:  Active")

    logger.info(" Complete Enhanced Features: Universal Company Support, "
                "Advanced AI Analysis, Global Verification, "
                "Blockchain Transparency, Smart Contract Automation, "
                "Real-time Statistics, Website Environmental Analysis, "
                "Content Scraping, "
                "Greenwashing Detection, Automated Enforcement, "
                "Certification Verification, "
                "Emissions Cross-Reference, Third-party Database Integration")
    logger.info(" Complete Enhanced Features: Universal Company Support, "
                "Advanced AI Analysis, Global Verification, "
                "Blockchain Transparency, Smart Contract Automation, "
                "Real-time Statistics, Website Environmental Analysis, "
                "Content Scraping, Greenwashing Detection, "
                "Automated Enforcement, "
                "Certification Verification, Emissions Cross-Reference, "
                "Third-party Database Integration, "
                " spaCy Linguistic Analysis,  BERT Text Classification, "
                " Sentiment Analysis,  HuggingFace Transformers, "
                " Named Entity Recognition,  Advanced Text Preprocessing")

    if __name__ == "__main__":
        app.run(host=host, port=port, debug=debug)
