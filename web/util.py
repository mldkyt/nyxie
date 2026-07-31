from flask import make_response


def quick_response(msg: str, code: int):
    response = make_response(msg)
    response.status_code = code

    return response
