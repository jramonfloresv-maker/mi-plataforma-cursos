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

def actualizar_imagen_curso(curso_id, imagen_url):
    try:
        with engine.connect() as conn:
            conn.execute(
                text("UPDATE courses SET thumbnail = :url WHERE id = :id"),
                {"url": imagen_url, "id": curso_id}
            )
            conn.commit()
            print(f"✅ Imagen actualizada para curso ID {curso_id}")
            return True
    except Exception as e:
        print(f"❌ Error al actualizar imagen: {e}")
        return False

print("📦 Actualizando base de datos...")
print("=" * 50)

# 1. Agregar columna thumbnail si no existe
add_column_if_not_exists("thumbnail", "VARCHAR")

# 2. Agregar otras columnas que ya tenías
add_column_if_not_exists("course_version", "VARCHAR DEFAULT 'recorded'")
add_column_if_not_exists("sandbox_url", "VARCHAR")
add_column_if_not_exists("mentor_hours", "INTEGER DEFAULT 0")
add_column_if_not_exists("projects_count", "INTEGER DEFAULT 0")
add_column_if_not_exists("includes_certificate", "BOOLEAN DEFAULT TRUE")
add_column_if_not_exists("includes_dc3", "BOOLEAN DEFAULT FALSE")

print("=" * 50)

# 3. Actualizar imagen del curso ISO 14001 (ID 12)
# URL transformada de Cloudinary para banner horizontal
imagen_iso = "https://res.cloudinary.com/dykdvhixb/image/upload/c_fill,w_1200,h_400,g_auto/v1777843509/iso14001_portada_kmddtj.jpg"

print("\n🖼️ Actualizando imagen del curso ISO 14001...")
actualizar_imagen_curso(12, imagen_iso)

print("\n✅ Actualización completada")