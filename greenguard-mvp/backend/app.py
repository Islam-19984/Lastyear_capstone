from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv
import logging

from blockchain_verification import (
    add_verification_to_blockchain,
    add_claim_analysis_to_blockchain,
    get_blockchain_verification_proof,
    get_company_blockchain_history,
    get_user_blockchain_history,
    get_blockchain_statistics,
)

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = os.getenv("DATABASE_NAME", "greenguard_db")

try:
    client = MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]
    client.admin.command("ismaster")
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    exit(1)

companies_collection = db.companies
claims_collection = db.claims
verifications_collection = db.verifications
user_submissions_collection = db.user_submissions
alternatives_collection = db.alternatives
users_collection = db.users


class UniversalCompanyAnalyzer:

    def __init__(self):
        self.sustainability_leaders = {
            "patagonia": 0.95,
            "tesla": 0.92,
            "unilever": 0.85,
            "microsoft": 0.88,
            "google": 0.87,
            "apple": 0.84,
            "nike": 0.76,
            "ikea": 0.83,
            "ben jerry": 0.89,
            "seventh generation": 0.91,
            "whole foods": 0.86,
            "interface": 0.94,
            "novo nordisk": 0.88,
            "schneider electric": 0.89,
            "johnson johnson": 0.78,
            "procter gamble": 0.74,
            "coca cola": 0.71,
            "nestle": 0.68,
            "walmart": 0.73,
            "amazon": 0.75,
            "facebook": 0.79,
            "meta": 0.79,
            "salesforce": 0.86,
            "adobe": 0.82,
            "intel": 0.81,
        }

        self.high_impact_industries = [
            "oil",
            "gas",
            "petroleum",
            "coal",
            "mining",
            "chemical",
            "plastic",
            "fast fashion",
            "airline",
            "shipping",
            "steel",
            "cement",
            "paper",
        ]

    def analyze_company(self, company_name):
        """Analyze any company for environmental credibility"""
        company_lower = company_name.lower().strip()

        analysis = {
            "company_name": company_name,
            "found_in_leaders": False,
            "sustainability_score": 0.5,
            "industry_penalty": 0.0,
            "size_factor": self._estimate_company_size(company_name),
            "reputation_score": 0.5,
            "transparency_bonus": 0.0,
        }

        for leader, score in self.sustainability_leaders.items():
            if leader in company_lower or self._fuzzy_match(leader,
                                                            company_lower):
                analysis["found_in_leaders"] = True
                analysis["sustainability_score"] = score
                analysis["reputation_score"] = min(0.95, score + 0.1)
                break

        for industry in self.high_impact_industries:
            if industry in company_lower:
                analysis["industry_penalty"] = 0.15
                break

        if self._is_likely_public_company(company_name):
            analysis["transparency_bonus"] = 0.1

        return analysis

    def _estimate_company_size(self, company_name):
        """Estimate company size based on naming patterns"""
        company_lower = company_name.lower()

        large_indicators = [
            "corp",
            "corporation",
            "inc",
            "incorporated",
            "ltd",
            "limited",
            "group",
            "holdings",
        ]
        if any(indicator in company_lower for indicator in large_indicators):
            return "large"

        small_indicators = ["llc", "co", "studio", "shop", "local", "boutique"]
        if any(indicator in company_lower for indicator in small_indicators):
            return "small"

        return "medium"

    def _is_likely_public_company(self, company_name):
        """Determine if company is likely publicly traded"""
        company_lower = company_name.lower()
        public_indicators = [
            "inc",
            "corp",
            "corporation",
            "plc",
            "ltd",
            "limited",
            "group",
        ]
        return any(indicator in company_lower for indicator in
                   public_indicators)

    def _fuzzy_match(self, leader, company_name):
        suffixes = ["inc", "corp", "ltd", "llc", "co", "company",
                    "corporation"]
        clean_company = company_name
        for suffix in suffixes:
            clean_company = clean_company.replace(f" {suffix}", "").replace(
                f".{suffix}", ""
            )

        return leader in clean_company or clean_company in leader


class ClaimDetector:
    def __init__(self):
        self.environmental_keywords = [
            "sustainable",
            "eco-friendly",
            "green",
            "carbon neutral",
            "renewable",
            "biodegradable",
            "organic",
            "recycled",
            "zero waste",
            "climate positive",
            "earth friendly",
            "environmentally responsible",
            "natural",
            "clean energy",
            "carbon negative",
            "net zero",
            "climate friendly",
            "compostable",
            "eco",
            "environmental",
            "climate action",
            "sustainable development",
        ]

        self.greenwashing_indicators = [
            "eco",
            "green",
            "natural",
            "pure",
            "clean",
            "fresh",
            "earth",
            "planet",
            "nature",
            "environmental",
            "sustainable",
        ]

    def detect_claims(self, text):
        """Detect environmental claims in text"""
        claims = []
        sentences = re.split(r"[.!?]+", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            for keyword in self.environmental_keywords:
                if keyword in sentence.lower():
                    claim_data = {
                        "text": sentence,
                        "keyword": keyword,
                        "confidence": self.calculate_confidence(sentence),
                        "greenwashing_risk":
                            self.assess_greenwashing_risk(sentence),
                    }
                    claims.append(claim_data)
                    break

        return claims

    def calculate_confidence(self, sentence):
        """Calculate confidence score for claim detection"""
        words = sentence.lower().split()
        env_word_count = sum(
            1 for word in words if any(kw in word for kw in self.
                                       environmental_keywords)
        )
        confidence = min(0.95, 0.3 + (env_word_count / len(words)) * 2)
        return round(confidence, 2)

    def assess_greenwashing_risk(self, sentence):
        risk_factors = 0
        sentence_lower = sentence.lower()

        vague_terms = [
            "eco",
            "green",
            "natural",
            "sustainable",
            "clean",
            "pure",
            "fresh",
        ]
        risk_factors += sum(1 for term in vague_terms if term in
                            sentence_lower)

        absolute_terms = [
            "100%",
            "completely",
            "totally",
            "fully",
            "entirely",
            "perfect",
        ]
        risk_factors += sum(2 for term in absolute_terms if term in
                            sentence_lower)

        specificity_terms = ["certified", "verified", "approved", "audited",
                             "measured"]
        if not any(cert in sentence_lower for cert in specificity_terms):
            risk_factors += 1

        superlatives = [
            "best",
            "most",
            "leading",
            "ultimate",
            "revolutionary",
            "amazing",
        ]
        risk_factors += sum(1 for sup in superlatives if sup in sentence_lower)

        risk_score = min(1.0, risk_factors / 8)
        return round(risk_score, 2)


company_analyzer = UniversalCompanyAnalyzer()
claim_detector = ClaimDetector()


def simulate_universal_verification(claim_text, company_name):
    """Universal verification system for any public company"""

    company_analysis = company_analyzer.analyze_company(company_name)

    claim_analysis = claim_detector.detect_claims(claim_text)

    base_score = 5.0

    base_score += company_analysis["sustainability_score"] * 3.0
    base_score -= company_analysis["industry_penalty"] * 10
    base_score += company_analysis["transparency_bonus"] * 5

    if company_analysis["size_factor"] == "large":
        base_score += 0.5
    elif company_analysis["size_factor"] == "small":
        base_score -= 0.3

    if claim_analysis:
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis
        )
        avg_confidence = sum(c["confidence"] for c in claim_analysis) / len(
            claim_analysis
        )

        base_score -= avg_risk * 4.0
        base_score += (avg_confidence - 0.5) * 2.0

    claim_lower = claim_text.lower()

    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?|mw|gwh)", claim_lower):
        base_score += 1.5

    cert_keywords = [
        "certified",
        "iso",
        "verified",
        "audit",
        "third-party",
        "independent",
    ]
    if any(cert in claim_lower for cert in cert_keywords):
        base_score += 1.2

    vague_marketing = [
        "eco-friendly",
        "green",
        "natural",
        "sustainable",
        "environmentally conscious",
    ]
    vague_count = sum(1 for term in vague_marketing if term in claim_lower)
    base_score -= vague_count * 0.4

    absolute_claims = [
        "100%",
        "completely",
        "totally",
        "zero",
        "carbon neutral",
        "net zero",
    ]
    if any(abs_term in claim_lower for abs_term in absolute_claims):
        base_score -= 1.5

    initiative_keywords = [
        "renewable energy",
        "solar",
        "wind",
        "recycling",
        "circular economy",
    ]
    if any(init in claim_lower for init in initiative_keywords):
        base_score += 0.8

    final_score = max(0, min(10, base_score))

    score_percentage = final_score / 10

    if score_percentage >= 0.8:
        risk_level = "LOW"
        status = "VERIFIED"
        trustworthiness = "Highly Trustworthy"
    elif score_percentage >= 0.65:
        risk_level = "LOW-MEDIUM"
        status = "LIKELY VALID"
        trustworthiness = "Moderately Trustworthy"
    elif score_percentage >= 0.45:
        risk_level = "MEDIUM"
        status = "NEEDS VERIFICATION"
        trustworthiness = "Questionable"
    elif score_percentage >= 0.25:
        risk_level = "HIGH"
        status = "QUESTIONABLE"
        trustworthiness = "Highly Questionable"
    else:
        risk_level = "VERY HIGH"
        status = "HIGH RISK"
        trustworthiness = "Not Trustworthy"

    recommendations = generate_dynamic_recommendations(
        score_percentage, company_analysis, claim_analysis, claim_text
    )

    evidence_summary = generate_universal_evidence_summary(
        company_analysis, claim_analysis, score_percentage, claim_text
    )

    return {
        "overall_score": score_percentage,
        "risk_level": risk_level,
        "status": status,
        "trustworthiness": trustworthiness,
        "evidence_summary": evidence_summary,
        "company_analysis": company_analysis,
        "sources": {
            "company_database": {
                "status": "checked",
                "found": company_analysis["found_in_leaders"],
            },
            "ai_analysis": {
                "claims_detected": len(claim_analysis),
                "status": "analyzed",
            },
            "industry_analysis": {
                "penalty_applied": company_analysis["industry_penalty"] > 0,
                "status": "checked",
            },
            "reputation_check": {
                "score": company_analysis["reputation_score"],
                "status": "evaluated",
            },
        },
        "recommendations": recommendations,
        "detailed_breakdown": {
            "company_score": company_analysis["sustainability_score"],
            "claim_risk": sum(c["greenwashing_risk"] for c in claim_analysis)
            / max(len(claim_analysis), 1),
            "specificity_bonus": 1.5 if re.search(r"\d+%", claim_text.lower())
            else 0,
            "certification_bonus": (
                1.2
                if any(cert in claim_text.lower() for cert in ["certified",
                                                               "verified"])
                else 0
            ),
        },
    }


def generate_dynamic_recommendations(
    score_percentage, company_analysis, claim_analysis, claim_text
):
    """Generate dynamic recommendations based on analysis"""
    recommendations = []

    if score_percentage >= 0.8:
        recommendations = [
            "This claim appears well-supported by available evidence",
            "Company demonstrates strong environmental commitment",
            "Consider this a reliable environmental statement",
            "Verified and recorded on blockchain for transparency",
        ]
    elif score_percentage >= 0.65:
        recommendations = [
            "Claim shows reasonable evidence of validity",
            "Company appears committed to sustainability",
            "Look for additional third-party verification",
            "Blockchain verification provides transparency",
        ]
    elif score_percentage >= 0.45:
        recommendations = [
            "Limited evidence available to support this claim",
            "Request specific data and certifications",
            "Look for independent third-party verification",
            "Blockchain record shows need for improvement",
        ]
    else:
        recommendations = [
            "Significant concerns about claim validity",
            "High risk of greenwashing detected",
            "Demand concrete evidence and certifications",
            "Blockchain transparency reveals credibility issues",
        ]

    if not company_analysis["found_in_leaders"]:
        recommendations.append(
            f"Company '{
                company_analysis[
                    'company_name']}' not found in sustainability leadership databases"
        )

    if company_analysis["industry_penalty"] > 0:
        recommendations.append(
            "Company operates in high-environmental-impact industry - extra"
            "scrutiny advised"
        )

    if claim_analysis:
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis
        )
        if avg_risk > 0.7:
            recommendations.append(
                "AI analysis indicates high risk of greenwashing language"
            )

    claim_lower = claim_text.lower()
    if any(abs_term in claim_lower for abs_term in ["100%", "completely",
                                                    "zero"]):
        recommendations.append(
            "Absolute claims require strong third-party verification"
        )

    if not any(cert in claim_lower for cert in ["certified", "verified",
                                                "audited"]):
        recommendations.append(
        )

    return recommendations


def generate_universal_evidence_summary(
    company_analysis, claim_analysis, score_percentage, claim_text
):
    """Generate comprehensive evidence summary for any company"""
    evidence_parts = []

    if company_analysis["found_in_leaders"]:
        evidence_parts.append(
            f"Company recognized as sustainability leader (score:"
            "{company_analysis['sustainability_score']:.2f})"
        )
    else:
        evidence_parts.append(f"Company not found in major sustainability"
                              "databases")

    if company_analysis["industry_penalty"] > 0:
        evidence_parts.append("Company operates in high-environmental-impact "
                              "industry")

    if company_analysis["transparency_bonus"] > 0:
        evidence_parts.append(
            "Large public company with expected transparency requirements"
        )

    if claim_analysis:
        evidence_parts.append(f"AI detected {len(claim_analysis)}"
                              "environmental claims")
        avg_risk = sum(c["greenwashing_risk"] for c in claim_analysis) / len(
            claim_analysis
        )
        if avg_risk > 0.7:
            evidence_parts.append("High greenwashing risk indicators present")
        elif avg_risk < 0.3:
            evidence_parts.append("Low greenwashing risk indicators")

    claim_lower = claim_text.lower()
    if re.search(r"\d+%|\d+\s*(tons?|kg|pounds?)", claim_lower):
        evidence_parts.append("Claim includes quantifiable metrics")

    if any(cert in claim_lower for cert in ["certified", "verified", "audit"]):
        evidence_parts.append("Mention of third-party verification found")
    else:
        evidence_parts.append("No third-party verification mentioned")

    if score_percentage >= 0.75:
        evidence_parts.append("Strong overall evidence supporting claim")
    elif score_percentage >= 0.5:
        evidence_parts.append("Moderate evidence supporting claim")
    else:
        evidence_parts.append("Insufficient evidence to support claim")

    return "; ".join(evidence_parts)


def create_claim_document(
    claim_text, keyword, confidence_score, greenwashing_risk, source_url
):
    """Create a claim document for database storage"""
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
                "certifications": ["Fair Trade", "B-Corp",
                                   "1% for the Planet"],
                "sustainability_score": 0.95,
                "price_range": "Premium",
                "url": "https://patagonia.com",
                "why_better": "Verified certifications and transparent supply"
                "chain",
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
            {
                "name": "Method",
                "product": "Green Cleaning Products",
                "certifications": ["Cradle to Cradle",
                                   "EPA Design for Environment"],
                "sustainability_score": 0.82,
                "price_range": "Affordable",
                "url": "https://methodhome.com",
                "why_better": "Biodegradable formulas in recycled packaging",
            },
        ],
    }

    return alternatives_db.get(category, alternatives_db["general"])


@app.route("/api/auth/register", methods=["POST"])
def register_user():
    """Register a new user"""
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

        logger.info(f"New user registered: {email}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "User registered successfully",
                    "user": user_response,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({"error": "Registration failed", "details": str(e)}),
    500


@app.route("/api/auth/login", methods=["POST"])
def login_user():
    """Login user"""
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

        logger.info(f"User logged in: {email}")

        return (
            jsonify(
                {"success": True, "message": "Login successful",
                 "user": user_response}
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed", "details": str(e)}), 500


@app.route("/api/auth/logout", methods=["POST"])
def logout_user():
    """Logout user"""
    try:
        return jsonify({"success": True, "message": "Logout successful"}), 200

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({"error": "Logout failed", "details": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        client.admin.command("ismaster")
        db_status = "connected"

        blockchain_stats = get_blockchain_statistics()
        blockchain_status = (
            "operational"
            if blockchain_stats.get("network_status") == "operational"
            else "warning"
        )

    except Exception:
        db_status = "disconnected"
        blockchain_status = "error"

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "blockchain": blockchain_status,
            "features": {
                "universal_company_verification": True,
                "ai_claim_detection": True,
                "dynamic_scoring": True,
                "global_company_support": True,
                "blockchain_transparency": True,
                "immutable_records": True,
            },
            "endpoints": {
                "auth_register": "/api/auth/register",
                "auth_login": "/api/auth/login",
                "auth_logout": "/api/auth/logout",
                "claims_detect": "/api/claims/detect",
                "claims_verify": "/api/claims/verify",
                "alternatives": "/api/alternatives/suggest",
                "community": "/api/community/submit",
                "blockchain_stats": "/api/blockchain/stats",
                "blockchain_verify": "/api/blockchain/verify/<id>",
                "blockchain_company": "/api/blockchain/company/<name>/history",
                "debug_stats": "/api/admin/debug-stats",
            },
        }
    )


@app.route("/api/claims/detect", methods=["POST"])
def detect_claims():
    """Detect environmental claims in text with blockchain recording"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "") or data.get("content", "")
        url = data.get("url", "")
        user_email = data.get("user_email", "anonymous")

        if not text:
            return jsonify({"error": "Text/content is required"}), 400

        if len(text) < 10:
            return jsonify({"error": "Text too short for analysis"}), 400

        detected_claims = claim_detector.detect_claims(text)

        stored_claims = []
        for claim in detected_claims:
            claim_doc = create_claim_document(
                claim["text"],
                claim["keyword"],
                claim["confidence"],
                claim["greenwashing_risk"],
                url,
            )

            try:
                result = claims_collection.insert_one(claim_doc)
                claim_doc["_id"] = str(result.inserted_id)
                stored_claims.append(claim_doc)
            except Exception as e:
                logger.error(f"Error storing claim: {e}")

        avg_risk = sum(c["greenwashing_risk"] for c in detected_claims) / max(
            len(detected_claims), 1
        )

        high_risk_claims = [c for c in detected_claims if
                            c["greenwashing_risk"] >= 0.7]

        if avg_risk >= 0.7:
            risk_level = "High"
            summary = f"Found {len(detected_claims)} environmental claims with"
            "high greenwashing risk. These claims appear vague or "
            "unsubstantiated."
        elif avg_risk >= 0.4:
            risk_level = "Medium"
            summary = f"Found {len(detected_claims)} environmental claims with"
            "moderate risk. Some claims may need verification."
        else:
            risk_level = "Low"
            summary = f"Found {len(detected_claims)} environmental claims that"
            "appear well-substantiated."

        blockchain_id = None
        try:
            blockchain_data = {
                "content": text,
                "claims_count": len(detected_claims),
                "risk_score": avg_risk,
                "summary": summary,
                "claims": stored_claims,
                "url": url,
                "user_email": user_email,
            }
            blockchain_id = add_claim_analysis_to_blockchain(blockchain_data)
            logger.info(f"Claim analysis added to blockchain: {blockchain_id}")
        except Exception as e:
            logger.error(f"Error adding to blockchain: {str(e)}")

        return jsonify(
            {
                "success": True,
                "claims_count": len(detected_claims),
                "risk_score": avg_risk,
                "summary": summary,
                "claims": stored_claims,
                "blockchain_id": blockchain_id,
                "blockchain_secured": blockchain_id is not None,
                "analysis_summary": {
                    "total_sentences": len(text.split(".")),
                    "environmental_claims": len(detected_claims),
                    "avg_risk_score": round(avg_risk, 2),
                    "high_risk_claims": len(high_risk_claims),
                },
            }
        )

    except Exception as e:
        logger.error(f"Error detecting claims: {str(e)}")
        return jsonify({"error": "Internal server error",
                        "details": str(e)}), 500


@app.route("/api/claims/verify", methods=["POST"])
def verify_claim():
    """Verify environmental claims for ANY public company with blockchain"""
    """transparency"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        claim_text = data.get("claim_text", "") or data.get("claim", "")
        company_name = data.get("company_name", "") or data.get("company", "")
        user_email = data.get("user_email", "anonymous")

        if not claim_text:
            return jsonify({"error": "Claim text is required"}), 400

        if not company_name:
            return jsonify({"error": "Company name is required"}), 400

        verification_results = simulate_universal_verification(claim_text,
                                                               company_name)

        blockchain_verification_data = {
            "company_name": company_name,
            "claim": claim_text,
            "verification_score": verification_results["overall_score"],
            "status": verification_results["status"],
            "risk_level": verification_results["risk_level"],
            "trustworthiness": verification_results["trustworthiness"],
            "evidence_summary": verification_results["evidence_summary"],
            "recommendations": verification_results["recommendations"],
            "company_analysis": verification_results["company_analysis"],
            "sources": verification_results["sources"],
            "user_email": user_email,
        }

        verification_doc = {
            "claim_text": claim_text,
            "company_name": company_name,
            "verification_score": verification_results["overall_score"],
            "risk_level": verification_results["risk_level"],
            "trustworthiness": verification_results["trustworthiness"],
            "status": verification_results["status"],
            "evidence_summary": verification_results["evidence_summary"],
            "company_analysis": verification_results["company_analysis"],
            "data_sources": verification_results["sources"],
            "recommendations": verification_results["recommendations"],
            "verification_timestamp": datetime.utcnow(),
            "user_email": user_email,
        }

        try:
            result = verifications_collection.insert_one(verification_doc)
            verification_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing verification: {e}")

        blockchain_id = None
        try:
            blockchain_id = add_verification_to_blockchain(
                blockchain_verification_data)
            logger.info(f"Verification added to blockchain: {blockchain_id}")
        except Exception as e:
            logger.error(f"Error adding verification to blockchain: {str(e)}")

        trustworthy = verification_results["overall_score"] >= 0.6
        analysis = (
            f"**Status: {verification_results['status']}**\n\n"
            + f"**Analysis:**\n"
            + f"Based on our verification, this claim appears to be {
                verification_results['status'].lower()}. "
            + f"Overall verification score: {verification_results[
                'overall_score']:.1%}\n\n"
            + f"**Evidence:**\n" + "\n".join([f"* {
                rec}" for rec in verification_results[
                "recommendations"]])
            + f"\n\n**Blockchain Security:** {
                '✅ Secured' if blockchain_id else '⚠️ Not secured'}"
        )

        response_data = {
            "success": True,
            "trustworthy": trustworthy,
            "analysis": analysis,
            "evidence": verification_results["recommendations"],
            "verification": verification_doc,
            "detailed_breakdown": verification_results["detailed_breakdown"],
            "blockchain_id": blockchain_id,
            "blockchain_secured": blockchain_id is not None,
            "transparency_info": {
                "immutable_record": blockchain_id is not None,
                "public_verification": True,
                "tamper_proof": blockchain_id is not None,
            },
        }

        logger.info(
            f"Universal verification completed for {company_name}: {
                verification_results['overall_score']:.1%} ({
                    verification_results['status']})"
        )

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error verifying claim: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}),
    500


@app.route("/api/alternatives/suggest", methods=["POST"])
def suggest_alternatives():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        company_name = data.get("company_name", "")
        product_category = data.get("product_category", "general")

        alternatives = generate_alternatives(company_name, product_category)

        return jsonify(
            {
                "success": True,
                "alternatives": alternatives,
                "total_found": len(alternatives),
                "category": product_category,
                "search_criteria": {
                    "min_sustainability_score": 0.8,
                    "verified_certifications": True,
                    "price_competitive": True,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error suggesting alternatives: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}),
    500


@app.route("/api/community/submit", methods=["POST"])
def submit_community_feedback():
    """Submit community feedback on claims"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        feedback_type = data.get("feedback_type", "") or data.get("type", "")
        company = data.get("company", "") or data.get("company_name", "")
        content = data.get("content", "") or data.get("description", "")
        user_id = data.get("user_id", "anonymous")

        if not all([feedback_type, company, content]):
            error_msg = (
                "feedback_type/type, company, "
                "and content/description are required"
            )
            return jsonify({"error": error_msg}), 400

        credibility_score = calculate_credibility_score(content, feedback_type)

        submission_doc = {
            "feedback_type": feedback_type,
            "company": company,
            "content": content,
            "user_id": user_id,
            "credibility_score": credibility_score,
            "submission_timestamp": datetime.utcnow(),
            "votes": {"helpful": 0, "not_helpful": 0},
            "status": "pending_review",
        }

        try:
            result = user_submissions_collection.insert_one(submission_doc)
            submission_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing submission: {e}")

        success_message = "Thank you for your contribution to the community!"

        return (
            jsonify(
                {
                    "success": True,
                    "submission": submission_doc,
                    "message": success_message,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error(f"Error submitting community feedback: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}),
    500


def calculate_credibility_score(content, feedback_type):
    """Calculate credibility score for community submissions"""
    base_score = 0.5

    if len(content) > 100:
        base_score += 0.2

    evidence_keywords = [
        "certified",
        "verified",
        "source",
        "data",
        "report",
        "study",
        "research",
    ]
    evidence_count = sum(
        1 for keyword in evidence_keywords if keyword in content.lower()
    )
    base_score += evidence_count * 0.1

    if feedback_type == "additional_info":
        base_score += 0.1
    elif feedback_type == "dispute":
        base_score += 0.05

    return round(min(1.0, base_score), 2)


@app.route("/api/blockchain/stats", methods=["GET"])
def get_blockchain_stats():
    """Get comprehensive blockchain network statistics"""
    try:
        blockchain_stats = get_blockchain_statistics()
        return (
            jsonify(
                {
                    "success": True,
                    "blockchain_stats": blockchain_stats,
                    "transparency_features": {
                        "immutable_records": True,
                        "public_verification": True,
                        "tamper_proof": True,
                        "decentralized": True,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error getting blockchain stats: {str(e)}")
        return jsonify({"error": "Failed to get blockchain stats"}), 500


@app.route("/api/blockchain/verify/<verification_id>", methods=["GET"])
def get_verification_proof(verification_id):
    """Get immutable proof of verification from blockchain"""
    try:
        proof = get_blockchain_verification_proof(verification_id)
        if proof:
            return (
                jsonify(
                    {
                        "success": True,
                        "verification_proof": proof,
                        "blockchain_integrity": {
                            "immutable": True,
                            "tamper_proof": True,
                            "cryptographically_secured": True,
                            "publicly_verifiable": True,
                        },
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "error": "Verification not found on blockchain",
                        "verification_id": verification_id,
                    }
                ),
                404,
            )
    except Exception as e:
        logger.error(f"Error getting verification proof: {str(e)}")
        return jsonify({"error": "Failed to get verification proof"}), 500


@app.route("/api/blockchain/company/<company_name>/history", methods=["GET"])
def get_company_verification_history(company_name):
    """Get company's complete verification history from blockchain"""
    try:
        history = get_company_blockchain_history(company_name)
        return (
            jsonify(
                {
                    "success": True,
                    "company_name": company_name,
                    "verification_history": history,
                    "total_verifications": len(history),
                    "blockchain_transparency": {
                        "immutable_records": True,
                        "complete_history": True,
                        "public_access": True,
                    },
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error getting company history: {str(e)}")
        return jsonify({"error": "Failed to get company history"}), 500


@app.route("/api/blockchain/user/<user_email>/history", methods=["GET"])
def get_user_verification_history(user_email):
    """Get user's verification history from blockchain"""
    try:
        history = get_user_blockchain_history(user_email)
        return (
            jsonify(
                {
                    "success": True,
                    "user_email": user_email,
                    "verification_history": history,
                    "total_verifications": len(history),
                    "transparency_note":
                        "All user verifications are recorded on blockchain for"
                        "transparency",
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error getting user history: {str(e)}")
        return jsonify({"error": "Failed to get user history"}), 500


@app.route("/api/analytics/stats", methods=["GET"])
def get_analytics():
    """Get real-time analytics and statistics with blockchain data"""
    try:
        total_claims = claims_collection.count_documents({})
        high_risk_claims = claims_collection.count_documents(
            {"greenwashing_risk": {"$gte": 0.7}}
        )

        total_users = users_collection.count_documents({})
        total_verifications = verifications_collection.count_documents({})
        total_community_reports = user_submissions_collection.count_documents({})

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_claims = claims_collection.count_documents(
            {"detected_timestamp": {"$gte": seven_days_ago}}
        )

        pipeline = [
            {"$group": {"_id": "$keyword", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5},
        ]
        top_keywords = list(claims_collection.aggregate(pipeline))

        greenwashing_rate = round(high_risk_claims / max(total_claims, 1), 2)

        try:
            blockchain_stats = get_blockchain_statistics()
        except Exception as e:
            logger.error(f"Error getting blockchain stats: {str(e)}")
            blockchain_stats = {"total_blocks": 0, "verification_blocks": 0}

        logger.info(
            f"Real-time stats - Claims: {total_claims}, Verifications: {
                total_verifications}, Reports: {
                    total_community_reports}, Users: {total_users}"
        )

        return jsonify(
            {
                "success": True,
                "total_claims_analyzed": total_claims,
                "companies_verified": total_verifications,
                "community_reports": total_community_reports,
                "greenwashing_detected": high_risk_claims,
                "statistics": {
                    "total_claims_analyzed": total_claims,
                    "total_users": total_users,
                    "high_risk_claims": high_risk_claims,
                    "recent_claims_7days": recent_claims,
                    "greenwashing_rate": greenwashing_rate,
                    "top_keywords": top_keywords,
                    "last_updated": datetime.utcnow().isoformat(),
                },
                "blockchain": {
                    "total_blocks": blockchain_stats.get("total_blocks", 0),
                    "verification_blocks": blockchain_stats.get(
                        "verification_blocks", 0
                    ),
                    "companies_on_blockchain": blockchain_stats.get(
                        "companies_on_blockchain", 0
                    ),
                    "chain_valid": blockchain_stats.get("chain_integrity",
                                                        {}).get(
                        "valid", False
                    ),
                    "network_status": blockchain_stats.get("network_status",
                                                           "unknown"),
                },
                "data_source": "real_time_mongodb_blockchain",
                "transparency_features": {
                    "blockchain_secured": True,
                    "immutable_records": True,
                    "public_verification": True,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}),
    500


@app.route("/api/admin/debug-stats", methods=["GET"])
def debug_statistics():
    """Debug endpoint to see what's in the database and blockchain"""
    try:
        claims_count = claims_collection.count_documents({})
        verifications_count = verifications_collection.count_documents({})
        submissions_count = user_submissions_collection.count_documents({})
        users_count = users_collection.count_documents({})
        companies_count = companies_collection.count_documents({})

        sample_claim = claims_collection.find_one()
        sample_verification = verifications_collection.find_one()
        sample_submission = user_submissions_collection.find_one()
        sample_user = users_collection.find_one()

        def clean_doc(doc):
            if doc:
                if "_id" in doc:
                    doc["_id"] = str(doc["_id"])
                for key, value in doc.items():
                    if isinstance(value, datetime):
                        doc[key] = value.isoformat()
            return doc

        high_risk_claims = claims_collection.count_documents(
            {"greenwashing_risk": {"$gte": 0.7}}
        )

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_claims = claims_collection.count_documents(
            {"detected_timestamp": {"$gte": seven_days_ago}}
        )

        try:
            blockchain_stats = get_blockchain_statistics()
        except Exception as e:
            logger.error(f"Error getting blockchain stats: {str(e)}")
            blockchain_stats = {"error": str(e)}

        return jsonify(
            {
                "success": True,
                "dashboard_numbers_explanation": {
                    "claims_analyzed":
                        f"From claims collection: {claims_count} documents",
                    "companies_verified":
                        f"From verifications collection: {verifications_count}"
                        "documents",
                    "community_reports":
                        f"From user_submissions collection: {
                            submissions_count} documents",
                    "greenwashing_detected":
                        f"High-risk claims (>=0.7): {high_risk_claims}"
                        "documents",
                },
                "detailed_counts": {
                    "claims": claims_count,
                    "verifications": verifications_count,
                    "user_submissions": submissions_count,
                    "users": users_count,
                    "companies": companies_count,
                    "high_risk_claims": high_risk_claims,
                    "recent_claims_7days": recent_claims,
                },
                "sample_documents": {
                    "sample_claim": clean_doc(sample_claim),
                    "sample_verification": clean_doc(sample_verification),
                    "sample_submission": clean_doc(sample_submission),
                    "sample_user": clean_doc(sample_user),
                },
                "blockchain_info": blockchain_stats,
                "note": "This shows exactly what data is in your MongoDB"
                "collections and blockchain",
                "system_features": {
                    "universal_company_support": True,
                    "dynamic_scoring": True,
                    "ai_powered_analysis": True,
                    "global_verification": True,
                    "blockchain_transparency": True,
                    "immutable_records": True,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error debugging statistics: {str(e)}")
        return jsonify({"error": "Failed to debug statistics",
                        "details": str(e)}), 500


@app.route("/api/admin/reset-stats", methods=["POST"])
def reset_statistics():
    """Reset all statistics to zero (for testing purposes)"""
    try:
        before_counts = {
            "claims": claims_collection.count_documents({}),
            "verifications": verifications_collection.count_documents({}),
            "submissions": user_submissions_collection.count_documents({}),
            "users": users_collection.count_documents({}),
        }

        claims_collection.delete_many({})
        verifications_collection.delete_many({})
        user_submissions_collection.delete_many({})

        logger.info(f"Database reset - Before: {before_counts}")

        return jsonify(
            {
                "success": True,
                "message": "Statistics reset successfully",
                "cleared_counts": before_counts,
                "note": "All analytics will now show real-time data from new"
                "user interactions. Blockchain records remain immutable.",
                "blockchain_note": "Blockchain data cannot be deleted - this"
                "ensures transparency and immutability",
            }
        )

    except Exception as e:
        logger.error(f"Error resetting statistics: {str(e)}")
        return jsonify({"error": "Failed to reset statistics",
                        "details": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    available_endpoints = [
        "/api/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/logout",
        "/api/claims/detect",
        "/api/claims/verify",
        "/api/alternatives/suggest",
        "/api/community/submit",
        "/api/analytics/stats",
        "/api/blockchain/stats",
        "/api/blockchain/verify/<id>",
        "/api/blockchain/company/<name>/history",
        "/api/blockchain/user/<email>/history",
        "/api/admin/debug-stats",
        "/api/admin/reset-stats",
    ]

    return (
        jsonify(
            {
                "error": "Endpoint not found",
                "available_endpoints": available_endpoints,
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request - check your JSON data"}), 400


def init_database():
    """Initialize database with proper indexes"""
    try:
        claims_collection.create_index([("detected_timestamp", -1)],
                                       background=True)
        claims_collection.create_index([("greenwashing_risk", -1)],
                                       background=True)
        claims_collection.create_index([("keyword", 1)], background=True)

        verifications_collection.create_index([("company_name", 1)],
                                              background=True)
        verifications_collection.create_index(
            [("verification_timestamp", -1)], background=True
        )
        verifications_collection.create_index(
            [("verification_score", -1)], background=True
        )
        verifications_collection.create_index([("user_email", 1)],
                                              background=True)

        user_submissions_collection.create_index(
            [("submission_timestamp", -1)], background=True
        )
        user_submissions_collection.create_index([("company", 1)],
                                                 background=True)

        users_collection.create_index([("email", 1)], unique=True,
                                      background=True)
        users_collection.create_index([("created_at", -1)], background=True)

        logger.info("Database indexes created successfully")

    except Exception as e:
        logger.warning(f"Index creation warning: {e}")


if __name__ == "__main__":
    init_database()

    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    host = os.getenv("HOST", "127.0.0.1")

    logger.info(
        f"Starting GreenGuard Universal Verification API with Blockchain on {
            host}:{port}"
    )
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Database: {DATABASE_NAME}")
    logger.info(
        "Features: Universal Company Support, Dynamic AI Analysis, Global"
        "Verification, Blockchain Transparency"
    )

    app.run(host=host, port=port, debug=debug)
