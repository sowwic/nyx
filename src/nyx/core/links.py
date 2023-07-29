from nyx.core._invertible_dict import InvertibleDict


class Links(InvertibleDict):
    def serialize(self) -> dict:
        # TODO: add optional validation
        return self._forward

    def deserialize(self, data: dict):
        for key, value in data.items():
            self[key] = value
