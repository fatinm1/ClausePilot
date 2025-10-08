-- SQL script to update processing rules to remove hardcoded values
-- This allows firm details to be used instead of hardcoded company/person names

-- Update rules with "JMC Investment LLC" to use placeholder
UPDATE processing_rule
SET instruction = REPLACE(instruction, 'JMC Investment LLC', '[FIRM_NAME]')
WHERE instruction LIKE '%JMC Investment LLC%';

-- Update rules with "John Bagge" to use placeholder
UPDATE processing_rule
SET instruction = REPLACE(instruction, 'John Bagge', '[SIGNER_NAME]')
WHERE instruction LIKE '%John Bagge%';

-- Update rules with "Vice President" to use placeholder
UPDATE processing_rule
SET instruction = REPLACE(instruction, 'Vice President', '[TITLE]')
WHERE instruction LIKE '%Vice President%';

-- Update rules with "Welch Capital Partners" to use placeholder
UPDATE processing_rule
SET instruction = REPLACE(instruction, 'Welch Capital Partners', '[FIRM_NAME]')
WHERE instruction LIKE '%Welch Capital Partners%';

-- Show the updated rules
SELECT id, name, category, instruction
FROM processing_rule
WHERE instruction LIKE '%[FIRM_NAME]%'
   OR instruction LIKE '%[SIGNER_NAME]%'
   OR instruction LIKE '%[TITLE]%';

