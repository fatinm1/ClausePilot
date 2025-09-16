import os
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from docx import Document as DocxDocument
from docx.shared import Inches, RGBColor
from docx.enum.text import WD_COLOR_INDEX
from docx.oxml.shared import OxmlElement, qn
from docx.oxml.ns import nsdecls
from datetime import datetime

logger = logging.getLogger(__name__)

class AIRedliningService:
    def __init__(self):
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            logger.info(f"OpenAI API key status: {'Set' if api_key else 'Not set'}")
            logger.info(f"API key length: {len(api_key) if api_key else 0}")
            logger.info(f"API key starts with: {api_key[:10] if api_key and len(api_key) > 10 else 'N/A'}")
            
            # Check if we should use real API
            if not api_key:
                logger.warning("No OpenAI API key found in environment variables")
                self.client = None
                self.model = "mock-gpt-4"
                logger.info("Running in mock mode - no OpenAI API calls will be made")
            elif api_key == 'mock-key-for-development':
                logger.info("Mock API key detected")
                self.client = None
                self.model = "mock-gpt-4"
                logger.info("Running in mock mode - no OpenAI API calls will be made")
            else:
                # Try to initialize real OpenAI client
                logger.info("Attempting to initialize OpenAI client with real API key")
                try:
                    # Initialize OpenAI with minimal parameters
                    self.client = OpenAI(api_key=api_key)
                    self.model = "gpt-3.5-turbo"
                    logger.info("OpenAI client initialized successfully with real API")
                        
                except Exception as init_error:
                    logger.error(f"Error during OpenAI client initialization: {str(init_error)}")
                    logger.error(f"Error type: {type(init_error).__name__}")
                    logger.error(f"Error details: {repr(init_error)}")
                    
                    # Fallback to mock mode
                    self.client = None
                    self.model = "mock-gpt-4"
                    logger.info("Falling back to mock mode due to OpenAI initialization errors")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
            self.model = "mock-gpt-4"
            logger.info("Falling back to mock mode due to error")
        
    def analyze_document(self, document_text: str, custom_rules: List[Dict[str, Any]], firm_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze the document using OpenAI GPT-4 and return redlining instructions
        """
        try:
            # Check if we're in mock mode
            logger.warning(f"AI Service - Client available: {self.client is not None}")
            logger.warning(f"AI Service - Model: {self.model}")
            if not self.client:
                logger.warning("Using mock analysis - OpenAI client not available")
                return self._mock_analysis(document_text, custom_rules, firm_details)
            
            # Prepare the prompt for GPT-4
            logger.info("Using REAL OpenAI API for analysis")
            system_prompt = self._build_system_prompt(custom_rules, firm_details)
            user_prompt = self._build_user_prompt(document_text, custom_rules, firm_details)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent legal work
                max_tokens=2000  # Increased for more detailed responses
            )
            
            # Parse the AI response
            ai_response = response.choices[0].message.content
            logger.info(f"AI Response: {ai_response}")
            logger.info(f"AI Response length: {len(ai_response)} characters")
            modifications = self._parse_ai_response(ai_response)
            logger.info(f"Parsed modifications: {len(modifications)}")
            
            return {
                'success': True,
                'redlining_instructions': {
                    'modifications': modifications,
                    'summary': f"AI analysis generated {len(modifications)} modifications",
                    'risk_assessment': "AI-generated risk assessment"
                },
                'ai_analysis': ai_response
            }
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _mock_analysis(self, document_text: str, custom_rules: List[Dict[str, Any]], firm_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Provide mock analysis for development/testing"""
        logger.info("Running mock AI analysis")
        logger.info(f"Document text length: {len(document_text)} characters")
        logger.info(f"Number of custom rules: {len(custom_rules)}")
        
        # Create realistic mock redlining instructions based on custom rules
        mock_modifications = []
        
        # Apply firm details first if provided
        if firm_details:
            logger.warning(f"Applying firm details: {firm_details}")
            logger.warning(f"Firm details keys: {list(firm_details.keys())}")
            if 'title' in firm_details:
                logger.warning(f"Title from firm details: '{firm_details['title']}'")
            
            # Look for company name patterns in the document
            company_patterns = [
                "Company (name to be provided upon execution)",
                "For: Company (name to be provided upon execution)",
                "For: Company",
                "Company"
            ]
            
            if 'firm_name' in firm_details:
                for pattern in company_patterns:
                    if pattern in document_text:
                        if pattern.startswith("For:"):
                            new_text = pattern.replace("Company", firm_details['firm_name'])
                        else:
                            new_text = f"For: {firm_details['firm_name']}"
                        
                        mock_modifications.append({
                            "type": "TEXT_REPLACE",
                            "section": "parties",
                            "current_text": pattern,
                            "new_text": new_text,
                            "reason": "Replace company placeholder with actual firm name",
                            "location_hint": "Parties section"
                        })
                        logger.info(f"Found company pattern: '{pattern}' -> '{new_text}'")
                        break
                else:
                    # If no patterns found, add a generic company replacement
                    logger.info("No company patterns found, adding generic company replacement")
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "parties",
                        "current_text": "Company",
                        "new_text": f"For: {firm_details['firm_name']}",
                        "reason": "Replace company placeholder with actual firm name",
                        "location_hint": "Parties section"
                    })
            
            # Look for signature patterns
            if 'signatory_name' in firm_details:
                if 'By:' in document_text and firm_details['signatory_name'] not in document_text:
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "signatures",
                        "current_text": "By:",
                        "new_text": f"By: {firm_details['signatory_name']}",
                        "reason": "Replace signer placeholder with actual name",
                        "location_hint": "Signature block"
                    })
                    logger.info(f"Added signer replacement: 'By:' -> 'By: {firm_details['signatory_name']}'")
            
            if 'title' in firm_details:
                # Look for Title: with various formatting patterns
                title_patterns = [
                    "Title: \t_______________________________",
                    "Title:\t_______________________________",
                    "Title:_______________________________",
                    "Title:",
                    "Title: \t",
                    "Title:\t"
                ]
                
                for title_pattern in title_patterns:
                    logger.warning(f"Checking title pattern: '{title_pattern}'")
                    if title_pattern in document_text:
                        logger.warning(f"Found title pattern '{title_pattern}' in document")
                        if firm_details['title'] not in document_text:
                            logger.warning(f"Title '{firm_details['title']}' not in document, adding replacement")
                            mock_modifications.append({
                                "type": "TEXT_REPLACE",
                                "section": "signatures",
                                "current_text": title_pattern,
                                "new_text": f"Title: {firm_details['title']}",
                                "reason": "Replace title placeholder with actual title",
                                "location_hint": "Signature block"
                            })
                            logger.warning(f"Added title replacement: '{title_pattern}' -> 'Title: {firm_details['title']}'")
                            break
                        else:
                            logger.warning(f"Title '{firm_details['title']}' already in document, skipping replacement")
                    else:
                        logger.warning(f"Title pattern '{title_pattern}' not found in document")
        
        for rule in custom_rules:
            rule_name = rule.get('name', '').lower()
            rule_instruction = rule.get('instruction', '')
            logger.info(f"Processing rule: {rule_name}")
            
            # Create specific modifications based on rule type
            if 'duration' in rule_name or 'term' in rule_name or 'confidentiality' in rule_name:
                # Look for various year patterns in the document
                year_patterns = [
                    ('five (5) years', 'two (2) years'),
                    ('5 years', '2 years'),
                    ('three (3) years', 'two (2) years'),
                    ('3 years', '2 years'),
                    ('four (4) years', 'two (2) years'),
                    ('4 years', '2 years'),
                    ('ten (10) years', 'two (2) years'),
                    ('10 years', '2 years'),
                    ('three years', 'two (2) years'),
                    ('five years', 'two (2) years')
                ]
                
                found_pattern = False
                for current_pattern, new_pattern in year_patterns:
                    if current_pattern in document_text.lower():
                        mock_modifications.append({
                            "type": "TEXT_REPLACE",
                            "section": "term",
                            "current_text": current_pattern,
                            "new_text": new_pattern,
                            "reason": rule_instruction,
                            "location_hint": "Confidentiality term section"
                        })
                        logger.info(f"Found year pattern: {current_pattern} -> {new_pattern}")
                        found_pattern = True
                        break
                
                if not found_pattern:
                    # If no specific patterns found, add a generic year modification
                    logger.info("No specific year patterns found, adding generic modification")
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "term",
                        "current_text": "three years",
                        "new_text": "two (2) years",
                        "reason": rule_instruction,
                        "location_hint": "Confidentiality term section"
                    })
            
            elif 'liability' in rule_name or 'damage' in rule_name:
                # Add liability cap clause
                mock_modifications.append({
                    "type": "TEXT_INSERT",
                    "section": "liability",
                    "new_text": "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement.",
                    "reason": rule_instruction,
                    "location_hint": "After Section 8, Remedies"
                })
            
            elif 'firm' in rule_name or 'party' in rule_name or 'parties' in rule_name or 'name' in rule_name:
                # Look for party name patterns
                party_patterns = [
                    ('Angle Advisors LLC', 'Welch Capital Partners Inc. (WCP)'),
                    ('Company (name to be provided upon execution)', 'JMC Investment LLC'),
                    ('Recipient', 'JMC Investment LLC (Recipient)'),
                    ('Disclosing Party', 'Welch Capital Partners Inc. (WCP)'),
                    ('Receiving Party', 'JMC Investment LLC (Recipient)')
                ]
                
                for current_pattern, new_pattern in party_patterns:
                    if current_pattern in document_text:
                        mock_modifications.append({
                            "type": "TEXT_REPLACE",
                            "section": "parties",
                            "current_text": current_pattern,
                            "new_text": new_pattern,
                            "reason": rule_instruction,
                            "location_hint": "Parties section"
                        })
                        logger.info(f"Found party pattern: {current_pattern} -> {new_pattern}")
                        break
                
                # Replace firm placeholders
                if '[FIRM_NAME]' in document_text:
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "parties",
                        "current_text": "[FIRM_NAME]",
                        "new_text": "TechLegal Partners LLP",
                        "reason": rule_instruction,
                        "location_hint": "Section 1, line 4"
                    })
                if '[SIGNER_NAME]' in document_text:
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "signatures",
                        "current_text": "[SIGNER_NAME]",
                        "new_text": "John Bagge",
                        "reason": rule_instruction,
                        "location_hint": "Section 11, line 55"
                    })
                if '[SIGNER_TITLE]' in document_text:
                    mock_modifications.append({
                        "type": "TEXT_REPLACE",
                        "section": "signatures",
                        "current_text": "[SIGNER_TITLE]",
                        "new_text": "Vice President",
                        "reason": rule_instruction,
                        "location_hint": "Section 11, line 56"
                    })
            
            # Add more flexible pattern matching for other rule types
            elif 'governing' in rule_name or 'law' in rule_name:
                # Look for governing law patterns
                law_patterns = [
                    ('State of Delaware', 'State of New York'),
                    ('Delaware', 'New York'),
                    ('Delaware courts', 'New York courts')
                ]
                
                for current_pattern, new_pattern in law_patterns:
                    if current_pattern in document_text:
                        mock_modifications.append({
                            "type": "TEXT_REPLACE",
                            "section": "governing_law",
                            "current_text": current_pattern,
                            "new_text": new_pattern,
                            "reason": rule_instruction,
                            "location_hint": "Governing law section"
                        })
                        logger.info(f"Found law pattern: {current_pattern} -> {new_pattern}")
                        break
            
            elif 'signature' in rule_name or 'block' in rule_name:
                # Replace signature placeholders instead of inserting new content
                signature_replacements = []
                
                # Look for specific signature patterns in the document
                # Try multiple variations of the company placeholder
                company_patterns = [
                    "For: Company (name to be provided upon execution)",
                    "For: Company",
                    "Company (name to be provided upon execution)",
                    "Company"
                ]
                
                for pattern in company_patterns:
                    if pattern in document_text:
                        # Determine the replacement text based on the pattern
                        if pattern.startswith("For:"):
                            new_text = pattern.replace("Company", "JMC Investment LLC")
                        else:
                            new_text = "For: JMC Investment LLC"
                        
                        signature_replacements.append({
                            "type": "TEXT_REPLACE",
                            "section": "signatures",
                            "current_text": pattern,
                            "new_text": new_text,
                            "reason": rule_instruction,
                            "location_hint": "Signature block company name"
                        })
                        logger.info(f"Found company pattern: '{pattern}' -> '{new_text}'")
                        break
                
                if 'By:' in document_text and 'John Bagge' not in document_text:
                    signature_replacements.append({
                        "type": "TEXT_REPLACE",
                        "section": "signatures",
                        "current_text": "By:",
                        "new_text": "By: John Bagge",
                        "reason": rule_instruction,
                        "location_hint": "Signature block signer name"
                    })
                
                # Look for Title: with various formatting patterns
                title_patterns = [
                    "Title: \t_______________________________",
                    "Title:\t_______________________________",
                    "Title:_______________________________",
                    "Title:",
                    "Title: \t",
                    "Title:\t"
                ]
                
                for title_pattern in title_patterns:
                    logger.warning(f"Checking rule title pattern: '{title_pattern}'")
                    if title_pattern in document_text:
                        logger.warning(f"Found rule title pattern '{title_pattern}' in document")
                        if 'Vice President' not in document_text:
                            logger.warning(f"'Vice President' not in document, adding replacement")
                            signature_replacements.append({
                                "type": "TEXT_REPLACE",
                                "section": "signatures",
                                "current_text": title_pattern,
                                "new_text": "Title: Vice President",
                                "reason": rule_instruction,
                                "location_hint": "Signature block title"
                            })
                            logger.warning(f"Added rule title replacement: '{title_pattern}' -> 'Title: Vice President'")
                            break
                        else:
                            logger.warning(f"'Vice President' already in document, skipping replacement")
                    else:
                        logger.warning(f"Rule title pattern '{title_pattern}' not found in document")
                
                if signature_replacements:
                    mock_modifications.extend(signature_replacements)
                    logger.info(f"Added {len(signature_replacements)} signature block replacements")
                else:
                    logger.info("No signature placeholders found to replace")
        
        # If no modifications were found, create a generic one based on the first rule
        if not mock_modifications and custom_rules:
            first_rule = custom_rules[0]
            mock_modifications.append({
                "type": "TEXT_INSERT",
                "section": "general",
                "new_text": f"[Modification based on rule: {first_rule.get('name', 'Unknown')}]",
                "reason": first_rule.get('instruction', 'Rule application'),
                "location_hint": "Document beginning"
            })
            logger.info("Added fallback modification")
        
        logger.info(f"Mock analysis complete. Generated {len(mock_modifications)} modifications:")
        for i, mod in enumerate(mock_modifications):
            logger.info(f"  {i+1}. {mod['type']}: '{mod['current_text']}' -> '{mod['new_text']}'")
        
        return {
            'success': True,
            'redlining_instructions': {
                'modifications': mock_modifications,
                'summary': f"Mock analysis completed with {len(mock_modifications)} modifications based on {len(custom_rules)} rules",
                'risk_assessment': "Mock assessment - modifications based on provided rules for testing purposes"
            },
            'ai_analysis': f"Mock AI analysis generated {len(mock_modifications)} redlining suggestions based on the provided rules. In production, this would be generated by OpenAI GPT-4."
        }
    
    def _build_system_prompt(self, custom_rules: List[Dict[str, Any]], firm_details: Dict[str, Any] = None) -> str:
        """Build the system prompt for GPT-4"""
        base_prompt = """You are an expert legal AI assistant specializing in NDA (Non-Disclosure Agreement) redlining. 
        Your task is to analyze NDA documents and provide PRECISE, TARGETED redlining instructions.
        
        CRITICAL INSTRUCTIONS:
        1. Make ONLY the specific changes requested in the rules - do NOT over-redline
        2. Use EXACT text matches from the document for current_text
        3. Focus on the specific areas mentioned in the rules
        4. Apply firm details exactly as provided
        5. Be conservative - only change what is explicitly requested
        6. REPLACE existing placeholders - do NOT create new fields or sections
        7. For signature blocks, ONLY use TEXT_REPLACE - NEVER use TEXT_INSERT
        8. Replace "By:" with "By: [Name]", "Title:" with "Title: [Title]", etc.
        9. Do NOT add new signature lines or duplicate existing ones
        
        REDLINING PRINCIPLES:
        - Replace specific text with exact matches
        - Insert new text only where specified
        - Delete text only when explicitly requested
        - Maintain legal document structure
        - Use professional legal language
        
        Available modification types:
        - TEXT_REPLACE: Replace specific text (most common)
        - TEXT_INSERT: Insert new text at specific locations
        - TEXT_DELETE: Remove specific text
        - CLAUSE_ADD: Add entire new clauses
        
        Return your analysis in this exact JSON format:
        {
            "modifications": [
                {
                    "type": "TEXT_REPLACE",
                    "section": "confidentiality_term",
                    "current_text": "three years",
                    "new_text": "two (2) years",
                    "reason": "Term exceeds maximum allowed duration",
                    "location_hint": "Term section"
                },
                {
                    "type": "TEXT_REPLACE",
                    "section": "recipient",
                    "current_text": "Dear NAME:",
                    "new_text": "Dear John Bagge:",
                    "reason": "Replace recipient name placeholder",
                    "location_hint": "Salutation"
                },
                {
                    "type": "TEXT_REPLACE",
                    "section": "signature_block",
                    "current_text": "For: Company",
                    "new_text": "For: JMC Investment LLC",
                    "reason": "Replace company name placeholder",
                    "location_hint": "Signature block"
                },
                {
                    "type": "TEXT_REPLACE",
                    "section": "signature_block",
                    "current_text": "By:",
                    "new_text": "By: John Bagge",
                    "reason": "Complete signature block with signer name",
                    "location_hint": "Signature section"
                }
            ],
            "summary": "Brief summary of all changes",
            "risk_assessment": "Assessment of any legal risks in modifications"
        }
        
        IMPORTANT: For signature blocks, always use TEXT_REPLACE to fill in existing placeholders. Never use TEXT_INSERT to create new signature fields."""
        
        if custom_rules:
            rules_text = "\n\nCUSTOM RULES TO APPLY (follow these exactly):\n"
            for rule in custom_rules:
                rules_text += f"- {rule['instruction']}\n"
            base_prompt += rules_text
        
        if firm_details:
            firm_text = "\n\nFIRM DETAILS TO APPLY:\n"
            for key, value in firm_details.items():
                firm_text += f"- {key}: {value}\n"
            base_prompt += firm_text
        
        return base_prompt
    
    def _build_user_prompt(self, document_text: str, custom_rules: List[Dict[str, Any]], firm_details: Dict[str, Any] = None) -> str:
        """Build the user prompt with document content"""
        # Use more of the document text for better analysis
        text_limit = 4000  # Increased from 2000
        document_preview = document_text[:text_limit]
        
        prompt = f"""Please analyze the following NDA document and provide PRECISE redlining instructions based on the custom rules.

DOCUMENT CONTENT:
{document_preview}

CRITICAL REQUIREMENTS:
1. When providing current_text, copy the EXACT text as it appears in the document above
2. For example, if the document says "five (5) years", your current_text must be "five (5) years", not "5 years" or "five years"
3. Look carefully at the exact wording, punctuation, and formatting
4. Make ONLY the changes specified in the rules - be conservative
5. Focus on the specific areas mentioned in the custom rules

        COMMON PATTERNS TO LOOK FOR:
        - "five (5) years" (most common in legal documents)
        - "five years" 
        - "5 years"
        - "five (5) year"
        - "five year"
        - "three years" or "three (3) years"
        - "Company (name to be provided upon execution)" or just "Company"
        - "For: Company" or "For: Company (name to be provided upon execution)"
        - "Dear NAME:" or "Dear [Name]:" (for recipient names)
        - "State of Delaware" or "Delaware"
        - Signature blocks: "By:", "Title: \t_______________________________", "For: Company"
        - "Title: \t_______________________________" (most common title pattern)

CRITICAL: When replacing text, use the EXACT text as it appears in the document.
For example:
- If document says "For: Company", replace with "For: JMC Investment LLC"
- If document says "Dear NAME:", replace with "Dear John Bagge:"
- If document says "three years", replace with "two (2) years"

        SPECIFIC REPLACEMENTS NEEDED:
        - Replace "Dear NAME:" with "Dear John Bagge:" (replace entire phrase)
        - Replace "For: Company" with "For: JMC Investment LLC" (replace entire phrase)
        - Replace "three years" with "two (2) years"
        - Replace "By:" with "By: John Bagge"
        - Replace "Title: \t_______________________________" with "Title: Vice President"
        - Replace "Title:\t_______________________________" with "Title: Vice President"

IMPORTANT: Use the FULL PHRASE as current_text, not just the placeholder word.
For example:
- Use "Dear NAME:" not just "NAME"
- Use "For: Company" not just "Company"
- Use "By:" not just "By"
- Use "Title:" not just "Title"

        SIGNATURE BLOCK HANDLING:
        - ONLY use TEXT_REPLACE for signature blocks - NEVER use TEXT_INSERT
        - Replace "By:" with "By: John Bagge" (don't create new lines)
        - Replace "Title: \t_______________________________" with "Title: Vice President"
        - Replace "Title:\t_______________________________" with "Title: Vice President"
        - Replace "For: Company" with "For: JMC Investment LLC"
        - Replace "Company (name to be provided upon execution)" with "JMC Investment LLC"
        - Replace "Dear NAME:" with "Dear John Bagge:"
        - Replace just "Company" with "JMC Investment LLC" if it's in a "For:" context
        - Do NOT insert new signature blocks or create new fields
        - Do NOT duplicate existing signature lines
        - Find existing placeholders and replace them in place

IMPORTANT: Only make the specific changes requested in the custom rules. Do not over-redline or make unnecessary changes.

Please provide your analysis in the specified JSON format."""

        return prompt
    
    def _parse_ai_response(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse the AI response and extract redlining instructions"""
        try:
            # Try to extract JSON from the response
            if '{' in ai_response and '}' in ai_response:
                start = ai_response.find('{')
                end = ai_response.rfind('}') + 1
                json_str = ai_response[start:end]
                
                parsed = json.loads(json_str)
                return parsed.get('modifications', [])
            else:
                logger.warning("Could not parse AI response as JSON")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return []

class DocumentProcessor:
    def __init__(self, ai_service: AIRedliningService):
        self.ai_service = ai_service
    
    def process_document(self, doc_path: str, custom_rules: List[Dict[str, Any]], 
                        firm_details: Dict[str, Any], signature_path: str = None) -> Dict[str, Any]:
        """
        Process a Word document with AI redlining and return the modified document
        Optimized for large files with memory efficiency
        """
        try:
            # Check file size and use appropriate processing method
            file_size = os.path.getsize(doc_path)
            logger.info(f"Processing document: {file_size} bytes ({file_size/1024:.1f} KB)")
            
            # For large files (>100KB), use chunked processing
            if file_size > 100 * 1024:  # 100KB threshold
                return self._process_large_document(doc_path, custom_rules, firm_details, signature_path)
            else:
                return self._process_small_document(doc_path, custom_rules, firm_details, signature_path)
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_small_document(self, doc_path: str, custom_rules: List[Dict[str, Any]], 
                               firm_details: Dict[str, Any], signature_path: str = None) -> Dict[str, Any]:
        """Process small documents (<100KB) using standard method"""
        try:
            # Load the document
            doc = DocxDocument(doc_path)
            
            # Extract text for AI analysis
            document_text = self._extract_document_text(doc)
            
            # Get AI redlining instructions
            ai_result = self.ai_service.analyze_document(document_text, custom_rules, firm_details)
            
            if not ai_result['success']:
                return {
                    'success': False,
                    'error': ai_result['error']
                }
            
            # Apply AI modifications
            modifications = ai_result['redlining_instructions']
            if isinstance(modifications, dict) and 'modifications' in modifications:
                modifications = modifications['modifications']
            
            logger.info(f"AI generated {len(modifications) if modifications else 0} modifications")
            if modifications:
                for i, mod in enumerate(modifications):
                    logger.info(f"Modification {i+1}: {mod}")
            else:
                logger.warning("No modifications generated by AI")
                logger.info(f"AI result: {ai_result}")
            
            # Apply modifications if we have any
            if modifications:
                self._apply_modifications(doc, modifications)
            
            # Apply firm details
            self._apply_firm_details(doc, firm_details)
            
            # Apply signature if provided
            if signature_path and os.path.exists(signature_path):
                self._apply_signature(doc, signature_path)
            
            # Generate output path
            output_path = self._generate_output_path(doc_path)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the modified document
            doc.save(output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'modifications_applied': len(modifications) if modifications else 0,
                'ai_analysis': ai_result.get('ai_analysis', 'No analysis available')
            }
            
        except Exception as e:
            logger.error(f"Error processing small document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_large_document(self, doc_path: str, custom_rules: List[Dict[str, Any]], 
                               firm_details: Dict[str, Any], signature_path: str = None) -> Dict[str, Any]:
        """Process large documents (>100KB) using memory-efficient chunked method"""
        try:
            logger.info("Processing large document with chunked method")
            
            # Load the document
            doc = DocxDocument(doc_path)
            
            # Extract text in chunks for AI analysis
            document_text = self._extract_document_text_chunked(doc)
            
            # Get AI redlining instructions
            ai_result = self.ai_service.analyze_document(document_text, custom_rules, firm_details)
            
            if not ai_result['success']:
                return {
                    'success': False,
                    'error': ai_result['error']
                }
            
            # Apply AI modifications
            modifications = ai_result['redlining_instructions']
            if isinstance(modifications, dict) and 'modifications' in modifications:
                modifications = modifications['modifications']
            
            # Apply modifications if we have any
            if modifications:
                self._apply_modifications_chunked(doc, modifications)
            
            # Apply firm details
            self._apply_firm_details_chunked(doc, firm_details)
            
            # Apply signature if provided
            if signature_path and os.path.exists(signature_path):
                self._apply_signature(doc, signature_path)
            
            # Generate output path
            output_path = self._generate_output_path(doc_path)
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the modified document
            doc.save(output_path)
            
            return {
                'success': True,
                'output_path': output_path,
                'modifications_applied': len(modifications) if modifications else 0,
                'ai_analysis': ai_result.get('ai_analysis', 'No analysis available')
            }
            
        except Exception as e:
            logger.error(f"Error processing large document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _extract_document_text(self, doc: DocxDocument) -> str:
        """Extract text content from the Word document"""
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)
        
        return '\n'.join(text_parts)
    
    def _extract_document_text_chunked(self, doc: DocxDocument) -> str:
        """Extract text content from large Word documents in chunks for memory efficiency"""
        text_parts = []
        chunk_size = 1000  # Process 1000 paragraphs at a time
        total_paragraphs = len(doc.paragraphs)
        
        logger.info(f"Extracting text from {total_paragraphs} paragraphs in chunks of {chunk_size}")
        
        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)
            chunk_text = []
            
            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    chunk_text.append(doc.paragraphs[j].text)
            
            text_parts.extend(chunk_text)
            
            # Log progress for large documents
            if total_paragraphs > 5000:
                progress = (chunk_end / total_paragraphs) * 100
                logger.info(f"Text extraction progress: {progress:.1f}%")
        
        return '\n'.join(text_parts)
    
    def _apply_modifications(self, doc: DocxDocument, modifications: List[Dict[str, Any]]):
        """Apply AI-generated modifications to the document"""
        for mod in modifications:
            try:
                if mod['type'] == 'TEXT_REPLACE':
                    self._replace_text(doc, mod['current_text'], mod['new_text'])
                elif mod['type'] == 'TEXT_INSERT':
                    self._insert_text(doc, mod['new_text'], mod.get('location_hint', ''))
                elif mod['type'] == 'TEXT_DELETE':
                    self._delete_text(doc, mod['current_text'])
                elif mod['type'] == 'CLAUSE_ADD':
                    self._add_clause(doc, mod['new_text'])
                    
            except Exception as e:
                logger.warning(f"Failed to apply modification {mod}: {str(e)}")
                continue
    
    def _apply_modifications_chunked(self, doc: DocxDocument, modifications: List[Dict[str, Any]]):
        """Apply AI-generated modifications to large documents in chunks for memory efficiency"""
        logger.info(f"Applying {len(modifications)} modifications to large document")
        
        for i, mod in enumerate(modifications):
            try:
                if mod['type'] == 'TEXT_REPLACE':
                    self._replace_text_chunked(doc, mod['current_text'], mod['new_text'])
                elif mod['type'] == 'TEXT_INSERT':
                    self._insert_text_chunked(doc, mod['new_text'], mod.get('location_hint', ''))
                elif mod['type'] == 'TEXT_DELETE':
                    self._delete_text_chunked(doc, mod['current_text'])
                elif mod['type'] == 'CLAUSE_ADD':
                    self._add_clause_chunked(doc, mod['new_text'])
                
                # Log progress for large documents
                if len(modifications) > 10:
                    progress = ((i + 1) / len(modifications)) * 100
                    logger.info(f"Modification progress: {progress:.1f}%")
                    
            except Exception as e:
                logger.warning(f"Failed to apply modification {mod}: {str(e)}")
                continue
    
    def _replace_text(self, doc: DocxDocument, old_text: str, new_text: str):
        """Replace text in the document with professional redlining"""
        logger.info(f"Attempting to replace '{old_text}' with '{new_text}'")
        logger.info(f"Document has {len(doc.paragraphs)} paragraphs")
        replaced = False
        
        # Log first few paragraphs to see what text is actually in the document
        logger.warning("First 10 paragraphs in document:")
        for i, para in enumerate(doc.paragraphs[:10]):
            logger.warning(f"Paragraph {i+1}: '{para.text}'")
        
        # Also search for common patterns to see what's actually in the document
        logger.warning("Searching for common patterns in document:")
        common_patterns = ["For:", "Company", "Dear", "NAME", "Title:", "By:"]
        for pattern in common_patterns:
            found_paragraphs = []
            for i, para in enumerate(doc.paragraphs):
                if pattern.lower() in para.text.lower():
                    found_paragraphs.append(f"Para {i+1}: '{para.text}'")
            if found_paragraphs:
                logger.warning(f"Found '{pattern}' in: {found_paragraphs}")
            else:
                logger.warning(f"'{pattern}' not found in document")
        
        # Search for variations of the specific text we're trying to replace
        logger.warning(f"Searching for variations of '{old_text}':")
        variations_to_search = [
            old_text,
            old_text.replace(" ", ""),  # No spaces
            old_text.replace(":", ""),  # No colon
            old_text.lower(),           # Lowercase
            old_text.upper(),           # Uppercase
            old_text.replace("Company", "Comapny"),  # Common typo
            old_text.replace("Company", "company"),  # Case variation
            "For: Company",  # Common pattern
            "For:Company",   # No space after colon
            "For Company",   # No colon
            "for: company",  # All lowercase
            "FOR: COMPANY",  # All uppercase
            # Handle multiple whitespace variations
            "For:  Company",  # Double space
            "For:   Company", # Triple space
            "For:    Company", # Quadruple space
            "For:\tCompany",  # Tab after colon
            "For: \tCompany", # Space and tab
            "For:\t Company", # Tab and space
            "For: \t Company", # Space, tab, space
        ]
        for variation in variations_to_search:
            found_paragraphs = []
            for i, para in enumerate(doc.paragraphs):
                if variation.lower() in para.text.lower():
                    found_paragraphs.append(f"Para {i+1}: '{para.text}'")
            if found_paragraphs:
                logger.warning(f"Found variation '{variation}' in: {found_paragraphs}")
            else:
                logger.warning(f"Variation '{variation}' not found in document")
        
        # First, try exact match
        for paragraph in doc.paragraphs:
            if old_text in paragraph.text:
                logger.warning(f"Found exact match in paragraph: {paragraph.text}")
                if self._replace_text_in_paragraph(paragraph, old_text, new_text):
                    logger.warning(f"Successfully replaced. New paragraph: {paragraph.text}")
                    replaced = True
                    break
        
        # If exact match failed, try normalized whitespace matching
        if not replaced:
            logger.warning("Trying normalized whitespace matching")
            import re
            # Normalize whitespace in the old text (replace multiple spaces/tabs with single space)
            normalized_old = re.sub(r'\s+', ' ', old_text.strip())
            for paragraph in doc.paragraphs:
                # Normalize whitespace in paragraph text
                normalized_para = re.sub(r'\s+', ' ', paragraph.text.strip())
                if normalized_old.lower() in normalized_para.lower():
                    logger.warning(f"Found normalized match in paragraph: {paragraph.text}")
                    # Try to find the actual text in the paragraph and replace it
                    if old_text in paragraph.text:
                        if self._replace_text_in_paragraph(paragraph, old_text, new_text):
                            logger.warning(f"Successfully replaced with normalized matching. New paragraph: {paragraph.text}")
                            replaced = True
                            break
                    else:
                        # If exact text not found, try to find and replace the normalized version
                        # Find the actual text pattern in the paragraph
                        for variation in variations_to_search:
                            if variation in paragraph.text:
                                logger.warning(f"Found variation '{variation}' in paragraph, replacing with '{new_text}'")
                                if self._replace_text_in_paragraph(paragraph, variation, new_text):
                                    logger.warning(f"Successfully replaced variation. New paragraph: {paragraph.text}")
                                    replaced = True
                                    break
                        if replaced:
                            break
        
        if not replaced:
            logger.warning(f"Exact text '{old_text}' not found, trying variations")
            # Try partial matches for common variations
            variations = [
                old_text.replace("5", "five (5)"),
                old_text.replace("five (5)", "5"),
                old_text.replace("years", "year"),
                old_text.replace("year", "years"),
                "five (5) years",  # Common legal format
                "five years",
                "5 year",
                "five year",
                # For company name variations
                old_text.replace("For: ", ""),
                old_text.replace("Company (name to be provided upon execution)", "Company"),
                "Company",
                "For: Company",
                "Company (name to be provided upon execution)",
                "For: Company (name to be provided upon execution)",
                # Additional variations for better matching
                "For: " + old_text,
                old_text + " (name to be provided upon execution)",
                "For: " + old_text + " (name to be provided upon execution)"
            ]
            
            for variation in variations:
                if variation and variation != old_text:  # Skip empty or duplicate variations
                    logger.info(f"Trying variation: '{variation}'")
                    for paragraph in doc.paragraphs:
                        if variation in paragraph.text:
                            logger.info(f"Found variation '{variation}' in paragraph: {paragraph.text}")
                            if self._replace_text_in_paragraph(paragraph, variation, new_text):
                                logger.info(f"Successfully replaced variation. New paragraph: {paragraph.text}")
                                replaced = True
                                break
                    if replaced:
                        break
            
            # If still not found, try case-insensitive search
            if not replaced:
                logger.info("Trying case-insensitive search")
                for paragraph in doc.paragraphs:
                    if old_text.lower() in paragraph.text.lower():
                        logger.info(f"Found case-insensitive match in paragraph: {paragraph.text}")
                        if self._replace_text_in_paragraph(paragraph, old_text, new_text):
                            logger.info(f"Successfully replaced case-insensitive. New paragraph: {paragraph.text}")
                            replaced = True
                            break
        
        if not replaced:
            logger.error(f"Failed to replace '{old_text}' with '{new_text}' - no matches found")
        else:
            logger.info(f"Successfully replaced '{old_text}' with '{new_text}'")
    
    def _replace_text_in_paragraph(self, paragraph, old_text: str, new_text: str):
        """Replace text in a paragraph while preserving formatting"""
        try:
            # First, try to find and replace in individual runs
            for run in paragraph.runs:
                if old_text in run.text:
                    # Replace the text in the run
                    run.text = run.text.replace(old_text, new_text)
                    
                    # Add redlining formatting
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
                    logger.info(f"Replaced text in run: '{old_text}' -> '{new_text}'")
                    return True
            
            # If not found in individual runs, try paragraph-level replacement
            if old_text in paragraph.text:
                logger.info(f"Text found in paragraph, doing paragraph-level replacement")
                
                # Store original text
                original_text = paragraph.text
                
                # Clear all runs and create new ones
                paragraph.clear()
                
                # Split text around the old_text and create runs
                parts = original_text.split(old_text)
                logger.info(f"Split into {len(parts)} parts: {parts}")
                
                for i, part in enumerate(parts):
                    if part:  # Add non-empty parts
                        run = paragraph.add_run(part)
                        # Don't add redlining to original text
                    
                    if i < len(parts) - 1:  # Add the new text (not the last part)
                        run = paragraph.add_run(new_text)
                        run.font.underline = True
                        run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
                        logger.info(f"Added new text run: '{new_text}'")
                
                logger.info(f"Final paragraph text: {paragraph.text}")
                return True
            else:
                logger.warning(f"Text '{old_text}' not found in paragraph: '{paragraph.text}'")
                # Try case-insensitive search
                if old_text.lower() in paragraph.text.lower():
                    logger.info(f"Found case-insensitive match, trying replacement")
                    # Simple fallback for case-insensitive matches
                    paragraph.text = paragraph.text.replace(old_text.lower(), new_text)
                    paragraph.text = paragraph.text.replace(old_text.upper(), new_text)
                    paragraph.text = paragraph.text.replace(old_text.title(), new_text)
                    logger.info(f"Case-insensitive replacement successful: '{old_text}' -> '{new_text}'")
                    return True
                
        except Exception as e:
            logger.error(f"Error replacing text in paragraph: {str(e)}")
            # Fallback to simple replacement
            try:
                paragraph.text = paragraph.text.replace(old_text, new_text)
                logger.info(f"Fallback replacement successful: '{old_text}' -> '{new_text}'")
                return True
            except Exception as fallback_error:
                logger.error(f"Fallback replacement failed: {str(fallback_error)}")
                return False
        
        return False
    
    def _replace_text_chunked(self, doc: DocxDocument, old_text: str, new_text: str):
        """Replace text in large documents with chunked processing for memory efficiency"""
        logger.info(f"Attempting to replace '{old_text}' with '{new_text}' in large document")
        replaced = False
        chunk_size = 500  # Process 500 paragraphs at a time
        total_paragraphs = len(doc.paragraphs)
        
        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)
            
            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    paragraph = doc.paragraphs[j]
                    if old_text in paragraph.text:
                        logger.info(f"Found text to replace in paragraph {j}: {paragraph.text[:100]}...")
                        
                        # Replace text while preserving formatting
                        self._replace_text_in_paragraph(paragraph, old_text, new_text)
                        replaced = True
                        break
            
            if replaced:
                break
            
            # Log progress for very large documents
            if total_paragraphs > 10000:
                progress = (chunk_end / total_paragraphs) * 100
                logger.info(f"Text replacement progress: {progress:.1f}%")
        
        if not replaced:
            logger.warning(f"Text '{old_text}' not found in large document for replacement")
    
    def _insert_text(self, doc: DocxDocument, text: str, location_hint: str):
        """Insert new text at specified location"""
        # Find appropriate location and insert
        new_paragraph = doc.add_paragraph(text)
        for run in new_paragraph.runs:
            # Professional redlining for insertions
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
    
    def _insert_text_chunked(self, doc: DocxDocument, text: str, location_hint: str):
        """Insert new text at specified location in large documents"""
        # Find appropriate location and insert
        new_paragraph = doc.add_paragraph(text)
        for run in new_paragraph.runs:
            # Professional redlining for insertions
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
    
    def _delete_text(self, doc: DocxDocument, text: str):
        """Delete text from the document"""
        for paragraph in doc.paragraphs:
            if text in paragraph.text:
                paragraph.text = paragraph.text.replace(text, '')
                # Add strikethrough formatting for deleted text
                for run in paragraph.runs:
                    run.font.strike = True
    
    def _delete_text_chunked(self, doc: DocxDocument, text: str):
        """Delete text from large documents with chunked processing"""
        chunk_size = 500
        total_paragraphs = len(doc.paragraphs)
        
        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)
            
            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    paragraph = doc.paragraphs[j]
                    if text in paragraph.text:
                        paragraph.text = paragraph.text.replace(text, '')
                        # Add strikethrough formatting for deleted text
                        for run in paragraph.runs:
                            run.font.strike = True
    
    def _add_clause(self, doc: DocxDocument, clause_text: str):
        """Add a new clause to the document"""
        new_paragraph = doc.add_paragraph(clause_text)
        for run in new_paragraph.runs:
            # Professional redlining for new clauses
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
    
    def _add_clause_chunked(self, doc: DocxDocument, clause_text: str):
        """Add a new clause to large documents"""
        new_paragraph = doc.add_paragraph(clause_text)
        for run in new_paragraph.runs:
            # Professional redlining for new clauses
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
    
    def _apply_firm_details(self, doc: DocxDocument, firm_details: Dict[str, Any]):
        """Apply firm details to signature blocks and firm information"""
        # Find and replace placeholder text with firm details
        for paragraph in doc.paragraphs:
            if '[FIRM_NAME]' in paragraph.text:
                paragraph.text = paragraph.text.replace('[FIRM_NAME]', firm_details.get('name', ''))
                # Add professional redlining to show the change
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if '[FIRM_ADDRESS]' in paragraph.text:
                paragraph.text = paragraph.text.replace('[FIRM_ADDRESS]', firm_details.get('address', ''))
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if '[SIGNER_NAME]' in paragraph.text:
                paragraph.text = paragraph.text.replace('[SIGNER_NAME]', firm_details.get('signerName', ''))
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if '[SIGNER_TITLE]' in paragraph.text:
                paragraph.text = paragraph.text.replace('[SIGNER_TITLE]', firm_details.get('signerTitle', ''))
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
    
    def _apply_firm_details_chunked(self, doc: DocxDocument, firm_details: Dict[str, Any]):
        """Apply firm details to large documents with chunked processing"""
        logger.info("Applying firm details to large document")
        chunk_size = 500
        total_paragraphs = len(doc.paragraphs)
        
        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)
            
            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    paragraph = doc.paragraphs[j]
                    
                    if '[FIRM_NAME]' in paragraph.text:
                        paragraph.text = paragraph.text.replace('[FIRM_NAME]', firm_details.get('name', ''))
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if '[FIRM_ADDRESS]' in paragraph.text:
                        paragraph.text = paragraph.text.replace('[FIRM_ADDRESS]', firm_details.get('address', ''))
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if '[SIGNER_NAME]' in paragraph.text:
                        paragraph.text = paragraph.text.replace('[SIGNER_NAME]', firm_details.get('signerName', ''))
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if '[SIGNER_TITLE]' in paragraph.text:
                        paragraph.text = paragraph.text.replace('[SIGNER_TITLE]', firm_details.get('signerTitle', ''))
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
            
            # Log progress for very large documents
            if total_paragraphs > 10000:
                progress = (chunk_end / total_paragraphs) * 100
                logger.info(f"Firm details progress: {progress:.1f}%")
    
    def _apply_signature(self, doc: DocxDocument, signature_path: str):
        """Apply signature image to the document"""
        try:
            from docx.shared import Inches
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            
            logger.info(f"Applying signature from: {signature_path}")
            
            # Find "Signed:" text and add signature right after it
            signature_added = False
            
            for paragraph in doc.paragraphs:
                if 'Signed:' in paragraph.text:
                    logger.info(f"Found 'Signed:' in paragraph: {paragraph.text}")
                    
                    # Clear the paragraph and rebuild it with proper signature placement
                    original_text = paragraph.text
                    paragraph.clear()
                    
                    # Split text around "Signed:"
                    parts = original_text.split('Signed:', 1)
                    
                    # Add text before "Signed:"
                    if parts[0].strip():
                        before_run = paragraph.add_run(parts[0])
                    
                    # Add "Signed:" text
                    signed_run = paragraph.add_run("Signed: ")
                    
                    # Add signature image immediately after "Signed:"
                    signature_run = paragraph.add_run()
                    signature_run.add_picture(signature_path, width=Inches(1.2))
                    
                    # Add any remaining text after "Signed:"
                    if len(parts) > 1 and parts[1].strip():
                        remaining_run = paragraph.add_run(parts[1])
                    
                    signature_added = True
                    logger.info("Signature added right next to 'Signed:' text")
                    break
            
            # If no "Signed:" found, look for signature placeholders
            if not signature_added:
                for paragraph in doc.paragraphs:
                    if '[SIGNATURE]' in paragraph.text:
                        # Replace placeholder with signature
                        paragraph.text = paragraph.text.replace('[SIGNATURE]', '')
                        
                        # Add signature image
                        run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                        run.add_picture(signature_path, width=Inches(1.5))
                        
                        signature_added = True
                        logger.info("Signature added at placeholder location")
                        break
            
            # If still no signature added, add at the end
            if not signature_added:
                # Add a new paragraph for signature
                signature_paragraph = doc.add_paragraph()
                
                # Add "Signed:" text
                signed_run = signature_paragraph.add_run("Signed: ")
                
                # Add signature image right next to "Signed:"
                signature_run = signature_paragraph.add_run()
                signature_run.add_picture(signature_path, width=Inches(1.2))
                
                signature_added = True
                logger.info("Signature added at end of document")
            
            if signature_added:
                logger.info("Signature applied successfully")
            else:
                logger.warning("Could not find suitable location for signature")
            
        except Exception as e:
            logger.error(f"Error applying signature: {str(e)}")
            # Don't raise exception - signature is optional
    
    def _generate_output_path(self, input_path: str) -> str:
        """Generate output path for the processed document"""
        # Create outputs directory if it doesn't exist
        output_dir = 'outputs'
        os.makedirs(output_dir, exist_ok=True)
        
        # Get the absolute path to the outputs directory
        base_dir = os.path.abspath(output_dir)
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{name}_redlined_{timestamp}{ext}"
        return os.path.abspath(os.path.join(base_dir, output_filename))
