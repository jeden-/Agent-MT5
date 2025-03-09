-- Schemat bazy danych dla zarządzania pozycjami

-- Tabela przechowująca informacje o pozycjach
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    ea_id VARCHAR(50) NOT NULL,
    ticket BIGINT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    position_type VARCHAR(10) NOT NULL, -- BUY, SELL
    volume NUMERIC(10, 2) NOT NULL,
    open_price NUMERIC(15, 5) NOT NULL,
    current_price NUMERIC(15, 5),
    sl NUMERIC(15, 5) DEFAULT 0,
    tp NUMERIC(15, 5) DEFAULT 0,
    profit NUMERIC(15, 2),
    open_time TIMESTAMP NOT NULL,
    close_price NUMERIC(15, 5),
    close_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- OPEN, CLOSED, PENDING, ERROR
    last_update TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sync_status BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    UNIQUE(ea_id, ticket)
);

-- Indeksy
CREATE INDEX IF NOT EXISTS idx_positions_ea_id ON positions(ea_id);
CREATE INDEX IF NOT EXISTS idx_positions_ticket ON positions(ticket);
CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_open_time ON positions(open_time);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);

-- Tabela przechowująca historię modyfikacji pozycji
CREATE TABLE IF NOT EXISTS position_history (
    id SERIAL PRIMARY KEY,
    position_id INTEGER NOT NULL REFERENCES positions(id),
    modification_type VARCHAR(20) NOT NULL, -- UPDATE, CLOSE, SL_MODIFY, TP_MODIFY
    old_value TEXT, -- Przechowuje poprzedni stan pozycji jako JSON
    new_value TEXT, -- Przechowuje nowy stan pozycji jako JSON
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50) -- ID użytkownika/systemu, który dokonał zmiany
);

-- Indeksy
CREATE INDEX IF NOT EXISTS idx_position_history_position_id ON position_history(position_id);
CREATE INDEX IF NOT EXISTS idx_position_history_timestamp ON position_history(timestamp);

-- Funkcja do automatycznej aktualizacji last_update w tabeli positions
CREATE OR REPLACE FUNCTION update_position_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_update = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger na aktualizację timestamp
CREATE TRIGGER update_positions_timestamp
BEFORE UPDATE ON positions
FOR EACH ROW
EXECUTE FUNCTION update_position_timestamp();

-- Funkcja do dodawania wpisu w historii pozycji
CREATE OR REPLACE FUNCTION log_position_change()
RETURNS TRIGGER AS $$
DECLARE
    change_type VARCHAR(20);
    old_json TEXT;
    new_json TEXT;
BEGIN
    -- Określenie typu zmiany
    IF TG_OP = 'UPDATE' THEN
        IF OLD.status != NEW.status AND NEW.status = 'CLOSED' THEN
            change_type := 'CLOSE';
        ELSIF OLD.sl != NEW.sl THEN
            change_type := 'SL_MODIFY';
        ELSIF OLD.tp != NEW.tp THEN
            change_type := 'TP_MODIFY';
        ELSE
            change_type := 'UPDATE';
        END IF;
        
        -- Konwersja do JSON
        old_json := row_to_json(OLD)::TEXT;
        new_json := row_to_json(NEW)::TEXT;
        
        -- Dodanie wpisu w historii
        INSERT INTO position_history (
            position_id, 
            modification_type, 
            old_value, 
            new_value, 
            timestamp
        ) VALUES (
            NEW.id,
            change_type,
            old_json,
            new_json,
            CURRENT_TIMESTAMP
        );
    END IF;
    
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Trigger na zapis do historii
CREATE TRIGGER log_position_changes
AFTER UPDATE ON positions
FOR EACH ROW
EXECUTE FUNCTION log_position_change(); 