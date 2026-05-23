-- Add 'category' column to llm_providers if not exists
ALTER TABLE llm_providers ADD COLUMN category TEXT;
