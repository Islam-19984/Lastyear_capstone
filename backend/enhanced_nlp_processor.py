import spacy
import re
import logging
from transformers import pipeline
import torch
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedNLPProcessor:
    def __init__(self):
        self.initialization_status = {
            "spacy": False,
            "bert_classifier": False,
            "sentiment_analyzer": False,
            "initialization_time": datetime.utcnow().isoformat()
        }
        try:
            self.nlp = spacy.load("en_core_web_sm")
            self.initialization_status["spacy"] = True
            logger.info(
                " spaCy model loaded successfully for linguistic analysis")
        except Exception as e:
            logger.error(f" Failed to load spaCy model: {e}")
            self.nlp = None

        try:
            self.greenwashing_classifier = pipeline(
                "text-classification",
                model="distilbert-base-uncased",
                device=0 if torch.cuda.is_available() else -1
            )
            self.initialization_status["bert_classifier"] = True
            logger.info(" BERT-based classifier initialized "
                        "for advanced claim detection")
        except Exception as e:
            logger.error(f" Failed to initialize BERT classifier: {e}")
            self.greenwashing_classifier = None

        try:
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if torch.cuda.is_available() else -1
            )
            self.initialization_status["sentiment_analyzer"] = True
            logger.info(" Sentiment analyzer initialized "
                        "using HuggingFace transformers")
        except Exception as e:
            logger.error(f" Failed to initialize sentiment analyzer: {e}")
            self.sentiment_analyzer = None

        self.environmental_keywords = [
            "sustainable", "sustainability", "eco-friendly", "carbon neutral",
            "renewable", "biodegradable", "organic", "recycled", "recyclable",
            "zero waste", "climate positive", "climate neutral",
            "earth friendly",
            "environmentally responsible", "natural", "clean energy",
            "clean technology",
            "circular economy", "carbon footprint", "renewable energy",
            "solar power",
            "wind power", "environmental stewardship", "habitat conservation",
            "net zero", "carbon negative", "zero emission", "green energy"
        ]

        print(f" Enhanced NLP Processor initialized: "
              f"spaCy={self.initialization_status['spacy']}, "
              f"BERT={self.initialization_status['bert_classifier']}, "
              f"Sentiment={self.initialization_status['sentiment_analyzer']}")

    def get_nlp_status(self) -> Dict:
        return {
            "spacy_available": self.nlp is not None,
            "bert_available": self.greenwashing_classifier is not None,
            "sentiment_available": self.sentiment_analyzer is not None,
            "transformers_available": True,
            "initialization_status": self.initialization_status,
            "system_ready": True
        }

    def analyze_text_comprehensive(self, text: str) -> Dict:
        try:
            analysis_start_time = datetime.utcnow()
            spacy_analysis = self.preprocess_text_with_spacy(text)
            bert_claims = self.detect_environmental_claims_with_bert(text)
            avg_confidence = 0
            avg_greenwashing_risk = 0
            avg_specificity = 0
            if bert_claims:
                avg_confidence = sum(claim.get(
                    'confidence_score',
                    0) for claim in bert_claims) / len(bert_claims)
                avg_greenwashing_risk = sum(claim.get(
                    'greenwashing_risk',
                    0) for claim in bert_claims) / len(bert_claims)
                avg_specificity = sum(claim.get(
                    'specificity_score',
                    0) for claim in bert_claims) / len(bert_claims)
            comprehensive_analysis = {
                "original_text": text,
                "spacy_analysis": spacy_analysis,
                "bert_claims": bert_claims,
                "nlp_metrics": {
                    "total_claims_detected": len(bert_claims),
                    "average_confidence": round(avg_confidence, 3),
                    "average_greenwashing_risk": round(
                        avg_greenwashing_risk, 3),
                    "average_specificity": round(avg_specificity, 3),
                    "entities_found": len(spacy_analysis.get("entities", [])),
                    "sentences_analyzed": len(
                        spacy_analysis.get("sentences", []))
                },
                "processing_method":
                    "enhanced_nlp_with_bert_spacy_transformers",
                "nlp_capabilities": self.initialization_status,
                "analysis_timestamp": analysis_start_time.isoformat(),
                "processing_time_ms": (
                    datetime.utcnow() - analysis_start_time).total_seconds()
                * 1000
            }
            return comprehensive_analysis
        except Exception as e:
            logger.error(f" Comprehensive analysis error: {e}")
            return {
                "error": str(e),
                "processing_method": "fallback",
                "nlp_capabilities": self.initialization_status
            }

    def preprocess_text_with_spacy(self, text: str) -> Dict:
        if not self.nlp:
            return {
                "processed_text": text,
                "entities": [],
                "sentences": [text],
                "error": "spaCy not available"
            }

        try:
            doc = self.nlp(text)
            entities = []
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "description": spacy.explain(ent.label_)
                })

            sentences = [
                sent.text.strip() for sent in doc.sents if sent.text.strip()]

            return {
                "processed_text": text,
                "original_text": text,
                "entities": entities,
                "sentences": sentences,
                "token_count": len(doc),
                "spacy_analysis": True
            }
        except Exception as e:
            logger.error(f" spaCy preprocessing error: {e}")
            return {
                "processed_text": text,
                "entities": [],
                "sentences": [text],
                "error": str(e)
            }

    def detect_environmental_claims_with_bert(self, text: str) -> List[Dict]:
        if not self.greenwashing_classifier:
            return []

        try:
            spacy_results = self.preprocess_text_with_spacy(text)
            sentences = spacy_results.get("sentences", [text])
            environmental_claims = []
            for sentence in sentences:
                sentence_lower = sentence.lower()
                matching_keywords = [
                    keyword for keyword in self.environmental_keywords
                    if keyword.lower() in sentence_lower
                ]
                if matching_keywords:
                    try:
                        classification_results = self.greenwashing_classifier(
                            sentence)
                        sentiment_result = None
                        if self.sentiment_analyzer:
                            try:
                                sentiment_result = self.sentiment_analyzer(
                                    sentence)
                                if isinstance(sentiment_result,
                                              list) and len(
                                                  sentiment_result) > 0:
                                    sentiment_result = sentiment_result[0]
                            except Exception as e:
                                logger.warning(
                                    f"Sentiment analysis failed for sentence: "
                                    f"{e}")
                        sentence_entities = []
                        if self.nlp:
                            doc = self.nlp(sentence)
                            sentence_entities = [
                                {"text": ent.text, "label": ent.label_}
                                for ent in doc.ents
                                if ent.label_ in ["ORG", "PRODUCT",
                                                  "PERCENT", "QUANTITY",
                                                  "MONEY", "DATE"]
                            ]
                        claim_data = {
                            "text": sentence,
                            "environmental_keywords": matching_keywords,
                            "bert_classification": classification_results,
                            "sentiment": sentiment_result,
                            "entities": sentence_entities,
                            "confidence_score":
                                self._calculate_bert_confidence(
                                    classification_results, sentiment_result,
                                    matching_keywords),
                            "greenwashing_risk":
                                self._calculate_bert_greenwashing_risk(
                                    classification_results, sentence,
                                    matching_keywords),
                            "specificity_score":
                                self._calculate_specificity_with_nlp(sentence),
                            "bert_analysis": True
                        }

                        environmental_claims.append(claim_data)
                    except Exception as e:
                        logger.error(f"BERT analysis failed for sentence '"
                                     f"{sentence[:50]}...': {e}")
                        continue

            logger.info(f" BERT detected "
                        f"{len(environmental_claims)} environmental claims")
            return environmental_claims

        except Exception as e:
            logger.error(f" BERT claim detection error: {e}")
            return []

    def _calculate_bert_confidence(self, classification_results,
                                   sentiment_result,
                                   matching_keywords) -> float:
        try:
            base_confidence = 0.3
            bert_bonus = 0
            if classification_results and isinstance(classification_results,
                                                     list):
                max_score = 0
                for result in classification_results:
                    if isinstance(result, dict) and 'score' in result:
                        max_score = max(max_score, result['score'])
                bert_bonus = max_score * 0.3
            elif isinstance(classification_results,
                            dict) and 'score' in classification_results:
                bert_bonus = classification_results['score'] * 0.3
            sentiment_bonus = 0
            if sentiment_result and isinstance(sentiment_result, dict):
                if sentiment_result.get('label') in ['POSITIVE', 'LABEL_2']:
                    sentiment_bonus = sentiment_result.get('score', 0) * 0.2
            keyword_bonus = min(0.2, len(matching_keywords) * 0.05)
            total_confidence = base_confidence + bert_bonus + sentiment_bonus
            + keyword_bonus
            return min(0.95, total_confidence)
        except Exception as e:
            logger.error(f" BERT confidence calculation error: {e}")
            return 0.5

    def _calculate_bert_greenwashing_risk(self, classification_results,
                                          sentence: str,
                                          matching_keywords) -> float:
        try:
            base_risk = 0.2
            bert_risk = 0.2
            if classification_results and isinstance(classification_results,
                                                     list):
                positive_results = []
                for result in classification_results:
                    if isinstance(result, dict) and 'label' in result:
                        if 'positive' in result.get('label', '').lower():
                            positive_results.append(result)
                if positive_results:
                    avg_positive_score = sum(r.get(
                        'score', 0) for r in positive_results) / len(
                            positive_results)
                    if avg_positive_score < 0.6:
                        bert_risk = 0.3
                    else:
                        bert_risk = 0.1
            elif isinstance(classification_results, dict):
                if 'positive' in classification_results.get('label',
                                                            '').lower():
                    if classification_results.get('score', 0) < 0.6:
                        bert_risk = 0.3
                    else:
                        bert_risk = 0.1
            traditional_risk = 0
            vague_terms = ['eco', 'green', 'natural', 'clean', 'pure']
            absolute_terms = ['100%', 'completely', 'totally', 'perfect',
                              'entirely']
            sentence_lower = sentence.lower()
            for term in vague_terms:
                if term in sentence_lower:
                    traditional_risk += 0.1
            for term in absolute_terms:
                if term in sentence_lower:
                    traditional_risk += 0.2
            if len(matching_keywords) > 3:
                traditional_risk += 0.1
            total_risk = base_risk + bert_risk + traditional_risk
            return min(0.9, total_risk)
        except Exception as e:
            logger.error(f" BERT greenwashing risk calculation error: {e}")
            return 0.3

    def _calculate_specificity_with_nlp(self, sentence: str) -> float:
        try:
            base_specificity = 0.3
            if re.search(r'\d+%', sentence):
                base_specificity += 0.25
            if re.search(r'\d+\s*(tons?|kg|pounds?|mw|gwh|kwh)', sentence):
                base_specificity += 0.20
            if self.nlp:
                doc = self.nlp(sentence)
                specific_entities = [
                    ent for ent in doc.ents if ent.label_ in ["PERCENT",
                                                              "QUANTITY",
                                                              "DATE", "ORG",
                                                              "MONEY"]]
                entity_bonus = min(0.3, len(specific_entities) * 0.1)
                base_specificity += entity_bonus
                cert_terms = ["certified", "verified", "audited", "iso",
                              "leed", "energy star", "b-corp"]
                cert_bonus = 0.2 if any(
                    term in sentence.lower() for term in cert_terms) else 0
                base_specificity += cert_bonus
                numbers = [token for token in doc if token.like_num]
                if numbers:
                    base_specificity += min(0.15, len(numbers) * 0.05)
            return min(1.0, base_specificity)
        except Exception as e:
            logger.error(f" Specificity calculation error: {e}")
            return 0.5


if __name__ == "__main__":
    print(" Testing Enhanced NLP Processor...")

    processor = EnhancedNLPProcessor()

    test_text = "Tesla has achieved carbon neutrality through 100% renewable "
    "energy and reduced emissions by 25%."

    print(f" Status: {processor.get_nlp_status()}")

    results = processor.analyze_text_comprehensive(test_text)
    print(" Analysis Results:")
    print(f"  - Processing method: {results.get('processing_method')}")
    print(f"  - Claims detected: "
          f"{results.get('nlp_metrics', {}).get('total_claims_detected', 0)}")
    print(f"  - Entities found: "
          f"{results.get('nlp_metrics', {}).get('entities_found', 0)}")
    print(f"  - Processing time: {results.get('processing_time_ms', 0)}ms")

    print(" Enhanced NLP Processor test completed!")
