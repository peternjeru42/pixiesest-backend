from rest_framework.response import Response


def success(data=None, message=None, status=200):
    payload = {"success": True, "data": data}
    if message:
        payload["message"] = message
    return Response(payload, status=status)


def error(message, code=None, status=400, details=None):
    payload = {"success": False, "error": {"message": message}}
    if code:
        payload["error"]["code"] = code
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=status)
