"""The lock of the media store, as the pipeline uses it.

The lock is the store's own: `ops_media.StoreLock`, in the lock-aware version of the installed store
(`store_patch/ops_media.py`, made by `store_patch/make_patch.py`). The store's importers take it around "write the
file" + "write the row"; the pipeline takes it for the whole of intake, processing, submit, sync, clean-up and
rollback. So everybody who writes, registers or deletes in the store through its own code does so one at a time,
across processes (GPT's reviews of 08.10.2026: a lock inside the pipeline alone cannot protect a file an importer
has written and not yet registered).

It must be one and the same class for both sides: the pipeline calls the store while it holds the lock, and the lock
is re-entrant only for the object that knows it is already held. Hence the import, and no second implementation here.
"""
try:
    from ops_media import StoreLock as PipelineLock
except ImportError:
    raise ImportError('the media pipeline needs the lock-aware media store: put runtime/media_pipeline/store_patch before '
                      'runtime/server on the Python path (on the server: the patched /opt/kryuk24/ops_media.py)') from None


def require_locking_store(store_class):
    """Refuse to work on a store whose importers do not take the lock: with it a removal could take a file from
    under an importer."""
    if getattr(store_class, 'LOCKING', 0) != 1:
        raise RuntimeError('this media store does not lock its importers (MediaStore.LOCKING is missing); the pipeline does not run on it')
