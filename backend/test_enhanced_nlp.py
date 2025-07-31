import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def test_enhanced_nlp():
    print(" Testing Enhanced NLP Integration...")
    print("=" * 50)
    try:
        from enhanced_nlp_processor import EnhancedNLPProcessor
        print(" Enhanced NLP processor imported successfully")
    except ImportError as e:
        print(f" Failed to import Enhanced NLP processor: {e}")
        return False
    try:
        nlp_processor = EnhancedNLPProcessor()
        print(" Enhanced NLP processor initialized")
        status = nlp_processor.get_nlp_status()
        print(" NLP Status:")
        print(f"   - spaCy: {'' if status['spacy_available'] else ''}")
        print(f"   - BERT: {'' if status['bert_available'] else ''}")
        print(f"   - Sentiment: {'' if status['sentiment_available'] else ''}")
        print(f"   - System Ready: {'' if status['system_ready'] else ''}")
    except Exception as e:
        print(f" Failed to initialize Enhanced NLP processor: {e}")
        return False
    test_text = """
    Our company is 100% carbon neutral and uses only renewable energy.
    We have achieved ISO 14001 certification and reduced our emissions by 50%
    last year.
    Our products are completely eco-friendly and made from recycled materials.
    """
    print("\n Testing with sample text:")
    print(f"'{test_text[:100]}...'")
    try:
        analysis = nlp_processor.analyze_text_comprehensive(test_text)
        print("\n Analysis Results:")
        print("   - Claims detected: "
              "{analysis['nlp_metrics']['total_claims_detected']}")
        print(f"   - Average confidence: "
              f"{analysis['nlp_metrics']['average_confidence']:.2f}")
        print(f"   - Average risk: "
              f"{analysis['nlp_metrics']['average_greenwashing_risk']:.2f}")
        print(f"   - Entities found: "
              f"{analysis['nlp_metrics']['entities_found']}")
        print(f"   - Processing time: {analysis['processing_time_ms']:.1f}ms")
        bert_claims = analysis.get('bert_claims', [])
        if bert_claims:
            print("\nx Detected Claims:")
            for i, claim in enumerate(bert_claims[:3], 1):
                print(f"   {i}. '{claim['text'][:60]}...'")
                print(f"      Keywords: {claim['environmental_keywords']}")
                print(f"      Confidence: {claim['confidence_score']:.2f}")
                print(f"      Risk: {claim['greenwashing_risk']:.2f}")
        spacy_analysis = analysis.get('spacy_analysis', {})
        entities = spacy_analysis.get('entities', [])
        if entities:
            print("\n Named Entities:")
            for entity in entities[:5]:
                print(f"   - {entity['text']} ({entity['label']})")
        print("\n Enhanced NLP analysis completed successfully!")
    except Exception as e:
        print(f" Enhanced NLP analysis failed: {e}")
        return False
    try:
        from app import claim_detector
        print("\n Testing integration with existing claim detector...")
        claims = claim_detector.detect_claims(test_text)
        print(f"   - Total claims detected: {len(claims)}")
        if claims:
            first_claim = claims[0]
            has_enhanced = first_claim.get('enhanced_nlp', False)
            print(f"   - Enhanced NLP features: {'' if has_enhanced else ''}")
            print(f"   - Detection method: "
                  f"{first_claim.get('detection_method', 'unknown')}")
            if 'bert_analysis' in first_claim:
                print("   - BERT analysis:  Available")
            if 'spacy_entities' in first_claim:
                print("   - spaCy entities:  Available")
        print(" Integration test completed successfully!")
    except Exception as e:
        print(f" Integration test failed: {e}")
        return False
    print("\n All tests passed! Enhanced "
          "NLP integration is working correctly.")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_enhanced_nlp()
    exit(0 if success else 1)
