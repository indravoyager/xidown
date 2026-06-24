# Use import aliases to prevent naming pollution
from pathlib import Path as _P
from typing import (
    Any as _A,
    Callable as _Cb,
    Dict as _D,
    Union as _U
)

PathLike = _U[str, _P]  # --> str or Path
AnyDict = _D[str, _A]   # --> Dict[str, Any]
AnyCallable = _Cb[..., _A]  # --> (...) -> Any
