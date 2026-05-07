"""Phase 3 — PDF audit-trail report renderer.

Public surface:
    render_pass_pdf(asset_id, date) -> Path
"""

from phase3.render_pdf import render_pass_pdf

__all__ = ["render_pass_pdf"]
