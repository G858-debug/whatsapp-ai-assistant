-- Update column name in relevant tables
ALTER TABLE messages RENAME COLUMN content TO message_text;
ALTER TABLE chat_history RENAME COLUMN content TO message_text;