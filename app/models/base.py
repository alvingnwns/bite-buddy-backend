from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelModel(BaseModel):
    """
    Base model for all schemas in BiteBuddy.
    Automatically converts python snake_case fields to camelCase in JSON responses,
    and accepts camelCase fields from JSON requests.
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
