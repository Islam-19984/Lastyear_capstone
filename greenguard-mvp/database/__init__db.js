print("Initializing GreenGuard Database...");

db.companies.drop();
db.claims.drop();
db.verifications.drop();
db.user_submissions.drop();
db.alternatives.drop();

print(" Creating collections...");

db.createCollection("companies", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "domain", "industry_sector"],
      properties: {
        name: { bsonType: "string" },
        domain: { bsonType: "string" },
        industry_sector: { bsonType: "string" },
        sustainability_scores: {
          bsonType: "object",
          properties: {
            overall_score: { bsonType: "number", minimum: 0, maximum: 1 },
            carbon_score: { bsonType: "number", minimum: 0, maximum: 1 },
            transparency_score: { bsonType: "number", minimum: 0, maximum: 1 },
            certification_score: { bsonType: "number", minimum: 0, maximum: 1 }
          }
        }
      }
    }
  }
});

db.createCollection("claims", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["claim_text", "confidence_score", "greenwashing_risk"],
      properties: {
        claim_text: { bsonType: "string" },
        confidence_score: { bsonType: "number", minimum: 0, maximum: 1 },
        greenwashing_risk: { bsonType: "number", minimum: 0, maximum: 1 },
        verification_status: { 
          bsonType: "string", 
          enum: ["pending", "verified", "disputed", "flagged"] 
        }
      }
    }
  }
});

db.createCollection("verifications");
db.createCollection("user_submissions");
db.createCollection("alternatives");

print("🔍 Creating indexes...");

db.companies.createIndex({ "domain": 1 }, { unique: true });
db.companies.createIndex({ "industry_sector": 1 });
db.companies.createIndex({ "sustainability_scores.overall_score": -1 });

db.claims.createIndex({ "detected_timestamp": -1 });
db.claims.createIndex({ "greenwashing_risk": -1 });
db.claims.createIndex({ "company_id": 1 });
db.claims.createIndex({ "verification_status": 1 });

db.verifications.createIndex({ "claim_id": 1 });
db.verifications.createIndex({ "verification_timestamp": -1 });
db.verifications.createIndex({ "verification_score": -1 });

db.user_submissions.createIndex({ "claim_id": 1 });
db.user_submissions.createIndex({ "submission_timestamp": -1 });
db.user_submissions.createIndex({ "credibility_score": -1 });

db.alternatives.createIndex({ "original_company_id": 1 });
db.alternatives.createIndex({ "recommendation_confidence": -1 });

print(" Inserting sample companies...");

db.companies.insertMany([
  {
    "_id": "ecofashion123",
    "name": "EcoFashion Co",
    "domain": "ecofashion.com",
    "industry_sector": "fashion",
    "verified_data": {
      "carbon_emissions": 15000,
      "renewable_energy_percentage": 25,
      "certifications": ["GOTS", "Fair Trade"],
      "sustainability_reports": [
        {
          "year": 2024,
          "report_url": "https://ecofashion.com/sustainability-2024.pdf",
          "verified": false
        }
      ],
      "last_verified": new Date()
    },
    "sustainability_scores": {
      "overall_score": 0.45,
      "carbon_score": 0.3,
      "transparency_score": 0.6,
      "certification_score": 0.8
    },
    "created_at": new Date(),
    "last_updated": new Date()
  },
  {
    "_id": "greentech456",
    "name": "GreenTech Inc",
    "domain": "greentech.com",
    "industry_sector": "technology",
    "verified_data": {
      "carbon_emissions": 8000,
      "renewable_energy_percentage": 75,
      "certifications": ["B-Corp", "Carbon Neutral", "Science-Based Targets"],
      "sustainability_reports": [
        {
          "year": 2024,
          "report_url": "https://greentech.com/impact-report-2024.pdf",
          "verified": true
        }
      ],
      "last_verified": new Date()
    },
    "sustainability_scores": {
      "overall_score": 0.85,
      "carbon_score": 0.9,
      "transparency_score": 0.8,
      "certification_score": 0.85
    },
    "created_at": new Date(),
    "last_updated": new Date()
  },
  {
    "_id": "sustsol789",
    "name": "Sustainable Solutions Ltd",
    "domain": "sustsol.com",
    "industry_sector": "consumer_goods",
    "verified_data": {
      "carbon_emissions": 12000,
      "renewable_energy_percentage": 50,
      "certifications": ["EPA Safer Choice", "USDA BioPreferred"],
      "sustainability_reports": [],
      "last_verified": new Date()
    },
    "sustainability_scores": {
      "overall_score": 0.65,
      "carbon_score": 0.7,
      "transparency_score": 0.5,
      "certification_score": 0.75
    },
    "created_at": new Date(),
    "last_updated": new Date()
  }
]);

print(" Inserting sample claims...");

db.claims.insertMany([
  {
    "company_id": "ecofashion123",
    "claim_text": "Made from 100% sustainable materials",
    "keyword": "sustainable",
    "confidence_score": 0.85,
    "greenwashing_risk": 0.78,
    "verification_status": "flagged",
    "source_url": "https://ecofashion.com/products/jacket",
    "detected_timestamp": new Date(),
    "context": {
      "surrounding_text": "Our premium jacket is made from 100% sustainable materials and represents our commitment to the environment.",
      "page_title": "EcoFashion Premium Jacket - Sustainable Clothing",
      "element_type": "product_description"
    }
  },
  {
    "company_id": "greentech456",
    "claim_text": "Our data centers run on 100% renewable energy verified by third-party audits",
    "keyword": "renewable energy",
    "confidence_score": 0.95,
    "greenwashing_risk": 0.15,
    "verification_status": "verified",
    "source_url": "https://greentech.com/sustainability",
    "detected_timestamp": new Date(),
    "context": {
      "surrounding_text": "We are committed to environmental responsibility. Our data centers run on 100% renewable energy verified by third-party audits and certified by the Green-e program.",
      "page_title": "GreenTech Sustainability Commitment",
      "element_type": "sustainability_page"
    }
  }
]);

print(" Inserting sample verifications...");

db.verifications.insertMany([
  {
    "claim_text": "Made from 100% sustainable materials",
    "company_name": "EcoFashion Co",
    "verification_score": 0.25,
    "risk_level": "HIGH",
    "data_sources": {
      "cdp": {"score": 0.2, "status": "not_found"},
      "sbti": {"score": 0.1, "status": "not_registered"},
      "epa": {"score": 0.3, "status": "no_data"}
    },
    "recommendations": [
      "No third-party verification found",
      "Claims appear to be unsubstantiated",
      "Consider looking for certified alternatives"
    ],
    "verification_timestamp": new Date()
  },
  {
    "claim_text": "100% renewable energy verified by third-party audits",
    "company_name": "GreenTech Inc",
    "verification_score": 0.88,
    "risk_level": "LOW",
    "data_sources": {
      "cdp": {"score": 0.9, "status": "verified"},
      "sbti": {"score": 0.85, "status": "approved_targets"},
      "epa": {"score": 0.9, "status": "green_power_partner"}
    },
    "recommendations": [
      "Claims appear to be well-substantiated",
      "Good transparency in reporting",
      "Consider this a reliable option"
    ],
    "verification_timestamp": new Date()
  }
]);

print(" Inserting sample alternatives...");

db.alternatives.insertMany([
  {
    "original_company_id": "ecofashion123",
    "alternative_company_id": "greentech456",
    "product_category": "general",
    "comparison_metrics": {
      "sustainability_advantage": 0.4,
      "price_difference": 0.15,
      "availability_score": 0.8,
      "certification_advantage": 0.05
    },
    "recommendation_confidence": 0.85,
    "user_ratings": {
      "average_rating": 4.2,
      "total_ratings": 127,
      "last_updated": new Date()
    },
    "created_at": new Date(),
    "last_updated": new Date()
  }
]);

print(" Verifying data insertion...");

print("Companies inserted: " + db.companies.countDocuments());
print("Claims inserted: " + db.claims.countDocuments());
print("Verifications inserted: " + db.verifications.countDocuments());
print("Alternatives inserted: " + db.alternatives.countDocuments());

print(" Testing sample queries...");

print("High-risk claims: " + db.claims.countDocuments({"greenwashing_risk": {"$gte": 0.7}}));
print("Verified companies: " + db.companies.countDocuments({"sustainability_scores.overall_score": {"$gte": 0.8}}));

print(" Database initialization completed successfully!");
print(" GreenGuard database is ready for use!");

print("\n Database Statistics:");
print("Database: " + db.getName());
print("Collections: " + db.getCollectionNames().length);
print("Total documents: " + (
  db.companies.countDocuments() + 
  db.claims.countDocuments() + 
  db.verifications.countDocuments() + 
  db.user_submissions.countDocuments() + 
  db.alternatives.countDocuments()
));

print("\n MongoDB Connection String:");
print("mongodb://localhost:27017/greenguard_db");