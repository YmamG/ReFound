from django.conf import settings
from django.core.files.uploadhandler import FileUploadHandler, StopUpload


class BoundedImageUploadHandler(FileUploadHandler):
    """Abort oversized files while streaming, before form/Pillow decoding."""
    def receive_data_chunk(self, raw_data, start):
        if start + len(raw_data) > settings.REFOUND_MAX_IMAGE_BYTES:
            self.request.refound_upload_too_large = True
            raise StopUpload(connection_reset=True)
        return raw_data

    def file_complete(self, file_size):
        return None
