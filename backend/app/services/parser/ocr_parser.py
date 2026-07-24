"""PaddleOCR 封装

PaddleOCR 用于识别扫描件（图片型 PDF）中的文字。
支持图片预处理、置信度评估、结果格式化。
"""

import asyncio

from loguru import logger


class PaddleOCRClient:
    """PaddleOCR 客户端封装

    使用 PaddleOCR 的 Python API 进行 OCR 识别。
    支持单张图片和 PDF 转换后的图片序列。
    """

    def __init__(self):
        self._ocr = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """延迟初始化 OCR 引擎（避免启动时加载模型）"""
        if self._initialized:
            return
        try:
            from paddleocr import PaddleOCR

            # 中英文混合识别，使用新版 PaddleOCR API
            self._ocr = PaddleOCR(
                use_angle_cls=True,        # 启用文本方向分类（自动旋转）
                lang="ch",                  # 中文识别
                use_gpu=False,              # 默认 CPU（生产环境可配置 GPU）
                show_log=False,
            )
            self._initialized = True
            logger.info("PaddleOCR 引擎初始化完成")
        except ImportError:
            logger.warning("PaddleOCR 未安装，请执行: pip install paddleocr")
            raise

    async def recognize(self, image_path: str) -> dict:
        """识别单张图片中的文字

        Args:
            image_path: 图片文件路径

        Returns:
            {
                "full_text": str,
                "confidence": float,       # 平均置信度 0-1
                "details": list[dict],     # 逐行识别详情
            }
        """
        self._ensure_initialized()

        logger.info(f"PaddleOCR 开始识别 | image={image_path}")

        # 在线程池中执行（PaddleOCR 同步 API）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._ocr.ocr, image_path, True)

        if result is None or len(result) == 0 or result[0] is None:
            logger.warning(f"PaddleOCR 未识别到文字 | image={image_path}")
            return self._empty_result()

        return self._format_result(result[0])

    async def recognize_pdf_images(self, image_paths: list[str]) -> dict:
        """批量识别 PDF 转换后的多张图片"""
        all_texts = []
        all_details = []
        confidences = []

        for _i, img_path in enumerate(image_paths):
            result = await self.recognize(img_path)
            if result["full_text"]:
                all_texts.append(result["full_text"])
            all_details.extend(result.get("details", []))
            confidences.append(result["confidence"])

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        logger.info(
            f"PaddleOCR 批量识别完成 | images={len(image_paths)} "
            f"| avg_confidence={avg_confidence:.2%}"
        )

        return {
            "full_text": "\n\n".join(all_texts),
            "confidence": round(avg_confidence, 4),
            "details": all_details,
            "page_count": len(image_paths),
        }

    # ==================== 置信度评估 ====================

    @staticmethod
    def evaluate_quality(result: dict, min_confidence: float = 0.7) -> dict:
        """评估 OCR 识别质量"""
        confidence = result.get("confidence", 0)
        status = "good" if confidence >= min_confidence else "low"
        return {
            "status": status,
            "confidence": confidence,
            "needs_review": status == "low",       # 低置信度需要人工复核
            "suggestion": (
                "OCR 识别质量良好" if status == "good"
                else f"OCR 置信度偏低({confidence:.2%})，建议人工复核"
            ),
        }

    # ==================== 工具方法 ====================

    def _format_result(self, ocr_result: list) -> dict:
        """格式化 OCR 结果"""
        full_text_lines = []
        details = []
        confidences = []

        for line in ocr_result:
            if line is None or len(line) < 2:
                continue
            box, (text, confidence) = line
            if text:
                full_text_lines.append(text)
                details.append({
                    "text": text,
                    "confidence": round(confidence, 4),
                    "box": [[int(p[0]), int(p[1])] for p in box],
                })
                confidences.append(confidence)

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "full_text": "\n".join(full_text_lines),
            "confidence": round(avg_confidence, 4),
            "details": details,
        }

    @staticmethod
    def _empty_result() -> dict:
        """返回空识别结果"""
        return {
            "full_text": "",
            "confidence": 0.0,
            "details": [],
        }


paddle_ocr = PaddleOCRClient()
