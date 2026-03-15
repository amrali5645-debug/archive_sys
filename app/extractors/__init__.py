"""Extractor plugin interfaces and registry."""

from .base import BaseExtractor, ExtractResult
from .registry import ExtractorRegistry
from .text_extractor import PlainTextExtractor
