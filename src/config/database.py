from mongoengine import connect


def initialize_db(app):
    db_uri = app.config['MONGODB_URI']
    db_name = app.config['MONGODB_NAME']
    connect(db_name, host=db_uri)

