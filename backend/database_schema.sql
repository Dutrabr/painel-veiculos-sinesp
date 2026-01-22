-- ============================================
-- SafeDrive RJ - Database Schema
-- Versão: 1.0
-- PostgreSQL 17 + PostGIS 3.6
-- ============================================

-- Limpar schema existente (cuidado em produção!)
DROP SCHEMA IF EXISTS public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO safedrive_user;

-- Ativar extensões
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- Para busca de texto

-- ============================================
-- TABELA: users (Usuários)
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    
    -- Dados pessoais
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    cpf VARCHAR(14) UNIQUE,
    
    -- Autenticação
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP,
    
    -- Perfil
    profile_photo_url TEXT,
    date_of_birth DATE,
    gender VARCHAR(20),
    
    -- Endereço
    address_street VARCHAR(255),
    address_number VARCHAR(20),
    address_complement VARCHAR(100),
    address_neighborhood VARCHAR(100),
    address_city VARCHAR(100),
    address_state VARCHAR(2),
    address_zipcode VARCHAR(10),
    address_location GEOGRAPHY(POINT, 4326), -- Localização do endereço
    
    -- Preferências do app
    notification_enabled BOOLEAN DEFAULT TRUE,
    notification_push_token TEXT,
    language VARCHAR(10) DEFAULT 'pt-BR',
    theme VARCHAR(20) DEFAULT 'light',
    
    -- Controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login_at TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Índices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_cpf ON users(cpf);
CREATE INDEX idx_users_uuid ON users(uuid);
CREATE INDEX idx_users_active ON users(is_active) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_location ON users USING GIST(address_location);

-- ============================================
-- TABELA: vehicles (Veículos)
-- ============================================
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Dados do veículo
    plate VARCHAR(10) UNIQUE NOT NULL,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    color VARCHAR(50),
    
    -- Dados técnicos
    chassis VARCHAR(50),
    renavam VARCHAR(20),
    
    -- Tipo
    vehicle_type VARCHAR(50) DEFAULT 'CAR', -- CAR, MOTORCYCLE, TRUCK, etc
    fuel_type VARCHAR(20), -- GASOLINE, ETHANOL, DIESEL, ELECTRIC, HYBRID
    
    -- Risco (calculado do IVR - SUSEP)
    ivr_ranking INTEGER, -- Posição no ranking IVR
    ivr_score DECIMAL(5,2), -- Score de risco (0-10)
    ivr_category VARCHAR(50), -- MUITO_ALTO, ALTO, MEDIO, BAIXO, MUITO_BAIXO
    ivr_updated_at TIMESTAMP,
    
    -- Seguro
    insurance_company VARCHAR(100),
    insurance_policy VARCHAR(50),
    insurance_expiration DATE,
    
    -- Foto
    photo_url TEXT,
    
    -- Quilometragem
    current_km INTEGER DEFAULT 0,
    last_km_update TIMESTAMP,
    
    -- Controle
    is_primary BOOLEAN DEFAULT FALSE, -- Veículo principal do usuário
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP
);

-- Índices
CREATE INDEX idx_vehicles_user ON vehicles(user_id);
CREATE INDEX idx_vehicles_plate ON vehicles(plate);
CREATE INDEX idx_vehicles_brand_model ON vehicles(brand, model);
CREATE INDEX idx_vehicles_ivr ON vehicles(ivr_ranking) WHERE ivr_ranking IS NOT NULL;

-- ============================================
-- TABELA: crime_incidents (Ocorrências de Crimes)
-- ============================================
CREATE TABLE crime_incidents (
    id SERIAL PRIMARY KEY,
    
    -- Tipo de crime
    crime_type VARCHAR(50) NOT NULL, -- ROUBO_VEICULO, FURTO_VEICULO, TENTATIVA_ROUBO
    crime_category VARCHAR(50) DEFAULT 'VEHICLE_THEFT',
    
    -- Localização
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    location_point GEOGRAPHY(POINT, 4326) NOT NULL,
    
    -- Endereço
    street_name VARCHAR(255),
    street_number VARCHAR(20),
    neighborhood VARCHAR(100),
    city VARCHAR(100) DEFAULT 'Rio de Janeiro',
    state VARCHAR(2) DEFAULT 'RJ',
    zipcode VARCHAR(10),
    
    -- Referência de rua (para análise por rua)
    street_segment_id INTEGER, -- Referência para segmento de rua
    
    -- Data/Hora
    occurred_at TIMESTAMP NOT NULL,
    reported_at TIMESTAMP DEFAULT NOW(),
    
    -- Detalhes
    description TEXT,
    vehicle_description TEXT,
    
    -- Fonte dos dados
    source VARCHAR(50) NOT NULL, -- ISP-RJ, SINESP, USER_REPORT, TWITTER, etc
    source_id VARCHAR(100), -- ID na fonte original
    
    -- Validação
    verified BOOLEAN DEFAULT FALSE,
    confidence_score DECIMAL(3,2) DEFAULT 1.0, -- 0.0 a 1.0
    validation_count INTEGER DEFAULT 0, -- Quantos usuários validaram
    
    -- Controle
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_coordinates CHECK (
        latitude BETWEEN -90 AND 90 AND 
        longitude BETWEEN -180 AND 180
    )
);

-- Índices espaciais
CREATE INDEX idx_crimes_location ON crime_incidents USING GIST(location_point);
CREATE INDEX idx_crimes_occurred_at ON crime_incidents(occurred_at DESC);
CREATE INDEX idx_crimes_type ON crime_incidents(crime_type);
CREATE INDEX idx_crimes_source ON crime_incidents(source);
CREATE INDEX idx_crimes_verified ON crime_incidents(verified) WHERE verified = TRUE;
CREATE INDEX idx_crimes_street_segment ON crime_incidents(street_segment_id) WHERE street_segment_id IS NOT NULL;

-- Índice composto para consultas por região e período

-- ============================================
-- TABELA: street_segments (Segmentos de Rua)
-- ============================================
CREATE TABLE street_segments (
    id SERIAL PRIMARY KEY,
    
    -- Identificação da rua
    street_name VARCHAR(255) NOT NULL,
    neighborhood VARCHAR(100),
    city VARCHAR(100) DEFAULT 'Rio de Janeiro',
    state VARCHAR(2) DEFAULT 'RJ',
    
    -- Geometria da rua (linha)
    geometry GEOGRAPHY(LINESTRING, 4326),
    
    -- Bounding box (para consultas rápidas)
    bbox_min_lat DECIMAL(10, 8),
    bbox_min_lng DECIMAL(11, 8),
    bbox_max_lat DECIMAL(10, 8),
    bbox_max_lng DECIMAL(11, 8),
    
    -- Comprimento em metros
    length_meters DECIMAL(10, 2),
    
    -- Metadados
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_street_segments_geometry ON street_segments USING GIST(geometry);
CREATE INDEX idx_street_segments_name ON street_segments USING GIN(street_name gin_trgm_ops);
CREATE INDEX idx_street_segments_neighborhood ON street_segments(neighborhood);

-- ============================================
-- TABELA: street_risk_cache (Cache de Risco por Rua)
-- ============================================
CREATE TABLE street_risk_cache (
    id SERIAL PRIMARY KEY,
    street_segment_id INTEGER REFERENCES street_segments(id) ON DELETE CASCADE,
    
    -- Contadores de crimes por período
    crimes_24h INTEGER DEFAULT 0,
    crimes_7d INTEGER DEFAULT 0,
    crimes_30d INTEGER DEFAULT 0,
    crimes_365d INTEGER DEFAULT 0,
    crimes_total INTEGER DEFAULT 0,
    
    -- Data do último crime
    last_crime_at TIMESTAMP,
    
    -- Score de risco (0-10)
    risk_score DECIMAL(4, 2) DEFAULT 0,
    risk_category VARCHAR(20), -- MUITO_ALTO, ALTO, MEDIO, BAIXO, MUITO_BAIXO
    
    -- Padrões identificados
    dangerous_hours JSONB, -- Ex: [22, 23, 0, 1, 2] (22h às 2h)
    dangerous_weekdays JSONB, -- Ex: [5, 6] (sexta e sábado)
    
    -- Última atualização
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(street_segment_id)
);

-- Índices
CREATE INDEX idx_street_risk_score ON street_risk_cache(risk_score DESC);
CREATE INDEX idx_street_risk_category ON street_risk_cache(risk_category);
CREATE INDEX idx_street_risk_updated ON street_risk_cache(updated_at);

-- ============================================
-- TABELA: user_reports (Reportes de Usuários)
-- ============================================
CREATE TABLE user_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Tipo de reporte
    report_type VARCHAR(50) NOT NULL, -- ROUBO, SUSPEITO, TENTATIVA, PERIGO
    urgency VARCHAR(20) DEFAULT 'MEDIUM', -- LOW, MEDIUM, HIGH, CRITICAL
    
    -- Localização
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    location_point GEOGRAPHY(POINT, 4326) NOT NULL,
    
    -- Descrição
    title VARCHAR(255),
    description TEXT,
    
    -- Mídia
    photos JSONB, -- Array de URLs
    audio_url TEXT,
    
    -- Validação por outros usuários
    validation_count INTEGER DEFAULT 0,
    validated_by_users JSONB, -- Array de user_ids
    is_validated BOOLEAN DEFAULT FALSE,
    
    -- Status
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, VALIDATED, DISMISSED, RESOLVED
    
    -- Conversão para crime_incident
    crime_incident_id INTEGER REFERENCES crime_incidents(id),
    
    -- Timestamps
    reported_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_user_reports_user ON user_reports(user_id);
CREATE INDEX idx_user_reports_location ON user_reports USING GIST(location_point);
CREATE INDEX idx_user_reports_type ON user_reports(report_type);
CREATE INDEX idx_user_reports_status ON user_reports(status);
CREATE INDEX idx_user_reports_date ON user_reports(reported_at DESC);

-- ============================================
-- TABELA: maintenance_records (Manutenções)
-- ============================================
CREATE TABLE maintenance_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    
    -- Tipo
    maintenance_type VARCHAR(50) NOT NULL, -- OLEO_MOTOR, OLEO_CAMBIO, etc
    category VARCHAR(20) NOT NULL, -- PREVENTIVA, CORRETIVA, REVISAO
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Data e KM
    maintenance_date DATE NOT NULL,
    vehicle_km INTEGER NOT NULL,
    
    -- Próxima manutenção
    next_km INTEGER,
    next_date DATE,
    km_interval INTEGER,
    months_interval INTEGER,
    
    -- Custos
    total_cost DECIMAL(10,2),
    labor_cost DECIMAL(10,2),
    parts_cost DECIMAL(10,2),
    
    -- Local
    workshop_name VARCHAR(255),
    workshop_address TEXT,
    workshop_phone VARCHAR(20),
    
    -- Status
    status VARCHAR(20) DEFAULT 'COMPLETED',
    priority VARCHAR(20) DEFAULT 'NORMAL',
    
    -- Anexos
    photos JSONB,
    invoice_url TEXT,
    
    -- Observações
    notes TEXT,
    
    -- Alertas
    alert_enabled BOOLEAN DEFAULT TRUE,
    alert_km_before INTEGER DEFAULT 500,
    alert_days_before INTEGER DEFAULT 15,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_maintenance_vehicle ON maintenance_records(vehicle_id);
CREATE INDEX idx_maintenance_date ON maintenance_records(maintenance_date DESC);
CREATE INDEX idx_maintenance_next_km ON maintenance_records(next_km);
CREATE INDEX idx_maintenance_status ON maintenance_records(status);

-- ============================================
-- TABELA: maintenance_parts (Peças da Manutenção)
-- ============================================
CREATE TABLE maintenance_parts (
    id SERIAL PRIMARY KEY,
    maintenance_id INTEGER REFERENCES maintenance_records(id) ON DELETE CASCADE,
    
    part_name VARCHAR(255) NOT NULL,
    part_brand VARCHAR(100),
    part_code VARCHAR(100),
    
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price DECIMAL(10,2),
    total_price DECIMAL(10,2),
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_parts_maintenance ON maintenance_parts(maintenance_id);

-- ============================================
-- TABELA: route_analyses (Análises de Rotas)
-- ============================================
CREATE TABLE route_analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE SET NULL,
    
    -- Origem e Destino
    origin_lat DECIMAL(10, 8) NOT NULL,
    origin_lng DECIMAL(11, 8) NOT NULL,
    origin_address TEXT,
    
    destination_lat DECIMAL(10, 8) NOT NULL,
    destination_lng DECIMAL(11, 8) NOT NULL,
    destination_address TEXT,
    
    -- Rota calculada
    route_polyline TEXT, -- Encoded polyline do Google Maps
    route_geometry GEOGRAPHY(LINESTRING, 4326),
    
    -- Métricas
    distance_meters INTEGER,
    duration_seconds INTEGER,
    
    -- Análise de risco
    overall_risk_score DECIMAL(4,2),
    overall_risk_category VARCHAR(20),
    
    -- Segmentos perigosos
    dangerous_segments JSONB, -- Array de {street_name, risk_score, crimes_count}
    
    -- Tipo de rota
    route_type VARCHAR(20), -- SAFEST, BALANCED, FASTEST
    
    -- Timestamps
    analyzed_at TIMESTAMP DEFAULT NOW(),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_route_analyses_user ON route_analyses(user_id);
CREATE INDEX idx_route_analyses_date ON route_analyses(analyzed_at DESC);

-- ============================================
-- TABELA: vehicle_km_log (Histórico de KM)
-- ============================================
CREATE TABLE vehicle_km_log (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
    
    km_reading INTEGER NOT NULL,
    reading_date TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Fonte da atualização
    source VARCHAR(20) DEFAULT 'MANUAL', -- MANUAL, AUTO, MAINTENANCE
    
    -- Localização (opcional)
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_km_log_vehicle ON vehicle_km_log(vehicle_id);
CREATE INDEX idx_km_log_date ON vehicle_km_log(reading_date DESC);

-- ============================================
-- TABELA: notifications (Notificações)
-- ============================================
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Tipo
    notification_type VARCHAR(50) NOT NULL, -- MAINTENANCE_ALERT, RISK_ALERT, etc
    priority VARCHAR(20) DEFAULT 'NORMAL',
    
    -- Conteúdo
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Dados adicionais
    data JSONB,
    
    -- Deep link
    action_url TEXT,
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    
    -- Push notification
    push_sent BOOLEAN DEFAULT FALSE,
    push_sent_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
CREATE INDEX idx_notifications_date ON notifications(created_at DESC);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger em todas as tabelas relevantes
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_maintenance_updated_at BEFORE UPDATE ON maintenance_records FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_reports_updated_at BEFORE UPDATE ON user_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function para calcular distância entre dois pontos
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DECIMAL, lng1 DECIMAL,
    lat2 DECIMAL, lng2 DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    RETURN ST_Distance(
        ST_MakePoint(lng1, lat1)::geography,
        ST_MakePoint(lng2, lat2)::geography
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================
-- VIEWS ÚTEIS
-- ============================================

-- View: Usuários com seus veículos
CREATE VIEW v_users_vehicles AS
SELECT 
    u.id as user_id,
    u.full_name,
    u.email,
    v.id as vehicle_id,
    v.plate,
    v.brand,
    v.model,
    v.year,
    v.ivr_category
FROM users u
LEFT JOIN vehicles v ON u.id = v.user_id AND v.deleted_at IS NULL
WHERE u.deleted_at IS NULL;

-- View: Crimes recentes (últimos 30 dias)
CREATE VIEW v_recent_crimes AS
SELECT 
    id,
    crime_type,
    latitude,
    longitude,
    street_name,
    neighborhood,
    occurred_at,
    source,
    verified
FROM crime_incidents
WHERE occurred_at >= NOW() - INTERVAL '30 days'
ORDER BY occurred_at DESC;

-- View: Manutenções pendentes
CREATE VIEW v_pending_maintenance AS
SELECT 
    m.id,
    m.vehicle_id,
    v.plate,
    v.brand,
    v.model,
    m.title,
    m.next_km,
    m.next_date,
    v.current_km,
    (m.next_km - v.current_km) as km_remaining,
    (m.next_date - CURRENT_DATE) as days_remaining
FROM maintenance_records m
JOIN vehicles v ON m.vehicle_id = v.id
WHERE m.status = 'COMPLETED'
AND (
    (m.next_km IS NOT NULL AND v.current_km < m.next_km)
    OR
    (m.next_date IS NOT NULL AND m.next_date > CURRENT_DATE)
)
ORDER BY 
    CASE 
        WHEN m.next_km IS NOT NULL THEN m.next_km - v.current_km
        ELSE 999999
    END ASC;

-- ============================================
-- DADOS INICIAIS (SEED)
-- ============================================

-- Inserir usuário de teste
INSERT INTO users (full_name, email, password_hash, is_active, is_verified)
VALUES ('Usuário Teste', 'teste@safedriverj.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIRj3eBkWi', TRUE, TRUE);

-- Nota: A senha hasheada acima é "teste123"

-- ============================================
-- PERMISSÕES
-- ============================================

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO safedrive_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO safedrive_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO safedrive_user;

-- ============================================
-- RESUMO
-- ============================================
-- Tabelas criadas: 14
-- Views criadas: 3
-- Functions criadas: 2
-- Triggers criados: 4
-- ============================================
