from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, timedelta
import re
import os
from dotenv import load_dotenv
import logging

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
            "biodegradable",
            "compostable",
            "eco",
            "environmental",
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
                        "greenwashing_risk": self.assess_greenwashing_risk(sentence),
                    }
                    claims.append(claim_data)
                    break

        return claims

    def calculate_confidence(self, sentence):
        """Calculate confidence score for claim detection"""
        words = sentence.lower().split()
        env_word_count = sum(
            1 for word in words if any(kw in word for kw in self.environmental_keywords)
        )
        confidence = min(0.95, 0.3 + (env_word_count / len(words)) * 2)
        return round(confidence, 2)

    def assess_greenwashing_risk(self, sentence):
        """Assess greenwashing risk of a claim"""
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
        risk_factors += sum(1 for term in vague_terms if term in sentence_lower)

        absolute_terms = [
            "100%",
            "completely",
            "totally",
            "fully",
            "entirely",
            "perfect",
        ]
        risk_factors += sum(2 for term in absolute_terms if term in sentence_lower)

        specificity_terms = ["certified", "verified", "approved", "audited"]
        if not any(cert in sentence_lower for cert in specificity_terms):
            risk_factors += 1

        superlatives = ["best", "most", "leading", "ultimate", "revolutionary"]
        risk_factors += sum(1 for sup in superlatives if sup in sentence_lower)

        risk_score = min(1.0, risk_factors / 6)
        return round(risk_score, 2)


claim_detector = ClaimDetector()


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


def simulate_verification(claim_text, company_name):
    """Simulate verification against external data sources"""
    cdp_score = (
        0.2 if "carbon neutral" in claim_text.lower() and not company_name else 0.7
    )

    sbti_score = 0.1 if "science-based" not in claim_text.lower() else 0.8
    epa_score = 0.6 if "renewable energy" in claim_text.lower() else 0.3
    overall_score = round((cdp_score + sbti_score + epa_score) / 3, 2)

    if overall_score < 0.4:
        risk_level = "HIGH"
        recommendations = [
            "No third-party verification found",
            "Claims appear to be unsubstantiated",
            "Consider looking for certified alternatives",
        ]
    elif overall_score < 0.7:
        risk_level = "MEDIUM"
        recommendations = [
            "Some verification found but incomplete",
            "Look for additional certifications",
            "Request more detailed sustainability information",
        ]
    else:
        risk_level = "LOW"
        recommendations = [
            "Claims appear to be well-substantiated",
            "Good transparency in reporting",
            "Consider this a reliable option",
        ]

    return {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "sources": {
            "cdp": {"score": cdp_score, "status": "checked"},
            "sbti": {"score": sbti_score, "status": "checked"},
            "epa": {"score": epa_score, "status": "checked"},
        },
        "recommendations": recommendations,
    }


def generate_alternatives(company_name, category):
    """Generate alternative product suggestions"""
    alternatives_db = {
        "fashion": [
            {
                "name": "Patagonia",
                "product": "Organic Cotton Jacket",
                "certifications": ["Fair Trade", "B-Corp", "1% for the Planet"],
                "sustainability_score": 0.92,
                "price_range": "$80-120",
                "url": "https://patagonia.com",
                "why_better": ("Verified certifications and transparent supply chain"),
            },
            {
                "name": "Eileen Fisher",
                "product": "Sustainable Outerwear",
                "certifications": ["GOTS Certified", "Cradle to Cradle"],
                "sustainability_score": 0.88,
                "price_range": "$90-150",
                "url": "https://eileenfisher.com",
                "why_better": "Circular design and take-back program",
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
                "why_better": ("Plant-based ingredients with EPA certification"),
            },
            {
                "name": "Method",
                "product": "Green Cleaning Products",
                "certifications": ["Cradle to Cradle", "EPA Design for Environment"],
                "sustainability_score": 0.82,
                "price_range": "Affordable",
                "url": "https://methodhome.com",
                "why_better": ("Biodegradable formulas in recycled packaging"),
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
                "preferences": {"notifications": True, "analysis_level": "medium"},
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
        return jsonify({"error": "Registration failed", "details": str(e)}), 500


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
                {"success": True, "message": "Login successful", "user": user_response}
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
    except Exception:
        db_status = "disconnected"

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "database": db_status,
            "endpoints": {
                "auth_register": "/api/auth/register",
                "auth_login": "/api/auth/login",
                "auth_logout": "/api/auth/logout",
                "claims_detect": "/api/claims/detect",
                "claims_verify": "/api/claims/verify",
                "alternatives": "/api/alternatives/suggest",
                "community": "/api/community/submit",
                "debug_stats": "/api/admin/debug-stats",
            },
        }
    )


@app.route("/api/claims/detect", methods=["POST"])
def detect_claims():
    """Detect environmental claims in text"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get("text", "") or data.get("content", "")
        url = data.get("url", "")

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

        high_risk_claims = [c for c in detected_claims if c["greenwashing_risk"] >= 0.7]

        if avg_risk >= 0.7:
            risk_level = "High"
            summary = f"Found {len(detected_claims)} environmental claims with high greenwashing risk. These claims appear vague or unsubstantiated."
        elif avg_risk >= 0.4:
            risk_level = "Medium"
            summary = f"Found {len(detected_claims)} environmental claims with moderate risk. Some claims may need verification."
        else:
            risk_level = "Low"
            summary = f"Found {len(detected_claims)} environmental claims that appear well-substantiated."

        return jsonify(
            {
                "success": True,
                "claims_count": len(detected_claims),
                "risk_score": avg_risk,
                "summary": summary,
                "claims": stored_claims,
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
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/api/claims/verify", methods=["POST"])
def verify_claim():
    """Verify a specific environmental claim"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        claim_text = data.get("claim_text", "") or data.get("claim", "")
        company_name = data.get("company_name", "") or data.get("company", "")

        if not claim_text:
            return jsonify({"error": "Claim text is required"}), 400

        verification_results = simulate_verification(claim_text, company_name)

        verification_doc = {
            "claim_text": claim_text,
            "company_name": company_name,
            "verification_score": verification_results["overall_score"],
            "risk_level": verification_results["risk_level"],
            "data_sources": verification_results["sources"],
            "recommendations": verification_results["recommendations"],
            "verification_timestamp": datetime.utcnow(),
        }

        try:
            result = verifications_collection.insert_one(verification_doc)
            verification_doc["_id"] = str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error storing verification: {e}")

        trustworthy = verification_results["overall_score"] >= 0.6
        analysis = (
            f"Based on our verification, this claim appears to be {'trustworthy' if trustworthy else 'questionable'}. "
            + f"Overall verification score: {verification_results['overall_score']:.1%}"
        )

        response_data = {
            "success": True,
            "trustworthy": trustworthy,
            "analysis": analysis,
            "evidence": verification_results["recommendations"],
            "verification": verification_doc,
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error verifying claim: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/api/alternatives/suggest", methods=["POST"])
def suggest_alternatives():
    """Suggest sustainable alternatives"""
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
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


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
                "feedback_type/type, company, and content/description are required"
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
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


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


@app.route("/api/analytics/stats", methods=["GET"])
def get_analytics():
    """Get real-time analytics and statistics"""
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

        logger.info(
            f"Real-time stats - Claims: {total_claims}, Verifications: {total_verifications}, Reports: {total_community_reports}, Users: {total_users}"
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
                "data_source": "real_time_mongodb",
            }
        )

    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/api/admin/debug-stats", methods=["GET"])
def debug_statistics():
    """Debug endpoint to see what's in the database"""
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

        return jsonify(
            {
                "success": True,
                "dashboard_numbers_explanation": {
                    "claims_analyzed_111": f"From claims collection: {claims_count} documents",
                    "companies_verified_4": f"From verifications collection: {verifications_count} documents",
                    "community_reports_6": f"From user_submissions collection: {submissions_count} documents",
                    "greenwashing_detected_0": f"High-risk claims (>=0.7): {high_risk_claims} documents",
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
                "note": "This shows exactly what data is in your MongoDB collections causing the dashboard numbers",
            }
        )

    except Exception as e:
        logger.error(f"Error debugging statistics: {str(e)}")
        return jsonify({"error": "Failed to debug statistics", "details": str(e)}), 500


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
                "note": "All analytics will now show real-time data from new user interactions",
            }
        )

    except Exception as e:
        logger.error(f"Error resetting statistics: {str(e)}")
        return jsonify({"error": "Failed to reset statistics", "details": str(e)}), 500


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


def init_sample_data():
    """Initialize database with sample data if empty"""
    try:
        if companies_collection.count_documents({}) == 0:
            sample_companies = [
                {
                    "_id": "ecofashion123",
                    "name": "EcoFashion Co",
                    "domain": "ecofashion.com",
                    "industry_sector": "fashion",
                    "verified_data": {
                        "carbon_emissions": 15000,
                        "renewable_energy_percentage": 25,
                        "certifications": ["GOTS", "Fair Trade"],
                        "last_verified": datetime.utcnow(),
                    },
                    "sustainability_scores": {
                        "overall_score": 0.45,
                        "carbon_score": 0.3,
                        "transparency_score": 0.6,
                        "certification_score": 0.8,
                    },
                    "created_at": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                },
                {
                    "_id": "greentech456",
                    "name": "GreenTech Inc",
                    "domain": "greentech.com",
                    "industry_sector": "technology",
                    "verified_data": {
                        "carbon_emissions": 8000,
                        "renewable_energy_percentage": 75,
                        "certifications": ["B-Corp", "Carbon Neutral"],
                        "last_verified": datetime.utcnow(),
                    },
                    "sustainability_scores": {
                        "overall_score": 0.85,
                        "carbon_score": 0.9,
                        "transparency_score": 0.8,
                        "certification_score": 0.85,
                    },
                    "created_at": datetime.utcnow(),
                    "last_updated": datetime.utcnow(),
                },
            ]

            companies_collection.insert_many(sample_companies)
            logger.info("Sample companies inserted")

        try:
            companies_collection.create_index(
                [("domain", 1)], unique=True, background=True
            )
            claims_collection.create_index(
                [("detected_timestamp", -1)], background=True
            )
            claims_collection.create_index([("greenwashing_risk", -1)], background=True)
            verifications_collection.create_index([("claim_id", 1)], background=True)
            user_submissions_collection.create_index(
                [("submission_timestamp", -1)], background=True
            )
            users_collection.create_index([("email", 1)], unique=True, background=True)
            logger.info("Database indexes created")
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")

        logger.info("Database initialization completed")

    except Exception as e:
        logger.error(f"Error initializing sample data: {e}")


if __name__ == "__main__":
    init_sample_data()

    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    host = os.getenv("HOST", "127.0.0.1")

    logger.info(f"Starting GreenGuard API server on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Database: {DATABASE_NAME}")

    app.run(host=host, port=port, debug=debug)
