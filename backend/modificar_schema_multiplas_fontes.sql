-- ═══════════════════════════════════════════════════════════
-- MODIFICAR SCHEMA - SUPORTE A MÚLTIPLAS FONTES
-- ═══════════════════════════════════════════════════════════

-- Adicionar novos campos para múltiplas fontes
ALTER TABLE noticias_crimes 
ADD COLUMN IF NOT EXISTS fonte_principal VARCHAR(100),
ADD COLUMN IF NOT EXISTS fontes_alternativas TEXT[], -- Array de fontes
ADD COLUMN IF NOT EXISTS links_alternativos TEXT[],  -- Array de links
ADD COLUMN IF NOT EXISTS num_fontes INTEGER DEFAULT 1;

-- Migrar dados existentes
UPDATE noticias_crimes 
SET fonte_principal = fonte,
    num_fontes = 1
WHERE fonte_principal IS NULL;

-- Criar índice para busca por similaridade
CREATE INDEX IF NOT EXISTS idx_titulo_trgm ON noticias_crimes 
USING gin (lower(titulo) gin_trgm_ops);

-- Criar índice para múltiplas fontes
CREATE INDEX IF NOT EXISTS idx_num_fontes ON noticias_crimes(num_fontes DESC);

-- Criar função para normalizar título (para deduplicação)
CREATE OR REPLACE FUNCTION normalizar_titulo(titulo TEXT) 
RETURNS TEXT AS $$
BEGIN
    RETURN lower(
        regexp_replace(
            regexp_replace(titulo, '[^a-zA-Z0-9\s]', '', 'g'),
            '\s+', ' ', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Criar índice com título normalizado
CREATE INDEX IF NOT EXISTS idx_titulo_normalizado ON noticias_crimes 
(normalizar_titulo(titulo));

COMMENT ON COLUMN noticias_crimes.fonte_principal IS 'Primeira fonte que noticiou';
COMMENT ON COLUMN noticias_crimes.fontes_alternativas IS 'Outras fontes que noticiaram o mesmo crime';
COMMENT ON COLUMN noticias_crimes.links_alternativos IS 'Links das fontes alternativas';
COMMENT ON COLUMN noticias_crimes.num_fontes IS 'Número total de fontes';

-- Query de exemplo para ver crimes noticiados por múltiplas fontes
-- SELECT titulo, fonte_principal, fontes_alternativas, num_fontes 
-- FROM noticias_crimes 
-- WHERE num_fontes > 1 
-- ORDER BY num_fontes DESC 
-- LIMIT 20;
