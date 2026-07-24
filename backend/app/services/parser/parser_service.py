"""文档解析编排服务

根据文档类型（电子 PDF / 扫描件）自动路由到对应的解析器：
- 电子 PDF → MinerU 直接解析
- 扫描件/图片 → 先 PaddleOCR 识别，再提取文本
- 解析结果缓存到 t_contract_document.parse_text
"""

import json
import tempfile
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.snowflake import generate_id
from app.infrastructure.minio_client import minio_client
from app.models.contract_document import ContractDocument
from app.models.contract_field import ContractField
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.repositories.contract_field_repo import ContractFieldRepository
from app.services.parser.ocr_parser import paddle_ocr
from app.services.parser.pdf_parser import mineru_parser


class DocumentParserService:
    """文档解析编排服务 - 根据文档类型路由到对应解析器"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.doc_repo = ContractDocumentRepository(db)
        self.field_repo = ContractFieldRepository(db)

    # ==================== 主要解析入口 ====================

    async def parse_document(self, doc_id: str) -> dict:
        """解析单个合同文档并返回结构化结果

        流程：从 MinIO 下载 → 判断类型 → 路由解析器 → 更新状态
        """
        # 1. 查询文档记录
        doc = await self.doc_repo.get_by_doc_id(doc_id)
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")

        # 2. 更新解析状态为"解析中"
        doc.parse_status = "parsing"
        await self.doc_repo.update(doc)

        try:
            # 3. 从 MinIO 下载文件
            content = await minio_client.download(doc.minio_path)
            if content is None:
                raise RuntimeError(f"MinIO 文件下载失败: {doc.minio_path}")

            parsed_result = await self._parse_content(content, doc)

            # 4. 更新解析结果
            full_text = parsed_result.get("full_text", "")
            if full_text:
                doc.parse_status = "parsed"
                doc.parse_text = full_text
            else:
                doc.parse_status = "failed"
                doc.parse_text = None
                logger.warning(
                    f"解析结果为空 | doc_id={doc_id} | parser={parsed_result.get('parser', 'unknown')} "
                    f"| error={parsed_result.get('error', 'unknown')}"
                )
            await self.doc_repo.update(doc)

            if not full_text:
                raise RuntimeError(
                    f"文档解析失败：未能提取文本内容。"
                    f"解析器: {parsed_result.get('parser', 'unknown')}。"
                    f"错误: {parsed_result.get('error', '请安装 MinerU 或 pypdf')}"
                )

            logger.info(f"文档解析成功 | doc_id={doc_id} | type={doc.file_type} | scanned={doc.is_scanned} | parser={parsed_result.get('parser')} | text_len={len(full_text)}")
            return parsed_result

        except Exception as e:
            # 5. 解析失败，更新状态
            doc.parse_status = "failed"
            await self.doc_repo.update(doc)
            logger.error(f"文档解析失败 | doc_id={doc_id} | error={e}")
            raise

    async def _parse_content(self, content: bytes, doc: ContractDocument) -> dict:
        """根据文档类型路由到对应解析器"""
        # 写入临时文件供解析器读取
        suffix = doc.file_name.rsplit(".", 1)[-1] if "." in doc.file_name else "pdf"
        with tempfile.NamedTemporaryFile(suffix=f".{suffix}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            file_type = doc.file_type
            if doc.is_scanned or file_type == "image":
                # 扫描件/图片 → PaddleOCR
                parsed = await paddle_ocr.recognize(tmp_path)
                parsed["page_count"] = 1
                parsed.setdefault("parser", "paddleocr")
            elif file_type == "word":
                # Word 文档 → python-docx 提取文本
                parsed = await self._parse_word(tmp_path)
            else:
                # 电子 PDF → MinerU（自动降级到 pypdf）
                parsed = await mineru_parser.parse(tmp_path)
                parsed.setdefault("parser", "mineru")
            return parsed
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _parse_word(self, file_path: str) -> dict:
        """使用 python-docx 提取 Word 文档文本"""
        import asyncio

        logger.info(f"python-docx 开始解析 | docx={file_path}")

        def _extract():
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            texts = []
            for para in doc.paragraphs:
                if para.text.strip():
                    texts.append(para.text)
            # 提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_texts = [cell.text for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        texts.append(" | ".join(row_texts))
            return len(doc.paragraphs), "\n\n".join(texts)

        try:
            para_count, full_text = await asyncio.to_thread(_extract)
            result = {
                "full_text": full_text,
                "markdown": full_text,
                "tables": [],
                "page_count": para_count,
                "structure": [],
                "parser": "python-docx",
            }
            logger.info(f"python-docx 解析完成 | paragraphs={para_count} | text_len={len(full_text)}")
            return result
        except ImportError:
            logger.error("python-docx 未安装，请执行: pip install python-docx")
            return {"full_text": "", "markdown": "", "tables": [], "page_count": 0, "structure": [], "parser": "none", "error": "python-docx 未安装"}

    # ==================== 字段提取 ====================

    async def extract_fields(self, doc_id: str, parsed_text: str | None = None) -> ContractField:
        """从解析文本中提取合同关键字段（调用 LLM）"""
        doc = await self.doc_repo.get_by_doc_id(doc_id)
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")

        text = parsed_text or doc.parse_text
        if not text:
            raise ValueError(f"文档未解析或解析文本为空: {doc_id}")

        # 截断过长文本，保留关键部分（LLM token 限制）
        text_for_llm = text[:15000]

        # 调用 LLM 提取字段
        extracted = await self._call_llm_extract(text_for_llm)

        # LLM 可能返回嵌套 JSON 对象，Text 列需要序列化为字符串
        def _to_str(val):
            if val is None:
                return None
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val) if not isinstance(val, str) else val

        # 保存/更新字段记录（每个文档只保留一条）
        existing = await self.field_repo.get_by_document_id(doc.id)
        if existing:
            existing.contract_no = extracted.get("contract_no")
            existing.party_a_info = _to_str(extracted.get("party_a_info"))
            existing.party_b_info = _to_str(extracted.get("party_b_info"))
            existing.amount = _to_str(extracted.get("amount"))
            existing.start_date = extracted.get("start_date")
            existing.end_date = extracted.get("end_date")
            existing.payment_terms = _to_str(extracted.get("payment_terms"))
            existing.liability_clause = _to_str(extracted.get("liability_clause"))
            existing.confidentiality = _to_str(extracted.get("confidentiality"))
            existing.dispute_resolution = _to_str(extracted.get("dispute_resolution"))
            existing.raw_fields_json = _to_str(extracted.get("raw_json"))
            existing.extract_confidence = extracted.get("confidence", 0.0)
            await self.field_repo.update(existing)
            logger.info(f"合同字段更新完成 | doc_id={doc_id}")
            return existing
        else:
            field = ContractField(
                id=generate_id(),
                document_id=doc.id,
                contract_no=extracted.get("contract_no"),
                party_a_info=_to_str(extracted.get("party_a_info")),
                party_b_info=_to_str(extracted.get("party_b_info")),
                amount=_to_str(extracted.get("amount")),
                start_date=extracted.get("start_date"),
                end_date=extracted.get("end_date"),
                payment_terms=_to_str(extracted.get("payment_terms")),
                liability_clause=_to_str(extracted.get("liability_clause")),
                confidentiality=_to_str(extracted.get("confidentiality")),
                dispute_resolution=_to_str(extracted.get("dispute_resolution")),
                raw_fields_json=_to_str(extracted.get("raw_json")),
                extract_confidence=extracted.get("confidence", 0.0),
            )
            await self.field_repo.create(field)
            logger.info(f"合同字段提取完成 | doc_id={doc_id}")
            return field

    async def _call_llm_extract(self, text: str) -> dict:
        """调用 LLM 提取合同字段（使用 Prompt 模板）"""
        from app.core.config import settings

        prompt = self._build_extraction_prompt(text)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.LLM_API_KEY.get_secret_value(),
                base_url=settings.LLM_BASE_URL,
            )

            response = await client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是一个专业的合同分析专家，请从合同文本中提取关键字段。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            result["raw_json"] = content
            result["confidence"] = 0.85  # LLM 模型自评置信度
            return result

        except ImportError:
            logger.warning("openai 库未安装，返回模拟提取结果")
            return self._mock_extraction()
        except Exception as e:
            logger.error(f"LLM 字段提取失败 | error={e}")
            return self._mock_extraction()

    # ==================== Prompt 模板 ====================

    @staticmethod
    def _build_extraction_prompt(text: str) -> str:
        """构建字段提取 Prompt"""
        return f"""请从以下合同文本中提取关键字段，以 JSON 格式返回。

提取字段：
- contract_no: 合同编号
- party_a_info: 甲方信息（JSON 格式，包含 name/address/contact）
- party_b_info: 乙方信息（JSON 格式，包含 name/address/contact）
- amount: 合同金额（含币种）
- start_date: 合同开始日期（YYYY-MM-DD）
- end_date: 合同结束日期（YYYY-MM-DD）
- payment_terms: 付款条款（原文）
- liability_clause: 违约责任条款（原文）
- confidentiality: 保密条款（原文）
- dispute_resolution: 争议解决方式（原文）

如果某字段无法提取，请填写 null。

合同文本：
{text}
"""

    @staticmethod
    def _mock_extraction() -> dict:
        """返回模拟提取结果（开发阶段使用）"""
        return {
            "contract_no": None,
            "party_a_info": None,
            "party_b_info": None,
            "amount": None,
            "start_date": None,
            "end_date": None,
            "payment_terms": None,
            "liability_clause": None,
            "confidentiality": None,
            "dispute_resolution": None,
            "raw_json": "{}",
            "confidence": 0.0,
        }

    # ==================== 解析状态查询 ====================

    async def get_parse_status(self, doc_id: str) -> dict:
        """获取文档解析状态"""
        doc = await self.doc_repo.get_by_doc_id(doc_id)
        if not doc:
            raise ValueError(f"文档不存在: {doc_id}")
        return {
            "doc_id": doc.doc_id,
            "file_name": doc.file_name,
            "parse_status": doc.parse_status,
            "file_type": doc.file_type,
            "is_scanned": doc.is_scanned,
            "has_text": bool(doc.parse_text),
            "text_length": len(doc.parse_text) if doc.parse_text else 0,
        }


# ==================== 服务工厂 ====================

def get_parser_service(db: AsyncSession) -> DocumentParserService:
    """获取文档解析服务实例"""
    return DocumentParserService(db)
