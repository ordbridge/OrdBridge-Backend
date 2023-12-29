import uuid


def create_uuid_with_time():
    unique_id = uuid.uuid1(node=0, clock_seq=0)
    return str(unique_id)
