from marshmallow import Schema, fields

class UsageSchema(Schema):
    current = fields.Int()
    limit = fields.Raw()  # Can be Int or 'Unlimited' string/float representation

class UserPermissionsSchema(Schema):
    role = fields.String()
    permissions = fields.Dict(keys=fields.String(), values=fields.Boolean())
    quotas = fields.Dict(keys=fields.String(), values=fields.Nested(UsageSchema))
