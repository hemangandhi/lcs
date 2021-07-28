import re

import googlemaps as gm

from src.schemas import *

@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"}
    },
    "required": ["token"]
})
@ensure_logged_in_user()
def validate(event, context, user=None):
    """
    Given a token, ensure that the token is an unexpired token of the user with the provided email.
    """
    return {"statusCode": 200, "body": user, "isBase64Encoded": False}


def validate_updates(user, updates):
    """
    Ensures that the user is being updated in a legal way. Invariants are explained at line 116 for most fields and
    65 for the registration_status in detail.
    """

    # if the user updating is not provided, we assume the user's updating themselves.
    auth_usr = user

    # quick utilities
    # rejects all updates
    def say_no(x, y, z):
        return False


    # For all fields, we map a regex to a function of the old and new value and the operator being used. The function
    # determines the validity of the update. We "and" all the regexes, so an update is valid for all regexes it matches,
    # not just one.
    validator = {
        # this is a Mongo internal. DO NOT TOUCH.
        '_id': say_no,
        'password': say_no,
        # no hacks on the role object
        '^role$': say_no,
        # can't change email
        'email': say_no,
        # can't change your own votes
        # auth tokens are never given access
        'token': say_no,
    }

    def find_dotted(key):
        """
        Traverse the dictionary, moving down the dots (ie. role.mentor indicates the mentor field within the role object
         within the user).
        """
        curr = user
        for i in key.split('.'):
            if i not in curr:

                # We assume that absence means the addition of a new field, which we allow.
                return None
            curr = curr[i]
        return curr

    def validate(key, op):
        """
        Finds out if a key is present in the object. If it is, ensure that for each regex it matches (from the validator
         - line 116), the validator accepts the change. Returns a boolean.
        """
        usr_attr = find_dotted(key)
        for item in validator:
            if re.match(item, key) is not None:
                if not validator[item](usr_attr, updates[op][key], op):
                    return False
        return True

    # return all the valid updates that can be performed
    return {i: {j: updates[i][j] for j in updates[i] if validate(j, i)} for i in updates}


# TODO: get this to replace the above fn
@ensure_schema({
    "type": "object",
    "properties": {
        "token": {"type": "string"},
        "user_email": {"type": "string", "format": "email"},
        "updates": {
            "type": "object",
            "properties": {
                "$set": {"type": "object"},
                "$inc": {
                    "type": "object",
                    "properties": {
                        "votes": {"type": "number"}
                    },
                    "additionalProperties": False
                },
                "$push": {
                    "type": "object",
                    "properties": {
                        "votes_from": {"type": "string", "format": "email"},
                        "skipped_users": {"type": "string", "format": "email"}
                    },
                    "additionalProperties": False
                }
            },
            "additionalProperties": False
        }
    },
    "required": ["user_email", "token", "updates"]
})
@ensure_logged_in_user()
def update(event, context, auth_user):
    """
    Given a user email, a token, and the dictionary of updates, performs all updates the
    authorised user is permitted to, from the "updates" object, on the user with email "user_email".
    """

    user_coll = util.coll('users')

    # assuming the user is authorised through the token, find the user being modified.
    # if the user making changes is the same the one to be updated, no need for extra lookups
    if event['user_email'] == auth_user['email']:
        # save a query in the nice case
        results = auth_user
    else:
        return {"statusCode": 403, "body": "Permission denied"}

    # ensure that the user was indeed found.
    if results is None or results == [] or results == {}:
        return {"statusCode": 400, "body": "User email not found."}

    # validate the updates, passing only the allowable ones through.
    updates = validate_updates(results, event['updates'], auth_user)

    # update the user and report success.
    user_coll.update_one({'email': event['user_email']}, updates)
    return {"statusCode": 200, "body": "Successful request."}
