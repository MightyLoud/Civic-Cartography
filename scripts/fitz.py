"""Minimal PyMuPDF-compatible rendering shim backed by pypdfium2.

This repository historically imported ``fitz`` in two governed PDF-map
derivation scripts.  The shim retains only the tiny API surface those scripts
use while avoiding the PyMuPDF AGPL/commercial dependency.  It is not a
general PyMuPDF replacement.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image


class Matrix:
    def __init__(self, x_scale: float, y_scale: float) -> None:
        if x_scale <= 0 or y_scale <= 0:
            raise ValueError("render scales must be positive")
        self.x_scale = float(x_scale)
        self.y_scale = float(y_scale)


class _Rect:
    def __init__(self, width: float, height: float) -> None:
        self.width = float(width)
        self.height = float(height)


class _Pixmap:
    def __init__(self, image: Image.Image) -> None:
        self._image = image
        self.width, self.height = image.size

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._image.save(destination)


class _Page:
    def __init__(self, page: Any) -> None:
        self._page = page
        width, height = page.get_size()
        self.rect = _Rect(width, height)

    def get_pixmap(self, *, matrix: Matrix | None = None, alpha: bool = False) -> _Pixmap:
        matrix = matrix or Matrix(1.0, 1.0)
        if abs(matrix.x_scale - matrix.y_scale) > 1e-9:
            raise ValueError("non-uniform scaling is not supported by this compatibility shim")
        bitmap = self._page.render(scale=matrix.x_scale)
        image = bitmap.to_pil()
        target = (
            int(round(self.rect.width * matrix.x_scale)),
            int(round(self.rect.height * matrix.y_scale)),
        )
        if image.size != target:
            image = image.resize(target, Image.Resampling.LANCZOS)
        if not alpha and image.mode != "RGB":
            image = image.convert("RGB")
        return _Pixmap(image)


class _Document:
    def __init__(self, path: str | Path) -> None:
        self._document = pdfium.PdfDocument(str(path))

    def __len__(self) -> int:
        return len(self._document)

    def __getitem__(self, index: int) -> _Page:
        return _Page(self._document[index])


def open(path: str | Path) -> _Document:
    return _Document(path)
