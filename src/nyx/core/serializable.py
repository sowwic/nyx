from collections import OrderedDict
import uuid


class Serializable:
    def __init__(self) -> None:
        self.uuid = str(uuid.uuid4())

    def serialize(self) -> OrderedDict:
        """Serialize object ot OrderedDict.

        Returns:
            OrderedDict: serialized data
        """
        data = OrderedDict()
        data["uuid"] = self.uuid
        return data

    def deserialize(self, data: OrderedDict, restore_id=True):
        """Deserialize object from given data.

        Args:
            data (OrderedDict): object data.
            restore_id (bool, optional): if uuid should be restored. Defaults to True.
        """
        if restore_id:
            self.uuid = data["uuid"]
