CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome VARCHAR(100) NOT NULL,
    apelido VARCHAR(32) NOT NULL UNIQUE,
    nascimento DATE NOT NULL,
    stack VARCHAR(32)[]
);
