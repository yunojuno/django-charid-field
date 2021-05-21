class CuidTypeMismatch(ValueError):
    error_message_type = "invalid_type"


class CuidPrefixMismatch(ValueError):
    error_message_type = "invalid_prefix"


class CuidInvalid(ValueError):
    error_message_type = "invalid_cuid"
