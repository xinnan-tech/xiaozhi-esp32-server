-- Content Library Data Population Script
-- This script populates the content_library table with music and story metadata

USE `vibrant-vitality`;

-- Clear existing data (optional - comment out if you want to keep existing data)
TRUNCATE TABLE content_library;

-- English Music
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'Baa Baa Black Sheep', 'Baa Baa Black Sheep', 'Baa Baa Black Sheep.mp3', 'music', 'English', '["Baa Baa Black Sheep","baa baa black sheep","black sheep song","sheep song","nursery rhyme sheep","wool song","classic nursery rhyme","baa baa"]', 1),
(UUID(), 'Baby Shark Dance', 'Baby Shark Dance', 'Baby Shark Dance.mp3', 'music', 'English', '["Baby Shark Dance","baby shark","shark song","doo doo doo","baby shark family","shark dance","kids shark song","popular kids song","viral kids song"]', 1),
(UUID(), 'Five Little Animals', 'Five Little Animals', 'Five Little Animals.mp3', 'music', 'English', '["Five Little Animals","five animals","little animals","counting animals","animal counting song","5 little animals","animals song","counting song"]', 1),
(UUID(), 'Five Little Ducks', 'Five Little Ducks', 'Five Little Ducks.mp3', 'music', 'English', '["Five Little Ducks","five ducks","little ducks","duck song","counting ducks","5 little ducks","ducks went swimming","mother duck song","quack quack song"]', 1),
(UUID(), 'Once I Caught A Fish Alive', 'Once I Caught A Fish Alive', 'Once I Caught A Fish Alive.mp3', 'music', 'English', '["Once I Caught A Fish Alive","fish alive","caught a fish","fishing song","fish counting song","1 2 3 4 5 fish","counting fish","fish nursery rhyme"]', 1),
(UUID(), 'Ten Little Dinos', 'Ten Little Dinos', 'Ten Little Dinos.mp3', 'music', 'English', '["Ten Little Dinos","ten dinos","little dinosaurs","dinosaur song","counting dinosaurs","10 little dinos","dino counting song","prehistoric song","kids dinosaur song"]', 1),
(UUID(), 'The Wheels on the Bus', 'The Wheels on the Bus', 'The Wheels on the Bus.mp3', 'music', 'English', '["The Wheels on the Bus","wheels on the bus","bus song","wheels go round and round","children bus song","classic kids song","nursery rhyme bus","preschool bus song"]', 1);

-- Hindi Music (sample entries)
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'चंदा मामा दूर के', 'Chanda Mama Door Ke', 'Chanda Mama Door Ke.mp3', 'music', 'Hindi', '["Chanda Mama Door Ke","चंदा मामा","moon song","hindi nursery rhyme"]', 1),
(UUID(), 'मछली जल की रानी है', 'Machli Jal Ki Rani Hai', 'Machli Jal Ki Rani Hai.mp3', 'music', 'Hindi', '["Machli Jal Ki Rani Hai","मछली जल की रानी","fish song hindi","water queen fish"]', 1);

-- Kannada Music (sample entries)
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'ಆನೆ ಬಂತು ಆನೆ', 'Aane Banthu Aane', 'Aane Banthu Aane.mp3', 'music', 'Kannada', '["Aane Banthu Aane","ಆನೆ ಬಂತು","elephant song kannada"]', 1),
(UUID(), 'ಚಿಕ್ಕ ಚಿಕ್ಕ ಅಂಗಡಿ', 'Chikka Chikka Angadi', 'Chikka Chikka Angadi.mp3', 'music', 'Kannada', '["Chikka Chikka Angadi","ಚಿಕ್ಕ ಅಂಗಡಿ","small shop song"]', 1);

-- Telugu Music (sample entries)
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'చందమామ రావే', 'Chandamama Raave', 'Chandamama Raave.mp3', 'music', 'Telugu', '["Chandamama Raave","చందమామ","moon uncle song telugu"]', 1),
(UUID(), 'చిట్టి చిలకమ్మ', 'Chitti Chilakamma', 'Chitti Chilakamma.mp3', 'music', 'Telugu', '["Chitti Chilakamma","చిట్టి చిలకమ్మ","parrot song telugu"]', 1);

-- Phonics Music (sample entries)
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'ABC Phonics Song', 'ABC Phonics Song', 'ABC Phonics Song.mp3', 'music', 'Phonics', '["ABC Phonics Song","alphabet song","phonics abc","letter sounds"]', 1),
(UUID(), 'Letter A Song', 'Letter A Song', 'Letter A Song.mp3', 'music', 'Phonics', '["Letter A Song","a for apple","phonics a","letter a sounds"]', 1);

-- Adventure Stories
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'a portrait of a cat', 'a portrait of a cat', 'a portrait of a cat.mp3', 'story', 'Adventure', '["portrait of cat","cat portrait","cat story"]', 1),
(UUID(), 'a visit from st nicholas', 'a visit from st nicholas', 'a visit from st nicholas.mp3', 'story', 'Adventure', '["visit from st nicholas","st nicholas","christmas story"]', 1),
(UUID(), 'agent bertie part (1)', 'agent bertie part (1)', 'agent bertie part (1).mp3', 'story', 'Adventure', '["agent bertie","bertie part 1","bertie adventure"]', 1),
(UUID(), 'astropup and the revenge of the parrot', 'astropup and the revenge of the parrot', 'astropup and the revenge of the parrot.mp3', 'story', 'Adventure', '["astropup parrot revenge","astropup revenge","space dog parrot"]', 1),
(UUID(), 'astropup and the ship of birds', 'astropup and the ship of birds', 'astropup and the ship of birds.mp3', 'story', 'Adventure', '["astropup ship birds","astropup birds","space dog birds"]', 1),
(UUID(), 'astropup the hero', 'astropup the hero', 'astropup the hero.mp3', 'story', 'Adventure', '["astropup hero","hero story","space dog hero"]', 1);

-- Bedtime Stories
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'bedtime meditation', 'bedtime meditation', 'bedtime meditation.mp3', 'story', 'Bedtime', '["meditation for sleep","sleep meditation","calm bedtime"]', 1),
(UUID(), 'the sleepy train', 'the sleepy train', 'the sleepy train.mp3', 'story', 'Bedtime', '["sleepy train story","train to dreamland","bedtime train"]', 1),
(UUID(), 'counting sheep', 'counting sheep', 'counting sheep.mp3', 'story', 'Bedtime', '["sheep counting","sleep counting","bedtime counting"]', 1);

-- Educational Stories
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'learn about colors', 'learn about colors', 'learn about colors.mp3', 'story', 'Educational', '["colors lesson","learning colors","color education"]', 1),
(UUID(), 'the water cycle', 'the water cycle', 'the water cycle.mp3', 'story', 'Educational', '["water cycle story","science story","rain cycle"]', 1),
(UUID(), 'counting to ten', 'counting to ten', 'counting to ten.mp3', 'story', 'Educational', '["number story","counting lesson","math story"]', 1);

-- Fairy Tales
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'cinderella', 'cinderella', 'cinderella.mp3', 'story', 'Fairy Tales', '["cinderella story","glass slipper","fairy godmother"]', 1),
(UUID(), 'goldilocks and the three bears', 'goldilocks and the three bears', 'goldilocks and the three bears.mp3', 'story', 'Fairy Tales', '["goldilocks","three bears","porridge story"]', 1),
(UUID(), 'little red riding hood', 'little red riding hood', 'little red riding hood.mp3', 'story', 'Fairy Tales', '["red riding hood","wolf story","grandmother story"]', 1);

-- Fantasy Stories  
INSERT INTO content_library (id, title, romanized, filename, content_type, category, alternatives, is_active) VALUES
(UUID(), 'the magic forest', 'the magic forest', 'the magic forest.mp3', 'story', 'Fantasy', '["magical forest","enchanted woods","fantasy forest"]', 1),
(UUID(), 'dragon and the princess', 'dragon and the princess', 'dragon and the princess.mp3', 'story', 'Fantasy', '["dragon story","princess tale","fantasy adventure"]', 1),
(UUID(), 'the flying carpet', 'the flying carpet', 'the flying carpet.mp3', 'story', 'Fantasy', '["magic carpet","flying adventure","arabian fantasy"]', 1);

-- Show summary
SELECT content_type, category, COUNT(*) as count 
FROM content_library 
GROUP BY content_type, category 
ORDER BY content_type, category;

SELECT COUNT(*) as total_content FROM content_library;