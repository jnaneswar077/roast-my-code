import difflib

def make_diff(original: str, improved: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(),
        improved.splitlines(),
        lineterm="",
        fromfile="original",
        tofile="improved"
    )
    return "\n".join(diff)
