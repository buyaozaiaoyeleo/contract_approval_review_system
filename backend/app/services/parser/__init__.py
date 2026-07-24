"""文档解析服务导出"""

from app.services.parser.ocr_parser import PaddleOCRClient, paddle_ocr
from app.services.parser.parser_service import DocumentParserService, get_parser_service
from app.services.parser.pdf_parser import MinerUPdfParser, mineru_parser

__all__ = [
    "DocumentParserService",
    "get_parser_service",
    "MinerUPdfParser",
    "mineru_parser",
    "PaddleOCRClient",
    "paddle_ocr",
]
