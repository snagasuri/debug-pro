-- First create the exec_sql function
CREATE OR REPLACE FUNCTION exec_sql(sql text)
RETURNS void AS $$
BEGIN
    EXECUTE sql;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION exec_sql(text) TO authenticated;

-- Create the create_tables function that will execute SQL commands
CREATE OR REPLACE FUNCTION create_tables(sql_commands text)
RETURNS void AS $$
BEGIN
    PERFORM exec_sql(sql_commands);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION create_tables(text) TO authenticated;

-- Create functions for individual table creation
CREATE OR REPLACE FUNCTION create_debugging_sessions_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS debugging_sessions (
        id UUID PRIMARY KEY,
        context TEXT NOT NULL,
        error TEXT NOT NULL,
        logs TEXT NOT NULL,
        snapshot_id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        metadata JSONB
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_snapshots_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS snapshots (
        id UUID PRIMARY KEY,
        session_id UUID REFERENCES debugging_sessions(id),
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        storage_path TEXT NOT NULL,
        metadata JSONB,
        CONSTRAINT fk_session
            FOREIGN KEY(session_id)
            REFERENCES debugging_sessions(id)
            ON DELETE CASCADE
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION create_version_history_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS version_history (
        id UUID PRIMARY KEY,
        session_id UUID REFERENCES debugging_sessions(id),
        snapshot_id UUID REFERENCES snapshots(id),
        version INT NOT NULL,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        diff JSONB,
        CONSTRAINT fk_session
            FOREIGN KEY(session_id)
            REFERENCES debugging_sessions(id)
            ON DELETE CASCADE,
        CONSTRAINT fk_snapshot
            FOREIGN KEY(snapshot_id)
            REFERENCES snapshots(id)
            ON DELETE CASCADE
    );
END;
$$ LANGUAGE plpgsql;
