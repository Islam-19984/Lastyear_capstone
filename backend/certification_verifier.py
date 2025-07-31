import re
import logging

logger = logging.getLogger(__name__)


class EnhancedCertificationVerifier:
    def __init__(self):
        self.certification_databases = {
            "iso": {
                "patterns": [r"iso\s*14001", r"iso\s*50001", r"iso\s*9001"],
                "verification_url": "https://www.iso.org/search.html",
                "weight": 0.9
            },
            "leed": {
                "patterns": [r"leed\s*(certified|gold|silver|platinum)",
                             r"leed\s*building"],
                "verification_url": "https://www.usgbc.org/projects",
                "weight": 0.85
            },
            "energy_star": {
                "patterns": [r"energy\s*star", r"energystar"],
                "verification_url": "https://www.energystar.gov",
                "weight": 0.8
            },
            "b_corp": {
                "patterns": [r"b\s*corp", r"certified\s*b\s*corporation",
                             r"benefit\s*corporation"],
                "verification_url": "https://bcorporation.net",
                "weight": 0.95
            },
            "fair_trade": {
                "patterns": [r"fair\s*trade", r"fairtrade"],
                "verification_url": "https://www.fairtradecertified.org",
                "weight": 0.85
            },
            "carbon_neutral": {
                "patterns": [r"carbon\s*neutral\s*certified", r"carbonfund",
                             r"gold\s*standard"],
                "verification_url": "https://www.goldstandard.org",
                "weight": 0.9
            },
            "forest_stewardship": {
                "patterns": [r"fsc\s*certified", r"forest\s*stewardship"],
                "verification_url": "https://fsc.org",
                "weight": 0.8
            },
            "cradle_to_cradle": {
                "patterns": [r"cradle\s*to\s*cradle", r"c2c\s*certified"],
                "verification_url": "https://www.c2ccertified.org",
                "weight": 0.85
            }
        }

        self.verified_companies = {
            "patagonia": {
                "certifications": ["b_corp", "fair_trade", "organic_content"],
                "verified": True,
                "last_checked": "2024-01-15"
            },
            "ben jerry": {
                "certifications": ["b_corp", "fair_trade", "organic"],
                "verified": True,
                "last_checked": "2024-01-15"
            },
            "seventh generation": {
                "certifications": ["epa_safer_choice", "usda_biobased"],
                "verified": True,
                "last_checked": "2024-01-15"
            },
            "tesla": {
                "certifications": ["iso_14001", "energy_efficiency"],
                "verified": True,
                "last_checked": "2024-01-15"
            },
            "microsoft": {
                "certifications": ["carbon_neutral", "iso_14001", "leed"],
                "verified": True,
                "last_checked": "2024-01-15"
            },
            "google": {
                "certifications": ["carbon_neutral",
                                   "renewable_energy", "leed"],
                "verified": True,
                "last_checked": "2024-01-15"
            }
        }

        logger.info(" Enhanced Certification Verifier initialized")

    def verify_certifications(self, claim_text, company_name):
        """Comprehensive certification verification"""
        try:
            company_lower = company_name.lower().strip()
            claim_lower = claim_text.lower()
            verification_results = {
                "certifications_found": [],
                "verification_status": {},
                "overall_credibility": 0.0,
                "verification_method": [],
                "warnings": [],
                "verified_claims": 0,
                "total_claims": 0
            }
            for cert_type, cert_data in self.certification_databases.items():
                for pattern in cert_data["patterns"]:
                    matches = re.findall(pattern, claim_lower)
                    if matches:
                        verification_results["certifications_found"].append({
                            "type": cert_type,
                            "matches": matches,
                            "pattern_confidence": 0.8,
                            "weight": cert_data["weight"]
                        })
                        verification_results["total_claims"] += len(matches)
            company_verification = self._verify_company_certifications(
                company_lower)
            if company_verification["verified"]:
                verification_results["verification_method"].append(
                    "company_database")
                verification_results["verified_claims"] += len(
                    company_verification["certifications"])
                for found_cert in verification_results["certifications_found"]:
                    cert_type = found_cert["type"]
                    if any(cert_type in known_cert for known_cert in
                           company_verification["certifications"]):
                        verification_results["verification_status"][
                            cert_type] = "VERIFIED"
                        found_cert["verified"] = True
                    else:
                        verification_results["verification_status"][
                            cert_type] = "UNVERIFIED"
                        found_cert["verified"] = False
                        verification_results["warnings"].append(
                            f"Claimed {cert_type} certification not found in "
                            "verified database"
                        )

            advanced_verification = self._advanced_certification_analysis(
                claim_lower)
            verification_results.update(advanced_verification)
            credibility = self._calculate_certification_credibility(
                verification_results)
            verification_results["overall_credibility"] = credibility
            verification_results[
                "recommendations"] = self._generate_cert_recommendations(
                verification_results, company_name
            )

            logger.info(
                f" Certification verification for {company_name}: "
                f"{len(verification_results['certifications_found'])} found, "
                "credibility: {credibility:.2f}")
            return verification_results
        except Exception as e:
            logger.error(f" Certification verification error: {str(e)}")
            return {
                "certifications_found": [],
                "verification_status": {},
                "overall_credibility": 0.0,
                "error": str(e)
            }

    def _verify_company_certifications(self, company_name):
        """Check company against verified certification database"""
        for verified_company, data in self.verified_companies.items():
            if self._is_company_match(verified_company, company_name):
                return {
                    "verified": True,
                    "certifications": data["certifications"],
                    "last_checked": data["last_checked"],
                    "database_match": verified_company
                }
        return {"verified": False, "certifications": [],
                "database_match": None}

    def _advanced_certification_analysis(self, claim_text):
        """Advanced analysis for certification authenticity"""
        analysis = {
            "specificity_indicators": [],
            "authenticity_score": 0.5,
            "red_flags": []
        }
        specificity_patterns = [
            (r"certificate\s*#?\s*[a-zA-Z0-9]+",
             "Certificate number mentioned", 0.3),
            (r"valid\s*until|expires?\s*\d{4}|renewed\s*\d{4}",
             "Expiration/validity mentioned", 0.2),
            (r"audited\s*by|verified\s*by|certified\s*by\s*[a-zA-Z\s]+",
             "Certifying body mentioned", 0.25),
            (r"\d{4}\s*certified|\d{4}\s*renewal",
             "Certification year mentioned", 0.15),
            (r"scope\s*of\s*certification|certificate\s*covers",
             "Scope mentioned", 0.1)
        ]

        for pattern, description, score_boost in specificity_patterns:
            if re.search(pattern, claim_text):
                analysis["specificity_indicators"].append(description)
                analysis["authenticity_score"] += score_boost
        red_flag_patterns = [
            (r"self\s*certified|internal\s*audit",
             "Self-certification mentioned"),
            (r"working\s*towards|planning\s*to|will\s*be\s*certified",
             "Future/planned certification"),
            (r"equivalent\s*to|similar\s*to|like\s*[a-zA-Z\s]+\s*certified",
             "Equivalent claims"),
            (r"certified\*|certification\*", "Asterisk indicating conditions")
        ]

        for pattern, description in red_flag_patterns:
            if re.search(pattern, claim_text):
                analysis["red_flags"].append(description)
                analysis["authenticity_score"] -= 0.2
        analysis["authenticity_score"] = max(0.0, min(1.0, analysis[
            "authenticity_score"]))
        return analysis

    def _calculate_certification_credibility(self, verification_results):
        if not verification_results["certifications_found"]:
            return 0.0
        total_weight = 0.0
        weighted_score = 0.0
        for cert in verification_results["certifications_found"]:
            weight = cert["weight"]
            verified = cert.get("verified", False)
            confidence = cert.get("pattern_confidence", 0.5)
            if verified:
                cert_score = 1.0
            else:
                cert_score = confidence * 0.6
            weighted_score += cert_score * weight
            total_weight += weight
        base_credibility = (
            weighted_score / total_weight if total_weight > 0 else 0.0
        )
        authenticity_bonus = verification_results.get(
            "authenticity_score", 0.5) * 0.2
        red_flag_penalty = len(verification_results.get("red_flags", [])) * 0.1
        final_credibility = base_credibility + authenticity_bonus
        - red_flag_penalty
        return max(0.0, min(1.0, final_credibility))

    def _generate_cert_recommendations(self, verification_results,
                                       company_name):
        """Generate recommendations based on certification analysis"""
        recommendations = []
        if not verification_results["certifications_found"]:
            recommendations.append(
                "🔍 No certifications mentioned - request verified credentials")
            return recommendations
        verified_count = sum(1 for cert in verification_results[
            "certifications_found"] if cert.get("verified", False))
        total_count = len(verification_results["certifications_found"])
        if verified_count == total_count:
            recommendations.append(
                " all claimed certifications verified in database")
        elif verified_count > 0:
            recommendations.append(
                f" {verified_count}/{total_count} certifications verified")
            recommendations.append(
                "🔍 request documentation for unverified claims")
        else:
            recommendations.append(" No certifications verified in database")
            recommendations.append(
                " Demand certificate numbers and issuing bodies")
        if verification_results.get("red_flags"):
            recommendations.append(" Red flags detected - exercise caution")
            for flag in verification_results["red_flags"]:
                recommendations.append(f"   • {flag}")
        if verification_results.get("specificity_indicators"):
            recommendations.append(" Good specificity indicators found:")
            for indicator in verification_results["specificity_indicators"]:
                recommendations.append(f"   • {indicator}")
        return recommendations

    def _is_company_match(self, db_company, input_company):
        db_words = set(db_company.lower().split())
        input_words = set(input_company.lower().split())
        common_words = {"the", "inc", "corp", "ltd", "company", "co"}
        db_words -= common_words
        input_words -= common_words
        if not db_words or not input_words:
            return False
        return len(db_words.intersection(input_words)) > 0


def enhance_verification_with_certifications(claim_text, company_name,
                                             existing_verification):
    cert_verifier = EnhancedCertificationVerifier()
    cert_results = cert_verifier.verify_certifications(claim_text,
                                                       company_name)
    existing_verification["certification_analysis"] = cert_results
    cert_boost = cert_results["overall_credibility"] * 0.15
    existing_verification["overall_score"] = min(0.95, existing_verification[
        "overall_score"] + cert_boost)

    existing_verification["recommendations"].extend(cert_results[
        "recommendations"])

    return existing_verification
