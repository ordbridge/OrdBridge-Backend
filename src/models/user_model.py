from mongoengine import Document, StringField


class UserDetails(Document):
    unisat_address = StringField(required=True)
    metamask_address = StringField(required=False)
    session_key = StringField(required=True, unique=True)
    meta = {
        'indexes': [
            {'fields': ['unisat_address', 'metamask_address'], 'unique': True}
        ]
    }

    def to_dict(self):
        # Convert TokenSale object to a dictionary
        return {
            'unisat_address': self.unisat_address,
            'metamask_address': self.metamask_address,
            'session_key': self.session_key
        }

