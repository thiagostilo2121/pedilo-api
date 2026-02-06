-- Migración: Sistema de Toppings
-- Fecha: 2026-02-05
-- Descripción: Agrega tablas y columnas para el sistema de toppings/extras

-- ============================================================
-- 1. AGREGAR COLUMNA A TABLA EXISTENTE
-- ============================================================

-- Agregar columna toppings_seleccionados a pedido_items
ALTER TABLE pedido_items 
ADD COLUMN IF NOT EXISTS toppings_seleccionados JSONB DEFAULT '[]'::jsonb;

-- ============================================================
-- 2. CREAR NUEVAS TABLAS
-- ============================================================

-- Tabla: grupos_topping
CREATE TABLE IF NOT EXISTS grupos_topping (
    id SERIAL PRIMARY KEY,
    negocio_id INTEGER NOT NULL REFERENCES negocios(id),
    nombre VARCHAR NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_grupos_topping_negocio_id ON grupos_topping(negocio_id);

-- Tabla: toppings (opciones individuales)
CREATE TABLE IF NOT EXISTS toppings (
    id SERIAL PRIMARY KEY,
    grupo_id INTEGER NOT NULL REFERENCES grupos_topping(id),
    nombre VARCHAR NOT NULL,
    precio_extra INTEGER DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_toppings_grupo_id ON toppings(grupo_id);

-- Tabla: producto_grupo_topping (relación M:N con configuración)
CREATE TABLE IF NOT EXISTS producto_grupo_topping (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    grupo_id INTEGER NOT NULL REFERENCES grupos_topping(id),
    min_selecciones INTEGER DEFAULT 0,
    max_selecciones INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_producto_grupo_topping_producto_id ON producto_grupo_topping(producto_id);
CREATE INDEX IF NOT EXISTS ix_producto_grupo_topping_grupo_id ON producto_grupo_topping(grupo_id);

-- ============================================================
-- PARA REVERTIR (si es necesario):
-- ============================================================
-- DROP TABLE IF EXISTS producto_grupo_topping;
-- DROP TABLE IF EXISTS toppings;
-- DROP TABLE IF EXISTS grupos_topping;
-- ALTER TABLE pedido_items DROP COLUMN IF EXISTS toppings_seleccionados;
