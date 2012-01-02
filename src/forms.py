from wtforms import Form, SelectField, TextField, validators

class UserSearchForm(Form):
    username = TextField('Username')
    realm    = SelectField('Realm', coerce=int)