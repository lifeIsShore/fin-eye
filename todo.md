Both fixes are done. Now you need to generate an Alembic migration to apply the column type change to the actual database:

bash
cd Y:\programing\projects\fin-eye\backend
alembic revision --autogenerate -m "volume_bigint"
alembic upgrade head


Then re-run the seed:

bash
python scripts/seed_live_data.py