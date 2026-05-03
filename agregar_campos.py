from backend.app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Agregar campo audiencia
    try:
        conn.execute(text("ALTER TABLE courses ADD COLUMN audiencia TEXT"))
        print("✅ Campo 'audiencia' agregado")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("⚠️ Campo 'audiencia' ya existe")
        else:
            print(f"❌ Error: {e}")

    # Agregar campo modalidad
    try:
        conn.execute(text("ALTER TABLE courses ADD COLUMN modalidad VARCHAR DEFAULT 'online'"))
        print("✅ Campo 'modalidad' agregado")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("⚠️ Campo 'modalidad' ya existe")
        else:
            print(f"❌ Error: {e}")

    conn.commit()
    print("\n✅ Proceso completado")