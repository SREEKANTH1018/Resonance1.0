import asyncio
import importlib
import importlib.util
import inspect
import os
import sys

# Loads a teammate's trained model as an in-process callable for "local" mode.
#
# Contract for the local module (see docs/ENGINES_CONTRACT.md):
#   - exposes `predict(payload: dict) -> dict`  (sync or async)
#   - optionally exposes `warmup()` to load weights once; it is called a single
#     time on first use, inside a worker thread, before the first predict().
#
# Target string forms (ARGUS_<PREFIX>_LOCAL):
#   "pkg.module"                      -> attribute `predict`
#   "pkg.module:run"                  -> attribute `run`
#   "D:\\models\\clf.py"              -> file, attribute `predict`
#   "D:\\models\\clf.py:run"          -> file, attribute `run`
#   "/abs/path/model.py:predict"      -> file, attribute `predict`

_CALLABLES = {}  # target string -> resolved callable (cached after first load)


class LocalEngineError(RuntimeError):
    pass


def _split_target(target):
    attr = "predict"
    body = target
    if ":" in target:
        head, tail = target.rsplit(":", 1)
        if tail.isidentifier():           # ignores the ':' in "D:\..."
            body, attr = head, tail
    return body, attr


def _looks_like_file(body):
    return (
        body.endswith(".py")
        or os.path.sep in body
        or (os.path.altsep and os.path.altsep in body)
    )


def _load_module_from_file(file_path):
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise LocalEngineError(f"Local engine file not found: {file_path}")

    directory = os.path.dirname(file_path)
    if directory and directory not in sys.path:
        # append, not insert(0): still lets the model file import its siblings,
        # without a teammate's utils.py / config.py shadowing the backend's.
        sys.path.append(directory)

    mod_name = "argus_local_" + os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(mod_name, file_path)
    if spec is None or spec.loader is None:
        raise LocalEngineError(f"Cannot build import spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module        # register BEFORE exec so pickle/relative imports resolve
    try:
        spec.loader.exec_module(module)
    except Exception as exc:              # noqa: BLE001 - surface any import-time failure
        sys.modules.pop(mod_name, None)
        raise LocalEngineError(f"Failed to import local engine '{file_path}': {exc}") from exc
    return module


def load_target(target):
    """Import the module, run warmup() once, return the callable. Cached."""
    target = target.strip()
    if target in _CALLABLES:
        return _CALLABLES[target]

    body, attr = _split_target(target)
    if _looks_like_file(body):
        module = _load_module_from_file(body)
    else:
        try:
            module = importlib.import_module(body)
        except Exception as exc:          # noqa: BLE001
            raise LocalEngineError(f"Cannot import local engine module '{body}': {exc}") from exc

    fn = getattr(module, attr, None)
    if not callable(fn):
        raise LocalEngineError(f"Local engine '{target}' has no callable '{attr}'")

    warmup = getattr(module, "warmup", None)
    if callable(warmup):
        try:
            warmup()
        except Exception as exc:          # noqa: BLE001
            raise LocalEngineError(f"warmup() failed for local engine '{target}': {exc}") from exc

    _CALLABLES[target] = fn
    return fn


async def call_local(target, payload, lock):
    """Run local inference off the event loop, serialised per engine.

    The per-engine lock matters: most torch modules are not safe under concurrent
    forward() from the shared thread pool, and the failure there is silent wrong
    output, not an exception.
    """
    async with lock:
        fn = await asyncio.to_thread(load_target, target)   # first call may load weights
        if asyncio.iscoroutinefunction(fn):
            return await fn(payload)
        result = await asyncio.to_thread(fn, payload)
        if inspect.isawaitable(result):        # e.g. an object with async __call__
            result = await result
        return result
