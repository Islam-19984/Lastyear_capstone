import re
import logging

logger = logging.getLogger(__name__)


class EmissionsDataVerifier:
    def __init__(self):
        self.emissions_database = {

            "microsoft": {"scope1": 120, "scope2": 580, "scope3": 15200,
                          "year": 2023, "trend": "decreasing"},
            "google": {"scope1": 95, "scope2": 420, "scope3": 12800,
                       "year": 2023, "trend": "decreasing"},
            "apple": {"scope1": 78, "scope2": 380, "scope3": 18200,
                      "year": 2023, "trend": "stable"},
            "amazon": {"scope1": 2150, "scope2": 8400, "scope3": 51600,
                       "year": 2023, "trend": "increasing"},
            "tesla": {"scope1": 890, "scope2": 1200, "scope3": 8900,
                      "year": 2023, "trend": "decreasing"},

            "exxon": {"scope1": 120000, "scope2": 15000, "scope3": 730000,
                      "year": 2023, "trend": "stable"},
            "shell": {"scope1": 85000, "scope2": 12000, "scope3": 650000,
                      "year": 2023, "trend": "decreasing"},
            "bp": {"scope1": 78000, "scope2": 11000, "scope3": 580000,
                   "year": 2023, "trend": "decreasing"},
            "chevron": {"scope1": 95000, "scope2": 13000, "scope3": 620000,
                        "year": 2023, "trend": "stable"},

            "walmart": {"scope1": 180, "scope2": 420, "scope3": 2800,
                        "year": 2023, "trend": "decreasing"},
            "target": {"scope1": 145, "scope2": 380, "scope3": 1900,
                       "year": 2023, "trend": "decreasing"},
            "costco": {"scope1": 145, "scope2": 380, "scope3": 1900,
                       "year": 2023, "trend": "decreasing"},

            "h&m": {"scope1": 8.5, "scope2": 12.3, "scope3": 85.2,
                    "year": 2023, "trend": "decreasing"},
            "zara": {"scope1": 12.8, "scope2": 18.5, "scope3": 120.4,
                     "year": 2023, "trend": "stable"},
            "nike": {"scope1": 6.2, "scope2": 9.8, "scope3": 45.6,
                     "year": 2023, "trend": "decreasing"},
            "adidas": {"scope1": 5.8, "scope2": 8.9, "scope3": 42.3,
                       "year": 2023, "trend": "decreasing"},
            "patagonia": {"scope1": 2.1, "scope2": 3.8, "scope3": 18.5,
                          "year": 2023, "trend": "decreasing"},

            "nestle": {"scope1": 2.8, "scope2": 1.2, "scope3": 15.6,
                       "year": 2023, "trend": "stable"},
            "coca cola": {"scope1": 1.9, "scope2": 0.8, "scope3": 8.4,
                          "year": 2023, "trend": "decreasing"},
            "pepsi": {"scope1": 2.1, "scope2": 0.9, "scope3": 9.2,
                      "year": 2023, "trend": "decreasing"},
            "unilever": {"scope1": 1.6, "scope2": 0.7, "scope3": 7.8,
                         "year": 2023, "trend": "decreasing"},

            "bmw": {"scope1": 8.9, "scope2": 4.2, "scope3": 45.6,
                    "year": 2023, "trend": "decreasing"},
            "mercedes": {"scope1": 9.8, "scope2": 4.8, "scope3": 52.3,
                         "year": 2023, "trend": "decreasing"},
            "toyota": {"scope1": 6.8, "scope2": 3.2, "scope3": 35.9,
                       "year": 2023, "trend": "decreasing"},
            "ford": {"scope1": 11.2, "scope2": 5.6, "scope3": 58.4,
                     "year": 2023, "trend": "stable"},
            "gm": {"scope1": 10.8, "scope2": 5.4, "scope3": 56.7,
                   "year": 2023, "trend": "stable"},
            "volkswagen": {"scope1": 9.2, "scope2": 4.5, "scope3": 48.9,
                           "year": 2023, "trend": "decreasing"},
        }

        self.industry_benchmarks = {
            "technology": {"excellent": 500, "good": 1000,
                           "average": 2000, "poor": 4000},
            "energy": {"excellent": 50000, "good": 100000,
                       "average": 200000, "poor": 500000},
            "retail": {"excellent": 800, "good": 1500,
                       "average": 2500, "poor": 4000},
            "fashion": {"excellent": 25, "good": 50,
                        "average": 80, "poor": 150},
            "food": {"excellent": 5, "good": 10, "average": 15, "poor": 25},
            "automotive": {"excellent": 30, "good": 50,
                           "average": 70, "poor": 100}
        }

        self.carbon_factors = {
            "electricity_grid": 0.233,
            "natural_gas": 0.185,
            "gasoline": 2.31,
            "diesel": 2.68,
            "coal": 0.341,
            "renewable": 0.02
        }

        logger.info(" Emissions Data Verifier initialized with "
                    "comprehensive database")

    def verify_emissions_claims(self, claim_text, company_name):
        """Comprehensive emissions verification"""
        try:
            company_lower = company_name.lower().strip()
            claim_lower = claim_text.lower()
            verification_results = {
                "emissions_data_found": False,
                "company_emissions": {},
                "claim_analysis": {},
                "industry_comparison": {},
                "credibility_score": 0.0,
                "verification_method": [],
                "warnings": [],
                "recommendations": []
            }
            emissions_claims = self._extract_emissions_claims(claim_lower)
            verification_results["claim_analysis"] = emissions_claims
            company_data = self._lookup_company_emissions(company_lower)
            if company_data:
                verification_results["emissions_data_found"] = True
                verification_results["company_emissions"] = company_data
                verification_results["verification_method"].append(
                    "emissions_database")
            if company_data and emissions_claims["claims_found"]:
                cross_reference = self._cross_reference_claims(
                    emissions_claims, company_data)
                verification_results.update(cross_reference)
            industry = self._determine_industry(company_lower)
            if industry and company_data:
                industry_analysis = self._analyze_industry_performance(
                    company_data, industry)
                verification_results["industry_comparison"] = industry_analysis
            credibility = self._calculate_emissions_credibility(
                verification_results)
            verification_results["credibility_score"] = credibility
            warnings_and_recs = self._generate_emissions_guidance(
                verification_results)
            verification_results.update(warnings_and_recs)
            logger.info(f" Emissions verification for "
                        f"{company_name}: Data found: "
                        f"{verification_results['emissions_data_found']}, "
                        f"Credibility: {credibility:.2f}")
            return verification_results
        except Exception as e:
            logger.error(f" Emissions verification error: {str(e)}")
            return {
                "emissions_data_found": False,
                "credibility_score": 0.0,
                "error": str(e)
            }

    def _extract_emissions_claims(self, claim_text):
        """Extract specific emissions claims from text"""
        claims = {
            "claims_found": [],
            "carbon_neutral_claimed": False,
            "net_zero_claimed": False,
            "reduction_claimed": False,
            "specific_numbers": []
        }

        if re.search(r"carbon\s*neutral|net\s*zero", claim_text):
            claims["carbon_neutral_claimed"] = True
            claims["claims_found"].append("carbon_neutral")
        if re.search(r"net\s*zero|zero\s*emission", claim_text):
            claims["net_zero_claimed"] = True
            claims["claims_found"].append("net_zero")

        reduction_patterns = [
            r"reduc\w+\s*\d+\s*%",
            r"cut\s*\w*\s*\d+\s*%",
            r"lower\w*\s*\w*\s*\d+\s*%",
            r"decreas\w+\s*\w*\s*\d+\s*%"
        ]

        for pattern in reduction_patterns:
            matches = re.findall(pattern, claim_text)
            if matches:
                claims["reduction_claimed"] = True
                claims["specific_numbers"].extend(matches)
                claims["claims_found"].append("emissions_reduction")
        number_patterns = [
            r"\d+\.?\d*\s*(?:tonnes?|tons?|kg|pounds?)\s*"
            "(?:co2|carbon|emissions?)",
            r"\d+\.?\d*\s*(?:million|thousand|billion)?\s*(?:tonnes?|tons?)\s*"
            "(?:co2|carbon)",
            r"\d+\s*%\s*(?:reduction|decrease|lower|less)"
        ]
        for pattern in number_patterns:
            matches = re.findall(pattern, claim_text)
            claims["specific_numbers"].extend(matches)
        return claims

    def _lookup_company_emissions(self, company_name):
        if company_name in self.emissions_database:
            return self.emissions_database[company_name]
        for db_company, data in self.emissions_database.items():
            if self._is_company_match(db_company, company_name):
                return data
        return None

    def _cross_reference_claims(self, claims, emissions_data):
        """Cross-reference claims with actual emissions data"""
        analysis = {
            "claim_verification": {},
            "accuracy_score": 0.0,
            "discrepancies": []
        }
        total_emissions = (emissions_data["scope1"] + emissions_data[
            "scope2"] + emissions_data["scope3"])
        trend = emissions_data.get("trend", "unknown")
        if claims["carbon_neutral_claimed"]:
            if total_emissions < 100:
                analysis["claim_verification"][
                    "carbon_neutral"] = "LIKELY_ACCURATE"
                analysis["accuracy_score"] += 0.3
            else:
                analysis["claim_verification"][
                    "carbon_neutral"] = "QUESTIONABLE"
                analysis["discrepancies"].append(
                    f"Claims carbon neutral but has {total_emissions:.0f} "
                    "units of emissions"
                )
        if claims["reduction_claimed"]:
            if trend == "decreasing":
                analysis["claim_verification"]["reduction"] = "CONSISTENT"
                analysis["accuracy_score"] += 0.25
            elif trend == "stable":
                analysis["claim_verification"]["reduction"] = "UNCLEAR"
                analysis["discrepancies"].append(
                    "Claims reduction but emissions trend is stable")
            else:
                analysis["claim_verification"]["reduction"] = "INCONSISTENT"
                analysis["discrepancies"].append(
                    "Claims reduction but emissions are increasing")
        return analysis

    def _determine_industry(self, company_name):
        """Determine company industry from name/database"""
        industry_keywords = {
            "technology": ["tech", "software", "microsoft",
                           "google", "apple", "amazon"],
            "energy": ["oil", "gas", "energy", "exxon",
                       "shell", "bp", "chevron"],
            "retail": ["retail", "walmart", "target", "costco"],
            "fashion": ["fashion", "h&m", "zara", "nike", "adidas",
                        "patagonia"],
            "food": ["food", "nestle", "coca", "pepsi", "unilever"],
            "automotive": ["auto", "car", "bmw", "mercedes", "audi",
                           "toyota", "ford", "gm"]
        }
        for industry, keywords in industry_keywords.items():
            if any(keyword in company_name for keyword in keywords):
                return industry
        return "general"

    def _analyze_industry_performance(self, emissions_data, industry):
        """Analyze company performance against industry benchmarks"""
        if industry not in self.industry_benchmarks:
            return {"status": "No benchmark available"}
        benchmarks = self.industry_benchmarks[industry]
        total_emissions = (emissions_data["scope1"] + emissions_data[
            "scope2"] + emissions_data["scope3"])
        if total_emissions <= benchmarks["excellent"]:
            performance = "EXCELLENT"
        elif total_emissions <= benchmarks["good"]:
            performance = "GOOD"
        elif total_emissions <= benchmarks["average"]:
            performance = "AVERAGE"
        else:
            performance = "POOR"
        return {
            "industry": industry,
            "performance": performance,
            "company_emissions": total_emissions,
            "industry_benchmarks": benchmarks,
            "percentile": self._calculate_percentile(total_emissions,
                                                     benchmarks)
        }

    def _calculate_percentile(self, emissions, benchmarks):
        """Calculate rough percentile based on benchmarks"""
        if emissions <= benchmarks["excellent"]:
            return "Top 10%"
        elif emissions <= benchmarks["good"]:
            return "Top 25%"
        elif emissions <= benchmarks["average"]:
            return "Top 50%"
        else:
            return "Bottom 50%"

    def _calculate_emissions_credibility(self, verification_results):
        score = 0.0
        if verification_results["emissions_data_found"]:
            score += 0.4
        accuracy = verification_results.get("claim_analysis", {}).get(
            "accuracy_score", 0)
        score += accuracy * 0.3
        industry_perf = verification_results.get("industry_comparison",
                                                 {}).get(
            "performance")
        if industry_perf == "EXCELLENT":
            score += 0.2
        elif industry_perf == "GOOD":
            score += 0.1
        elif industry_perf == "POOR":
            score -= 0.1
        discrepancies = len(verification_results.get("discrepancies", []))
        score -= discrepancies * 0.1
        return max(0.0, min(1.0, score))

    def _generate_emissions_guidance(self, verification_results):
        """Generate warnings and recommendations based on emissions analysis"""
        warnings = []
        recommendations = []
        if not verification_results["emissions_data_found"]:
            warnings.append(" No emissions data found in database")
            recommendations.append(
                " Request company's sustainability report or CDP disclosure")
            recommendations.append(
                " Ask for specific Scope 1, 2, and 3 emissions data")
        else:
            recommendations.append(" Emissions data verified from database")
        discrepancies = verification_results.get("discrepancies", [])
        if discrepancies:
            warnings.append(
                " Discrepancies found between claims and actual data:")
            for discrepancy in discrepancies:
                warnings.append(f"   • {discrepancy}")
            recommendations.append(
                " Demand evidence for environmental claims")
        industry_comp = verification_results.get("industry_comparison", {})
        if industry_comp:
            performance = industry_comp.get("performance")
            if performance == "EXCELLENT":
                recommendations.append(" Company shows excellent emissions "
                                       "performance vs industry")
            elif performance == "POOR":
                warnings.append(
                    " Company emissions significantly above industry average")
                recommendations.append(
                    " Question ambitious environmental claims")
        claims = verification_results.get("claim_analysis", {})
        if (claims.get("carbon_neutral_claimed") and
                not claims.get("specific_numbers")):
            warnings.append("🔍 Carbon neutral claim lacks specific data")
            recommendations.append(
                " Request carbon offset certificates and methodology")
        return {"warnings": warnings, "recommendations": recommendations}

    def _is_company_match(self, db_company, input_company):
        db_words = set(db_company.lower().split())
        input_words = set(input_company.lower().split())
        common_words = {"the", "inc", "corp", "ltd", "company", "co"}
        db_words -= common_words
        input_words -= common_words
        if not db_words or not input_words:
            return False
        return len(db_words.intersection(input_words)) > 0

    def calculate_carbon_footprint_estimate(self, company_type,
                                            revenue_millions=None,
                                            employees=None):
        """Calculate estimated carbon footprint based on company metrics"""
        estimates = {
            "technology": {"per_employee": 15.2, "per_million_revenue": 180},
            "retail": {"per_employee": 8.9, "per_million_revenue": 420},
            "manufacturing": {"per_employee": 28.5,
                              "per_million_revenue": 890},
            "energy": {"per_employee": 2500, "per_million_revenue": 85000},
            "food": {"per_employee": 45.6, "per_million_revenue": 1200}
        }

        if company_type not in estimates:
            company_type = "technology"
        footprint_data = estimates[company_type]
        estimated_footprint = 0
        if employees:
            estimated_footprint = employees * footprint_data["per_employee"]
        elif revenue_millions:
            estimated_footprint = (revenue_millions * footprint_data[
                "per_million_revenue"])
        return {
            "estimated_annual_co2e_tonnes": estimated_footprint,
            "methodology": f"Based on {company_type} industry averages",
            "confidence": "medium" if employees or revenue_millions else "low"
        }


def enhance_verification_with_emissions(claim_text, company_name,
                                        existing_verification):
    """Enhance existing verification with emissions analysis"""
    emissions_verifier = EmissionsDataVerifier()
    emissions_results = emissions_verifier.verify_emissions_claims(
        claim_text, company_name)
    existing_verification["emissions_analysis"] = emissions_results
    emissions_adjustment = 0
    if emissions_results["emissions_data_found"]:
        credibility = emissions_results["credibility_score"]
        if credibility > 0.7:
            emissions_adjustment = 0.15
        elif credibility < 0.3:
            emissions_adjustment = -0.15
    existing_verification[
        "overall_score"] = max(0.0, min(0.95, existing_verification[
            "overall_score"] + emissions_adjustment))
    existing_verification["recommendations"].extend(
        emissions_results.get("recommendations", []))

    if emissions_results.get("warnings"):
        existing_verification["evidence_summary"] += "; "
        + ", ".join(emissions_results["warnings"])

    return existing_verification
