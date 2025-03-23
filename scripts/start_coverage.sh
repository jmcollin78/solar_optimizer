rm -rf htmlcov/*
echo "Starting coverage tests"
coverage run -m pytest tests/
echo "Starting coverage report"
coverage report
echo "Starting coverage html"
coverage html