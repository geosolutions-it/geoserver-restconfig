PGPASSWORD=postgres psql -h localhost -U postgres -c "drop database db;"
PGPASSWORD=postgres psql -h localhost -U postgres -c "create database db;"
PGPASSWORD=postgres psql -h localhost -U postgres -d db -c "create extension postgis"
python setup.py test
