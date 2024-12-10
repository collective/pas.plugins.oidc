from pas.plugins.oidc import PLUGIN_ID
from pas.plugins.oidc.interfaces import IOIDCControlpanel
from plone import api
from plone.restapi.deserializer import json_body
from plone.restapi.deserializer.controlpanels import ControlpanelDeserializeFromJson
from plone.restapi.deserializer.controlpanels import FakeDXContext
from plone.restapi.interfaces import IDeserializeFromJson
from plone.restapi.interfaces import IFieldDeserializer
from z3c.form.interfaces import IManagerValidator
from zExceptions import BadRequest
from zope.component import adapter
from zope.component import queryMultiAdapter
from zope.interface import implementer
from zope.interface.exceptions import Invalid
from zope.schema import getFields
from zope.schema.interfaces import ValidationError


@implementer(IDeserializeFromJson)
@adapter(IOIDCControlpanel)
class OIDCControlpanelDeserializeFromJson(ControlpanelDeserializeFromJson):
    @property
    def proxy(self):
        portal = api.portal.get()
        plugin = portal.acl_users[PLUGIN_ID]
        return plugin

    def __call__(self, mask_validation_errors=True):
        controlpanel = self.controlpanel
        request = controlpanel.request
        data = json_body(request)

        proxy = self.proxy

        schema_data = {}
        errors = []

        # Make a fake context
        fake_context = FakeDXContext()

        for name, field in getFields(self.schema).items():
            field_data = schema_data.setdefault(self.schema, {})

            if field.readonly:
                continue

            if name in data:
                deserializer = queryMultiAdapter(
                    (field, fake_context, request), IFieldDeserializer
                )
                try:
                    # Make it sane
                    value = deserializer(data[name])
                    # Validate required etc
                    field.validate(value)
                    # Set the value.
                    setattr(proxy, name, value)
                except ValidationError as e:
                    errors.append({"message": e.doc(), "field": name, "error": e})
                except (ValueError, Invalid) as e:
                    errors.append({"message": str(e), "field": name, "error": e})
                else:
                    field_data[name] = value

        # Validate schemata
        for schema, field_data in schema_data.items():
            validator = queryMultiAdapter(
                (self.context, request, None, schema, None), IManagerValidator
            )
            for error in validator.validate(field_data):
                errors.append({"error": error, "message": str(error)})

        if errors:
            for error in errors:
                if mask_validation_errors:
                    # Drop Python specific error classes in order to
                    # be able to better handle errors on front-end
                    error["error"] = "ValidationError"
                error["message"] = api.env.translate(error["message"], context=request)
            raise BadRequest(errors)
