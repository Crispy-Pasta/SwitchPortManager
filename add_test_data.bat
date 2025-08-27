@echo off
echo Adding test data to production database...

ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (name) VALUES ('Main Campus');\""

ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (name) VALUES ('Building A');\""

ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (name) VALUES ('Building B');\""

ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (name) VALUES ('Data Center');\""

ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"INSERT INTO site (name) VALUES ('Remote Office');\""

echo Verifying data...
ssh janzen@10.50.0.225 "docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c \"SELECT COUNT(*) FROM site;\""

echo Done!
