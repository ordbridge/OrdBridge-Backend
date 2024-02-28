from mongoengine import Document, StringField


class SatsContract(Document):
    c_hash = StringField(required=True)
    con_hash = StringField(required=True)
    meta = {
        'indexes': [
            {'fields': ['c_hash', 'con_hash'], 'unique': True}
        ]
    }

    def to_dict(self):
        # Convert TokenSale object to a dictionary
        return {
            'c_hash': self.c_hash,
            'con_hash': self.con_hash
        }

