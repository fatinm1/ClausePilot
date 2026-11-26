import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from docx import Document as DocxDocument
from docx.oxml.shared import OxmlElement, qn
from docx.shared import RGBColor
from openai import OpenAI

logger = logging.getLogger(__name__)


# Free, OpenAI-compatible providers are tried first; paid OpenAI only if a key is set.
# Each entry: (name, api-key env var, base URL, model env var, default model)
PROVIDERS = {
    "groq": (
        "GROQ_API_KEY",
        "https://api.groq.com/openai/v1",
        "GROQ_MODEL",
        # tried in order; models a provider has retired are skipped automatically
        "openai/gpt-oss-120b,llama-3.3-70b-versatile,openai/gpt-oss-20b,llama-3.1-8b-instant",
    ),
    "gemini": (
        "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GEMINI_MODEL",
        "gemini-flash-latest,gemini-2.5-flash",
    ),
    "openrouter": (
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_MODEL",
        "openai/gpt-oss-120b:free,meta-llama/llama-3.3-70b-instruct:free",
    ),
    "openai": ("OPENAI_API_KEY", None, "OPENAI_MODEL", "gpt-4o-mini"),
}
DEFAULT_PROVIDER_ORDER = "groq,gemini,openrouter,openai"
PLACEHOLDER_KEYS = {"", "mock-key-for-development", "your-openai-api-key"}


class AIRedliningService:
    def __init__(self):
        """Build the chain of LLM providers from environment variables.

        Providers are tried in LLM_PROVIDER_ORDER (default: groq, gemini,
        openrouter, openai). A provider is used only if its API key is set.
        If none are configured, or every call fails, the rule-based mock
        analysis runs instead, so a review always completes.
        """
        self.providers: list[tuple[str, Any, str]] = []
        order = os.getenv("LLM_PROVIDER_ORDER", DEFAULT_PROVIDER_ORDER)
        for name in [n.strip().lower() for n in order.split(",") if n.strip()]:
            if name not in PROVIDERS:
                logger.warning(f"Unknown LLM provider '{name}' in LLM_PROVIDER_ORDER")
                continue
            key_env, base_url, model_env, default_model = PROVIDERS[name]
            api_key = (os.getenv(key_env) or "").strip()
            if api_key in PLACEHOLDER_KEYS:
                continue
            models = [
                m.strip()
                for m in (os.getenv(model_env) or default_model).split(",")
                if m.strip()
            ]
            try:
                kwargs = {"api_key": api_key, "max_retries": 1, "timeout": 90}
                if base_url:
                    kwargs["base_url"] = base_url
                self.providers.append((name, OpenAI(**kwargs), models))
                logger.info(f"LLM provider enabled: {name} ({', '.join(models)})")
            except Exception as init_error:
                logger.error(f"Could not initialise {name}: {init_error}")

        if self.providers:
            _, self.client, models = self.providers[0]
            self.model = models[0]
        else:
            self.client = None
            self.model = "rule-based"
            logger.warning("No LLM provider configured; using rule-based analysis")

    def _complete(self, messages: list[dict[str, str]], json_mode: bool = False):
        """Call each configured provider in order; return (provider, response)."""
        last_error = None
        for name, client, models in self.providers:
            while models:
                model = models[0]
                retired = False
                for use_json in [True, False] if json_mode else [False]:
                    try:
                        logger.warning(f"Calling LLM provider {name} ({model})")
                        kwargs = {
                            "model": model,
                            "messages": messages,
                            "temperature": 0,
                            "max_tokens": 4000,
                        }
                        if use_json:
                            kwargs["response_format"] = {"type": "json_object"}
                        response = client.chat.completions.create(**kwargs)
                        if response.choices and response.choices[0].message.content:
                            self.model = model
                            return name, response
                        last_error = RuntimeError("empty response")
                        break
                    except Exception as api_error:
                        last_error = api_error
                        msg = str(api_error).lower()
                        logger.error(
                            f"LLM provider {name} ({model}) failed: {api_error}"
                        )
                        if (
                            "model_not_found" in msg
                            or "does not exist" in msg
                            or "decommissioned" in msg
                        ):
                            retired = True
                            break
                        # retry without JSON mode only if the provider rejected that option
                        if not (
                            use_json and ("response_format" in msg or "json" in msg)
                        ):
                            break
                if retired:
                    logger.warning(
                        f"{name}: model {model} unavailable, trying the next one"
                    )
                    models.pop(0)
                    continue
                break
        raise RuntimeError(f"All LLM providers failed: {last_error}")

    def _llm_text(self, messages: list[dict[str, str]]) -> str:
        _, response = self._complete(messages, json_mode=True)
        return response.choices[0].message.content

    @staticmethod
    def normalize_firm(firm_details: dict | None) -> dict:
        """Accept both the web app's keys and older backend keys."""
        f = dict(firm_details or {})
        aliases = {
            "name": ["firm_name", "company", "company_name"],
            "signerName": ["signatory_name", "signer_name", "signer"],
            "signerTitle": ["title", "signer_title", "signatory_title"],
            "zipCode": ["zip_code", "zip"],
        }
        for key, alts in aliases.items():
            if not f.get(key):
                for a in alts:
                    if f.get(a):
                        f[key] = f[a]
                        break
        return f

    def plan_changes(
        self, paragraphs: list[str], custom_rules: list[dict], firm_details: dict | None
    ):
        """Plan tracked changes for a document given as a list of paragraphs."""
        from .redline_engine import plan_changes

        llm = self._llm_text if self.providers else None
        return plan_changes(
            paragraphs, custom_rules or [], self.normalize_firm(firm_details), llm
        )

    def analyze_document(
        self,
        document_text: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any] = None,
    ) -> dict[str, Any]:
        """Plan redlines for plain document text (one paragraph per line)."""
        try:
            changes, notes = self.plan_changes(
                document_text.split("\n"), custom_rules, firm_details
            )
            summary = f"{len(changes)} change(s) proposed"
            if notes:
                summary += ". Not applied: " + "; ".join(notes)
            return {
                "success": True,
                "redlining_instructions": {"modifications": changes},
                "ai_analysis": summary,
            }
        except Exception as e:
            logger.exception("Planning failed")
            return {"success": False, "error": str(e)}

    def _mock_analysis(
        self,
        document_text: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any] = None,
    ) -> dict[str, Any]:
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
            if "title" in firm_details:
                logger.warning(f"Title from firm details: '{firm_details['title']}'")
            else:
                logger.warning("No 'title' key in firm details")
        else:
            logger.warning("No firm details provided to mock analysis")

        # Check if title field exists in document
        if "Title:" in document_text:
            logger.warning("Found 'Title:' in document text")
            if "Title: \t_______________________________" in document_text:
                logger.warning(
                    "Found 'Title: \t_______________________________' pattern in document"
                )
            else:
                logger.warning(
                    "'Title: \t_______________________________' pattern not found in document"
                )
        else:
            logger.warning("'Title:' not found in document text")

        # Look for company name patterns in the document
        company_patterns = [
            "Company (name to be provided upon execution)",
            "For: Company (name to be provided upon execution)",
            "For: Company",
            "Company",
        ]

        if firm_details and "firm_name" in firm_details:
            for pattern in company_patterns:
                if pattern in document_text:
                    if pattern.startswith("For:"):
                        new_text = pattern.replace("Company", firm_details["firm_name"])
                    else:
                        new_text = f"For: {firm_details['firm_name']}"

                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "parties",
                            "current_text": pattern,
                            "new_text": new_text,
                            "reason": "Replace company placeholder with actual firm name",
                            "location_hint": "Parties section",
                        }
                    )
                    logger.info(f"Found company pattern: '{pattern}' -> '{new_text}'")
                    break
            else:
                # If no patterns found, add a generic company replacement
                logger.info(
                    "No company patterns found, adding generic company replacement"
                )
                mock_modifications.append(
                    {
                        "type": "TEXT_REPLACE",
                        "section": "parties",
                        "current_text": "Company",
                        "new_text": f"For: {firm_details['firm_name']}",
                        "reason": "Replace company placeholder with actual firm name",
                        "location_hint": "Parties section",
                    }
                )

            # Look for signature patterns
            if "signatory_name" in firm_details:
                if (
                    "By:" in document_text
                    and firm_details["signatory_name"] not in document_text
                ):
                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "signatures",
                            "current_text": "By:",
                            "new_text": f"By: {firm_details['signatory_name']}",
                            "reason": "Replace signer placeholder with actual name",
                            "location_hint": "Signature block",
                        }
                    )
                    logger.info(
                        f"Added signer replacement: 'By:' -> 'By: {firm_details['signatory_name']}'"
                    )

            if "title" in firm_details:
                logger.warning(f"Processing title field: '{firm_details['title']}'")
                # Look for Title: with various formatting patterns
                title_patterns = [
                    "Title: \t_______________________________",
                    "Title:\t_______________________________",
                    "Title:_______________________________",
                    "Title:",
                    "Title: \t",
                    "Title:\t",
                ]

                for title_pattern in title_patterns:
                    logger.warning(f"Checking title pattern: '{title_pattern}'")
                    if title_pattern in document_text:
                        logger.warning(
                            f"Found title pattern '{title_pattern}' in document"
                        )
                        if firm_details["title"] not in document_text:
                            logger.warning(
                                f"Title '{firm_details['title']}' not in document, adding replacement"
                            )
                            mock_modifications.append(
                                {
                                    "type": "TEXT_REPLACE",
                                    "section": "signatures",
                                    "current_text": title_pattern,
                                    "new_text": f"Title: {firm_details['title']}",
                                    "reason": "Replace title placeholder with actual title",
                                    "location_hint": "Signature block",
                                }
                            )
                            logger.warning(
                                f"Added title replacement: '{title_pattern}' -> 'Title: {firm_details['title']}'"
                            )
                            break
                        else:
                            logger.warning(
                                f"Title '{firm_details['title']}' already in document, skipping replacement"
                            )
                    else:
                        logger.warning(
                            f"Title pattern '{title_pattern}' not found in document"
                        )
            else:
                logger.warning(
                    "No 'title' key in firm_details, skipping title replacement"
                )

        for rule in custom_rules:
            rule_name = rule.get("name", "").lower()
            rule_instruction = rule.get("instruction", "")
            logger.info(f"Processing rule: {rule_name}")

            # Create specific modifications based on rule type
            if (
                "duration" in rule_name
                or "term" in rule_name
                or "confidentiality" in rule_name
            ):
                # Extract target duration from rule instruction
                import re

                target_years = 2  # Default fallback

                # Try to extract number from instruction (e.g., "Change to 5 years" → 5)
                year_match = re.search(
                    r"(\d+)\s*(?:\(\d+\))?\s*years?", rule_instruction, re.IGNORECASE
                )
                if year_match:
                    target_years = int(year_match.group(1))
                    logger.info(
                        f"📅 Extracted target duration: {target_years} years from instruction"
                    )
                else:
                    logger.warning(
                        f"⚠️ Could not extract duration from instruction '{rule_instruction}', using default: {target_years} years"
                    )

                # Build dynamic target pattern
                target_years_text = (
                    f"{target_years} ({target_years}) years"
                    if target_years > 0
                    else f"{target_years} years"
                )
                target_years_simple = f"{target_years} years"

                # Check if document already has the target duration - if so, skip modification
                target_patterns_in_doc = [
                    target_years_text.lower(),
                    target_years_simple.lower(),
                    f"{target_years} ({target_years}) year".lower(),  # singular
                    f"{target_years} year".lower(),  # singular
                ]

                # Also check word forms if target is 1-10
                word_to_num = {
                    1: "one",
                    2: "two",
                    3: "three",
                    4: "four",
                    5: "five",
                    6: "six",
                    7: "seven",
                    8: "eight",
                    9: "nine",
                    10: "ten",
                }
                if target_years in word_to_num:
                    word = word_to_num[target_years]
                    target_patterns_in_doc.extend(
                        [
                            f"{word} ({target_years}) years".lower(),
                            f"{word} years".lower(),
                        ]
                    )

                # Look for various year patterns in the document and replace with target
                # Note: We check for target patterns AFTER looking for patterns to replace,
                # so we can still replace other year patterns even if target already exists
                year_patterns = [
                    ("five (5) years", target_years_text),
                    ("5 years", target_years_simple),
                    ("three (3) years", target_years_text),
                    ("3 years", target_years_simple),
                    ("four (4) years", target_years_text),
                    ("4 years", target_years_simple),
                    ("ten (10) years", target_years_text),
                    ("10 years", target_years_simple),
                    ("seven (7) years", target_years_text),
                    ("7 years", target_years_simple),
                    ("three years", target_years_text),
                    ("five years", target_years_text),
                    ("seven years", target_years_text),
                    ("ten years", target_years_text),
                ]

                found_pattern = False
                for current_pattern, new_pattern in year_patterns:
                    if current_pattern in document_text.lower():
                        # Double-check: don't replace if it's already the target
                        if (
                            current_pattern.lower() == target_years_text.lower()
                            or current_pattern.lower() == target_years_simple.lower()
                        ):
                            logger.info(
                                f"⚠️ Pattern '{current_pattern}' already matches target '{target_years_text}' - skipping this pattern"
                            )
                            found_pattern = (
                                True  # Mark as found but don't add modification
                            )
                            continue  # Skip this pattern but continue checking others

                        mock_modifications.append(
                            {
                                "type": "TEXT_REPLACE",
                                "section": "term",
                                "current_text": current_pattern,
                                "new_text": new_pattern,
                                "reason": rule_instruction,
                                "location_hint": "Confidentiality term section",
                            }
                        )
                        logger.info(
                            f"Found year pattern: {current_pattern} -> {new_pattern}"
                        )
                        found_pattern = True
                        # Don't break - continue to find all patterns that need changing

                if not found_pattern:
                    # If no specific patterns found, add a generic year modification
                    logger.info(
                        "No specific year patterns found, adding generic modification"
                    )
                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "term",
                            "current_text": "three years",
                            "new_text": target_years_text,
                            "reason": rule_instruction,
                            "location_hint": "Confidentiality term section",
                        }
                    )

            elif "liability" in rule_name or "damage" in rule_name:
                # Add liability cap clause
                mock_modifications.append(
                    {
                        "type": "TEXT_INSERT",
                        "section": "liability",
                        "new_text": "In no event shall either party be liable for any indirect, incidental, special, consequential, or punitive damages arising out of or relating to this Agreement.",
                        "reason": rule_instruction,
                        "location_hint": "After Section 8, Remedies",
                    }
                )

            elif "representatives" in rule_name or (
                "add" in rule_name and "parties" in rule_name
            ):
                # Handle "Add parties" rule - expand Representatives definition
                # Look for Representatives definition in the document
                import re

                representatives_patterns = [
                    r'("Representatives"|Representatives).*?\)',
                    r'collectively, "Representatives"',
                    r"collectively, \'Representatives\'",
                ]

                for pattern in representatives_patterns:
                    matches = list(
                        re.finditer(pattern, document_text, re.IGNORECASE | re.DOTALL)
                    )
                    if matches:
                        for match in matches:
                            current_text = match.group(0)
                            # Check if investors/financing sources are already mentioned
                            if (
                                "investors" not in current_text.lower()
                                and "potential financing sources"
                                not in current_text.lower()
                            ):
                                # Find where to insert - typically before the closing parenthesis
                                if current_text.endswith(")"):
                                    # Insert before the closing paren
                                    new_text = (
                                        current_text[:-1]
                                        + ", investors, and potential financing sources)"
                                    )
                                else:
                                    # Append to the end
                                    new_text = (
                                        current_text
                                        + ", investors, and potential financing sources"
                                    )

                                mock_modifications.append(
                                    {
                                        "type": "TEXT_REPLACE",
                                        "section": "definitions",
                                        "current_text": current_text,
                                        "new_text": new_text,
                                        "reason": rule_instruction,
                                        "location_hint": "Representatives definition section",
                                    }
                                )
                                logger.info(
                                    f"Found Representatives definition: '{current_text[:50]}...' -> '{new_text[:50]}...'"
                                )
                                break
                        if mock_modifications:  # If we added one, break outer loop
                            break

            elif (
                "retention" in rule_name
                or "carve" in rule_name
                or "retain" in rule_name
            ):
                # Handle "Retention carve-out" rule - add clause allowing electronic copy retention
                # Look for return/destroy sections where we can add the carve-out
                retention_clause = "Notwithstanding the foregoing, Recipient may retain an electronic copy of Confidential Information and notes if required under Recipient's document retention policy, provided that such retained materials remain subject to the confidentiality obligations set forth herein."

                # Look for common return/destroy section patterns
                return_section_patterns = [
                    "return.*promptly",
                    "destroy.*return",
                    "return.*all.*material",
                    "return.*evaluation.*material",
                ]

                found_return_section = False
                for pattern in return_section_patterns:
                    matches = list(re.finditer(pattern, document_text, re.IGNORECASE))
                    if matches:
                        # Find the paragraph containing this text
                        for match in matches:
                            # Get surrounding context (the paragraph)
                            start = max(0, match.start() - 200)
                            end = min(len(document_text), match.end() + 200)
                            context = document_text[start:end]

                            # Check if retention clause already exists
                            if (
                                "retention policy" not in context.lower()
                                and "electronic copy" not in context.lower()
                            ):
                                # Find the end of the sentence/paragraph to insert after
                                paragraph_end = document_text.find(".", match.end())
                                if paragraph_end == -1:
                                    paragraph_end = match.end() + 100

                                # Insert the retention clause
                                insertion_point = paragraph_end + 1
                                current_text = document_text[
                                    insertion_point : insertion_point + 50
                                ].strip()

                                mock_modifications.append(
                                    {
                                        "type": "TEXT_INSERT",
                                        "section": "return_of_materials",
                                        "new_text": retention_clause,
                                        "reason": rule_instruction,
                                        "location_hint": "After return/destroy section",
                                    }
                                )
                                logger.info(
                                    "Added retention carve-out clause after return section"
                                )
                                found_return_section = True
                                break
                        if found_return_section:
                            break

                if not found_return_section:
                    # If no return section found, add as a new clause
                    mock_modifications.append(
                        {
                            "type": "TEXT_INSERT",
                            "section": "miscellaneous",
                            "new_text": retention_clause,
                            "reason": rule_instruction,
                            "location_hint": "Before final clauses",
                        }
                    )
                    logger.info("Added retention carve-out clause as new insertion")

            elif (
                "firm" in rule_name
                or ("party" in rule_name and "add" not in rule_name)
                or ("name" in rule_name and "parties" not in rule_name)
            ):
                # Get firm details or use defaults
                firm_name = (
                    firm_details.get("firm_name", "Sample Company LLC")
                    if firm_details
                    else "Sample Company LLC"
                )
                signer_name = (
                    firm_details.get("signatory_name", "Sample Signer")
                    if firm_details
                    else "Sample Signer"
                )
                signer_title = (
                    firm_details.get("title", "Authorized Signatory")
                    if firm_details
                    else "Authorized Signatory"
                )

                # Look for party name patterns using firm details
                party_patterns = [
                    ("Company (name to be provided upon execution)", firm_name),
                    ("Recipient", f"{firm_name} (Recipient)"),
                    ("Receiving Party", f"{firm_name} (Recipient)"),
                ]

                for current_pattern, new_pattern in party_patterns:
                    if current_pattern in document_text:
                        mock_modifications.append(
                            {
                                "type": "TEXT_REPLACE",
                                "section": "parties",
                                "current_text": current_pattern,
                                "new_text": new_pattern,
                                "reason": rule_instruction,
                                "location_hint": "Parties section",
                            }
                        )
                        logger.info(
                            f"Found party pattern: {current_pattern} -> {new_pattern}"
                        )
                        break

                # Replace firm placeholders with actual firm details
                if "[FIRM_NAME]" in document_text:
                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "parties",
                            "current_text": "[FIRM_NAME]",
                            "new_text": firm_name,
                            "reason": rule_instruction,
                            "location_hint": "Section 1, line 4",
                        }
                    )
                if "[SIGNER_NAME]" in document_text:
                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "signatures",
                            "current_text": "[SIGNER_NAME]",
                            "new_text": signer_name,
                            "reason": rule_instruction,
                            "location_hint": "Section 11, line 55",
                        }
                    )
                if "[SIGNER_TITLE]" in document_text:
                    mock_modifications.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "signatures",
                            "current_text": "[SIGNER_TITLE]",
                            "new_text": signer_title,
                            "reason": rule_instruction,
                            "location_hint": "Section 11, line 56",
                        }
                    )

            # Add more flexible pattern matching for other rule types
            elif "governing" in rule_name or "law" in rule_name:
                # Look for governing law patterns
                law_patterns = [
                    ("State of Delaware", "State of New York"),
                    ("Delaware", "New York"),
                    ("Delaware courts", "New York courts"),
                ]

                for current_pattern, new_pattern in law_patterns:
                    if current_pattern in document_text:
                        mock_modifications.append(
                            {
                                "type": "TEXT_REPLACE",
                                "section": "governing_law",
                                "current_text": current_pattern,
                                "new_text": new_pattern,
                                "reason": rule_instruction,
                                "location_hint": "Governing law section",
                            }
                        )
                        logger.info(
                            f"Found law pattern: {current_pattern} -> {new_pattern}"
                        )
                        break

            elif "signature" in rule_name or "block" in rule_name:
                # Get firm details or use defaults
                firm_name = (
                    firm_details.get("firm_name", "Sample Company LLC")
                    if firm_details
                    else "Sample Company LLC"
                )
                signer_name = (
                    firm_details.get("signatory_name", "Sample Signer")
                    if firm_details
                    else "Sample Signer"
                )
                signer_title = (
                    firm_details.get("title", "Authorized Signatory")
                    if firm_details
                    else "Authorized Signatory"
                )

                # Replace signature placeholders instead of inserting new content
                signature_replacements = []

                # Look for specific signature patterns in the document
                # Try multiple variations of the company placeholder
                company_patterns = [
                    "For: Company (name to be provided upon execution)",
                    "For: Company",
                    "Company (name to be provided upon execution)",
                    "Company",
                ]

                for pattern in company_patterns:
                    if pattern in document_text:
                        # Determine the replacement text based on the pattern using firm details
                        if pattern.startswith("For:"):
                            new_text = pattern.replace("Company", firm_name)
                        else:
                            new_text = f"For: {firm_name}"

                        signature_replacements.append(
                            {
                                "type": "TEXT_REPLACE",
                                "section": "signatures",
                                "current_text": pattern,
                                "new_text": new_text,
                                "reason": rule_instruction,
                                "location_hint": "Signature block company name",
                            }
                        )
                        logger.info(
                            f"Found company pattern: '{pattern}' -> '{new_text}'"
                        )
                        break

                # Check if signer name already exists to avoid duplicates
                if "By:" in document_text and signer_name not in document_text:
                    signature_replacements.append(
                        {
                            "type": "TEXT_REPLACE",
                            "section": "signatures",
                            "current_text": "By:",
                            "new_text": f"By: {signer_name}",
                            "reason": rule_instruction,
                            "location_hint": "Signature block signer name",
                        }
                    )

                # Look for Title: with various formatting patterns
                title_patterns = [
                    "Title: \t_______________________________",
                    "Title:\t_______________________________",
                    "Title:_______________________________",
                    "Title:",
                    "Title: \t",
                    "Title:\t",
                ]

                for title_pattern in title_patterns:
                    logger.warning(f"Checking rule title pattern: '{title_pattern}'")
                    if title_pattern in document_text:
                        logger.warning(
                            f"Found rule title pattern '{title_pattern}' in document"
                        )
                        # Check if title already exists to avoid duplicates
                        if signer_title not in document_text:
                            logger.warning(
                                f"'{signer_title}' not in document, adding replacement"
                            )
                            signature_replacements.append(
                                {
                                    "type": "TEXT_REPLACE",
                                    "section": "signatures",
                                    "current_text": title_pattern,
                                    "new_text": f"Title: {signer_title}",
                                    "reason": rule_instruction,
                                    "location_hint": "Signature block title",
                                }
                            )
                            logger.warning(
                                f"Added rule title replacement: '{title_pattern}' -> 'Title: {signer_title}'"
                            )
                            break
                        else:
                            logger.warning(
                                f"'{signer_title}' already in document, skipping replacement"
                            )
                    else:
                        logger.warning(
                            f"Rule title pattern '{title_pattern}' not found in document"
                        )

                if signature_replacements:
                    mock_modifications.extend(signature_replacements)
                    logger.info(
                        f"Added {len(signature_replacements)} signature block replacements"
                    )
                else:
                    logger.info("No signature placeholders found to replace")

        # If no modifications were found, create a generic one based on the first rule
        if not mock_modifications and custom_rules:
            first_rule = custom_rules[0]
            mock_modifications.append(
                {
                    "type": "TEXT_INSERT",
                    "section": "general",
                    "new_text": f"[Modification based on rule: {first_rule.get('name', 'Unknown')}]",
                    "reason": first_rule.get("instruction", "Rule application"),
                    "location_hint": "Document beginning",
                }
            )
            logger.info("Added fallback modification")

        logger.info(
            f"Mock analysis complete. Generated {len(mock_modifications)} modifications:"
        )
        for i, mod in enumerate(mock_modifications):
            current = mod.get("current_text", "N/A")
            new = mod.get("new_text", "N/A")
            logger.info(
                f"  {i+1}. {mod.get('type', 'UNKNOWN')}: '{current[:50] if current else 'N/A'}...' -> '{new[:50] if new else 'N/A'}...'"
            )

        return {
            "success": True,
            "redlining_instructions": {
                "modifications": mock_modifications,
                "summary": f"Mock analysis completed with {len(mock_modifications)} modifications based on {len(custom_rules)} rules",
                "risk_assessment": "Mock assessment - modifications based on provided rules for testing purposes",
            },
            "ai_analysis": f"Mock AI analysis generated {len(mock_modifications)} redlining suggestions based on the provided rules. No LLM provider was available, so these come from the rule-based pass.",
        }

    def _build_system_prompt(
        self, custom_rules: list[dict[str, Any]], firm_details: dict[str, Any] = None
    ) -> str:
        """Build the system prompt for GPT-4"""
        base_prompt = """You are an expert legal AI assistant specializing in NDA (Non-Disclosure Agreement) redlining.
        Your task is to analyze NDA documents and provide PRECISE, TARGETED redlining instructions.

        CRITICAL INSTRUCTIONS:
        1. Make ONLY the specific changes requested in the rules - do NOT over-redline
        2. Use EXACT text matches from the document for current_text
        3. Focus on the specific areas mentioned in the rules
        4. **FIRM DETAILS OVERRIDE RULES**: When firm details are provided, ALWAYS use them instead of any company names or person names mentioned in the rules
        5. Be EXTREMELY conservative - only change what is explicitly requested
        6. REPLACE existing placeholders - do NOT create new fields or sections
        7. For signature blocks, ONLY use TEXT_REPLACE - NEVER use TEXT_INSERT
        8. **FLEXIBLE SIGNATURE FIELD RECOGNITION**: Different NDAs use different formats. Look for and replace:
            - Company name fields: "For: Company", "Name of company (Recipient):", "Company (name to be provided)", "Recipient:", "Company:"
            - Signer name fields: "By:", "Name:", "Signed:", "Signer:", "Signature:"
            - Title fields: "Title:", "Position:", "Role:"
            - **ONLY replace fields that actually exist in the document** - don't look for fields that aren't there
        9. Do NOT add new signature lines or duplicate existing ones
        10. If a rule says "JMC Investment LLC" but firm details provide "MyCompany", USE "MyCompany"
        11. **CRITICAL - NEVER TOUCH THESE**: Do NOT replace "Company" when it appears in legal text:
            - (the "Company") - this is a legal definition
            - "the Company" - refers to the disclosing party
            - "concerning the Company"
            - "the Company acknowledges"
            - "acquisition of our client's machining business (the 'Company')"
            - ANY instance where "Company" is in quotes or parentheses in the body text
        12. **ONLY REPLACE "Company" IN SIGNATURE BLOCKS**:
            - "For: Company" → "For: [FIRM_NAME]"
            - "For:\tCompany" → "For:\t[FIRM_NAME]"
            - "Company (name to be provided upon execution)" → "[FIRM_NAME]"
        13. **ABSOLUTELY NEVER** replace "Company" in the first few paragraphs where it defines what "Company" means
        14. If you're unsure whether to replace "Company", DON'T replace it - only replace in signature blocks at the end
        15. When changing years/durations, ONLY make changes in numbered sections about Term/Duration, NOT in the opening paragraphs
        16. When a term duration rule is provided, extract the target duration from the rule instruction (e.g., "Change to 5 years" means replace with "5 (5) years")
        17. **FLEXIBLE DATE PATTERN RECOGNITION**: For date insertion rules, use pattern recognition, NOT exact text matching
        18. Recognize ANY date placeholder pattern (blanks, underscores, brackets, "[DATE]", etc.) and replace with today's date
        19. Be flexible with date patterns - "Month __, Year", "Month ___, Year", "[DATE]", "Date: _______" all should be recognized and replaced
        20. **ADD PARTIES RULE**: When a rule asks to expand "Representatives" definition to include "investors" and "potential financing sources", find the Representatives definition (usually in quotes or parentheses) and add these terms to the list. Use TEXT_REPLACE to modify the existing definition.
        21. **RETENTION CARVE-OUT RULE**: When a rule asks to add a retention carve-out allowing electronic copy retention, find the "return" or "destroy" section and add a new sentence or clause allowing retention for document retention policy purposes. Use TEXT_INSERT to add this clause.
        22. **TERM CHANGE RULE**: When a rule asks to reduce term from X years to Y years, find ALL instances of the term duration in the Term/Duration section (not in other sections) and replace them. Extract the target years from the rule instruction.

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

        Return your analysis in this exact JSON format (use the ACTUAL firm details values provided above, NOT these example values):
        {
            "modifications": [
                {
                    "type": "TEXT_REPLACE",
                    "section": "confidentiality_term",
                    "current_text": "three years",
                    "new_text": "X (X) years",
                    "reason": "Change term duration as specified in custom rule",
                    "location_hint": "Term section"
                }
            ],
            "summary": "Brief summary of all changes",
            "risk_assessment": "Assessment of any legal risks in modifications"
        }

        IMPORTANT: For signature blocks, always use TEXT_REPLACE to fill in existing placeholders. Never use TEXT_INSERT to create new signature fields."""

        if custom_rules:
            rules_text = "\n\n" + "=" * 80 + "\n"
            rules_text += "🚨 CRITICAL - CUSTOM RULES TO APPLY 🚨\n"
            rules_text += "=" * 80 + "\n"
            rules_text += "YOU MUST APPLY ALL OF THESE RULES. DO NOT SKIP ANY RULE.\n"
            rules_text += "EACH RULE MUST RESULT IN AT LEAST ONE MODIFICATION.\n\n"

            for idx, rule in enumerate(custom_rules, 1):
                rule_name = rule.get("name", "Unnamed Rule")
                instruction = rule["instruction"]

                # CRITICAL: Replace any placeholders or hardcoded values in rules with actual firm details
                original_instruction = instruction
                if firm_details:
                    # Replace placeholder tokens with actual firm details
                    if "[FIRM_NAME]" in instruction and firm_details.get("firm_name"):
                        instruction = instruction.replace(
                            "[FIRM_NAME]", firm_details["firm_name"]
                        )

                    if "[SIGNER_NAME]" in instruction and firm_details.get(
                        "signatory_name"
                    ):
                        instruction = instruction.replace(
                            "[SIGNER_NAME]", firm_details["signatory_name"]
                        )

                    if "[TITLE]" in instruction and firm_details.get("title"):
                        instruction = instruction.replace(
                            "[TITLE]", firm_details["title"]
                        )

                    # Also replace any remaining hardcoded company names
                    hardcoded_companies = [
                        "JMC Investment LLC",
                        "JMC Investment",
                        "JMC",
                        "Welch Capital Partners",
                    ]
                    for company in hardcoded_companies:
                        if company in instruction and firm_details.get("firm_name"):
                            instruction = instruction.replace(
                                company, firm_details["firm_name"]
                            )

                    # Replace hardcoded person names
                    hardcoded_names = ["John Bagge", "John", "Jane Doe"]
                    for name in hardcoded_names:
                        if name in instruction and firm_details.get("signatory_name"):
                            instruction = instruction.replace(
                                name, firm_details["signatory_name"]
                            )

                    # Replace hardcoded titles
                    hardcoded_titles = [
                        "Vice President",
                        "President",
                        "CEO",
                        "Managing Director",
                    ]
                    for title in hardcoded_titles:
                        if title in instruction and firm_details.get("title"):
                            instruction = instruction.replace(
                                title, firm_details["title"]
                            )

                    # Log if instruction was modified
                    if instruction != original_instruction:
                        logger.warning("RULE TRANSFORMED:")
                        logger.warning(f"  BEFORE: {original_instruction}")
                        logger.warning(f"  AFTER:  {instruction}")

                rules_text += f"RULE {idx}: {rule_name}\n"
                rules_text += f"  Instruction: {instruction}\n"
                rules_text += "  ⚠️  YOU MUST GENERATE AT LEAST ONE MODIFICATION FOR THIS RULE\n\n"

            rules_text += "=" * 80 + "\n"
            rules_text += "CRITICAL REMINDER: You must apply ALL rules above. Each rule type requires:\n\n"
            rules_text += "1. EXPAND REPRESENTATIVES / ADD PARTIES:\n"
            rules_text += "   - **CRITICAL**: If a rule asks to expand 'Representatives' definition, you MUST find it and modify it\n"
            rules_text += "   - Search for the word 'Representatives' (case-insensitive) in the document\n"
            rules_text += "   - The definition might appear as:\n"
            rules_text += "     * 'collectively, \"Representatives\"'\n"
            rules_text += "     * '(collectively, \"Representatives\")'\n"
            rules_text += "     * 'collectively, 'Representatives''\n"
            rules_text += "     * 'Representatives' (in quotes or parentheses)\n"
            rules_text += "   - Find the COMPLETE definition text that includes 'Representatives'\n"
            rules_text += "   - Add the new parties to the end of the list (before the closing quote/parenthesis)\n"
            rules_text += "   - Example: 'collectively, \"Representatives\"' → 'collectively, \"Representatives\", investors, and potential financing sources'\n"
            rules_text += "   - Example: '(collectively, \"Representatives\")' → '(collectively, \"Representatives\", investors, and potential financing sources)'\n"
            rules_text += (
                "   - **YOU MUST USE TEXT_REPLACE** to modify the existing definition\n"
            )
            rules_text += "   - **DO NOT SKIP THIS** - if the rule asks for it, you MUST generate a modification\n"
            rules_text += "   - If you can't find 'Representatives', search for 'representatives' (lowercase) or 'REPRESENTATIVES' (uppercase)\n\n"
            rules_text += "2. RETENTION CARVE-OUT:\n"
            rules_text += "   - **CRITICAL**: Search for sections about 'return', 'destroy', 'destroy or return', 'return of Evaluation Material', or 'Return of Evaluation Material'\n"
            rules_text += "   - Find the paragraph or section that requires returning/destroying Confidential Information\n"
            rules_text += "   - Look for sentences like: 'you will destroy or return promptly', 'return all written material', 'destroy or return'\n"
            rules_text += "   - Add a new sentence AFTER that paragraph/section allowing electronic copy retention\n"
            rules_text += "   - **DO NOT** add it in sections about contacting Company employees or other unrelated topics\n"
            rules_text += "   - Example text: 'Notwithstanding the foregoing, Recipient may retain an electronic copy of Confidential Information and notes if required under Recipient's document retention policy, provided that such retained materials remain subject to the confidentiality obligations set forth herein.'\n"
            rules_text += "   - Use TEXT_INSERT to add this clause\n"
            rules_text += "   - **IMPORTANT**: The current_text for TEXT_INSERT can be empty or the sentence before where you want to insert\n\n"
            rules_text += "3. TERM CHANGE:\n"
            rules_text += (
                "   - **CRITICAL**: You MUST find and change the term duration\n"
            )
            rules_text += "   - Search the ENTIRE document for sections about 'Term', 'Duration', 'Confidentiality Term', or numbered sections\n"
            rules_text += "   - Look for patterns like: 'This Agreement shall remain in effect', 'period of X years', 'for X years', 'X years from the date'\n"
            rules_text += "   - **SPECIAL CASE**: If you see '() years' or '( ) years' (empty parentheses), this is a placeholder that MUST be replaced\n"
            rules_text += (
                "     Example: 'period of () years' → 'period of two (2) years'\n"
            )
            rules_text += "   - Find ALL instances of the old duration (e.g., 'three years', 'three (3) years', '3 years', 'three (3) year', '() years')\n"
            rules_text += "   - Replace with the target duration from the rule (e.g., 'two (2) years')\n"
            rules_text += "   - **IMPORTANT**: Even if the term section is not in the preview, search for year patterns throughout the document\n"
            rules_text += "   - Use TEXT_REPLACE for each instance found\n"
            rules_text += "   - **DO NOT SKIP THIS** - if a term change rule exists, you MUST generate at least one modification\n\n"
            rules_text += "4. REPLACE COMPANY/NAME/TITLE:\n"
            rules_text += "   - Find placeholders like 'For: Company', 'By:', 'Title:', 'Dear NAME:'\n"
            rules_text += "   - Replace with actual values from firm details\n"
            rules_text += "   - Use TEXT_REPLACE\n\n"
            rules_text += "=" * 80 + "\n"
            rules_text += (
                "⚠️  FINAL CHECK: Before returning your response, verify that:\n"
            )
            rules_text += "   - You have generated AT LEAST ONE modification for EACH rule listed above\n"
            rules_text += "   - **RULE 1 (Add parties)**: If a rule asks to expand Representatives, you MUST:\n"
            rules_text += "     * Search the ENTIRE document for 'Representatives' (try all case variations)\n"
            rules_text += "     * Find the definition text (it might be long, spanning multiple words)\n"
            rules_text += "     * Generate a TEXT_REPLACE modification that adds the new parties\n"
            rules_text += "     * If you don't find it, still generate a modification based on common patterns\n"
            rules_text += "   - **RULE 2 (Retention carve-out)**: You MUST have a TEXT_INSERT modification\n"
            rules_text += "   - **RULE 3 (Term change)**: You MUST have at least one TEXT_REPLACE modification\n"
            rules_text += "   - **COUNT YOUR MODIFICATIONS**: If you have 3 rules, you should have AT LEAST 3 modifications (one per rule minimum)\n"
            rules_text += "=" * 80 + "\n"
            base_prompt += rules_text

        if firm_details:
            firm_text = "\n\n" + "=" * 80 + "\n"
            firm_text += "🚨 CRITICAL - MANDATORY FIRM DETAILS - DO NOT USE ANY OTHER VALUES 🚨\n"
            firm_text += "=" * 80 + "\n"
            firm_text += (
                "YOU MUST USE THESE EXACT VALUES - DO NOT SUBSTITUTE WITH EXAMPLES:\n\n"
            )

            if firm_details.get("firm_name"):
                firm_text += f"COMPANY NAME TO USE: '{firm_details['firm_name']}'\n"
                firm_text += "⚠️  **LOCATION**: ONLY at the END of the document in the signature block\n"
                firm_text += "✅ CORRECT PATTERNS TO FIND AND REPLACE:\n"
                firm_text += (
                    f"   - 'For: Company' → 'For: {firm_details['firm_name']}'\n"
                )
                firm_text += f"   - 'Name of company (Recipient):' → 'Name of company (Recipient): {firm_details['firm_name']}'\n"
                firm_text += f"   - 'Company (name to be provided)' → '{firm_details['firm_name']}'\n"
                firm_text += (
                    f"   - 'Recipient:' → 'Recipient: {firm_details['firm_name']}'\n"
                )
                firm_text += "   - Any company placeholder in signature block\n"
                firm_text += '❌ WRONG: Do NOT replace (the "Company") in the opening paragraphs\n'
                firm_text += '❌ WRONG: Do NOT replace "the Company" anywhere in the legal text body\n'
                firm_text += '❌ WRONG: Do NOT replace "Company" if it\'s in quotes or parentheses\n'
                firm_text += "  - In JSON: current_text should match the EXACT format in the document\n\n"

            if firm_details.get("signatory_name"):
                firm_text += f"SIGNER NAME TO USE: '{firm_details['signatory_name']}'\n"
                firm_text += "✅ CORRECT PATTERNS TO FIND AND REPLACE:\n"
                firm_text += (
                    f"   - 'Dear NAME:' → 'Dear {firm_details['signatory_name']}:'\n"
                )
                firm_text += f"   - 'By:' (with blank/underscore) → 'By: {firm_details['signatory_name']}'\n"
                firm_text += f"   - 'Name:' (with blank/underscore) → 'Name: {firm_details['signatory_name']}'\n"
                firm_text += f"   - 'Signed:' (with blank/underscore) → 'Signed: {firm_details['signatory_name']}'\n"
                firm_text += "   - Any name placeholder in signature block\n"
                firm_text += "  - In JSON: current_text should be the PLACEHOLDER (e.g., 'By:' or 'Name:'), not the firm detail value\n"
                firm_text += f"  - DO NOT search for '{firm_details['signatory_name']}' in the document!\n\n"

            if firm_details.get("title"):
                firm_text += f"TITLE TO USE: '{firm_details['title']}'\n"
                firm_text += "✅ CORRECT PATTERNS TO FIND AND REPLACE:\n"
                firm_text += f"   - 'Title:' (with blank/underscore) → 'Title: {firm_details['title']}'\n"
                firm_text += f"   - 'Title: \\t_______________________________' → 'Title: {firm_details['title']}'\n"
                firm_text += f"   - 'Position:' (with blank) → 'Position: {firm_details['title']}'\n"
                firm_text += "   - Any title placeholder in signature block\n"
                firm_text += "  - In JSON: current_text should be the PLACEHOLDER (e.g., 'Title:' or 'Title: \\t_______________________________')\n"
                firm_text += f"  - DO NOT search for '{firm_details['title']}' in the document!\n\n"

            firm_text += "=" * 80 + "\n"
            firm_text += "REMINDER: Use the EXACT values above. Do NOT use placeholder examples.\n"
            firm_text += "=" * 80 + "\n"
            base_prompt += firm_text

        return base_prompt

    def _build_user_prompt(
        self,
        document_text: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any] = None,
    ) -> str:
        """Build the user prompt with document content"""
        # Limit document text to fit within token budget (GPT-4 has 8192 total, we need room for prompt + response)
        # Using ~3000 chars (~750 tokens) for document preview - increased to include term sections that are often later in the document
        text_limit = 3000
        document_preview = document_text[:text_limit]

        # Also include a snippet from the end of the document (where term sections often are)
        # This helps catch term sections that might be near the end
        if len(document_text) > text_limit:
            end_snippet = document_text[-500:]  # Last 500 chars
            document_preview += (
                f"\n\n[... document continues ...]\n\n[end of document]:\n{end_snippet}"
            )

        # Check if document contains "Representatives" and log it
        has_representatives = (
            "Representatives" in document_text
            or "representatives" in document_text.lower()
        )
        logger.warning(f"Document contains 'Representatives': {has_representatives}")
        if has_representatives:
            # Find and log the context around "Representatives"
            import re

            reps_matches = list(re.finditer(r"[Rr]epresentatives", document_text))
            if reps_matches:
                for match in reps_matches[:3]:  # Log first 3 occurrences
                    start = max(0, match.start() - 100)
                    end = min(len(document_text), match.end() + 100)
                    context = document_text[start:end]
                    logger.warning(
                        f"Found 'Representatives' at position {match.start()}: ...{context}..."
                    )

        # Add a special note if Representatives is found and there's an "Add parties" rule
        add_parties_rule = None
        for rule in custom_rules:
            rule_name = rule.get("name", "").lower()
            if (
                "parties" in rule_name
                or "representatives" in rule.get("instruction", "").lower()
            ):
                add_parties_rule = rule
                break

        representatives_note = ""
        if add_parties_rule and has_representatives:
            representatives_note = (
                "\n\n🚨 CRITICAL: This document contains the word 'Representatives'. "
            )
            representatives_note += "You MUST find the definition of 'Representatives' and expand it according to the rule. "
            representatives_note += "Search carefully - it might be in quotes, parentheses, or part of a longer definition.\n"

        prompt = f"""Please analyze the following NDA document and provide PRECISE redlining instructions based on the custom rules.
{representatives_note}
DOCUMENT CONTENT:
{document_preview}

        CRITICAL REQUIREMENTS:
1. When providing current_text, copy the EXACT text as it appears in the document above
2. For example, if the document says "five (5) years", your current_text must be "five (5) years", not "5 years" or "five years"
3. Look carefully at the exact wording, punctuation, and formatting
4. Make ONLY the changes specified in the rules - be conservative
5. Focus on the specific areas mentioned in the custom rules
6. **MOST IMPORTANT**: If firm details are provided below, use them instead of ANY company/person names mentioned in the rules
7. **CRITICAL**: Do NOT replace "Company" when it refers to the disclosing party in legal text
8. **CRITICAL**: For date placeholders (e.g., "Month __, Year"), replace with today's current date in "Month Day, Year" format
9. **CRITICAL**: Only replace placeholders, not actual content
10. **CRITICAL - TERM CHANGE**: If a rule asks to change the term duration, you MUST search for year patterns throughout the document. Look for:
    - "three years", "three (3) years", "3 years"
    - "() years" or "( ) years" (empty parentheses - this is a placeholder that MUST be filled)
    - "This Agreement shall remain in effect for [X] years" or "period of () years"
    - "period of [X] years" or "period of () years"
    - "[X] years from the date" or "() years from the date"
    - Any numbered section that mentions duration or term
    - **Even if the term section is at the end of the document (shown in "[end of document]" section), you MUST find and change it**
    - **SPECIAL**: If you see "period of () years", replace the entire phrase including "()" with the target duration

        COMMON PATTERNS TO LOOK FOR:
        - "five (5) years" (most common in legal documents)
        - "five years"
        - "5 years"
        - "five (5) year"
        - "five year"
        - "three years" or "three (3) years"
        - **SIGNATURE BLOCK PATTERNS** (various formats):
          * Company name: "For: Company", "Name of company (Recipient):", "Company (name to be provided)", "Recipient:", "Company:"
          * Signer name: "By:", "Name:", "Signed:", "Signer:", "Signature:"
          * Title: "Title:", "Title: \t_______________________________", "Position:", "Role:"
          * Date: "Date:", "Dated:"
        - "Dear NAME:" or "Dear [Name]:" (for recipient names)
        - "State of Delaware" or "Delaware"
        - **IMPORTANT**: Only replace fields that actually exist in the document. Don't create new fields.

        FLEXIBLE DATE PATTERN RECOGNITION:
        The AI should intelligently recognize ANY date placeholder pattern and replace it with today's date.
        This includes but is NOT limited to:

        Pattern Examples (use regex-like flexibility):
        - "Month __, Year" or "Month __, YYYY" → "Month Day, Year" (e.g., "October __, 2025" → "October 27, 2025")
        - "Month ___, Year" → "Month Day, Year" (any number of underscores)
        - "[DATE]", "[date]", "(DATE)", "(date)" → "Month Day, Year"
        - "Date: _______________" or "Date: __________" → "Date: Month Day, Year"
        - "Dated: _______________" or "Dated: __________" → "Dated: Month Day, Year"
        - "_______" following "Date" or "Dated" → Replace with today's date
        - "Month __, YYYY" in header/footer → "Month Day, YYYY"
        - Any text like "[Insert date]" or "[Enter date]" → "Month Day, Year"
        - Pattern: "Month [blank], Year" where [blank] can be "__", "___,", "[ ]", "_______", etc.

        CRITICAL DATE RULES:
        - If you see ANY pattern that requests a date insertion (blanks, underscores, brackets, "[DATE]", etc.), replace it
        - Do NOT wait for exact pattern matches - use pattern recognition
        - If a date field is incomplete or has placeholders, fill it with today's date
        - ONLY replace dates that are incomplete/placeholder - DO NOT change complete dates
        - Use today's date in "Month Day, Year" format (e.g., "October 27, 2025")
        - Use pattern matching, not exact text matching - be flexible with variations

CRITICAL: When replacing text, use the EXACT text as it appears in the document.

IMPORTANT: Use the FULL PHRASE as current_text, not just the placeholder word.
For example:
- Use "Dear NAME:" not just "NAME"
- Use "For: Company" not just "Company"
- Use "By:" not just "By"
- Use "Title:" not just "Title"

        SIGNATURE BLOCK HANDLING:
        - ONLY use TEXT_REPLACE for signature blocks - NEVER use TEXT_INSERT
        - Replace "By:" with "By: [SIGNER_NAME]" using firm details provided
        - Replace "Title: \t_______________________________" with "Title: [SIGNER_TITLE]" using firm details
        - Replace "Title:\t_______________________________" with "Title: [SIGNER_TITLE]" using firm details
        - Replace "For: Company" with "For: [FIRM_NAME]" using firm details
        - Replace "Company (name to be provided upon execution)" with "[FIRM_NAME]" using firm details
        - Replace "Dear NAME:" with "Dear [SIGNER_NAME]:" using firm details
        - Replace just "Company" with "[FIRM_NAME]" if it's in a "For:" context
        - Do NOT insert new signature blocks or create new fields
        - Do NOT duplicate existing signature lines
        - Find existing placeholders and replace them in place
        - ALWAYS use the actual firm details values provided, NOT these placeholder examples

IMPORTANT: Only make the specific changes requested in the custom rules. Do not over-redline or make unnecessary changes.

Please provide your analysis in the specified JSON format."""

        # Add firm details reminder at the end for maximum emphasis
        if firm_details:
            prompt += "\n\n" + "!" * 80 + "\n"
            prompt += (
                "🚨 FINAL REMINDER - MANDATORY REPLACEMENTS - USE THESE EXACT VALUES:\n"
            )
            prompt += "!" * 80 + "\n"
            if firm_details.get("signatory_name"):
                prompt += f'✅ REQUIRED: Replace "Dear NAME:" with "Dear {firm_details["signatory_name"]}:"\n'
                prompt += f'✅ REQUIRED: Replace "By:" with "By: {firm_details["signatory_name"]}"\n'
            if firm_details.get("firm_name"):
                prompt += f'✅ REQUIRED: Replace "For: Company" with "For: {firm_details["firm_name"]}"\n'
            if firm_details.get("title"):
                prompt += f'✅ REQUIRED: Replace "Title:" fields with "Title: {firm_details["title"]}"\n'
            prompt += (
                "\n❌ DO NOT use placeholder examples - use actual firm details only!\n"
            )
            prompt += "❌ DO NOT leave placeholders like 'Dear NAME:', 'Company', or blanks unchanged!\n"
            prompt += "!" * 80 + "\n"

        return prompt

    def _parse_ai_response(self, ai_response: str) -> list[dict[str, Any]]:
        """Parse the AI response and extract redlining instructions"""
        try:
            # Try to extract JSON from the response
            if "{" in ai_response and "}" in ai_response:
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                json_str = ai_response[start:end]

                # Fix: Escape control characters (tabs, newlines) that might be in the JSON
                # This is necessary because the AI might include literal tabs in the response
                import re

                # Replace literal tab characters with escaped tabs
                json_str = json_str.replace("\t", "\\t")
                # Replace literal newlines with escaped newlines (if any)
                json_str = re.sub(r"(?<!\\)\n", "\\n", json_str)

                logger.info(f"Parsing AI response JSON (length: {len(json_str)})")
                parsed = json.loads(json_str)
                modifications = parsed.get("modifications", [])

                # Unescape control characters in the modifications
                # After JSON parsing, \t becomes literal "\t" but we need actual tab characters
                for mod in modifications:
                    if "current_text" in mod:
                        # Replace escaped sequences with actual characters
                        mod["current_text"] = (
                            mod["current_text"]
                            .replace("\\t", "\t")
                            .replace("\\n", "\n")
                        )
                    if "new_text" in mod:
                        mod["new_text"] = (
                            mod["new_text"].replace("\\t", "\t").replace("\\n", "\n")
                        )

                logger.info(
                    f"Successfully parsed {len(modifications)} modifications from AI response"
                )
                return modifications
            else:
                logger.warning("Could not find JSON in AI response")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            json_str_local = json_str if "json_str" in locals() else ""
            logger.error(f"JSON string that failed to parse: {json_str_local[:1000]}")
            # Check if response was truncated
            if (
                json_str_local
                and not json_str_local.strip().endswith("}")
                and not json_str_local.strip().endswith("]")
            ):
                logger.error(
                    "⚠️  Response appears to be truncated! The AI response was cut off."
                )
                logger.error(f"Response length: {len(json_str_local)} characters")
                logger.error(f"Last 200 chars: {json_str_local[-200:]}")
                # Try to extract what we can from the partial JSON
                try:
                    # Try to find the last complete modification
                    import re

                    # Find all complete modification objects (more flexible pattern)
                    mod_pattern = r'\{\s*"type":\s*"[^"]+",\s*"section":\s*"[^"]+",\s*"current_text":\s*"(?:[^"\\]|\\.)*",\s*"new_text":\s*"(?:[^"\\]|\\.)*",\s*"reason":\s*"(?:[^"\\]|\\.)*",\s*"location_hint":\s*"(?:[^"\\]|\\.)*"\s*\}'
                    matches = re.findall(mod_pattern, json_str_local, re.DOTALL)
                    if matches:
                        logger.warning(
                            f"Found {len(matches)} complete modifications in truncated response"
                        )
                        # Reconstruct a valid JSON
                        fixed_json = '{"modifications": [' + ",".join(matches) + "]}"
                        parsed = json.loads(fixed_json)
                        modifications = parsed.get("modifications", [])
                        logger.warning(
                            f"Successfully extracted {len(modifications)} modifications from truncated response"
                        )
                        return modifications
                except Exception as fix_error:
                    logger.error(f"Failed to fix truncated JSON: {fix_error}")
            return []
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return []

    def generate_changes_for_review(
        self, document_text: str, custom_rules: list[dict], firm_details: dict[str, str]
    ) -> dict[str, Any]:
        """Generate changes with unique IDs for review interface"""
        logger.info("Generating changes for review interface")

        # Get AI modifications - analyze_document returns a dict, extract the list
        analysis_result = self.analyze_document(
            document_text, custom_rules, firm_details
        )

        # Extract modifications from the nested structure
        if isinstance(analysis_result, dict):
            if "redlining_instructions" in analysis_result and isinstance(
                analysis_result["redlining_instructions"], dict
            ):
                modifications = analysis_result["redlining_instructions"].get(
                    "modifications", []
                )
            elif "modifications" in analysis_result:
                modifications = analysis_result["modifications"]
            else:
                logger.error(
                    f"Unexpected analysis_result structure: {analysis_result.keys()}"
                )
                modifications = []
        elif isinstance(analysis_result, list):
            # If it's already a list, use it directly
            modifications = analysis_result
        else:
            logger.error(f"Unexpected analysis_result type: {type(analysis_result)}")
            modifications = []

        logger.warning(
            f"Extracted {len(modifications)} modifications for review interface"
        )

        # Add unique IDs and metadata to each change
        changes = []
        for i, mod in enumerate(modifications):
            # Ensure mod is a dictionary, not a string
            if isinstance(mod, str):
                logger.warning(f"Skipping invalid modification (string): {mod}")
                continue
            if not isinstance(mod, dict):
                logger.warning(f"Skipping invalid modification (not dict): {type(mod)}")
                continue

            change_id = str(uuid.uuid4())
            change = {
                "id": change_id,
                "type": mod.get("type", "TEXT_REPLACE"),
                "section": mod.get("section", "general"),
                "current_text": mod.get("current_text", ""),
                "new_text": mod.get("new_text", ""),
                "reason": mod.get("reason", ""),
                "location_hint": mod.get("location_hint", ""),
                "status": "pending",  # pending, accepted, rejected
                "order": i + 1,
            }
            changes.append(change)

        return {
            "changes": changes,
            "total_changes": len(changes),
            "document_text": document_text,
            "firm_details": firm_details,
            "custom_rules": custom_rules,
        }

    def apply_accepted_changes(
        self, doc_path: str, accepted_changes: list[dict], signature_path: str = None
    ) -> dict[str, Any]:
        """Apply only the accepted changes, as Word tracked changes."""
        from .tracked_docx import apply_changes, enable_track_revisions

        try:
            doc = DocxDocument(doc_path)
            accepted = [
                c for c in accepted_changes if c.get("status", "accepted") == "accepted"
            ]
            applied, failed = apply_changes(doc, accepted)
            for c in failed:
                logger.warning(
                    f"Could not apply change: {str(c.get('current_text'))[:80]}"
                )
            enable_track_revisions(doc)
            if signature_path and os.path.exists(signature_path):
                self._apply_signature(doc, signature_path)
            output_path = self._generate_output_path(doc_path)
            doc.save(output_path)
            return {
                "success": True,
                "output_path": output_path,
                "changes_applied": len(applied),
                "changes_failed": len(failed),
            }
        except Exception as e:
            logger.error(f"Error applying accepted changes: {str(e)}")
            return {"success": False, "error": str(e)}

    def _generate_output_path(self, input_path: str) -> str:
        """Generate output path for the processed document"""
        # Create outputs directory if it doesn't exist
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # Get the absolute path to the outputs directory
        base_dir = os.path.abspath(output_dir)
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{name}_final_{timestamp}{ext}"
        return os.path.abspath(os.path.join(base_dir, output_filename))

    def _apply_signature(self, doc: DocxDocument, signature_path: str):
        """Apply signature image to the document"""
        try:
            from docx.shared import Inches

            logger.info(f"Applying signature from: {signature_path}")

            # Find "Signed:" text and add signature right after it
            signature_added = False

            for paragraph in doc.paragraphs:
                if "Signed:" in paragraph.text:
                    logger.info(f"Found 'Signed:' in paragraph: {paragraph.text}")

                    # Clear the paragraph and rebuild it with proper signature placement
                    original_text = paragraph.text
                    paragraph.clear()

                    # Split text around "Signed:"
                    parts = original_text.split("Signed:", 1)

                    # Add text before "Signed:"
                    if parts[0].strip():
                        paragraph.add_run(parts[0])

                    # Add "Signed:" text
                    paragraph.add_run("Signed: ")

                    # Add signature image immediately after "Signed:"
                    signature_run = paragraph.add_run()
                    signature_run.add_picture(signature_path, width=Inches(1.2))

                    # Add any remaining text after "Signed:"
                    if len(parts) > 1 and parts[1].strip():
                        paragraph.add_run(parts[1])

                    signature_added = True
                    logger.info("Signature added right next to 'Signed:' text")
                    break

            # If no "Signed:" found, look for signature placeholders
            if not signature_added:
                for paragraph in doc.paragraphs:
                    if "[SIGNATURE]" in paragraph.text:
                        # Replace placeholder with signature
                        paragraph.text = paragraph.text.replace("[SIGNATURE]", "")

                        # Add signature image
                        run = (
                            paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                        )
                        run.add_picture(signature_path, width=Inches(1.5))
                        signature_added = True
                        logger.info("Signature added at [SIGNATURE] placeholder")
                        break

            # If still not added, add at the end of the document
            if not signature_added:
                logger.warning(
                    "No signature placeholder found, adding at end of document"
                )
                last_paragraph = doc.paragraphs[-1]
                run = last_paragraph.add_run()
                run.add_picture(signature_path, width=Inches(1.5))

        except Exception as e:
            logger.error(f"Error applying signature: {str(e)}")

    def _apply_single_change(self, doc: DocxDocument, change: dict) -> bool:
        """Apply a single change to the document, returns True if successful"""
        try:
            old_text = change.get("current_text", "")
            new_text = change.get("new_text", "")

            if not old_text or not new_text:
                logger.warning(f"Skipping change with empty text: {change}")
                return False

            # Find and replace text in the document
            found = False
            for para_idx, paragraph in enumerate(doc.paragraphs):
                # Try exact match first
                if old_text in paragraph.text:
                    logger.warning(
                        f"  Found exact match in paragraph {para_idx}: '{paragraph.text[:100]}'"
                    )
                    success = self._replace_text_in_paragraph(
                        paragraph, old_text, new_text
                    )
                    if success:
                        logger.warning(f"  ✅ Change applied in paragraph {para_idx}")
                        found = True
                        break
                    else:
                        logger.warning(
                            f"  ❌ Failed to apply change in paragraph {para_idx}"
                        )

            # If not found, try with whitespace normalization (e.g., "For: Company" vs "For:\tCompany")
            if not found:
                import re

                # Normalize whitespace for comparison
                old_text_normalized = re.sub(r"\s+", " ", old_text.strip())

                for para_idx, paragraph in enumerate(doc.paragraphs):
                    para_text_normalized = re.sub(r"\s+", " ", paragraph.text.strip())
                    if old_text_normalized in para_text_normalized:
                        # Find the actual text in the original paragraph
                        # Extract the actual text with original whitespace
                        actual_old_text = self._find_text_with_whitespace(
                            paragraph.text, old_text
                        )
                        if actual_old_text:
                            logger.warning(
                                f"  Found with whitespace variation in paragraph {para_idx}"
                            )
                            logger.warning(f"    Looking for: '{old_text}'")
                            logger.warning(f"    Found actual: '{actual_old_text}'")
                            success = self._replace_text_in_paragraph(
                                paragraph, actual_old_text, new_text
                            )
                            if success:
                                logger.warning(
                                    f"  ✅ Change applied with whitespace normalization in paragraph {para_idx}"
                                )
                                found = True
                                break

            if not found:
                logger.warning(
                    f"  ⚠️  Text not found in any paragraph: '{old_text[:80]}'"
                )
                logger.warning(
                    "  Try checking the document for: variations with tabs/spaces"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Error applying single change: {str(e)}")
            return False

    def _find_text_with_whitespace(self, paragraph_text: str, search_text: str) -> str:
        """Find text in paragraph that matches after whitespace normalization"""
        import re

        # Try exact match first
        if search_text in paragraph_text:
            return search_text

        # Special handling for empty parentheses patterns like "() years"
        # The document might have "()" or "( )" or other variations
        if "()" in search_text:
            # Try variations with spaces inside parentheses
            variations_with_parens = [
                search_text.replace("()", "( )"),  # Space inside: "( )"
                search_text.replace("()", "(  )"),  # Double space: "(  )"
                search_text.replace("()", "()"),  # Keep original
            ]
            for variation in variations_with_parens:
                if variation in paragraph_text:
                    logger.warning(
                        f"    Found with parentheses variation: '{variation}'"
                    )
                    return variation

            # Try pattern matching for empty parentheses: match () or ( ) or (  ) etc.
            search_text.replace("()", r"\(\s*\)")  # Match () with optional spaces
            pattern = re.escape(search_text)
            pattern = pattern.replace(
                r"\(\)", r"\(\s*\)"
            )  # Allow spaces in empty parentheses
            pattern = pattern.replace(
                r"\ ", r"\s+"
            )  # Allow any whitespace where there was a space

            match = re.search(pattern, paragraph_text)
            if match:
                logger.warning(
                    f"    Found with empty parentheses pattern matching: '{match.group(0)}'"
                )
                return match.group(0)

        # Try common whitespace variations
        variations = [
            search_text.replace(" ", "\t"),  # Replace spaces with tabs
            search_text.replace(" ", "  "),  # Replace single space with double
            re.sub(r"\s+", "\t", search_text),  # All whitespace to tabs
        ]

        for variation in variations:
            if variation in paragraph_text:
                logger.warning(f"    Found with whitespace variation: '{variation}'")
                return variation

        # Try pattern matching with flexible whitespace
        # For "For: Company", match "For:<any whitespace>Company"
        pattern = re.escape(search_text)
        pattern = pattern.replace(
            r"\ ", r"\s+"
        )  # Allow any whitespace where there was a space

        match = re.search(pattern, paragraph_text)
        if match:
            logger.warning(f"    Found with pattern matching: '{match.group(0)}'")
            return match.group(0)

        return None

    def _replace_text_in_paragraph(
        self, paragraph, old_text: str, new_text: str
    ) -> bool:
        """Replace text in a paragraph while showing BOTH old and new text with Track Changes"""
        try:
            # Always use paragraph-level replacement to show BOTH old and new text
            if old_text in paragraph.text:
                logger.warning("    Applying Track Changes to show old and new text")

                # Store original text
                original_text = paragraph.text

                # Clear all runs and create new ones
                paragraph.clear()

                # Split text around the old_text and create runs
                parts = original_text.split(
                    old_text, 1
                )  # Split only once for first occurrence
                logger.warning(f"    Text split into {len(parts)} parts")

                # Add text before the replacement (no formatting)
                if parts[0]:
                    paragraph.add_run(parts[0])
                    logger.warning(f"    Added text before: '{parts[0][:50]}'")

                # Add OLD text with BLACK strikethrough (shows what was removed)
                deleted_run = paragraph.add_run(old_text)
                deleted_run.font.strike = True
                deleted_run.font.color.rgb = RGBColor(0, 0, 0)  # Black strikethrough
                logger.warning(
                    f"    ✅ Added DELETION (black strikethrough): '{old_text[:50]}'"
                )

                # Add NEW text with RED underline (shows what was added)
                added_run = paragraph.add_run(new_text)
                added_run.font.underline = True
                added_run.font.color.rgb = RGBColor(
                    255, 0, 0
                )  # Red underline for new text
                logger.warning(
                    f"    ✅ Added INSERTION (red underline): '{new_text[:50]}'"
                )

                # Add any remaining text after the replacement (no formatting)
                if len(parts) > 1 and parts[1]:
                    paragraph.add_run(parts[1])
                    logger.warning(f"    Added text after: '{parts[1][:50]}'")

                logger.warning(
                    "    ✅✅ Track Changes complete - document will show BOTH old (strikethrough) and new (red underline) text"
                )
                return True
            else:
                logger.warning(
                    f"Text '{old_text}' not found in paragraph: '{paragraph.text}'"
                )
                # Try case-insensitive search with change tracking
                if old_text.lower() in paragraph.text.lower():
                    logger.info(
                        "Found case-insensitive match, trying replacement with change tracking"
                    )

                    # Find the actual old text in the paragraph
                    text_lower = paragraph.text.lower()
                    idx = text_lower.find(old_text.lower())

                    if idx != -1:
                        # Extract the actual old text from the paragraph
                        actual_old_text = paragraph.text[idx : idx + len(old_text)]

                        # Clear the paragraph and rebuild with change tracking
                        original_text = paragraph.text
                        paragraph.clear()

                        # Split on the actual old text
                        parts = original_text.split(actual_old_text, 1)

                        # Add text before replacement
                        if parts[0]:
                            paragraph.add_run(parts[0])

                        # Add OLD text with black strikethrough
                        deleted_run = paragraph.add_run(actual_old_text)
                        deleted_run.font.strike = True
                        deleted_run.font.color.rgb = RGBColor(
                            0, 0, 0
                        )  # Black strikethrough

                        # Add NEW text with red underline
                        added_run = paragraph.add_run(new_text)
                        added_run.font.underline = True
                        added_run.font.color.rgb = RGBColor(255, 0, 0)  # Red underline

                        # Add remaining text
                        if len(parts) > 1:
                            paragraph.add_run(parts[1])

                        logger.info(
                            f"Case-insensitive replacement with visual change tracking: '{actual_old_text}' (strikethrough) -> '{new_text}' (red underline)"
                        )
                        return True

        except Exception as e:
            logger.error(f"Error replacing text in paragraph: {str(e)}")
            # Fallback to simple replacement with change tracking
            try:
                original_text = paragraph.text
                if old_text in original_text:
                    paragraph.clear()
                    parts = original_text.split(old_text, 1)

                    if parts[0]:
                        paragraph.add_run(parts[0])

                        # Use native Word Track Changes for deletion
                        deleted_run = paragraph.add_run(old_text)
                        self._add_track_change_deletion(deleted_run)

                        # Use native Word Track Changes for insertion
                        added_run = paragraph.add_run(new_text)
                        self._add_track_change_insertion(added_run)

                    if len(parts) > 1:
                        paragraph.add_run(parts[1])

                    logger.info(
                        f"Fallback replacement with visual change tracking successful: '{old_text}' (strikethrough) -> '{new_text}' (red underline)"
                    )
                    return True
                else:
                    logger.warning(
                        f"Text '{old_text}' not found in fallback replacement"
                    )
                    return False
            except Exception as fallback_error:
                logger.error(f"Fallback replacement failed: {str(fallback_error)}")
                return False

        return False

    def _add_track_change_deletion(self, run):
        """Add Word Track Changes deletion markup to a run"""
        try:
            import uuid

            # Create deletion markup - w:del must contain w:r (run) elements
            del_elem = OxmlElement("w:del")
            change_id = str(uuid.uuid4())[:8]  # Use unique ID for each change
            del_elem.set(qn("w:id"), change_id)
            del_elem.set(qn("w:author"), "ClausePilot")
            del_elem.set(qn("w:date"), datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

            # Create a run element inside the deletion
            run_elem = OxmlElement("w:r")

            # Add run properties (formatting)
            rPr = OxmlElement("w:rPr")
            # Copy any formatting from the original run
            if run.font.bold:
                b_elem = OxmlElement("w:b")
                rPr.append(b_elem)
            if run.font.italic:
                i_elem = OxmlElement("w:i")
                rPr.append(i_elem)
            # Add strikethrough for deleted text
            strike_elem = OxmlElement("w:strike")
            rPr.append(strike_elem)
            run_elem.append(rPr)

            # Use w:delText for deleted text (required for Track Changes deletions)
            text_elem = OxmlElement("w:delText")
            text_elem.set(qn("xml:space"), "preserve")  # Preserve whitespace
            text_elem.text = run.text
            run_elem.append(text_elem)
            del_elem.append(run_elem)

            # Replace the run's XML with the deletion markup
            run._element.getparent().replace(run._element, del_elem)
            logger.warning("      ✅ Track Changes deletion XML created")

        except Exception as e:
            logger.warning(f"      ❌ Track Changes deletion failed: {e}")
            logger.warning("      Using fallback strikethrough")
            # Fallback to strikethrough
            run.font.strike = True
            run.font.color.rgb = RGBColor(0, 0, 0)

    def _add_track_change_insertion(self, run):
        """Add Word Track Changes insertion markup to a run"""
        try:
            import uuid

            # Create insertion markup - w:ins must contain w:r (run) elements
            ins_elem = OxmlElement("w:ins")
            change_id = str(uuid.uuid4())[:8]  # Use unique ID for each change
            ins_elem.set(qn("w:id"), change_id)
            ins_elem.set(qn("w:author"), "ClausePilot")
            ins_elem.set(qn("w:date"), datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

            # Create a run element inside the insertion
            run_elem = OxmlElement("w:r")

            # Add run properties (formatting)
            rPr = OxmlElement("w:rPr")
            # Add underline for inserted text
            u_elem = OxmlElement("w:u")
            u_elem.set(qn("w:val"), "single")
            rPr.append(u_elem)
            # Add color for inserted text (red)
            color_elem = OxmlElement("w:color")
            color_elem.set(qn("w:val"), "FF0000")  # Red
            rPr.append(color_elem)
            run_elem.append(rPr)

            # Add the text to the run element
            text_elem = OxmlElement("w:t")
            text_elem.set(qn("xml:space"), "preserve")  # Preserve whitespace
            text_elem.text = run.text
            run_elem.append(text_elem)
            ins_elem.append(run_elem)

            # Replace the run's XML with the insertion markup
            run._element.getparent().replace(run._element, ins_elem)
            logger.warning("      ✅ Track Changes insertion XML created")

        except Exception as e:
            logger.warning(f"      ❌ Track Changes insertion failed: {e}")
            logger.warning("      Using fallback red underline")
            # Fallback to red underline
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)


class DocumentProcessor:
    def __init__(self, ai_service: AIRedliningService):
        self.ai_service = ai_service

    def process_document(
        self,
        doc_path: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any],
        signature_path: str = None,
    ) -> dict[str, Any]:
        """Redline a Word document: plan changes, write them as tracked changes, save."""
        from .tracked_docx import (
            apply_changes,
            body_paragraphs,
            enable_track_revisions,
            paragraph_text,
        )

        try:
            doc = DocxDocument(doc_path)
            paragraphs = [paragraph_text(p) for p in body_paragraphs(doc)]
            changes, notes = self.ai_service.plan_changes(
                paragraphs, custom_rules, firm_details
            )
            applied, failed = apply_changes(doc, changes)
            enable_track_revisions(doc)
            if signature_path and os.path.exists(signature_path):
                self._apply_signature(doc, signature_path)
            output_path = self._generate_output_path(doc_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            doc.save(output_path)
            analysis = f"{len(applied)} tracked change(s) applied"
            if failed:
                analysis += f", {len(failed)} could not be placed"
            if notes:
                analysis += ". Not applied: " + "; ".join(notes)
            return {
                "success": True,
                "output_path": output_path,
                "modifications_applied": len(applied),
                "changes": changes,
                "ai_analysis": analysis,
            }
        except Exception as e:
            logger.exception("Document processing failed")
            return {"success": False, "error": str(e)}

    def _process_small_document(
        self,
        doc_path: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any],
        signature_path: str = None,
    ) -> dict[str, Any]:
        """Process small documents (<100KB) using standard method"""
        try:
            # Load the document
            doc = DocxDocument(doc_path)

            # Extract text for AI analysis
            document_text = self._extract_document_text(doc)

            # Get AI redlining instructions
            ai_result = self.ai_service.analyze_document(
                document_text, custom_rules, firm_details
            )

            if not ai_result["success"]:
                return {"success": False, "error": ai_result["error"]}

            # Apply AI modifications
            modifications = ai_result["redlining_instructions"]
            if isinstance(modifications, dict) and "modifications" in modifications:
                modifications = modifications["modifications"]

            logger.info(
                f"AI generated {len(modifications) if modifications else 0} modifications"
            )
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
                "success": True,
                "output_path": output_path,
                "modifications_applied": len(modifications) if modifications else 0,
                "ai_analysis": ai_result.get("ai_analysis", "No analysis available"),
            }

        except Exception as e:
            logger.error(f"Error processing small document: {str(e)}")
            return {"success": False, "error": str(e)}

    def _process_large_document(
        self,
        doc_path: str,
        custom_rules: list[dict[str, Any]],
        firm_details: dict[str, Any],
        signature_path: str = None,
    ) -> dict[str, Any]:
        """Process large documents (>100KB) using memory-efficient chunked method"""
        try:
            logger.info("Processing large document with chunked method")

            # Load the document
            doc = DocxDocument(doc_path)

            # Extract text in chunks for AI analysis
            document_text = self._extract_document_text_chunked(doc)

            # Get AI redlining instructions
            ai_result = self.ai_service.analyze_document(
                document_text, custom_rules, firm_details
            )

            if not ai_result["success"]:
                return {"success": False, "error": ai_result["error"]}

            # Apply AI modifications
            modifications = ai_result["redlining_instructions"]
            if isinstance(modifications, dict) and "modifications" in modifications:
                modifications = modifications["modifications"]

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
                "success": True,
                "output_path": output_path,
                "modifications_applied": len(modifications) if modifications else 0,
                "ai_analysis": ai_result.get("ai_analysis", "No analysis available"),
            }

        except Exception as e:
            logger.error(f"Error processing large document: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_document_text(self, doc: DocxDocument) -> str:
        """Extract text content from the Word document"""
        text_parts = []
        for paragraph in doc.paragraphs:
            text_parts.append(paragraph.text)

        return "\n".join(text_parts)

    def _extract_document_text_chunked(self, doc: DocxDocument) -> str:
        """Extract text content from large Word documents in chunks for memory efficiency"""
        text_parts = []
        chunk_size = 1000  # Process 1000 paragraphs at a time
        total_paragraphs = len(doc.paragraphs)

        logger.info(
            f"Extracting text from {total_paragraphs} paragraphs in chunks of {chunk_size}"
        )

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

        return "\n".join(text_parts)

    def _apply_modifications(
        self, doc: DocxDocument, modifications: list[dict[str, Any]]
    ):
        """Apply AI-generated modifications to the document"""
        for mod in modifications:
            try:
                if mod["type"] == "TEXT_REPLACE":
                    self._replace_text(doc, mod["current_text"], mod["new_text"])
                elif mod["type"] == "TEXT_INSERT":
                    self._insert_text(
                        doc, mod["new_text"], mod.get("location_hint", "")
                    )
                elif mod["type"] == "TEXT_DELETE":
                    self._delete_text(doc, mod["current_text"])
                elif mod["type"] == "CLAUSE_ADD":
                    self._add_clause(doc, mod["new_text"])

            except Exception as e:
                logger.warning(f"Failed to apply modification {mod}: {str(e)}")
                continue

    def _apply_modifications_chunked(
        self, doc: DocxDocument, modifications: list[dict[str, Any]]
    ):
        """Apply AI-generated modifications to large documents in chunks for memory efficiency"""
        logger.info(f"Applying {len(modifications)} modifications to large document")

        for i, mod in enumerate(modifications):
            try:
                if mod["type"] == "TEXT_REPLACE":
                    self._replace_text_chunked(
                        doc, mod["current_text"], mod["new_text"]
                    )
                elif mod["type"] == "TEXT_INSERT":
                    self._insert_text_chunked(
                        doc, mod["new_text"], mod.get("location_hint", "")
                    )
                elif mod["type"] == "TEXT_DELETE":
                    self._delete_text_chunked(doc, mod["current_text"])
                elif mod["type"] == "CLAUSE_ADD":
                    self._add_clause_chunked(doc, mod["new_text"])

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
            old_text.lower(),  # Lowercase
            old_text.upper(),  # Uppercase
            old_text.replace("Company", "Comapny"),  # Common typo
            old_text.replace("Company", "company"),  # Case variation
            "For: Company",  # Common pattern
            "For:Company",  # No space after colon
            "For Company",  # No colon
            "for: company",  # All lowercase
            "FOR: COMPANY",  # All uppercase
            # Handle multiple whitespace variations
            "For:  Company",  # Double space
            "For:   Company",  # Triple space
            "For:    Company",  # Quadruple space
            "For:\tCompany",  # Tab after colon
            "For: \tCompany",  # Space and tab
            "For:\t Company",  # Tab and space
            "For: \t Company",  # Space, tab, space
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
                    logger.warning(
                        f"Successfully replaced. New paragraph: {paragraph.text}"
                    )
                    replaced = True
                    break

        # If exact match failed, try normalized whitespace matching
        if not replaced:
            logger.warning("Trying normalized whitespace matching")
            import re

            # Normalize whitespace in the old text (replace multiple spaces/tabs with single space)
            normalized_old = re.sub(r"\s+", " ", old_text.strip())
            for paragraph in doc.paragraphs:
                # Normalize whitespace in paragraph text
                normalized_para = re.sub(r"\s+", " ", paragraph.text.strip())
                if normalized_old.lower() in normalized_para.lower():
                    logger.warning(
                        f"Found normalized match in paragraph: {paragraph.text}"
                    )
                    # Try to find the actual text in the paragraph and replace it
                    if old_text in paragraph.text:
                        if self._replace_text_in_paragraph(
                            paragraph, old_text, new_text
                        ):
                            logger.warning(
                                f"Successfully replaced with normalized matching. New paragraph: {paragraph.text}"
                            )
                            replaced = True
                            break
                    else:
                        # If exact text not found, try to find and replace the normalized version
                        # Find the actual text pattern in the paragraph
                        for variation in variations_to_search:
                            if variation in paragraph.text:
                                logger.warning(
                                    f"Found variation '{variation}' in paragraph, replacing with '{new_text}'"
                                )
                                if self._replace_text_in_paragraph(
                                    paragraph, variation, new_text
                                ):
                                    logger.warning(
                                        f"Successfully replaced variation. New paragraph: {paragraph.text}"
                                    )
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
                old_text.replace(
                    "Company (name to be provided upon execution)", "Company"
                ),
                "Company",
                "For: Company",
                "Company (name to be provided upon execution)",
                "For: Company (name to be provided upon execution)",
                # Additional variations for better matching
                "For: " + old_text,
                old_text + " (name to be provided upon execution)",
                "For: " + old_text + " (name to be provided upon execution)",
            ]

            for variation in variations:
                if (
                    variation and variation != old_text
                ):  # Skip empty or duplicate variations
                    logger.info(f"Trying variation: '{variation}'")
                    for paragraph in doc.paragraphs:
                        if variation in paragraph.text:
                            logger.info(
                                f"Found variation '{variation}' in paragraph: {paragraph.text}"
                            )
                            if self._replace_text_in_paragraph(
                                paragraph, variation, new_text
                            ):
                                logger.info(
                                    f"Successfully replaced variation. New paragraph: {paragraph.text}"
                                )
                                replaced = True
                                break
                    if replaced:
                        break

            # If still not found, try case-insensitive search
            if not replaced:
                logger.info("Trying case-insensitive search")
                for paragraph in doc.paragraphs:
                    if old_text.lower() in paragraph.text.lower():
                        logger.info(
                            f"Found case-insensitive match in paragraph: {paragraph.text}"
                        )
                        if self._replace_text_in_paragraph(
                            paragraph, old_text, new_text
                        ):
                            logger.info(
                                f"Successfully replaced case-insensitive. New paragraph: {paragraph.text}"
                            )
                            replaced = True
                            break

        if not replaced:
            logger.error(
                f"Failed to replace '{old_text}' with '{new_text}' - no matches found"
            )
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
                logger.info(
                    "Text found in paragraph, doing paragraph-level replacement"
                )

                # Store original text
                original_text = paragraph.text

                # Clear all runs and create new ones
                paragraph.clear()

                # Split text around the old_text and create runs
                parts = original_text.split(old_text)
                logger.info(f"Split into {len(parts)} parts: {parts}")

                # Add text before the replacement
                if parts[0]:  # Add non-empty parts
                    run = paragraph.add_run(parts[0])
                    # Keep original formatting (no change tracking)

                # Use native Word Track Changes for deletion
                deleted_run = paragraph.add_run(old_text)
                self._add_track_change_deletion(deleted_run)

                # Use native Word Track Changes for insertion
                added_run = paragraph.add_run(new_text)
                self._add_track_change_insertion(added_run)

                # Add any remaining text after the replacement
                if len(parts) > 1:
                    run = paragraph.add_run(parts[1])
                    # Keep original formatting

                logger.info(
                    f"Visual change tracking added: '{old_text}' (strikethrough) -> '{new_text}' (red underline)"
                )

                logger.info(f"Final paragraph text: {paragraph.text}")
                return True
            else:
                logger.warning(
                    f"Text '{old_text}' not found in paragraph: '{paragraph.text}'"
                )
                # Try case-insensitive search with change tracking
                if old_text.lower() in paragraph.text.lower():
                    logger.info(
                        "Found case-insensitive match, trying replacement with change tracking"
                    )

                    # Find the actual old text in the paragraph
                    text_lower = paragraph.text.lower()
                    idx = text_lower.find(old_text.lower())

                    if idx != -1:
                        # Extract the actual old text from the paragraph
                        actual_old_text = paragraph.text[idx : idx + len(old_text)]

                        # Clear the paragraph and rebuild with change tracking
                        original_text = paragraph.text
                        paragraph.clear()

                        # Split on the actual old text
                        parts = original_text.split(actual_old_text, 1)

                        # Add text before replacement
                        if parts[0]:
                            run = paragraph.add_run(parts[0])

                        # Add OLD text with black strikethrough
                        deleted_run = paragraph.add_run(actual_old_text)
                        deleted_run.font.strike = True
                        deleted_run.font.color.rgb = RGBColor(
                            0, 0, 0
                        )  # Black strikethrough

                        # Add NEW text with red underline
                        added_run = paragraph.add_run(new_text)
                        added_run.font.underline = True
                        added_run.font.color.rgb = RGBColor(255, 0, 0)  # Red underline

                        # Add remaining text
                        if len(parts) > 1:
                            run = paragraph.add_run(parts[1])

                        logger.info(
                            f"Case-insensitive replacement with visual change tracking: '{actual_old_text}' (strikethrough) -> '{new_text}' (red underline)"
                        )
                        return True

        except Exception as e:
            logger.error(f"Error replacing text in paragraph: {str(e)}")
            # Fallback to simple replacement with change tracking
            try:
                original_text = paragraph.text
                if old_text in original_text:
                    paragraph.clear()
                    parts = original_text.split(old_text, 1)

                    if parts[0]:
                        paragraph.add_run(parts[0])

                        # Use native Word Track Changes for deletion
                        deleted_run = paragraph.add_run(old_text)
                        self._add_track_change_deletion(deleted_run)

                        # Use native Word Track Changes for insertion
                        added_run = paragraph.add_run(new_text)
                        self._add_track_change_insertion(added_run)

                    if len(parts) > 1:
                        paragraph.add_run(parts[1])

                    logger.info(
                        f"Fallback replacement with visual change tracking successful: '{old_text}' (strikethrough) -> '{new_text}' (red underline)"
                    )
                    return True
                else:
                    logger.warning(
                        f"Text '{old_text}' not found in fallback replacement"
                    )
                    return False
            except Exception as fallback_error:
                logger.error(f"Fallback replacement failed: {str(fallback_error)}")
                return False

        return False

    def _add_track_change_deletion(self, run):
        """Add Word Track Changes deletion markup to a run"""
        try:
            import uuid

            # Create deletion markup - w:del must contain w:r (run) elements
            del_elem = OxmlElement("w:del")
            change_id = str(uuid.uuid4())[:8]  # Use unique ID for each change
            del_elem.set(qn("w:id"), change_id)
            del_elem.set(qn("w:author"), "ClausePilot")
            del_elem.set(qn("w:date"), datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

            # Create a run element inside the deletion
            run_elem = OxmlElement("w:r")

            # Add run properties (formatting)
            rPr = OxmlElement("w:rPr")
            # Copy any formatting from the original run
            if run.font.bold:
                b_elem = OxmlElement("w:b")
                rPr.append(b_elem)
            if run.font.italic:
                i_elem = OxmlElement("w:i")
                rPr.append(i_elem)
            # Add strikethrough for deleted text
            strike_elem = OxmlElement("w:strike")
            rPr.append(strike_elem)
            run_elem.append(rPr)

            # Use w:delText for deleted text (required for Track Changes deletions)
            text_elem = OxmlElement("w:delText")
            text_elem.set(qn("xml:space"), "preserve")  # Preserve whitespace
            text_elem.text = run.text
            run_elem.append(text_elem)
            del_elem.append(run_elem)

            # Replace the run's XML with the deletion markup
            run._element.getparent().replace(run._element, del_elem)
            logger.warning("      ✅ Track Changes deletion XML created")

        except Exception as e:
            logger.warning(f"      ❌ Track Changes deletion failed: {e}")
            logger.warning("      Using fallback strikethrough")
            # Fallback to strikethrough
            run.font.strike = True
            run.font.color.rgb = RGBColor(0, 0, 0)

    def _add_track_change_insertion(self, run):
        """Add Word Track Changes insertion markup to a run"""
        try:
            import uuid

            # Create insertion markup - w:ins must contain w:r (run) elements
            ins_elem = OxmlElement("w:ins")
            change_id = str(uuid.uuid4())[:8]  # Use unique ID for each change
            ins_elem.set(qn("w:id"), change_id)
            ins_elem.set(qn("w:author"), "ClausePilot")
            ins_elem.set(qn("w:date"), datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"))

            # Create a run element inside the insertion
            run_elem = OxmlElement("w:r")

            # Add run properties (formatting)
            rPr = OxmlElement("w:rPr")
            # Add underline for inserted text
            u_elem = OxmlElement("w:u")
            u_elem.set(qn("w:val"), "single")
            rPr.append(u_elem)
            # Add color for inserted text (red)
            color_elem = OxmlElement("w:color")
            color_elem.set(qn("w:val"), "FF0000")  # Red
            rPr.append(color_elem)
            run_elem.append(rPr)

            # Add the text to the run element
            text_elem = OxmlElement("w:t")
            text_elem.set(qn("xml:space"), "preserve")  # Preserve whitespace
            text_elem.text = run.text
            run_elem.append(text_elem)
            ins_elem.append(run_elem)

            # Replace the run's XML with the insertion markup
            run._element.getparent().replace(run._element, ins_elem)
            logger.warning("      ✅ Track Changes insertion XML created")

        except Exception as e:
            logger.warning(f"      ❌ Track Changes insertion failed: {e}")
            logger.warning("      Using fallback red underline")
            # Fallback to red underline
            run.font.underline = True
            run.font.color.rgb = RGBColor(255, 0, 0)

    def _replace_text_chunked(self, doc: DocxDocument, old_text: str, new_text: str):
        """Replace text in large documents with chunked processing for memory efficiency"""
        logger.info(
            f"Attempting to replace '{old_text}' with '{new_text}' in large document"
        )
        replaced = False
        chunk_size = 500  # Process 500 paragraphs at a time
        total_paragraphs = len(doc.paragraphs)

        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)

            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    paragraph = doc.paragraphs[j]
                    if old_text in paragraph.text:
                        logger.info(
                            f"Found text to replace in paragraph {j}: {paragraph.text[:100]}..."
                        )

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
            logger.warning(
                f"Text '{old_text}' not found in large document for replacement"
            )

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
                paragraph.text = paragraph.text.replace(text, "")
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
                        paragraph.text = paragraph.text.replace(text, "")
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

    def _apply_firm_details(self, doc: DocxDocument, firm_details: dict[str, Any]):
        """Apply firm details to signature blocks and firm information"""
        # Find and replace placeholder text with firm details
        for paragraph in doc.paragraphs:
            if "[FIRM_NAME]" in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    "[FIRM_NAME]", firm_details.get("name", "")
                )
                # Add professional redlining to show the change
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if "[FIRM_ADDRESS]" in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    "[FIRM_ADDRESS]", firm_details.get("address", "")
                )
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if "[SIGNER_NAME]" in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    "[SIGNER_NAME]", firm_details.get("signerName", "")
                )
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions
            if "[SIGNER_TITLE]" in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    "[SIGNER_TITLE]", firm_details.get("signerTitle", "")
                )
                for run in paragraph.runs:
                    run.font.underline = True
                    run.font.color.rgb = RGBColor(255, 0, 0)  # Red for additions

    def _apply_firm_details_chunked(
        self, doc: DocxDocument, firm_details: dict[str, Any]
    ):
        """Apply firm details to large documents with chunked processing"""
        logger.info("Applying firm details to large document")
        chunk_size = 500
        total_paragraphs = len(doc.paragraphs)

        for i in range(0, total_paragraphs, chunk_size):
            chunk_end = min(i + chunk_size, total_paragraphs)

            for j in range(i, chunk_end):
                if j < len(doc.paragraphs):
                    paragraph = doc.paragraphs[j]

                    if "[FIRM_NAME]" in paragraph.text:
                        paragraph.text = paragraph.text.replace(
                            "[FIRM_NAME]", firm_details.get("name", "")
                        )
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if "[FIRM_ADDRESS]" in paragraph.text:
                        paragraph.text = paragraph.text.replace(
                            "[FIRM_ADDRESS]", firm_details.get("address", "")
                        )
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if "[SIGNER_NAME]" in paragraph.text:
                        paragraph.text = paragraph.text.replace(
                            "[SIGNER_NAME]", firm_details.get("signerName", "")
                        )
                        for run in paragraph.runs:
                            run.font.underline = True
                            run.font.color.rgb = RGBColor(255, 0, 0)
                    if "[SIGNER_TITLE]" in paragraph.text:
                        paragraph.text = paragraph.text.replace(
                            "[SIGNER_TITLE]", firm_details.get("signerTitle", "")
                        )
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

            logger.info(f"Applying signature from: {signature_path}")

            # Find "Signed:" text and add signature right after it
            signature_added = False

            for paragraph in doc.paragraphs:
                if "Signed:" in paragraph.text:
                    logger.info(f"Found 'Signed:' in paragraph: {paragraph.text}")

                    # Clear the paragraph and rebuild it with proper signature placement
                    original_text = paragraph.text
                    paragraph.clear()

                    # Split text around "Signed:"
                    parts = original_text.split("Signed:", 1)

                    # Add text before "Signed:"
                    if parts[0].strip():
                        paragraph.add_run(parts[0])

                    # Add "Signed:" text
                    paragraph.add_run("Signed: ")

                    # Add signature image immediately after "Signed:"
                    signature_run = paragraph.add_run()
                    signature_run.add_picture(signature_path, width=Inches(1.2))

                    # Add any remaining text after "Signed:"
                    if len(parts) > 1 and parts[1].strip():
                        paragraph.add_run(parts[1])

                    signature_added = True
                    logger.info("Signature added right next to 'Signed:' text")
                    break

            # If no "Signed:" found, look for signature placeholders
            if not signature_added:
                for paragraph in doc.paragraphs:
                    if "[SIGNATURE]" in paragraph.text:
                        # Replace placeholder with signature
                        paragraph.text = paragraph.text.replace("[SIGNATURE]", "")

                        # Add signature image
                        run = (
                            paragraph.runs[0] if paragraph.runs else paragraph.add_run()
                        )
                        run.add_picture(signature_path, width=Inches(1.5))

                        signature_added = True
                        logger.info("Signature added at placeholder location")
                        break

            # If still no signature added, add at the end
            if not signature_added:
                # Add a new paragraph for signature
                signature_paragraph = doc.add_paragraph()

                # Add "Signed:" text
                signature_paragraph.add_run("Signed: ")

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

    def apply_accepted_changes(
        self, document_path: str, accepted_changes: list, signature_path: str = None
    ) -> dict:
        """
        Apply accepted changes to the document and optionally insert signature

        Args:
            document_path: Path to the original document
            accepted_changes: List of changes that were accepted
            signature_path: Optional path to signature image file

        Returns:
            dict with success status and output path
        """
        try:

            from docx import Document as DocxDocument

            # Load the original document
            doc = DocxDocument(document_path)
            logger.info(f"📄 Applying {len(accepted_changes)} accepted changes")

            # Only process changes if there are any
            if accepted_changes:
                # Build flat list of all paragraphs (including inside tables)
                all_paragraphs = list(doc.paragraphs)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            all_paragraphs.extend(cell.paragraphs)

                # Apply each accepted change
                for change in accepted_changes:
                    try:
                        current_text = change.get("current_text", "")
                        new_text = change.get("new_text", "")

                        if not current_text or not new_text:
                            continue
                        applied = False

                        # Replace text in paragraphs (with whitespace-aware matching)
                        for paragraph in all_paragraphs:
                            target_text = None

                            if current_text in paragraph.text:
                                target_text = current_text
                            else:
                                target_text = self._find_text_with_whitespace(
                                    paragraph.text, current_text
                                )

                            if target_text:
                                if self._replace_text_in_paragraph(
                                    paragraph, target_text, new_text
                                ):
                                    logger.info(
                                        f"✅ Applied change: '{current_text[:30]}...' → '{new_text[:30]}...'"
                                    )
                                    applied = True
                                    break

                        if not applied:
                            logger.warning(
                                f"⚠️ Could not apply change (text not found): '{current_text[:50]}'"
                            )

                    except Exception as e:
                        logger.error(f"Error applying change: {e}")
                        continue
            else:
                logger.info(
                    "📄 No accepted changes to apply - returning document as-is (with signature if provided)"
                )

            # Insert signature if provided
            if signature_path and os.path.exists(signature_path):
                logger.info(f"✍️ Inserting signature from: {signature_path}")
                self._insert_signature(doc, signature_path)

            # Generate output path
            output_path = self._generate_output_path(document_path)

            # Save the document
            doc.save(output_path)
            logger.info(f"💾 Saved redlined document to: {output_path}")

            # Clean up temporary signature file
            if signature_path and os.path.exists(signature_path):
                try:
                    os.remove(signature_path)
                    logger.info("🗑️ Cleaned up temporary signature file")
                except Exception:
                    pass

            return {
                "success": True,
                "output_path": output_path,
                "message": f"Applied {len(accepted_changes)} changes successfully",
            }

        except Exception as e:
            logger.error(f"Error applying accepted changes: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _insert_signature(self, doc, signature_path: str):
        """Insert signature image into the document signature block"""
        try:
            import re

            from docx.shared import Inches

            # Find the "Signed:" or "By:" field in the document
            signature_inserted = False

            for paragraph in doc.paragraphs:
                raw_text = paragraph.text
                text_lower = raw_text.strip().lower()

                # Look for signature line (typically after "Signed:" or near "By:")
                if text_lower.startswith("signed:") or (
                    text_lower.startswith("by:") and "_" in raw_text
                ):
                    # Find ALL underscore sequences so we can insert after the last one
                    underscore_matches = list(re.finditer(r"(_+)", raw_text))

                    if underscore_matches:
                        last_match = underscore_matches[-1]
                        before_underscores = raw_text[: last_match.start()]
                        underscores = last_match.group(0)
                        after_underscores = raw_text[last_match.end() :]

                        # Clear paragraph and rebuild with precise ordering
                        paragraph.clear()

                        if before_underscores:
                            paragraph.add_run(before_underscores)

                        strike_run = paragraph.add_run(underscores)
                        strike_run.font.strike = True

                        # Insert signature immediately after the underscores
                        sig_run = paragraph.add_run()
                        sig_run.add_picture(signature_path, width=Inches(2.0))

                        if after_underscores:
                            paragraph.add_run(after_underscores)
                    else:
                        # No underscores found, just add at end with strikethrough on any existing underscores
                        for run in paragraph.runs:
                            if "_" in run.text:
                                run.font.strike = True
                        paragraph.add_run(" ")
                        sig_run = paragraph.add_run()
                        sig_run.add_picture(signature_path, width=Inches(2.0))

                    signature_inserted = True
                    logger.info(
                        f"✅ Inserted signature after underscores in: {raw_text[:40]}"
                    )
                    break

            if not signature_inserted:
                logger.warning("⚠️ Could not find signature location in document")

        except Exception as e:
            logger.error(f"Error inserting signature: {str(e)}", exc_info=True)

    def _generate_output_path(self, input_path: str) -> str:
        """Generate output path for the processed document"""
        # Create outputs directory if it doesn't exist
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)

        # Get the absolute path to the outputs directory
        base_dir = os.path.abspath(output_dir)
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{name}_redlined_{timestamp}{ext}"
        return os.path.abspath(os.path.join(base_dir, output_filename))
