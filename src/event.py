from src.schemas import *
from src import util

from datetime import datetime
from functools import wraps

from bson.objectid import ObjectId

"""
Event schema:
{
  id: Int
  name: String,
  start_time: Date,
  end_time: Date,
  type: String(public | private)
  attendees: [{attendee: String, role: String(host | guest)}]
}
"""

TIMESTAMP_FORMAT_CODE = "%Y-%m-%dT%H:%M:%SZ%z"

def validate_times_in_dict(event):
    parsed_start = datetime.strptime(event['start_date'], TIMESTAMP_FORMAT_CODE)
    parsed_end = datetime.strptime(event['end_date'], TIMESTAMP_FORMAT_CODE)
    if parsed_start > parsed_end:
        raise ValueError("Events ends before it starts")
    return parsed_start, parsed_end

def prepare_event_for_output(event):
    output = dict(**event)
    if "end_date" in output:
        output["end_date"] = output["end_date"].strftime(TIMESTAMP_FORMAT_CODE)
    if "start_date" in output:
        output["start_date"] = output["start_date"].strftime(TIMESTAMP_FORMAT_CODE)
    if "_id" in output: output["_id"] = str(output["_id"])
    print(output)
    return output

@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "start_date": {"type": "string", "format": "date-time"},
        "end_date": {"type": "string", "format": "date-time"}
    },
    "required": ["token", "start_date", "end_date"]
})
@ensure_logged_in_user()
def find_events(event, context, user):
    try:
        parsed_start, parsed_end = validate_times_in_dict(event)
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    events = util.coll('events')
    query = {"$and": [{"$or": [{"type": "public"},
                               {"attendees": {"$elemMatch": {"attendee": user["email"]}}}]},
                      {"start_date": {"$gt": parsed_start}},
                      {"end_date": {"$lt": parsed_end}}]}
    relevant = [prepare_event_for_output(e) for e in events.find(query)]
    if not relevant:
        return {"statusCode": 404, "body": "No events found for the user in the given time frame"}
    return {"statusCode": 200, "body": relevant}

def ensure_event_with_id(id_key="event_id", kw_arg_key=None,
                         on_failure=lambda e, c, m, *a: {"statusCode": 404, "body": m}):
    def wrapper(fn):
        @wraps(fn)
        def wrapped(event, context, *args):
            event_id = ObjectId(event[id_key])
            events = util.coll('events')
            found_event = events.find_one({'_id': event_id})
            if found_event is None:
                return on_failure(event, context, 'Event not found', *args)
            if kw_arg_key is None:
                return fn(event, context, args[0], found_event, *args[1:])
            else:
                return fn(event, context, *args, **{kw_arg_key: found_event})
        return wrapped
    return wrapper

@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "event_id": {"type": "integer"},
        "invited": {"type": "string", "format": "email"},
        "role": {"type": "string", "enum": ["host", "guest"]}
    },
    "required": ["token", "event_id", "invited"]
})
@ensure_logged_in_user()
@ensure_event_with_id()
def invite_to_event(event, context, user, found_event):
    if not any(attn['attendee'] == user['email'] and attn['role'] == 'host' for attn in found_event['attendees']):
        return {"statusCode": 403, "body": "User cannot invite people to this event"}
    events = util.coll('events')
    events.update_one({'id': found_event['id']},
                      {'attendees': {'$push': {'attendee': event['invited'], 'role': event.get('role', 'guest')}}})
    return {"statusCode": 200,
            "body": "Invited {} to event '{}'".format(event['invited'], found_event['name'])}
    
@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "name": {"type": "string"},
        "start_date": {"type": "string", "format": "date-time"},
        "end_date": {"type": "string", "format": "date-time"},
        "event_type": {"type": "string", "enum": ["public", "private"]},
  },
    "required": ["token", "name", "start_date", "end_date", "event_type"]
})
@ensure_logged_in_user()
@ensure_admin_user()
def create_event(event, context, user):
    try:
        parsed_start, parsed_end = validate_times_in_dict(event)
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}

    doc = {
        "name": event["name"],
        "start_date": parsed_start,
        "end_date": parsed_end,
        "event_type": event["event_type"]
    }
    if event["event_type"] == "private":
        doc["attendees"] = [{"attendee": user["email"], "role": "host"}]
    new_id = util.coll('events').insert_one(doc).inserted_id
    doc["_id"] = new_id
    return {"statusCode": 200, "body": prepare_event_for_output(doc)}

@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "event_id": {"type": "string"},
        "updates": {
            "type": "object",
            "properties": {
                "$set": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_time": {"type": "string"},
                        "type": {"type": "string", "enum": ["public", "private"]}
                    },
                    "additionalProperties": False
                },
                "$push": {
                    "type": "object",
                    "properties": {
                        "attendees": {
                            "type": "object",
                            "properties": {
                                "attendee": {"type": "string", "format": "email"},
                                "role": {"type": "string", "enum": ["guest", "host"]}
                            },
                            "additionalProperties": False
                        }
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }
    },
    "required": ["event_id", "token", "updates"]
})
@ensure_logged_in_user()
@ensure_admin_user()
@ensure_event_with_id()
def update_event(event, context, user, found_event):
    times = {
        "start_time": event['updates'].get('$set', {}).get('start_time', found_event['start_time']),
        "end_time": event['updates'].get('$set', {}).get('end_time', found_event['end_time'])
    }
    try:
        validate_times_in_dict(times)
    except Exception as e:
        return {"statusCode": 400, "body": str(e)}
    util.coll('events').update_one({"_id": found_event["_id"]}, event["updates"])
    return {"statusCode": 200, "body": "Updated event."}
