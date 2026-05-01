from backend.app.database import SessionLocal
from sqlalchemy import inspect

db = SessionLocal()
inspector = inspect(db.bind)
columns = [col['name'] for col in inspector.get_columns('courses')]
print("Columnas en la tabla courses:", columns)
print("¿video_promocional existe?", "video_promocional" in columns)
db.close()