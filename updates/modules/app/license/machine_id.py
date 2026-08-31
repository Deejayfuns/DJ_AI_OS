import hashlib
import platform
import uuid


class MachineID:

    def generate(self):

        system = platform.system()
        node = platform.node()
        processor = platform.processor()
        mac = hex(uuid.getnode())

        raw = f"{system}-{node}-{processor}-{mac}"

        return hashlib.sha256(
            raw.encode()
        ).hexdigest()
