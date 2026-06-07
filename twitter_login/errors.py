class TwitterException(Exception):
    ...


class HTTPError(TwitterException):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f'{status_code}: {message}')


class LoginError(TwitterException):
    ...


class DenyLoginSubtaskError(LoginError):
    ...


class AccountError(TwitterException):
    ...


class AccountSuspended(AccountError):
    ...


class NotLoggedIn(AccountError):
    ...


class MediaUploadError(TwitterException):
    ...


class ResponseError(TwitterException):
    def __init__(self, errors):
        self.errors = errors
        messages = [
            f'"{error["message"]}"'
            for error in errors
            if isinstance(error, dict) and 'message' in error
        ]
        message = (
            'Response error: '
            '\n'.join(messages)
        )
        super().__init__(message)
