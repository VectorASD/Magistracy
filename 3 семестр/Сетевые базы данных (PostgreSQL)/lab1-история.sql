CREATE DATABASE lab1_part1;
\c lab1_part1

    Часть 1:

CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    registered_at TIMESTAMPTZ DEFAULT now(),
    is_premium BOOLEAN DEFAULT false
);
\d+ players

CREATE TABLE characters (
    char_id SERIAL PRIMARY KEY,
    nickname VARCHAR(50) UNIQUE NOT NULL,
    level INT DEFAULT 1 CHECK (level >= 1 AND level <= 100),
    player_id INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_char_player FOREIGN KEY (player_id)
        REFERENCES players (player_id)
        ON DELETE CASCADE   -- при удалении игрока удаляются и его персонажи
);
\d+ characters
\d+ players

    Часть2:

ALTER TABLE players
  ADD COLUMN max_slots INT NOT NULL DEFAULT 4 CHECK (max_slots > 0),
  ADD COLUMN slot_size INT NOT NULL DEFAULT 5 CHECK (slot_size > 0),
  ADD COLUMN has_common_compressor BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN has_uncommon_compressor BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN has_rare_compressor BOOLEAN NOT NULL DEFAULT false;
\d+ players

CREATE TYPE resource_rarity AS ENUM ('Обычный', 'Редкий', 'Эпический', 'Легендарный');
\dT+ resource_rarity

CREATE TABLE resources (
    resource_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    rarity resource_rarity NOT NULL
);
\d+ resources

CREATE TABLE inventory (
    player_id INT NOT NULL,
    slot_number INT NOT NULL CHECK (slot_number > 0),
    resource_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0 CHECK (quantity > 0),
    
    -- Составной первичный ключ: один слот у одного игрока
    CONSTRAINT pk_inventory PRIMARY KEY (player_id, slot_number),

    CONSTRAINT fk_inventory_player FOREIGN KEY (player_id)
        REFERENCES players(player_id) ON DELETE CASCADE,
    CONSTRAINT fk_inventory_resource FOREIGN KEY (resource_id)
        REFERENCES resources(resource_id) ON DELETE RESTRICT
);
ALTER TABLE inventory RENAME COLUMN quantity TO count;
ALTER TABLE inventory ALTER COLUMN count SET DEFAULT 1;
\d+ inventory

CREATE OR REPLACE FUNCTION trg_inventory_validate()
RETURNS TRIGGER AS $$
DECLARE
    p_max_slots INT;
    p_slot_size INT;
    p_common BOOLEAN;
    p_uncommon BOOLEAN;
    p_rare BOOLEAN;
    r_rarity resource_rarity;
BEGIN
    SELECT max_slots, slot_size,
           has_common_compressor, has_uncommon_compressor, has_rare_compressor
    INTO p_max_slots, p_slot_size, p_common, p_uncommon, p_rare
    FROM players WHERE player_id = NEW.player_id;

    SELECT rarity INTO r_rarity
    FROM resources WHERE resource_id = NEW.resource_id;

    IF r_rarity = 'Обычный' AND p_common THEN
        p_slot_size := p_slot_size * 2;
    ELSIF r_rarity = 'Редкий' AND p_uncommon THEN
        p_slot_size := p_slot_size * 2;
    ELSIF r_rarity = 'Эпический' AND p_rare THEN
        p_slot_size := p_slot_size * 2;
    END IF;

    IF NEW.slot_number > p_max_slots THEN
        RAISE EXCEPTION 'Слот % превышает максимум (%) у игрока %', NEW.slot_number, p_max_slots, NEW.player_id;
    END IF;

    IF NEW.count > p_slot_size THEN
        RAISE EXCEPTION 'Количество ресурса не может превышать %, указано %', p_slot_size, NEW.count;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

\df+ trg_inventory_validate
\sf+ trg_inventory_validate

CREATE TRIGGER inventory_validate_trigger
    BEFORE INSERT OR UPDATE ON inventory
    FOR EACH ROW
    EXECUTE FUNCTION trg_inventory_validate();

\d+ inventory
