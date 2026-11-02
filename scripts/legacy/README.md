# Scripts heredados (NO usar sin revisar)

`fix_db.py` y `transfer_users.py` pertenecen a la versión anterior. `fix_db.py` ejecuta `DROP TABLE` y
`transfer_users.py` no es compatible con SQLAlchemy 2. Se conservan solo como referencia histórica.
Para administradores usa `flask create-admin`; para cambios de esquema, `flask db upgrade`.
