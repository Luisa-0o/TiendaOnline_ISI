from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
import os

basedir = os.path.abspath(os.path.dirname(__file__))
sqlite_uri = 'sqlite:///' + os.path.join(basedir, 'db.sqlite3')
pg_uri = os.environ.get('DATABASE_URL')

if not pg_uri:
    raise SystemExit('Setea la variable de entorno DATABASE_URL apuntando a Postgres antes de ejecutar.')

engine_sqlite = create_engine(sqlite_uri)
engine_pg = create_engine(pg_uri)

SessionSQLite = sessionmaker(bind=engine_sqlite)
SessionPG = sessionmaker(bind=engine_pg)

s_sql = SessionSQLite()
s_pg = SessionPG()

meta = MetaData(bind=engine_sqlite)
users_table_sql = Table('users', meta, autoload_with=engine_sqlite)

# asumimos la misma estructura en Postgres (migraciones aplicadas)
meta_pg = MetaData(bind=engine_pg)
users_table_pg = Table('users', meta_pg, autoload_with=engine_pg)

rows = s_sql.execute(select(users_table_sql)).fetchall()
print(f"Usuarios encontrados en sqlite: {len(rows)}")

for r in rows:
    username = r['username']
    email = r['email']
    password_hash = r['password_hash']
    is_admin = bool(r['is_admin'])

    existing = s_pg.execute(select(users_table_pg).where(users_table_pg.c.email == email)).first()
    if existing:
        print(f"Saltando {email}, ya existe en Postgres.")
        continue

    ins = users_table_pg.insert().values(
        username=username,
        email=email,
        password_hash=password_hash,
        is_admin=is_admin
    )
    s_pg.execute(ins)
    print(f"Copiado: {email}")

s_pg.commit()
s_sql.close()
s_pg.close()
print('Transferencia completada.')
