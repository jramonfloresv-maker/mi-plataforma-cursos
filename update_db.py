from backend.app.database import engine
from sqlalchemy import text

def add_column_if_not_exists(column_name, column_type):
    try:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE courses ADD COLUMN {column_name} {column_type}"))
            conn.commit()
            print(f"✅ Columna '{column_name}' agregada")
    except Exception as e:
        if 'duplicate column name' in str(e).lower() or 'already exists' in str(e).lower():
            print(f"⚠️ Columna '{column_name}' ya existe")
        else:
            print(f"❌ Error al agregar '{column_name}': {e}")

print("📦 Actualizando base de datos...")

# Agregar columnas
add_column_if_not_exists("course_version", "VARCHAR DEFAULT 'recorded'")
add_column_if_not_exists("sandbox_url", "VARCHAR")
add_column_if_not_exists("mentor_hours", "INTEGER DEFAULT 0")
add_column_if_not_exists("projects_count", "INTEGER DEFAULT 0")
add_column_if_not_exists("includes_certificate", "BOOLEAN DEFAULT TRUE")
add_column_if_not_exists("includes_dc3", "BOOLEAN DEFAULT FALSE")

print("\n✅ Actualización completada")