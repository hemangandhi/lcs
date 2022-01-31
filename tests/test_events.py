"""
The rough story:
1. creep makes a public and a private event
2. creep updates the private event to add a host (kataomoi)
3. creep tries to query for events
4. kataomoi invites kimino to the private event
"""

from testing_utils import *

import config
from src import event
from src import authorize

import pytest
import mock

user_email = "creep@radiohead.ed"
user_pass = "love"

# By stage 3, creep will have been made.
@pytest.mark.run(order=3)
def test_event_creation_successes():
    # Add admin role to the test user
    # NOTE: we'll remove it in subsequent tests, so assume that order 4 and 5 are
    # reserved for testing the event API and reuse creep from order=6 (as a non-admin)
    usr_dict = {'email': user_email, 'password': user_pass}
    auth = authorize.authorize(usr_dict, None)
    fail_event = {
        "token": auth["body"]["token"],
        "name": "eventful",
        "start_date": "2021-08-16T22:42:00Z-0400",
        "end_date": "2021-08-16T23:42:00Z-0400",
        "event_type": "public"
    }
    assert check_by_schema(
        schema_for_http(403, {"type": "string"}),
        event.create_event(fail_event, None))
    util.coll('users').update_one({'email': user_email}, {'$set': {'is_admin': True}})
    public_event = {
        "token": auth["body"]["token"],
        "name": "eventful",
        "start_date": "2021-08-16T22:42:00Z-0400",
        "end_date": "2021-08-16T23:42:00Z-0400",
        "event_type": "public"
    }
    assert check_by_schema(schema_for_http(200, {
        "type": "object",
        "properties": {
            "name": {"type": "string", "const": "eventful"},
            "start_date": {"type": "string", "const": "2021-08-16T22:42:00Z-0400"},
            "end_date": {"type": "string", "const": "2021-08-16T23:42:00Z-0400"},
            "event_type": {"type": "string", "const": "public"},
            "_id": {"type": "string"}
        },
        "required": ["name", "start_date", "end_date", "event_type", "_id"]
    }), event.create_event(public_event, None))
    private_event = {
        "token": auth["body"]["token"],
        "name": "uneventful",
        "start_date": "2021-08-16T22:42:00Z-0400",
        "end_date": "2021-08-16T23:42:00Z-0400",
        "event_type": "private"
    }
    private_response = event.create_event(private_event, None)
    assert check_by_schema(schema_for_http(200, {
        "type": "object",
        "properties": {
            "name": {"type": "string", "const": "uneventful"},
            "start_date": {"type": "string", "const": "2021-08-16T22:42:00Z-0400"},
            "end_date": {"type": "string", "const": "2021-08-16T23:42:00Z-0400"},
            "event_type": {"type": "string", "const": "private"},
            "_id": {"type": "string"}
        },
        "required": ["name", "start_date", "end_date", "event_type", "_id"]
    }), private_response)


@pytest.mark.run(order=4)
def test_event_readn_and_update_successes():
    usr_dict = {'email': user_email, 'password': user_pass}
    auth = authorize.authorize(usr_dict, None)
    event_query = {
        "token": auth["body"]["token"],
        "start_date": "2021-08-16T20:00:00Z-0400",
        "end_date": "2021-08-16T23:45:00Z-0400",
    }
    found_events = event.find_events(event_query, None)
    assert check_by_schema(schema_for_http(200, {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["_id", "name", "start_date", "end_date", "event_type"],
            "properties": {
                "name": {"type": "string"},
                "start_date": {"type": "string", "format": "date-time"},
                "end_date": {"type": "string", "format": "date-time"},
                "event_type": {"type": "string", "enum": ["public", "private"]},
                "_id": {"type": "string"}
            }
        }
    }), found_events)
    assert len(found_events["body"]) == 2
    
