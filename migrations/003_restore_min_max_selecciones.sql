-- Migration: Restore min_selecciones and max_selecciones to producto_grupo_topping
-- (These were accidentally dropped)

ALTER TABLE producto_grupo_topping ADD COLUMN min_selecciones INTEGER DEFAULT 0;
ALTER TABLE producto_grupo_topping ADD COLUMN max_selecciones INTEGER DEFAULT 1;
