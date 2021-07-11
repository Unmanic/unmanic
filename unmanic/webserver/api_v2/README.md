# Unmanic API

## Rules regarding endpoint creation:
1. All data will be returned in JSON format.
1. The success status of the data will be returned using HTTP status codes.
    - 200: for all successfully returned data.
    - 400: for errors caused by the client request.
    - 404: for an incorrectly structured API endpoint.
    - 500: status for internal errors and exception handling.
1. All unsuccessful return codes listed above should be accompanied by at least an error message in the format of:
   ```
   {'error': 'Some error message'}
   ```
1. The returned 'error' message should not be parsed by the client application. This message is subject to change.
1. Catch all exceptions with:
    ```
    try:
        ...
    except Exception as e:
        self.set_status(self.ERROR_INTERNAL, reason=str(e))
        self.write_error()
    ```
1. All endpoint functions must be wrapped in a broad exception capture as in the example above.