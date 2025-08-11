def filter_by_extensions(items, exts):
    exts_lc = {e.lower().lstrip('.') for e in exts}
    return [m for m in items if m.extension.lower() in exts_lc]

def filter_larger_than(items, min_kb):
    limit = max(0, min_kb) * 1024
    return [m for m in items if m.size_bytes >= limit]

def only_text_files(items):
    return [m for m in items if m.is_text]

def brief_view(items):
    human_size = lambda b: (f"{b/1024:.1f} KB" if b < 1_048_576 else f"{b/1_048_576:.2f} MB")
    return [
        {
            "name": m.name,
            "ext": (m.extension or "-"),
            "size": human_size(m.size_bytes),
            "folder": m.parent,
            "modified": m.modified.isoformat(timespec="seconds"),
        }
        for m in items
    ]

def count_by_extension(items):
    from collections import Counter
    c = Counter([m.extension or "-" for m in items])
    return {k: v for k, v in c.most_common()}

def sort_by(items, key_func, reverse=False):
    return sorted(list(items), key=key_func, reverse=reverse)
