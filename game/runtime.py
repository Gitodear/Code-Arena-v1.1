import ast
import sys
import threading
import traceback
from collections import deque

from game.api import PlayerAPI, StopExecution

SCRIPT_FILENAME = "<bot>"

# Builtins available to player code. There is no import, open(), eval(),
# getattr() etc., and the AST check below blocks `_private` / `__dunder__`
# names, which closes the usual ways out of the sandbox.
# NOTE: this is a guard rail for a learning game, not a security boundary -
# only run code you trust.
BASE_BUILTINS = {
    "range": range, "len": len, "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool, "abs": abs,
    "min": min, "max": max, "sum": sum, "sorted": sorted, "enumerate": enumerate,
    "list": list, "dict": dict, "tuple": tuple, "set": set, "zip": zip,
    "reversed": reversed, "round": round, "any": any, "all": all,
    "isinstance": isinstance,
    "Exception": Exception, "ValueError": ValueError,
}

BLOCKED_NODES = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)


class CodeRejected(Exception):
    pass


def validate(tree):
    """Reject code that reaches for private/dunder attributes or imports."""
    for node in ast.walk(tree):
        if isinstance(node, BLOCKED_NODES):
            raise CodeRejected(f"line {node.lineno}: imports and global/nonlocal are not allowed")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise CodeRejected(f"line {node.lineno}: access to '{node.attr}' is not allowed")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise CodeRejected(f"line {node.lineno}: name '{node.id}' is not allowed")


class ScriptRuntime:
    def __init__(self, api):
        self.api = api
        self.thread = None
        self.running = False
        self.messages = deque()     # (kind, text) for the output panel; kind in out/err/info

    # ---- called from the main thread ----
    def start(self, code_str):
        self.stop()
        try:
            tree = ast.parse(code_str, SCRIPT_FILENAME)
            validate(tree)
            code = compile(tree, SCRIPT_FILENAME, "exec")
        except SyntaxError as e:
            self._emit("err", f"SyntaxError (line {e.lineno}): {e.msg}")
            return False
        except CodeRejected as e:
            self._emit("err", f"Not allowed - {e}")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._run, args=(code,), daemon=True)
        self.thread.start()
        return True

    def stop(self):
        was_running = self.thread is not None and self.thread.is_alive()
        if was_running:
            self.api.request_stop()
            self.thread.join(timeout=2)
            if self.thread.is_alive():
                self._emit("err", "Script did not stop in time (stuck in a long built-in call).")
        self.api.clear_stop()
        self.running = False
        return was_running

    def poll_messages(self):
        out = []
        while self.messages:
            out.append(self.messages.popleft())
        return out

    # ---- script thread ----
    def _emit(self, kind, text):
        self.messages.append((kind, text))

    def _print(self, *args, sep=" ", end=""):
        self._emit("out", sep.join(str(a) for a in args))

    def _tracer(self, frame, event, arg):
        # Checked on every line of player code, so even a loop that never calls
        # an api action (e.g. `while True: pass`) can be stopped.
        if frame.f_code.co_filename != SCRIPT_FILENAME:
            return None
        if self.api.stop_requested:
            raise StopExecution()
        return self._tracer

    def _run(self, code):
        builtins = dict(BASE_BUILTINS, print=self._print)
        env = {"__builtins__": builtins, "api": PlayerAPI(self.api)}
        sys.settrace(self._tracer)
        try:
            exec(code, env)
            self._emit("info", "Script finished.")
        except StopExecution:
            pass
        except Exception as e:
            line = None
            for fs in traceback.extract_tb(e.__traceback__):
                if fs.filename == SCRIPT_FILENAME:
                    line = fs.lineno
            where = f" (line {line})" if line else ""
            self._emit("err", f"{type(e).__name__}{where}: {e}")
        finally:
            sys.settrace(None)
            self.running = False
