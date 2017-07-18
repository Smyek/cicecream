from enum import Enum

class SentenceCounters(Enum):
    placeholder = 1
    m_placeholder = 2
    f_placeholder = 3

class SentenceType(Enum):
    good = 1
    bad = 2
    filler = 3

class SentenceCustomMarkers(Enum):
    has_V = 1
    has_exception = 2


class TokenCustomMarkers(Enum):
    is_replaceable = 1
    exception = 2