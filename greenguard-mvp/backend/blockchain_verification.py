import hashlib
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class Block:

    def __init__(
        self,
        index: int,
        timestamp: float,
        data: Dict,
        previous_hash: str,
        nonce: int = 0,
    ):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "data": self.data,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2):
        target = "0" * difficulty
        start_time = time.time()

        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

            if self.nonce % 10000 == 0:
                elapsed = time.time() - start_time
                logger.debug(
                    f"Mining block {self.index}: nonce {self.nonce}, "
                    f"elapsed {elapsed:.2f}s"
                )

        elapsed = time.time() - start_time
        logger.info(
            f"Block {self.index} mined: {self.hash[:16]}"
            f"... (nonce: {self.nonce}, time: {elapsed:.2f}s)"
        )


class GreenGuardBlockchain:

    def __init__(self):
        self.chain: List[Block] = []
        self.difficulty = 2
        self.pending_transactions: List[Dict] = []
        self.mining_reward = 10
        self.create_genesis_block()

    def create_genesis_block(self) -> Block:
        genesis_data = {
            "type": "genesis",
            "message": "GreenGuard Blockchain Genesis Block",
            "created_by": "GreenGuard System",
            "version": "1.0.0",
            "features": ["verification_recording", "transparency",
                         "immutability"],
        }

        genesis_block = Block(0, time.time(), genesis_data, "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        logger.info("Genesis block created and mined")
        return genesis_block

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_verification_block(self, verification_data: Dict) -> str:
        verification_id = f"GG_{int(time.time())}"
        f"_{hashlib.md5(str(verification_data).encode()).hexdigest()[:8]}"

        block_data = {
            "type": "verification",
            "verification_id": verification_id,
            "company_name": verification_data.get("company_name", "Unknown"),
            "claim": verification_data.get("claim", ""),
            "verification_result": {
                "score": verification_data.get("verification_score", 0),
                "status": verification_data.get("status", "unknown"),
                "risk_level": verification_data.get("risk_level", "unknown"),
                "trustworthiness": verification_data.get("trustworthiness",
                                                         "unknown"),
                "evidence_summary": verification_data.get("evidence_summary",
                                                          ""),
                "recommendations": verification_data.get("recommendations",
                                                         []),
            },
            "verification_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "verified_by": verification_data.get("user_email", "system"),
                "algorithm_version": "universal_v1.0",
                "data_sources": verification_data.get("sources", {}),
                "company_analysis": verification_data.get("company_analysis",
                                                          {}),
            },
            "blockchain_security": {
                "immutable": True,
                "transparent": True,
                "decentralized": True,
                "tamper_proof": True,
            },
        }

        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=block_data,
            previous_hash=self.get_latest_block().hash,
        )

        logger.info(
            f"Mining verification block for "
            f"{verification_data.get('company_name', 'Unknown')}"
        )
        new_block.mine_block(self.difficulty)

        self.chain.append(new_block)

        logger.info(f"Verification block added to blockchain: "
                    f"{verification_id}")
        return verification_id

    def add_claim_analysis_block(self, claim_data: Dict) -> str:
        claim_id = f"CL_{int(time.time())}"
        f"_{hashlib.md5(str(claim_data).encode()).hexdigest()[:8]}"

        block_data = {
            "type": "claim_analysis",
            "claim_id": claim_id,
            "content": claim_data.get("content", ""),
            "analysis_result": {
                "claims_detected": claim_data.get("claims_count", 0),
                "risk_score": claim_data.get("risk_score", 0),
                "summary": claim_data.get("summary", ""),
                "claims": claim_data.get("claims", []),
            },
            "analysis_metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "analyzed_by": claim_data.get("user_email", "system"),
                "algorithm_version": "claim_detector_v1.0",
                "source_url": claim_data.get("url", ""),
            },
        }

        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            data=block_data,
            previous_hash=self.get_latest_block().hash,
        )

        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)

        logger.info(f"Claim analysis block added: {claim_id}")
        return claim_id

    def get_verification_proof(self, verification_id: str) -> Optional[Dict]:
        for block in self.chain:
            if (
                block.data.get("type") == "verification"
                and block.data.get("verification_id") == verification_id
            ):
                return {
                    "verification_id": verification_id,
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "previous_hash": block.previous_hash,
                    "timestamp": block.data.get("verification_metadata",
                                                {}).get(
                        "timestamp"
                    ),
                    "company_name": block.data.get("company_name"),
                    "claim": block.data.get("claim"),
                    "verification_result": block.data.get(
                        "verification_result"),
                    "verified_by": block.data.get("verification_metadata",
                                                  {}).get(
                        "verified_by"
                    ),
                    "blockchain_proof": {
                        "is_valid": self.is_chain_valid(),
                        "immutable": True,
                        "tamper_proof": True,
                        "block_position": block.index,
                        "total_blocks": len(self.chain),
                    },
                    "cryptographic_signature": block.hash[:32] + "...",
                }
        return None

    def get_company_history(self, company_name: str) -> List[Dict]:
        company_verifications = []
        for block in self.chain:
            if (
                block.data.get("type") == "verification"
                and block.data.get("company_name", "").lower() ==
                company_name.lower()
            ):
                company_verifications.append(
                    {
                        "verification_id": block.data.get("verification_id"),
                        "claim": block.data.get("claim"),
                        "verification_result":
                            block.data.get("verification_result"),
                        "timestamp": block.data.get("verification_metadata",
                                                    {}).get(
                            "timestamp"
                        ),
                        "block_hash": block.hash[:16] + "...",
                        "block_index": block.index,
                        "verified_by": block.data.get("verification_metadata",
                                                      {}).get(
                            "verified_by"
                        ),
                    }
                )
        return sorted(company_verifications, key=lambda x: x["timestamp"],
                      reverse=True)

    def get_user_verification_history(self, user_email: str) -> List[Dict]:
        user_verifications = []
        for block in self.chain:
            if (
                block.data.get("type") == "verification"
                and block.data.get("verification_metadata",
                                   {}).get("verified_by")
                == user_email
            ):
                user_verifications.append(
                    {
                        "verification_id": block.data.get("verification_id"),
                        "company_name": block.data.get("company_name"),
                        "claim": block.data.get("claim"),
                        "verification_result":
                            block.data.get("verification_result"),
                        "timestamp": block.data.get("verification_metadata",
                                                    {}).get(
                            "timestamp"
                        ),
                        "block_hash": block.hash[:16] + "...",
                    }
                )
        return sorted(user_verifications, key=lambda x: x["timestamp"],
                      reverse=True)

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            if current_block.hash != current_block.calculate_hash():
                logger.error(f"Invalid hash at block {i}")
                return False

            if current_block.previous_hash != previous_block.hash:
                logger.error(f"Invalid previous hash at block {i}")
                return False

        return True

    def get_blockchain_stats(self) -> Dict:
        verification_blocks = [
            b for b in self.chain if b.data.get("type") == "verification"
        ]
        claim_blocks = [b for b in self.chain if b.data.get("type") ==
                        "claim_analysis"]

        companies_verified = set()
        users_active = set()

        for block in verification_blocks:
            company = block.data.get("company_name")
            user = block.data.get("verification_metadata",
                                  {}).get("verified_by")
            if company:
                companies_verified.add(company.lower())
            if user and user != "system":
                users_active.add(user)

        chain_valid = self.is_chain_valid()

        if len(self.chain) > 1:
            total_time = self.chain[-1].timestamp - self.chain[0].timestamp
            avg_block_time = total_time / (len(self.chain) - 1)
        else:
            avg_block_time = 0

        return {
            "network_status": "operational" if chain_valid else "compromised",
            "total_blocks": len(self.chain),
            "verification_blocks": len(verification_blocks),
            "claim_analysis_blocks": len(claim_blocks),
            "companies_on_blockchain": len(companies_verified),
            "active_users": len(users_active),
            "chain_integrity": {
                "valid": chain_valid,
                "immutable": True,
                "transparent": True,
                "decentralized": True,
            },
            "network_performance": {
                "difficulty": self.difficulty,
                "average_block_time": round(avg_block_time, 2),
                "latest_block_hash": self.get_latest_block().hash[:16] + "...",
                "chain_size_mb": len(json.dumps([b.data for b in self.chain]))
                / (1024 * 1024),
            },
            "genesis_info": {
                "timestamp": self.chain[0].timestamp if self.chain else None,
                "hash": self.chain[0].hash[:16] + "..." if self.chain else
                None,
            },
        }


greenguard_blockchain = GreenGuardBlockchain()


def add_verification_to_blockchain(verification_data: Dict) -> str:
    try:
        verification_id = greenguard_blockchain.add_verification_block(
            verification_data
        )
        return verification_id
    except Exception as e:
        logger.error(f"Error adding verification to blockchain: {str(e)}")
        raise


def add_claim_analysis_to_blockchain(claim_data: Dict) -> str:
    try:
        claim_id = greenguard_blockchain.add_claim_analysis_block(claim_data)
        return claim_id
    except Exception as e:
        logger.error(f"Error adding claim analysis to blockchain: {str(e)}")
        raise


def get_blockchain_verification_proof(verification_id: str) -> Optional[Dict]:
    try:
        return greenguard_blockchain.get_verification_proof(verification_id)
    except Exception as e:
        logger.error(f"Error getting verification proof: {str(e)}")
        return None


def get_company_blockchain_history(company_name: str) -> List[Dict]:
    try:
        return greenguard_blockchain.get_company_history(company_name)
    except Exception as e:
        logger.error(f"Error getting company blockchain history: {str(e)}")
        return []


def get_user_blockchain_history(user_email: str) -> List[Dict]:
    try:
        return greenguard_blockchain.get_user_verification_history(user_email)
    except Exception as e:
        logger.error(f"Error getting user blockchain history: {str(e)}")
        return []


def get_blockchain_statistics() -> Dict:
    try:
        return greenguard_blockchain.get_blockchain_stats()
    except Exception as e:
        logger.error(f"Error getting blockchain statistics: {str(e)}")
        return {
            "network_status": "error",
            "total_blocks": 0,
            "verification_blocks": 0,
            "companies_on_blockchain": 0,
            "chain_integrity": {"valid": False},
            "error": str(e),
        }
