"""Risk review service."""

from io import BytesIO

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.snowflake import generate_id
from app.models.risk_review_result import RiskReviewResult
from app.repositories.contract_document_repo import ContractDocumentRepository
from app.repositories.contract_field_repo import ContractFieldRepository
from app.repositories.risk_review_result_repo import RiskReviewResultRepository
from app.services.risk.risk_engine import risk_engine
from app.services.risk.rule_service import RuleService


class RiskReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.rule_service = RuleService(db)
        self.result_repo = RiskReviewResultRepository(db)
        self.field_repo = ContractFieldRepository(db)
        self.doc_repo = ContractDocumentRepository(db)

    async def review_approval(self, approval_order_id: int) -> dict:
        docs = await self.doc_repo.list_by_approval_order(approval_order_id)
        if not docs:
            logger.warning(f"No contract documents found | approval_order_id={approval_order_id}")
            return {
                "status": "no_documents",
                "approval_order_id": approval_order_id,
                "results": [],
                "score": risk_engine.calculate_risk_score([]),
            }

        all_results: list[dict] = []
        for doc in docs:
            fields = await self.field_repo.get_by_document_id(doc.id)
            if not fields:
                logger.warning(f"No extracted fields found, skip review | doc_id={doc.doc_id}")
                continue

            contract_text = doc.parse_text or ""
            doc_results = await self._review_single_document(doc.id, fields, contract_text)
            all_results.extend(doc_results)

        score = risk_engine.calculate_risk_score(all_results)
        logger.info(
            f"Risk review completed | approval_order_id={approval_order_id} "
            f"| total={score['total_count']} | level={score['overall_level']}"
        )

        return {
            "status": "reviewed",
            "approval_order_id": approval_order_id,
            "results": all_results,
            "score": score,
        }

    async def _review_single_document(self, doc_id: int, fields, contract_text: str) -> list[dict]:
        rules = await self.rule_service.list_enabled()
        if not rules:
            logger.warning("No enabled risk rules found")
            return []

        engine_results = await risk_engine.evaluate(rules, fields, contract_text)
        results = [self._build_result_payload(item) for item in engine_results]
        logger.info(f"Document risk review completed | doc_id={doc_id} | risks={len(results)}")
        return results

    async def generate_report(self, approval_order_id: int) -> dict:
        contract_file_name = await self._resolve_contract_file_name(approval_order_id)
        existing_results = await self.result_repo.list_by_approval_order(approval_order_id)
        if existing_results:
            results = [
                {
                    "risk_id": item.risk_id,
                    "approval_order_id": str(approval_order_id),
                    "contract_file_name": contract_file_name,
                    "rule_id": item.rule_id,
                    "risk_level": item.risk_level,
                    "risk_description": item.risk_description,
                    "suggestion": item.suggestion,
                    "source_text": item.source_text,
                    "field_name": item.field_name,
                    "is_valid": bool(item.is_valid),
                }
                for item in existing_results
            ]
            score = risk_engine.calculate_risk_score(results)
        else:
            review_result = await self.review_approval(approval_order_id)
            results = review_result.get("results", [])
            for item in results:
                item["approval_order_id"] = str(approval_order_id)
                item["contract_file_name"] = contract_file_name
            score = review_result.get("score", risk_engine.calculate_risk_score([]))

        high_risks = [item for item in results if item["risk_level"] == "HIGH"]
        medium_risks = [item for item in results if item["risk_level"] == "MEDIUM"]
        low_risks = [item for item in results if item["risk_level"] == "LOW"]

        report = {
            "approval_order_id": str(approval_order_id),
            "overall_level": score.get("overall_level", "NONE"),
            "risk_score": score.get("score", 0),
            "summary": self._build_summary(score, high_risks, medium_risks, low_risks),
            "statistics": {
                "high": len(high_risks),
                "medium": len(medium_risks),
                "low": len(low_risks),
                "total": len(results),
            },
            "high_risks": high_risks,
            "medium_risks": medium_risks,
            "low_risks": low_risks,
        }

        logger.info(
            f"Risk report generated | approval_order_id={approval_order_id} "
            f"| level={report['overall_level']}"
        )
        return report

    async def export_report_pdf(self, approval_order_id: int) -> tuple[str, bytes]:
        report = await self.generate_report(approval_order_id)
        original_file_name = await self._resolve_contract_file_name(approval_order_id) or f"contract_{approval_order_id}.pdf"
        report_name = self._build_pdf_report_name(original_file_name, report.get("overall_level", "LOW"))
        report_text = self._build_pdf_report_text(original_file_name, report)
        return report_name, self._render_pdf_bytes(report_text)

    async def _resolve_contract_file_name(self, approval_order_id: int) -> str | None:
        docs = await self.doc_repo.list_by_approval_order(approval_order_id)
        if not docs:
            return None

        def _is_generated_report(file_name: str | None) -> bool:
            if not file_name:
                return False
            upper_name = file_name.upper()
            return upper_name.startswith("HIGH_") or upper_name.startswith("MEDIUM_") or upper_name.startswith("LOW_")

        docs = sorted(docs, key=lambda item: ((item.created_at or 0), item.id or 0))
        for doc in docs:
            if not _is_generated_report(doc.file_name):
                return doc.file_name
        return docs[0].file_name

    @staticmethod
    def _build_pdf_report_name(original_file_name: str, risk_level: str) -> str:
        name, _, _ext = original_file_name.rpartition(".")
        base_name = name or original_file_name
        return f"{risk_level.upper()}_{base_name}.pdf"

    def _build_pdf_report_text(self, original_file_name: str, report: dict) -> str:
        sections = [
            "合同风险审查报告",
            f"原始文档: {original_file_name}",
            f"审批单ID: {report.get('approval_order_id', '-')}",
            f"总体风险等级: {report.get('overall_level', 'NONE')}",
            f"风险评分: {report.get('risk_score', 0)}",
            f"风险总数: {report.get('statistics', {}).get('total', 0)}",
            "",
            "高风险:",
        ]
        sections.extend(self._format_pdf_risk_lines(report.get("high_risks", [])))
        sections.append("")
        sections.append("中风险:")
        sections.extend(self._format_pdf_risk_lines(report.get("medium_risks", [])))
        sections.append("")
        sections.append("低风险:")
        sections.extend(self._format_pdf_risk_lines(report.get("low_risks", [])))
        return "\n".join(sections)

    @staticmethod
    def _format_pdf_risk_lines(items: list[dict]) -> list[str]:
        if not items:
            return ["- 无"]

        lines: list[str] = []
        for index, item in enumerate(items, start=1):
            lines.append(f"{index}. 文档名称: {item.get('contract_file_name') or '-'}")
            lines.append(f"   风险描述: {item.get('risk_description') or '-'}")
            if item.get("suggestion"):
                lines.append(f"   建议: {item.get('suggestion')}")
            if item.get("source_text"):
                lines.append(f"   原文片段: {item.get('source_text')}")
            lines.append("")
        return lines

    @staticmethod
    def _render_pdf_bytes(report_text: str) -> bytes:
        page_width = 595
        page_height = 842
        margin_x = 50
        top_y = 790
        line_height = 18
        max_chars_per_line = 28
        max_lines_per_page = 38

        wrapped_lines: list[str] = []
        for raw_line in report_text.splitlines():
            if not raw_line:
                wrapped_lines.append("")
                continue

            remaining = raw_line
            while len(remaining) > max_chars_per_line:
                wrapped_lines.append(remaining[:max_chars_per_line])
                remaining = remaining[max_chars_per_line:]
            wrapped_lines.append(remaining)

        pages = [
            wrapped_lines[index:index + max_lines_per_page]
            for index in range(0, max(len(wrapped_lines), 1), max_lines_per_page)
        ]
        if not pages:
            pages = [["合同风险审查报告"]]

        objects: list[bytes] = []

        def add_object(payload: str | bytes) -> int:
            data = payload.encode("utf-8") if isinstance(payload, str) else payload
            objects.append(data)
            return len(objects)

        add_object("<< /Type /Catalog /Pages 2 0 R >>")
        add_object("__PAGES__")

        font_object_id = 3 + len(pages) * 2
        page_object_ids: list[int] = []

        for page_lines in pages:
            content_commands = ["BT", "/F1 11 Tf", f"1 0 0 1 {margin_x} {top_y} Tm"]
            first_line = True
            for line in page_lines:
                if not first_line:
                    content_commands.append(f"0 -{line_height} Td")
                first_line = False
                hex_text = line.encode("utf-16-be").hex().upper() if line else ""
                content_commands.append(f"<{hex_text}> Tj")
            content_commands.append("ET")
            content_stream = "\n".join(content_commands).encode("utf-8")
            content_object_id = add_object(
                b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream"
            )
            page_object_id = add_object(
                (
                    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} {page_height}] "
                    f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> /Contents {content_object_id} 0 R >>"
                )
            )
            page_object_ids.append(page_object_id)

        add_object(
            "<< /Type /Font /Subtype /Type0 /BaseFont /STSong-Light /Encoding /UniGB-UCS2-H /DescendantFonts ["
            "<< /Type /Font /Subtype /CIDFontType0 /BaseFont /STSong-Light "
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (GB1) /Supplement 4 >> >>] >>"
        )

        objects[1] = (
            f"<< /Type /Pages /Count {len(page_object_ids)} /Kids [{' '.join(f'{page_id} 0 R' for page_id in page_object_ids)}] >>"
        ).encode("utf-8")

        buffer = BytesIO()
        buffer.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, obj in enumerate(objects, start=1):
            offsets.append(buffer.tell())
            buffer.write(f"{index} 0 obj\n".encode("ascii"))
            buffer.write(obj)
            buffer.write(b"\nendobj\n")

        xref_offset = buffer.tell()
        buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        buffer.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
        buffer.write(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF"
            ).encode("ascii")
        )
        return buffer.getvalue()

    def _build_summary(self, score: dict, high_risks: list, medium_risks: list, low_risks: list) -> str:
        level = score.get("overall_level", "NONE")
        total_count = score.get("total_count", 0)

        if level == "HIGH":
            top_risk = high_risks[0]["risk_description"] if high_risks else "High risk clauses detected"
            return f"High risk: {total_count} risks found. Focus on: {top_risk}"
        if level == "MEDIUM":
            return f"Medium risk: {total_count} risks found. Review key clauses before approval."
        if level == "LOW":
            return f"Low risk: {total_count} low-level risks found. Overall risk is manageable."
        return "No obvious contract risk found."

    def format_comment_content(self, results: list[dict], score: dict) -> str:
        lines = ["Contract Review Summary", ""]
        lines.append(f"Overall risk level: {score.get('overall_level', 'NONE')}")
        lines.append(f"Risk score: {score.get('score', 0)}")
        lines.append(f"Risk count: {score.get('total_count', 0)}")
        lines.append("")

        for level in ("HIGH", "MEDIUM", "LOW"):
            level_items = [item for item in results if item.get("risk_level") == level]
            if not level_items:
                continue
            lines.append(f"[{level}]")
            for index, item in enumerate(level_items, start=1):
                lines.append(f"{index}. {item.get('risk_description', '')}")
                if item.get("suggestion"):
                    lines.append(f"Suggestion: {item['suggestion']}")
                if item.get("source_text"):
                    lines.append(f"Source: {item['source_text'][:200]}")
            lines.append("")

        return "\n".join(lines)

    async def get_results_by_approval(self, approval_order_id: int) -> list[RiskReviewResult]:
        return await self.result_repo.list_by_approval_order(approval_order_id)

    async def replace_results_for_approval(
        self,
        approval_order_id: int,
        results: list[dict],
    ) -> list[RiskReviewResult]:
        await self.result_repo.delete_by_approval_order(approval_order_id)
        if not results:
            logger.info(f"Risk results cleared | approval_order_id={approval_order_id}")
            return []

        entities: list[RiskReviewResult] = []
        for item in results:
            entities.append(
                RiskReviewResult(
                    id=generate_id(),
                    risk_id=item.get("risk_id") or f"RISK_{generate_id()}",
                    approval_order_id=approval_order_id,
                    rule_id=item.get("rule_id"),
                    risk_level=item.get("risk_level", "LOW"),
                    risk_description=item.get("risk_description", ""),
                    suggestion=item.get("suggestion") or "",
                    source_text=item.get("source_text") or "",
                    field_name=item.get("field_name") or "",
                    is_valid=bool(item.get("is_valid", True)),
                )
            )

        saved = await self.result_repo.bulk_create(entities)
        logger.info(
            f"Risk results saved | approval_order_id={approval_order_id} | count={len(saved)}"
        )
        return saved

    async def validate_result(self, risk_id: str, is_valid: bool) -> bool:
        result = await self.result_repo.get_by_risk_id(risk_id)
        if not result:
            return False
        result.is_valid = is_valid
        await self.result_repo.update(result)
        logger.info(f"Risk result updated | risk_id={risk_id} | is_valid={is_valid}")
        return True

    @staticmethod
    def _build_result_payload(result: dict) -> dict:
        return {
            "risk_id": result.get("risk_id") or f"RISK_{generate_id()}",
            "rule_id": result.get("rule_id"),
            "rule_name": result.get("rule_name", ""),
            "rule_category": result.get("rule_category", ""),
            "risk_level": result.get("risk_level", "LOW"),
            "risk_description": result.get("risk_description", ""),
            "suggestion": result.get("suggestion", ""),
            "source_text": result.get("source_text", ""),
            "field_name": result.get("field_name", ""),
            "is_valid": result.get("is_valid", True),
        }


def get_risk_review_service(db: AsyncSession) -> RiskReviewService:
    return RiskReviewService(db)
