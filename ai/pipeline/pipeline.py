"""
AI Pipeline 核心模块
整合检测 + OCR，对外提供统一接口
"""
import cv2
import time
from collections import Counter


def _edit_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离（Levenshtein）"""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insert = prev_row[j + 1] + 1
            delete = curr_row[j] + 1
            sub = prev_row[j] + (c1 != c2)
            curr_row.append(min(insert, delete, sub))
        prev_row = curr_row
    return prev_row[-1]


def _group_similar_plates(plates: list, max_distance: int = 1) -> list:
    """
    将相似的车牌分组，返回每组中出现最多的代表车牌。
    同一个车牌被OCR识别为略有不同的字符串时（如 京M76967 vs 京M76961），
    视为同一块车牌，投票合并计数。
    """
    if not plates:
        return []

    # 按出现频率排序
    counter = Counter(plates)
    sorted_plates = [p for p, _ in counter.most_common()]

    groups = []  # [(representative, [all_variants])]
    assigned = set()

    for plate in sorted_plates:
        if plate in assigned:
            continue
        group = [plate]
        assigned.add(plate)
        for other in sorted_plates:
            if other in assigned:
                continue
            # 长度不同或编辑距离 <= max_distance 视为同一车牌
            if _edit_distance(plate, other) <= max_distance:
                group.append(other)
                assigned.add(other)
        groups.append(group)

    # 每组返回出现次数最多的那个（也即 sorted_plates 中的第一个）
    result = []
    for group in groups:
        # 选出组内原始出现次数最多的
        best = max(group, key=lambda p: counter[p])
        # 合并计数
        total_count = sum(counter[p] for p in group)
        result.append((best, total_count))

    return result


class LicensePlatePipeline:
    """
    车牌识别Pipeline
    数据流：frame → 检测 → 裁剪 → OCR → 模糊投票 → 车牌号列表
    """

    def __init__(self, model_path=None, vote_frames=5):
        self.detector = None  # lazy init
        self.ocr = None
        self._model_path = model_path
        self.vote_frames = vote_frames

        self._plate_history = []  # 每帧的识别结果列表
        self._last_result = []
        self._last_process_time = 0
        self._min_interval = 0.5  # 最低处理间隔（秒）

    def _ensure_init(self):
        """延迟初始化，避免导入时加载模型"""
        if self.detector is None:
            from ai.detection.detector import PlateDetector
            from ai.ocr.ocr_engine import PlateOCR
            self.detector = PlateDetector(model_path=self._model_path)
            self.ocr = PlateOCR()

    def process(self, frame):
        if frame is None or frame.size == 0:
            return []

        self._ensure_init()

        current_time = time.time()
        if current_time - self._last_process_time < self._min_interval:
            return self._last_result

        self._last_process_time = current_time

        # Step 1: 检测车牌区域
        detections = self.detector.detect(frame)

        if not detections:
            # 无检测结果也记录空帧，保持投票窗口干净
            result = self._vote_plates([])
            self._last_result = result
            return result

        # Step 2: 裁剪并识别每个车牌
        plates = []
        for det in detections:
            bbox = det["bbox"]
            plate_img = self.detector.crop_plate(frame, bbox)

            # Step 3: OCR识别
            plate_text = self.ocr.recognize(plate_img)

            # 调试：打印原始识别结果
            print(f"[Pipeline] 原始识别: '{plate_text}' | 长度: {len(plate_text)}")

            if plate_text and len(plate_text) >= 5:
                plates.append(plate_text)

        # Step 4: 模糊多帧投票
        result = self._vote_plates(plates)
        self._last_result = result

        # 调试：打印最终结果
        if result:
            print(f"[Pipeline] 确认车牌: {result}")

        return result

    def _vote_plates(self, current_plates):
        """
        多帧投票（带模糊匹配）：
        - 同一车牌因OCR波动产生的变体自动合并计数
        - 需要至少 2 帧确认
        """
        self._plate_history.append(current_plates)

        if len(self._plate_history) > self.vote_frames:
            self._plate_history.pop(0)

        all_plates = []
        for plates in self._plate_history:
            all_plates.extend(plates)

        if not all_plates:
            return []

        # 模糊分组：编辑距离 ≤ 1 视为同一车牌
        grouped = _group_similar_plates(all_plates, max_distance=1)

        # 投票门槛：至少出现 2 次才确认
        threshold = max(2, self.vote_frames // 2)
        result = []
        for plate, count in grouped:
            if count >= threshold:
                result.append(plate)

        return result


# 全局单例
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = LicensePlatePipeline()
    return _pipeline


def process_frame(frame):
    pipeline = get_pipeline()
    return pipeline.process(frame)
