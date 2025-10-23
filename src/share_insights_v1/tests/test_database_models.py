#!/usr/bin/env python3

import sys
import os

# Add project root to path
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
# sys.path.insert(0, project_root)

from ..models.database import SessionLocal, create_tables
from ..services.database.database_service import DatabaseService

def test_database_models():
    """Test database models and operations"""
    
    # Initialize database
    db_service = DatabaseService()
    db = SessionLocal()
    
    try:
        print("=== Testing Database Models ===")
        
        # 1. Create US-China Trade War scenario
        print("\n1. Creating US-China Trade War scenario...")
        scenario = db_service.create_scenario(
            db=db,
            name="US-China Trade War",
            description="Escalating trade tensions between US and China",
            category="geopolitical",
            base_probability=0.30,
            timeframe="6M"
        )
        print(f"Created scenario: {scenario.name} (ID: {scenario.id})")
        
        # 2. Create scenario outcomes
        print("\n2. Creating scenario outcomes...")
        outcomes = [
            {
                "name": "Complete Decoupling",
                "probability": 0.40,
                "impact_description": "Full economic separation",
                "expected_duration": "2Y"
            },
            {
                "name": "Reconciliation",
                "probability": 0.60,
                "impact_description": "Return to normal trade relations",
                "expected_duration": "6M"
            }
        ]
        outcome_objects = db_service.create_scenario_outcomes(db, scenario.id, outcomes)
        print(f"Created {len(outcome_objects)} outcomes")
        
        # 3. Create investment strategy
        print("\n3. Creating investment strategy...")
        strategy = db_service.create_strategy(
            db=db,
            name="China Trade War Strategy",
            description="Strategy to navigate US-China trade tensions",
            strategy_type="scenario_based",
            timeframe="6M",
            risk_tolerance="moderate"
        )
        print(f"Created strategy: {strategy.name} (ID: {strategy.id})")
        
        # 4. Link strategy to scenario
        print("\n4. Linking strategy to scenario...")
        link = db_service.link_strategy_scenario(
            db=db,
            strategy_id=strategy.id,
            scenario_id=scenario.id,
            weight=0.8,  # 80% weight for this scenario
            impact_factor=1.2  # 20% impact multiplier
        )
        print(f"Linked strategy to scenario with weight: {link.weight}")
        
        # 5. Create portfolio
        print("\n5. Creating portfolio...")
        portfolio = db_service.create_portfolio(
            db=db,
            strategy_id=strategy.id,
            name="Trade War Portfolio",
            initial_value=100000.0
        )
        print(f"Created portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        # 6. Add positions
        print("\n6. Adding positions...")
        positions_data = [
            {"ticker": "AAPL", "target_weight": 0.20, "scenario_adjustment": 0.8},  # Reduce by 20% in bad scenario
            {"ticker": "MSFT", "target_weight": 0.15, "scenario_adjustment": 0.9},  # Reduce by 10%
            {"ticker": "GOOGL", "target_weight": 0.15, "scenario_adjustment": 0.85}, # Reduce by 15%
            {"ticker": "TSLA", "target_weight": 0.10, "scenario_adjustment": 0.7},  # Reduce by 30%
        ]
        
        for pos_data in positions_data:
            position = db_service.add_position(
                db=db,
                portfolio_id=portfolio.id,
                ticker=pos_data["ticker"],
                target_weight=pos_data["target_weight"],
                scenario_adjustment=pos_data["scenario_adjustment"]
            )
            print(f"Added position: {position.ticker} ({position.target_weight*100:.0f}% target)")
        
        # 7. Save analysis results
        print("\n7. Saving analysis results...")
        analysis_data = {
            "method": "dcf",
            "current_price": 150.0,
            "target_price": 180.0,
            "recommendation": "Buy",
            "confidence": "High"
        }
        
        analysis = db_service.save_analysis_result(
            db=db,
            ticker="AAPL",
            analysis_type="dcf",
            recommendation="Buy",
            target_price=180.0,
            confidence="High",
            raw_data=analysis_data,
            scenario_context_id=scenario.id
        )
        print(f"Saved analysis for {analysis.ticker}: {analysis.recommendation}")
        
        # 8. Update scenario probability
        print("\n8. Updating scenario probability...")
        updated_scenario = db_service.update_scenario_probability(
            db=db,
            scenario_id=scenario.id,
            new_probability=0.45,  # Increased from 0.30
            reason="Trump announces new tariffs"
        )
        print(f"Updated scenario probability: {updated_scenario.current_probability}")
        
        # 9. Query data
        print("\n9. Querying data...")
        active_scenarios = db_service.get_active_scenarios(db)
        print(f"Active scenarios: {len(active_scenarios)}")
        
        strategy_scenarios = db_service.get_strategy_scenarios(db, strategy.id)
        print(f"Strategy scenarios: {len(strategy_scenarios)}")
        
        portfolio_positions = db_service.get_portfolio_positions(db, portfolio.id)
        print(f"Portfolio positions: {len(portfolio_positions)}")
        
        analysis_history = db_service.get_analysis_history(db, "AAPL")
        print(f"Analysis history for AAPL: {len(analysis_history)} records")
        
        print("\n✅ Database models test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during database test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()

if __name__ == "__main__":
    test_database_models()