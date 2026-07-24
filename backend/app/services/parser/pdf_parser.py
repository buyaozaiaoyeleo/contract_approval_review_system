"""PDF 解析器封装

解析策略（按优先级降级）：
1. MinerU (magic-pdf CLI) — 最佳，支持结构提取、表格识别
2. pypdf — 轻量纯 Python 库，提取纯文本作为 fallback

通过子进程调用 magic-pdf CLI 进行解析。
"""

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from loguru import logger


class MinerUPdfParser:
    """PDF 解析器

    优先使用 MinerU，不可用时自动降级到 pypdf 提取纯文本。
    """

    # MinerU 输出目录结构
    OUTPUT_FILES = {
        "full_text": "auto/{name}_middle.json",       # 完整结构化内容
        "markdown": "auto/{name}.md",                 # Markdown 格式
        "content_list": "auto/{name}_content_list.json",  # 内容列表
    }

    async def parse(self, pdf_path: str, output_dir: str | None = None) -> dict:
        """解析 PDF 文件

        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录，不指定则使用临时目录

        Returns:
            {
                "full_text": str,       # 完整文本
                "markdown": str,        # Markdown 格式
                "tables": list[dict],   # 表格数据
                "page_count": int,      # 页数
                "structure": list,      # 结构信息
            }
        """
        pdf_name = Path(pdf_path).stem

        # 优先尝试 MinerU
        try:
            if output_dir is None:
                with TemporaryDirectory() as tmp_dir:
                    return await self._run_mineru(pdf_path, tmp_dir, pdf_name)
            else:
                return await self._run_mineru(pdf_path, output_dir, pdf_name)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"MinerU 不可用，降级到 pypdf | reason={e}")
            return await self._run_pypdf(pdf_path)

    async def _run_mineru(self, pdf_path: str, output_dir: str, pdf_name: str) -> dict:
        """执行 MinerU 解析命令"""
        logger.info(f"MinerU 开始解析 | pdf={pdf_path}")

        # 构建 magic-pdf 命令
        cmd = [
            "magic-pdf",
            "-p", pdf_path,                # 输入 PDF
            "-o", output_dir,              # 输出目录
            "-m", "auto",                  # 自动模式
        ]

        # 执行解析命令（异步子进程）
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")
            logger.error(f"MinerU 解析失败 | returncode={process.returncode} | error={error_msg[:500]}")
            raise RuntimeError(f"MinerU 解析失败: {error_msg[:200]}")

        logger.info(f"MinerU 解析完成 | pdf={pdf_path}")

        # 读取解析结果
        result = self._read_output(output_dir, pdf_name)
        return result

    async def _run_pypdf(self, pdf_path: str) -> dict:
        """使用 pypdf 提取纯文本（轻量 fallback）"""
        logger.info(f"pypdf 开始解析 | pdf={pdf_path}")

        try:
            from pypdf import PdfReader

            def _extract():
                reader = PdfReader(pdf_path)
                page_count = len(reader.pages)
                texts = []
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        texts.append(text)
                return page_count, "\n\n".join(texts)

            # 在线程池中执行（pypdf 是同步的）
            page_count, full_text = await asyncio.to_thread(_extract)

            result = {
                "full_text": full_text,
                "markdown": full_text,   # pypdf 不能生成 markdown
                "tables": [],
                "page_count": page_count,
                "structure": [],
                "parser": "pypdf",
            }
            logger.info(
                f"pypdf 解析完成 | pdf={pdf_path} | pages={page_count} | text_len={len(full_text)}"
            )
            return result

        except ImportError:
            logger.error("pypdf 未安装，请执行: pip install pypdf")
            return self._empty_result("pypdf 未安装")
        except Exception as e:
            logger.warning(f"pypdf 解析失败 | path={pdf_path} | error={e}")
            return self._empty_result(str(e))

    def _read_output(self, output_dir: str, pdf_name: str) -> dict:
        """读取 MinerU 输出文件"""
        auto_dir = Path(output_dir) / "auto"

        full_text = ""
        tables = []
        structure = []

        # 读取中间 JSON（包含完整结构化信息）
        middle_json_path = auto_dir / f"{pdf_name}_middle.json"
        if middle_json_path.exists():
            with open(middle_json_path, encoding="utf-8") as f:
                middle_data = json.load(f)
                structure = middle_data.get("pdf_info", [])
                # 从结构化数据中提取纯文本
                full_text = self._extract_text_from_structure(middle_data)

        # 读取 Markdown（包含表格）
        md_path = auto_dir / f"{pdf_name}.md"
        markdown = ""
        if md_path.exists():
            with open(md_path, encoding="utf-8") as f:
                markdown = f.read()
            tables = self._extract_tables_from_markdown(markdown)

        # 如果中间 JSON 没有文本，回退到 Markdown
        if not full_text and markdown:
            full_text = markdown

        result = {
            "full_text": full_text,
            "markdown": markdown,
            "tables": tables,
            "page_count": len(structure) if structure else 0,
            "structure": structure,
        }
        logger.debug(f"MinerU 解析结果 | pages={result['page_count']} | text_len={len(full_text)}")
        return result

    @staticmethod
    def _extract_text_from_structure(data: dict) -> str:
        """从 MinerU 结构数据中提取纯文本"""
        texts = []
        blocks = data.get("para_blocks", [])
        for block in blocks:
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    content = span.get("content", "")
                    if content:
                        texts.append(content)
        return "\n".join(texts)

    @staticmethod
    def _extract_tables_from_markdown(markdown: str) -> list[dict]:
        """从 Markdown 中提取表格"""
        tables = []
        lines = markdown.split("\n")
        in_table = False
        current_table: list[str] = []

        for line in lines:
            if line.strip().startswith("|") and "|" in line.strip()[1:]:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append({"raw": "\n".join(current_table)})
                    current_table = []
                in_table = False

        if current_table:
            tables.append({"raw": "\n".join(current_table)})

        return tables

    @staticmethod
    def _empty_result(reason: str = "") -> dict:
        """返回空解析结果"""
        return {
            "full_text": "",
            "markdown": "",
            "tables": [],
            "page_count": 0,
            "structure": [],
            "error": reason,
        }


mineru_parser = MinerUPdfParser()
