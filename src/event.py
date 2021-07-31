from src.schemas import *
from src import util

@ensure_schema({
    "type": "object",
    "properties": {
        "start_date": {"type": "string", "format": "date-time"}
        "end_date": {"type": "string", "format": "date-time"}
    }
})
