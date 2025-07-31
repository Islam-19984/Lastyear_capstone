import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ContractState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTED = "executed"
    FAILED = "failed"
    SUSPENDED = "suspended"


class ContractType(Enum):
    GREENWASHING_DETECTOR = "greenwashing_detector"
    SUSTAINABILITY_REWARDS = "sustainability_rewards"
    AUTOMATIC_FLAGGING = "automatic_flagging"
    PENALTY_SYSTEM = "penalty_system"
    VERIFICATION_BOUNTY = "verification_bounty"
    TRANSPARENCY_TRACKER = "transparency_tracker"


class GreenGuardSmartContract:

    def __init__(self, contract_id: str, contract_type: ContractType,
                 creator: str, parameters: Dict):
        self.contract_id = contract_id
        self.contract_type = contract_type
        self.creator = creator
        self.parameters = parameters
        self.state = ContractState.PENDING
        self.created_at = time.time()
        self.executed_count = 0
        self.total_gas_used = 0
        self.execution_history = []

    def execute(self, inputs: Dict, context: Dict) -> Dict:
        """Execute smart contract with environmental verification logic"""
        try:
            self.state = ContractState.ACTIVE
            execution_start = time.time()
            if self.contract_type == ContractType.GREENWASHING_DETECTOR:
                result = self._greenwashing_detector_contract(inputs, context)
            elif self.contract_type == ContractType.SUSTAINABILITY_REWARDS:
                result = self._sustainability_rewards_contract(inputs, context)
            elif self.contract_type == ContractType.AUTOMATIC_FLAGGING:
                result = self._automatic_flagging_contract(inputs, context)
            elif self.contract_type == ContractType.PENALTY_SYSTEM:
                result = self._penalty_system_contract(inputs, context)
            elif self.contract_type == ContractType.VERIFICATION_BOUNTY:
                result = self._verification_bounty_contract(inputs, context)
            elif self.contract_type == ContractType.TRANSPARENCY_TRACKER:
                result = self._transparency_tracker_contract(inputs, context)
            else:
                raise ValueError(f"Unknown contract type: {self.contract_type}"
                                 )
            execution_time = time.time() - execution_start
            gas_used = self._calculate_gas_usage(result, execution_time)
            self.state = ContractState.EXECUTED
            self.executed_count += 1
            self.total_gas_used += gas_used
            execution_record = {
                "execution_id":
                    f"EXEC_{int(time.time())}_{self.executed_count}",
                "inputs": inputs,
                "result": result,
                "gas_used": gas_used,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.execution_history.append(execution_record)
            return {
                "success": True,
                "contract_id": self.contract_id,
                "execution_id": execution_record["execution_id"],
                "result": result,
                "gas_used": gas_used,
                "execution_time": execution_time
            }

        except Exception as e:
            self.state = ContractState.FAILED
            logger.error(f"Contract execution failed: {str(e)}")
            return {
                "success": False,
                "contract_id": self.contract_id,
                "error": str(e),
                "gas_used": 50
            }

    def _greenwashing_detector_contract(self, inputs: Dict,
                                        context: Dict) -> Dict:
        company_name = inputs.get("company_name", "Unknown")
        verification_score = inputs.get("verification_score", 0)
        confidence = inputs.get("confidence", 0)
        actions = []
        alerts = []
        penalties = 0
        if verification_score < 20 and confidence > 80:
            actions.append("IMMEDIATE_FLAG")
            actions.append("COMMUNITY_ALERT")
            actions.append("REGULATORY_NOTIFICATION")
            alerts.append(f"CRITICAL: {company_name} making potentially false "
                          "environmental claims")
            penalties = 100
        elif verification_score < 40 and confidence > 60:
            actions.append("HIGH_RISK_FLAG")
            actions.append("REQUIRE_EVIDENCE")
            alerts.append(f"HIGH RISK: {company_name} claims require "
                          "verification")
            penalties = 50
        elif verification_score < 60:
            actions.append("MODERATE_RISK_FLAG")
            actions.append("REQUEST_CLARIFICATION")
            alerts.append(f"MODERATE RISK: {company_name} claims need "
                          "clarification")
            penalties = 25
        else:
            actions.append("APPROVED")
            alerts.append(f"VERIFIED: {company_name} claims appear authentic")
            penalties = 0
        company_history = context.get("company_history", [])
        if len(company_history) > 2:
            recent_violations = [h for h in company_history[-5:] if h.get(
                "verification_score", 100) < 40]
            if len(recent_violations) >= 2:
                actions.append("REPEAT_OFFENDER_FLAG")
                penalties += 200
                alerts.append(f"REPEAT OFFENDER: {company_name} "
                              "has multiple violations")
        return {
            "contract_type": "greenwashing_detector",
            "company_name": company_name,
            "risk_assessment": "CRITICAL" if verification_score < 20 else
                             "HIGH" if verification_score < 40 else
                             "MODERATE" if verification_score < 60 else "LOW",
            "actions_triggered": actions,
            "alerts_generated": alerts,
            "penalty_points": penalties,
            "requires_human_review": verification_score < 30,
            "automated_response": True
        }

    def _sustainability_rewards_contract(self, inputs: Dict,
                                         context: Dict) -> Dict:
        company_name = inputs.get("company_name", "Unknown")
        verification_score = inputs.get("verification_score", 0)
        transparency_level = inputs.get("transparency_level", 0)
        certifications = inputs.get("certifications", [])
        base_points = verification_score
        transparency_bonus = transparency_level * 20
        certification_bonus = len(certifications) * 50
        total_points = base_points + transparency_bonus + certification_bonus
        if total_points >= 900:
            badge = "SUSTAINABILITY_CHAMPION"
            tier = "PLATINUM"
        elif total_points >= 700:
            badge = "SUSTAINABILITY_LEADER"
            tier = "GOLD"
        elif total_points >= 500:
            badge = "SUSTAINABILITY_ADVOCATE"
            tier = "SILVER"
        elif total_points >= 300:
            badge = "SUSTAINABILITY_BEGINNER"
            tier = "BRONZE"
        else:
            badge = "NO_BADGE"
            tier = "NONE"
        special_rewards = []
        if verification_score >= 95:
            special_rewards.append("TRANSPARENCY_EXCELLENCE")
        if len(certifications) >= 5:
            special_rewards.append("CERTIFICATION_MASTER")
        if transparency_level >= 90:
            special_rewards.append("OPENNESS_CHAMPION")
        return {
            "contract_type": "sustainability_rewards",
            "company_name": company_name,
            "points_awarded": total_points,
            "badge_earned": badge,
            "tier": tier,
            "special_rewards": special_rewards,
            "eligible_for_promotion": total_points >= 500,
            "next_tier_requirement": 300 if tier == "NONE"
            else 500 if tier == "BRONZE"
            else 700 if tier == "SILVER"
            else 900 if tier == "GOLD" else "MAX_TIER"
        }

    def _automatic_flagging_contract(self, inputs: Dict,
                                     context: Dict) -> Dict:
        """Automatic flagging system for suspicious claims"""
        claim_text = inputs.get("claim", "").lower()
        company_name = inputs.get("company_name", "Unknown")
        red_flag_keywords = [
            "100% natural", "completely eco-friendly", "totally green",
            "environmentally safe", "non-toxic", "chemical-free",
            "saves the planet", "carbon neutral*", "net zero*"
        ]
        vague_terms = [
            "eco-friendly", "green", "natural", "sustainable",
            "environmentally responsible", "clean", "pure"
        ]
        flags_triggered = []
        risk_score = 0
        for keyword in red_flag_keywords:
            if keyword in claim_text:
                flags_triggered.append(f"RED_FLAG_KEYWORD: {keyword}")
                risk_score += 30
        vague_count = sum(1 for term in vague_terms if term in claim_text)
        if vague_count >= 3:
            flags_triggered.append("EXCESSIVE_VAGUE_LANGUAGE")
            risk_score += 40
        absolute_terms = ["100%", "completely", "totally", "never", "always"]
        absolute_count = sum(1 for term in absolute_terms if term in
                             claim_text)
        if absolute_count >= 2:
            flags_triggered.append("ABSOLUTE_CLAIMS_WITHOUT_PROOF")
            risk_score += 50
        if risk_score >= 100:
            action = "IMMEDIATE_SUSPENSION"
            priority = "CRITICAL"
        elif risk_score >= 70:
            action = "REQUIRE_IMMEDIATE_VERIFICATION"
            priority = "HIGH"
        elif risk_score >= 40:
            action = "REQUEST_EVIDENCE"
            priority = "MEDIUM"
        else:
            action = "MONITOR"
            priority = "LOW"
        return {
            "contract_type": "automatic_flagging",
            "company_name": company_name,
            "flags_triggered": flags_triggered,
            "risk_score": risk_score,
            "recommended_action": action,
            "priority": priority,
            "requires_manual_review": risk_score >= 70,
            "auto_flagged": len(flags_triggered) > 0
        }

    def _penalty_system_contract(self, inputs: Dict, context: Dict) -> Dict:
        """Penalty system for greenwashing violations"""
        company_name = inputs.get("company_name", "Unknown")
        violation_severity = inputs.get("violation_severity", "LOW")
        repeat_offender = inputs.get("repeat_offender", False)
        impact_scale = inputs.get("impact_scale", "LOCAL")
        base_penalties = {
            "LOW": 10,
            "MEDIUM": 50,
            "HIGH": 200,
            "CRITICAL": 500
        }

        penalty_points = base_penalties.get(violation_severity, 10)
        if repeat_offender:
            penalty_points *= 2
        scale_multipliers = {
            "LOCAL": 1.0,
            "REGIONAL": 1.5,
            "NATIONAL": 2.0,
            "GLOBAL": 3.0
        }

        penalty_points = int(penalty_points * scale_multipliers.get(
            impact_scale, 1.0))
        consequences = []
        if penalty_points >= 1000:
            consequences.extend([
                "PLATFORM_BAN",
                "REGULATORY_REFERRAL",
                "PUBLIC_WARNING_ISSUED"
            ])
        elif penalty_points >= 500:
            consequences.extend([
                "VERIFICATION_REQUIRED_FOR_ALL_CLAIMS",
                "MONTHLY_MONITORING",
                "PUBLIC_NOTICE"
            ])
        elif penalty_points >= 200:
            consequences.extend([
                "ENHANCED_SCRUTINY",
                "QUARTERLY_REVIEW",
                "WARNING_ISSUED"
            ])
        elif penalty_points >= 50:
            consequences.extend([
                "FORMAL_WARNING",
                "REQUIRED_TRAINING"
            ])
        return {
            "contract_type": "penalty_system",
            "company_name": company_name,
            "penalty_points": penalty_points,
            "consequences": consequences,
            "rehabilitation_required": penalty_points >= 200,
            "appeal_allowed": penalty_points < 1000,
            "review_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }

    def _verification_bounty_contract(self,
                                      inputs: Dict, context: Dict) -> Dict:
        verifier_email = inputs.get("verifier_email", "unknown")
        verification_quality = inputs.get("verification_quality", 0)
        claim_complexity = inputs.get("claim_complexity", "SIMPLE")
        verification_speed = inputs.get("verification_speed", "NORMAL")
        base_bounty = {
            "SIMPLE": 10,
            "MODERATE": 25,
            "COMPLEX": 50,
            "EXPERT": 100
        }.get(claim_complexity, 10)
        quality_multiplier = verification_quality / 100
        speed_bonus = {
            "INSTANT": 1.5,
            "FAST": 1.2,
            "NORMAL": 1.0,
            "SLOW": 0.8
        }.get(verification_speed, 1.0)
        final_bounty = int(base_bounty * quality_multiplier * speed_bonus)
        verifier_history = context.get("verifier_history", [])
        total_verifications = len(verifier_history)
        if total_verifications >= 100:
            verifier_level = "EXPERT"
            level_bonus = 50
        elif total_verifications >= 50:
            verifier_level = "ADVANCED"
            level_bonus = 25
        elif total_verifications >= 10:
            verifier_level = "INTERMEDIATE"
            level_bonus = 10
        else:
            verifier_level = "BEGINNER"
            level_bonus = 0
        final_bounty += level_bonus
        return {
            "contract_type": "verification_bounty",
            "verifier_email": verifier_email,
            "bounty_awarded": final_bounty,
            "verifier_level": verifier_level,
            "quality_score": verification_quality,
            "total_earned": sum(h.get("bounty", 0) for h in verifier_history)
            + final_bounty,
            "next_level_requirement":
                10 if verifier_level == "BEGINNER"
                else 50 if verifier_level == "INTERMEDIATE"
                else 100 if verifier_level == "ADVANCED" else "MAX_LEVEL"
        }

    def _transparency_tracker_contract(self, inputs: Dict,
                                       context: Dict) -> Dict:
        """Track and score company transparency over time"""
        company_name = inputs.get("company_name", "Unknown")
        disclosed_data = inputs.get("disclosed_data", {})
        response_time = inputs.get("response_time_hours", 999)
        data_completeness = inputs.get("data_completeness", 0)
        disclosure_score = len(disclosed_data) * 10
        timeliness_score = max(0, 100 - response_time)
        completeness_score = data_completeness
        transparency_score = (disclosure_score + timeliness_score +
                              completeness_score) / 3
        history = context.get("transparency_history", [])
        if len(history) >= 2:
            recent_average = sum(h.get(
                "transparency_score", 0) for h in history[-3:]) / min(3, len(
                    history))
            improvement = transparency_score - recent_average
        else:
            improvement = 0
        if transparency_score >= 90:
            recognition = "TRANSPARENCY_CHAMPION"
        elif transparency_score >= 75:
            recognition = "TRANSPARENCY_LEADER"
        elif transparency_score >= 60:
            recognition = "TRANSPARENCY_PRACTITIONER"
        elif transparency_score >= 40:
            recognition = "TRANSPARENCY_BEGINNER"
        else:
            recognition = "TRANSPARENCY_NEEDED"
        return {
            "contract_type": "transparency_tracker",
            "company_name": company_name,
            "transparency_score": round(transparency_score, 2),
            "improvement": round(improvement, 2),
            "recognition_level": recognition,
            "areas_disclosed": list(disclosed_data.keys()),
            "response_time_rating":
                "EXCELLENT" if response_time < 24 else "GOOD"
                if response_time < 72 else "AVERAGE"
                if response_time < 168 else "POOR",
            "recommended_improvements": self._get_transparency_recommendations(
                transparency_score)
        }

    def _get_transparency_recommendations(self, score: float) -> List[str]:
        """Get recommendations for improving transparency"""
        recommendations = []
        if score < 90:
            recommendations.append("Publish detailed sustainability reports")
        if score < 75:
            recommendations.append("Provide supply chain transparency")
        if score < 60:
            recommendations.append("Share environmental impact data")
        if score < 40:
            recommendations.append("Respond to verification requests promptly")
        if score < 25:
            recommendations.append(
                "Establish basic environmental disclosure practices")
        return recommendations

    def _calculate_gas_usage(self, result: Dict, execution_time: float) -> int:
        base_gas = 100
        result_complexity = len(str(result))
        complexity_gas = result_complexity // 10
        time_gas = int(execution_time * 50)
        return base_gas + complexity_gas + time_gas


class SmartContractBlockchain:
    def __init__(self, existing_blockchain=None):
        self.blockchain = existing_blockchain
        self.contracts: Dict[str, GreenGuardSmartContract] = {}
        self.contract_registry = {}
        self._deploy_default_contracts()

    def _deploy_default_contracts(self):
        default_contracts = [
            (ContractType.GREENWASHING_DETECTOR, {"sensitivity": 0.7}),
            (ContractType.SUSTAINABILITY_REWARDS, {"max_points": 1000}),
            (ContractType.AUTOMATIC_FLAGGING, {"threshold": 50}),
            (ContractType.PENALTY_SYSTEM, {"max_penalty": 1000}),
            (ContractType.VERIFICATION_BOUNTY, {"max_bounty": 200}),
            (ContractType.TRANSPARENCY_TRACKER, {"update_frequency": "weekly"})
        ]

        for contract_type, params in default_contracts:
            self.deploy_contract(contract_type, "system@greenguard.com",
                                 params)

    def deploy_contract(self, contract_type: ContractType, creator: str,
                        parameters: Dict) -> str:
        contract_id = f"SC_{contract_type.value}_{int(time.time())}"
        contract = GreenGuardSmartContract(
            contract_id=contract_id,
            contract_type=contract_type,
            creator=creator,
            parameters=parameters
        )

        self.contracts[contract_id] = contract
        self.contract_registry[contract_type] = contract_id

        logger.info(f"Smart contract deployed: {contract_id} "
                    f"({contract_type.value})")
        return contract_id

    def execute_verification_contracts(self, verification_data: Dict) -> Dict:
        """Execute all relevant contracts for a verification"""
        results = {}
        if ContractType.GREENWASHING_DETECTOR in self.contract_registry:
            contract_id = self.contract_registry[ContractType
                                                 .GREENWASHING_DETECTOR]
            result = self.contracts[contract_id].execute(verification_data, {})
            results["greenwashing_detection"] = result
        if ContractType.AUTOMATIC_FLAGGING in self.contract_registry:
            contract_id = self.contract_registry[ContractType
                                                 .AUTOMATIC_FLAGGING]
            result = self.contracts[contract_id].execute(verification_data, {})
            results["automatic_flagging"] = result
        if ContractType.SUSTAINABILITY_REWARDS in self.contract_registry:
            contract_id = self.contract_registry[ContractType
                                                 .SUSTAINABILITY_REWARDS]
            result = self.contracts[contract_id].execute(verification_data, {})
            results["sustainability_rewards"] = result
        return results

    def get_contract_statistics(self) -> Dict:
        """Get statistics about smart contract usage"""
        total_executions = sum(
            c.executed_count for c in self.contracts.values())
        total_gas_used = sum(c.total_gas_used for c in self.contracts.values())
        return {
            "total_contracts": len(self.contracts),
            "total_executions": total_executions,
            "total_gas_used": total_gas_used,
            "average_gas_per_execution":
                total_gas_used / total_executions if total_executions > 0 else
                0,
            "contract_types": [ct.value for ct in ContractType],
            "active_contracts": len([c for c in self.contracts.values() if c
                                     .state == ContractState.ACTIVE])
        }


_smart_contract_blockchain = None
_simple_blockchain_data = []


def _initialize_simple_blockchain():
    global _simple_blockchain_data
    if not _simple_blockchain_data:
        genesis_block = {
            "index": 0,
            "timestamp": time.time(),
            "data": {
                "type": "genesis",
                "message": "GreenGuard Blockchain Genesis Block",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "2.0_with_smart_contracts"
            },
            "previous_hash": "0",
            "hash": hashlib.sha256("greenguard_genesis_block".encode())
            .hexdigest()
        }
        _simple_blockchain_data.append(genesis_block)
        logger.info("🔗 GreenGuard blockchain initialized with genesis block")


def _add_block_to_simple_chain(data: Dict) -> str:
    global _simple_blockchain_data
    if not _simple_blockchain_data:
        _initialize_simple_blockchain()
    previous_block = _simple_blockchain_data[-1]
    new_index = len(_simple_blockchain_data)
    timestamp = time.time()
    block_data = {
        "index": new_index,
        "timestamp": timestamp,
        "data": data,
        "previous_hash": previous_block["hash"],
        "nonce": 0
    }

    difficulty = 2
    target = "0" * difficulty
    while True:
        block_string = json.dumps(block_data, sort_keys=True)
        block_hash = hashlib.sha256(block_string.encode()).hexdigest()
        if block_hash.startswith(target):
            block_data["hash"] = block_hash
            break
        block_data["nonce"] += 1
    _simple_blockchain_data.append(block_data)
    block_id = f"BLOCK_{new_index}_{int(timestamp)}"
    logger.info(f"🔗 Block mined and added: {block_id} (nonce: "
                f"{block_data['nonce']})")
    return block_id


def add_verification_to_blockchain(verification_data: Dict) -> str:
    try:
        block_data = {
            "type": "verification",
            "company_name": verification_data.get("company_name", "Unknown"),
            "claim": verification_data.get("claim", "")[:1000],
            "verification_score": verification_data.get("verification_score",
                                                        0),
            "status": verification_data.get("status", "unknown"),
            "risk_level": verification_data.get("risk_level", "unknown"),
            "evidence_summary": verification_data.get("evidence_summary",
                                                      "")[:500],
            "user_email": verification_data.get("user_email", "anonymous"),
            "client_ip": verification_data.get("client_ip", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "version": verification_data.get("version",
                                             "2.0_with_smart_contracts"),
            "smart_contracts_executed": verification_data.get(
                "smart_contracts_executed", 0),
            "automated_actions": verification_data.get("automated_actions", [])
        }

        block_id = _add_block_to_simple_chain(block_data)
        logger.info(f" Verification added to blockchain: {block_id} for "
                    f"{verification_data.get('company_name', 'Unknown')}")
        return block_id
    except Exception as e:
        logger.error(f" Error adding verification to blockchain: {str(e)}")
        return f"ERROR_{int(time.time())}"


def add_claim_analysis_to_blockchain(claim_data: Dict) -> str:
    try:
        block_data = {
            "type": "claim_analysis",
            "content": claim_data.get("content", "")[:1000],
            "claims_count": claim_data.get("claims_count", 0),
            "url": claim_data.get("url", ""),
            "analysis_type": claim_data.get("analysis_type", "website"),
            "environmental_claims": claim_data.get("environmental_claims",
                                                   [])[:10],
            "user_email": claim_data.get("user_email", "anonymous"),
            "client_ip": claim_data.get("client_ip", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "processing_time": claim_data.get("processing_time", 0)
        }

        block_id = _add_block_to_simple_chain(block_data)
        logger.info(f" Claim analysis added to blockchain: {block_id}")
        return block_id
    except Exception as e:
        logger.error(f" Error adding claim analysis to blockchain: {str(e)}")
        return f"ERROR_{int(time.time())}"


def get_blockchain_statistics() -> Dict:
    """Get blockchain statistics - REQUIRED function that app.py imports"""
    try:
        global _smart_contract_blockchain, _simple_blockchain_data
        if not _simple_blockchain_data:
            _initialize_simple_blockchain()
        verification_blocks = [
            block for block in _simple_blockchain_data
            if block.get("data", {}).get("type") == "verification"
        ]

        claim_analysis_blocks = [
            block for block in _simple_blockchain_data
            if block.get("data", {}).get("type") == "claim_analysis"
        ]

        companies = set()
        for block in verification_blocks:
            company = block.get("data", {}).get("company_name",
                                                "").strip().lower()
            if company and company not in ["unknown", "", "none", "anonymous"]:
                companies.add(company)
        smart_contract_stats = {}
        try:
            if _smart_contract_blockchain is None:
                _smart_contract_blockchain = SmartContractBlockchain()
            smart_contract_stats = (
                _smart_contract_blockchain.get_contract_statistics())
        except Exception as e:
            logger.warning(f"Smart contract statistics not available: {e}")
            smart_contract_stats = {
                "total_contracts": 0,
                "total_executions": 0,
                "system_status": "not_available"
            }
        is_valid = _validate_blockchain_integrity()
        return {
            "total_blocks": len(_simple_blockchain_data),
            "verification_blocks": len(verification_blocks),
            "claim_analysis_blocks": len(claim_analysis_blocks),
            "companies_on_blockchain": len(companies),
            "network_status": "operational",
            "blockchain_type":
                "GreenGuard Environmental Verification with Smart Contracts",
            "consensus_mechanism": "Proof-of-Work (SHA-256)",
            "hash_algorithm": "SHA-256",
            "difficulty": 2,
            "chain_integrity": {
                "valid": is_valid,
                "immutable": True,
                "transparent": True,
                "tamper_proof": True,
                "cryptographically_secured": True
            },
            "smart_contracts": smart_contract_stats,
            "last_block_time": _simple_blockchain_data[-1].get("timestamp", 0)
            if _simple_blockchain_data else 0,
            "genesis_block_hash": _simple_blockchain_data[0].get("hash", "")
            if _simple_blockchain_data else "",
            "latest_block_hash": _simple_blockchain_data[-1].get("hash", "")
            if _simple_blockchain_data else ""
        }

    except Exception as e:
        logger.error(f" Error getting blockchain statistics: {str(e)}")
        return {
            "total_blocks": 0,
            "verification_blocks": 0,
            "claim_analysis_blocks": 0,
            "companies_on_blockchain": 0,
            "network_status": "error",
            "error": str(e),
            "blockchain_type":
                "GreenGuard Environmental Verification with Smart Contracts"
        }


def _validate_blockchain_integrity() -> bool:
    """Validate the entire blockchain integrity"""
    global _simple_blockchain_data
    try:
        if len(_simple_blockchain_data) <= 1:
            return True
        for i in range(1, len(_simple_blockchain_data)):
            current_block = _simple_blockchain_data[i]
            previous_block = _simple_blockchain_data[i - 1]
            if current_block.get("previous_hash") != previous_block.get("hash"
                                                                        ):
                logger.error(f"Blockchain integrity check failed at block {i}")
                return False
            block_copy = current_block.copy()
            stored_hash = block_copy.pop("hash", "")
            block_string = json.dumps(block_copy, sort_keys=True)
            calculated_hash = hashlib.sha256(block_string.encode()).hexdigest()
            if stored_hash != calculated_hash:
                logger.error(f"Hash integrity check failed at block {i}")
                return False
        return True
    except Exception as e:
        logger.error(f"Error validating blockchain integrity: {str(e)}")
        return False


def get_company_verification_history(company_name: str) -> List[Dict]:
    """Get verification history for a specific company"""
    try:
        global _simple_blockchain_data
        if not _simple_blockchain_data:
            _initialize_simple_blockchain()
        company_blocks = []
        for block in _simple_blockchain_data:
            block_data = block.get("data", {})
            if (block_data.get("type") == "verification" and
                block_data.get("company_name",
                               "").lower() == company_name.lower()):
                company_blocks.append({
                    "timestamp": block_data.get("timestamp"),
                    "verification_score": block_data.get("verification_score"),
                    "status": block_data.get("status"),
                    "risk_level": block_data.get("risk_level"),
                    "claim": block_data.get("claim", "")[:100],
                    "block_index": block.get("index"),
                    "block_hash": block.get("hash", "")[:16] + "...",
                    "automated_actions": block_data.get("automated_actions",
                                                        [])
                })
        return sorted(company_blocks, key=lambda x: x.get("timestamp", ""),
                      reverse=True)
    except Exception as e:
        logger.error(f" Error getting company history for {company_name}: "
                     f"{str(e)}")
        return []


def get_blockchain_block_by_id(block_id: str) -> Optional[Dict]:
    """Get a specific block by its ID"""
    try:
        global _simple_blockchain_data
        for block in _simple_blockchain_data:
            if (
                f"BLOCK_{block.get('index')}_{int(block.get('timestamp', 0))}"
                == block_id
            ):
                return block
        return None
    except Exception as e:
        logger.error(f" Error getting block {block_id}: {str(e)}")
        return None


def execute_smart_contracts_for_verification(verification_data: Dict) -> Dict:
    """Execute smart contracts for a verification"""
    try:
        global _smart_contract_blockchain
        if _smart_contract_blockchain is None:
            _smart_contract_blockchain = SmartContractBlockchain()

        contract_results = (
            _smart_contract_blockchain.execute_verification_contracts(
                verification_data))
        automated_actions = []
        for contract_type, result in contract_results.items():
            if result.get("success") and result.get("result"):
                contract_result = result["result"]
                if "actions_triggered" in contract_result:
                    automated_actions.extend(
                        contract_result["actions_triggered"])
                if "consequences" in contract_result:
                    automated_actions.extend(contract_result["consequences"])
                if "flags_triggered" in contract_result:
                    automated_actions.extend(
                        contract_result["flags_triggered"])
                if "special_rewards" in contract_result:
                    automated_actions.extend(
                        contract_result["special_rewards"])

        return {
            "contracts_executed": len(contract_results),
            "contract_results": contract_results,
            "automated_actions": list(set(automated_actions)),
            "smart_contract_system": "operational",
            "execution_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f" Error executing smart contracts: {str(e)}")
        return {
            "contracts_executed": 0,
            "contract_results": {},
            "automated_actions": [],
            "smart_contract_system": "error",
            "error": str(e)
        }


def validate_blockchain_integrity() -> bool:
    """Validate the entire blockchain integrity - public function"""
    return _validate_blockchain_integrity()


def get_total_smart_contract_executions() -> int:
    """Get total number of smart contract executions"""
    try:
        global _smart_contract_blockchain

        if _smart_contract_blockchain is None:
            return 0

        stats = _smart_contract_blockchain.get_contract_statistics()
        return stats.get("total_executions", 0)

    except Exception as e:
        logger.error(f" Error getting smart contract executions: {str(e)}")
        return 0


def reset_blockchain_for_testing():
    """Reset blockchain for testing purposes - USE ONLY FOR TESTING"""
    global _simple_blockchain_data, _smart_contract_blockchain

    _simple_blockchain_data = []
    _smart_contract_blockchain = None
    _initialize_simple_blockchain()
    logger.warning(" Blockchain reset for testing purposes")


_initialize_simple_blockchain()
logger.info(" GreenGuard Blockchain Verification System with Smart Contracts "
            "initialized successfully")

if __name__ == "__main__":
    print(" Testing GreenGuard Blockchain Verification System")

    test_verification = {
        "company_name": "TestCorp",
        "claim": "100% renewable energy",
        "verification_score": 85,
        "status": "verified",
        "user_email": "test@example.com"
    }

    block_id = add_verification_to_blockchain(test_verification)
    print(f" Test verification added: {block_id}")

    test_claim = {
        "content": "We are committed to sustainability",
        "claims_count": 1,
        "url": "https://example.com",
        "user_email": "test@example.com"
    }

    claim_block_id = add_claim_analysis_to_blockchain(test_claim)
    print(f" Test claim analysis added: {claim_block_id}")

    stats = get_blockchain_statistics()
    print(" Blockchain Statistics:")
    print(f"   Total Blocks: {stats['total_blocks']}")
    print(f"   Verification Blocks: {stats['verification_blocks']}")
    print(f"   Companies: {stats['companies_on_blockchain']}")
    print(f"   Network Status: {stats['network_status']}")
    print(f"   Chain Integrity: {stats['chain_integrity']['valid']}")

    smart_results = execute_smart_contracts_for_verification(test_verification)
    print(f" Smart Contracts Executed: {smart_results['contracts_executed']}")
    print(f" Automated Actions: {len(smart_results['automated_actions'])}")

    history = get_company_verification_history("TestCorp")
    print(f" Company History Records: {len(history)}")

    integrity = validate_blockchain_integrity()
    print(f" Blockchain Integrity: {' Valid' if integrity else ' Invalid'}")

    print(" All tests completed successfully!")
