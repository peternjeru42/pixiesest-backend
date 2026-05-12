from rest_framework.exceptions import APIException


class QuotaExceeded(APIException):
    status_code = 400
    default_detail = "Storage quota exceeded."
    default_code = "quota_exceeded"


class GalleryAccessDenied(APIException):
    status_code = 403
    default_detail = "Gallery access denied."
    default_code = "gallery_access_denied"
