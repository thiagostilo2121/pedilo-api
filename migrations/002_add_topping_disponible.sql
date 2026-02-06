-- Migration to add 'disponible' column to 'toppings' table
ALTER TABLE toppings ADD COLUMN disponible BOOLEAN DEFAULT TRUE;
