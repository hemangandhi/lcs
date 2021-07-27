from datetime import datetime, timezone, timedelta

# uri should contain auth and default database
DB_URI = "mongodb://{}:{}@127.0.0.1:27017/"
DB_USER = "dat boi"
DB_PASSWORD = "dat boi's secret"
DB_COLLECTIONS = {
    "users": "users",
    "magic links": "magicLinks",
    "events": "events"
}

# Json webtoken
JWT_SECRET = "D9E8A570628A0FC66D267B115BCA343EC31070D68124EA8003494B8676FE32A0"
JWT_ALGO = "HS256"
