# Unmanic API

## Rules regarding endpoint creation:
1. All data will be returned in JSON format.
1. The success status of the data will be returned using HTTP status codes.
    - 200: for all successfully returned data.
    - 400: for errors caused by the client request. (self.STATUS_ERROR_EXTERNAL)
    - 404: for an incorrectly structured API endpoint. (self.STATUS_ERROR_ENDPOINT_NOT_FOUND)
    - 405: for a request to an API endpoint with a disallowed method. (self.STATUS_ERROR_METHOD_NOT_ALLOWED)
    - 500: status for internal errors and exception handling. (self.STATUS_ERROR_INTERNAL)
1. All unsuccessful return codes listed above should be executed with:
   ```
    self.set_status(self.STATUS_ERROR_INTERNAL, reason="Unable to read privacy policy.")
    self.write_error()
   ```
   This will provide an error message in the format of:
   ```
   {
        "error": "500: Unable to read privacy policy.",
        "messages": {},
        "traceback": []
    }
   ```
1. The returned 'error' message should not be parsed by the client application. This message is subject to change.
1. Catch all exceptions with:
    ```
    try:
        ...
    except BaseApiError as bae:
        tornado.log.app_log.error("BaseApiError.{}: {}".format(self.route.get('call_method'), str(bae)))
        return
    except Exception as e:
        self.set_status(self.ERROR_INTERNAL, reason=str(e))
        self.write_error()
    ```
1. All endpoint functions must be wrapped in a broad exception capture as in the example above.
