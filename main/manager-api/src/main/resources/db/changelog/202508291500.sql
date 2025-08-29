-- Add visibility control to agent templates
-- Only show Cheeko, English Teacher, and Puzzle Solver in app
-- -------------------------------------------------------

-- Add is_visible column to ai_agent_template table
ALTER TABLE `ai_agent_template` 
ADD COLUMN `is_visible` tinyint NOT NULL DEFAULT 0 COMMENT '是否在应用中显示（0不显示 1显示）' AFTER `sort`;

-- Set only the first 3 templates as visible: Cheeko, English Teacher, Puzzle Solver
-- Based on the sort order, these should be:
-- sort=1: Cheeko (Default) 
-- sort=2: English Teacher
-- sort=3: The Scientist -> change to Puzzle Solver

-- First, let's set all templates to not visible (0)
UPDATE `ai_agent_template` SET `is_visible` = 0;

-- Then make only the desired ones visible
-- Make Cheeko visible (sort = 1)
UPDATE `ai_agent_template` SET `is_visible` = 1 WHERE `sort` = 1;

-- Make English Teacher visible (sort = 3, which is the English teacher)
UPDATE `ai_agent_template` SET `is_visible` = 1 WHERE `agent_name` LIKE '%英语老师%' OR `agent_name` LIKE '%English%';

-- Change The Scientist to Puzzle Solver for the 3rd visible template
-- Find the existing Puzzle Solver template and update it to be visible with sort = 3
UPDATE `ai_agent_template` 
SET `is_visible` = 1, `sort` = 3 
WHERE `agent_name` = 'Puzzle Solver';

-- Hide The Scientist template (should have higher sort value)
UPDATE `ai_agent_template` 
SET `is_visible` = 0, `sort` = 10 
WHERE `agent_name` = 'The Scientist';