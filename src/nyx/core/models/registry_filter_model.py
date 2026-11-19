from .registry_model import RegistryListModel
from .token_filter_model import TOKEN_PATTERN, SearchToken, TokenFilterModel

__all__ = ["TOKEN_PATTERN", "RegistryFilterModel", "SearchToken"]


class RegistryFilterModel(TokenFilterModel):
    """Filter proxy over a `RegistryListModel`, searching by text and `key:value` tokens.

    The text has to be a part of the display name. Every token has to match too, so
    `tag:logic` keeps the types with a tag containing "logic". All comparing ignores
    case.
    """

    TOKEN_ROLES = {
        "tag": RegistryListModel.Roles.TYPE_TAGS,
        "section": RegistryListModel.Roles.PALETTE_SECTION,
        "id": RegistryListModel.Roles.TYPE_ID,
    }
    TEXT_ROLES = (RegistryListModel.Roles.TYPE_DISPLAY_NAME,)
