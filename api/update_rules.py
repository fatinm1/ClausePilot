#!/usr/bin/env python3
"""
Script to update processing rules to remove hardcoded values
This allows firm details to be used instead of hardcoded company/person names
"""
import os
import sys

# Add the api directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from config import Config

def update_rules():
    """Update rules to remove hardcoded values"""
    app = create_app(Config)
    
    with app.app_context():
        ProcessingRule = app.ProcessingRule
        
        # Get all rules
        rules = ProcessingRule.query.all()
        
        print(f"Found {len(rules)} rules")
        print("-" * 80)
        
        updated_count = 0
        
        for rule in rules:
            original_instruction = rule.instruction
            updated_instruction = original_instruction
            
            # Replace hardcoded company names with placeholder
            hardcoded_companies = [
                'JMC Investment LLC',
                'JMC Investment',
                'JMC',
                'Welch Capital Partners',
                'Welch Capital'
            ]
            
            for company in hardcoded_companies:
                if company in updated_instruction:
                    updated_instruction = updated_instruction.replace(company, '[FIRM_NAME]')
            
            # Replace hardcoded person names with placeholder
            hardcoded_names = [
                'John Bagge',
                'John',
                'Jane Doe'
            ]
            
            for name in hardcoded_names:
                if name in updated_instruction:
                    updated_instruction = updated_instruction.replace(name, '[SIGNER_NAME]')
            
            # Replace hardcoded titles with placeholder
            hardcoded_titles = [
                'Vice President',
                'President',
                'CEO',
                'Managing Director'
            ]
            
            for title in hardcoded_titles:
                if title in updated_instruction:
                    updated_instruction = updated_instruction.replace(title, '[TITLE]')
            
            # If instruction was modified, update it
            if updated_instruction != original_instruction:
                print(f"\nRule ID {rule.id}: {rule.name}")
                print(f"  Category: {rule.category}")
                print(f"  BEFORE: {original_instruction}")
                print(f"  AFTER:  {updated_instruction}")
                
                rule.instruction = updated_instruction
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print("\n" + "=" * 80)
            print(f"✅ Successfully updated {updated_count} rule(s)")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("ℹ️  No rules needed updating")
            print("=" * 80)

if __name__ == '__main__':
    update_rules()

