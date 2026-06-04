"""
OCR识别模块
使用PaddleOCR PP-OCRv4 进行车牌字符识别
"""
import cv2
import numpy as np

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False


class PlateOCR:
    """车牌OCR识别器（PP-OCRv4 + CLAHE预处理）"""

    def __init__(self):
        self.ocr_engine = None
        self._init_engine()

    def _init_engine(self):
        """初始化 PP-OCRv4 引擎"""
        if not PADDLE_AVAILABLE:
            print("[PlateOCR] PaddleOCR未安装")
            return

        try:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                det_db_box_thresh=0.45,
                det_db_unclip_ratio=1.8,
                use_dilation=True,
                rec_batch_num=6,
            )
            print("[PlateOCR] PP-OCRv4 初始化成功")
        except Exception as e:
            print(f"[PlateOCR] 初始化失败: {e}")
            self.ocr_engine = None

    def recognize(self, plate_img):
        if plate_img is None or plate_img.size == 0:
            return ""
        if not PADDLE_AVAILABLE or not self.ocr_engine:
            return ""

        processed = self._preprocess(plate_img)
        return self._paddle_recognize(processed)

    # ---- 预处理 ----

    def _preprocess(self, img):
        """CLAHE增强 → 双边滤波"""
        h, w = img.shape[:2]
        target_h = 64
        scale = target_h / h
        target_w = int(w * scale)
        target_w = max(target_w, 160)

        resized = cv2.resize(img, (target_w, target_h))

        if len(resized.shape) == 3:
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = resized

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)

        return cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)

    # ---- 识别 ----

    def _paddle_recognize(self, img):
        try:
            result = self.ocr_engine.ocr(img)
            if result is None or len(result) == 0 or result[0] is None:
                return ""

            texts = []
            for line in result[0]:
                if line:
                    text = line[1][0]
                    conf = line[1][1]
                    if conf > 0.5:
                        texts.append(text)

            raw_text = "".join(texts)
            return self._clean_plate_text(raw_text) if raw_text else ""

        except Exception as e:
            print(f"[PlateOCR] 识别失败: {e}")
            return ""

    # ---- 车牌文本清洗 & 校验 ----

    def _clean_plate_text(self, text):
        import re

        text = re.sub(r'[^a-zA-Z0-9一-龥]', '', text)
        text = text.upper()

        if not text or len(text) < 6:
            return ""

        VALID_PROVINCES = set('京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领')

        # --- 省份修复 ---
        province_fix = {
            '原': '京', '惊': '京', '晾': '京', '凉': '京', '景': '京',
            '泸': '沪', '户': '沪', '护': '沪',
            '渐': '浙', '洲': '浙', '折': '浙', '哲': '浙',
            '粵': '粤', '奧': '粤', '奥': '粤',
            '闵': '闽', '门': '闽', '闷': '闽',
            '蜀': '川', '州': '川',
            '黔': '贵', '柱': '贵',
            '滇': '云', '去': '云', '坛': '云',
            '桂': '桂', '佳': '桂',
            '琼': '琼', '穷': '琼',
            '陝': '陕', '闪': '陕',
            '翼': '冀', '粪': '冀',
            '予': '豫', '预': '豫', '像': '豫',
            '卾': '鄂', '噩': '鄂',
            '戆': '赣', '干': '赣',
            '院': '皖', '完': '皖', '晚': '皖',
            '酥': '苏', '办': '苏',
            '缃': '湘', '相': '湘', '箱': '湘',
            '卤': '鲁',
            '普': '晋',
            '朦': '蒙',
            '疗': '辽',
            '古': '吉',
            '里': '黑',
            '亲': '新',
            '宇': '宁',
            '苷': '甘',
            '清': '青', '请': '青',
            '芷': '藏',
            '偷': '渝', '俞': '渝',
            '疆': '新',
        }
        if text and text[0] in province_fix:
            text = province_fix[text[0]] + text[1:]

        # --- 预检 ---
        if text[0] not in VALID_PROVINCES and not text.startswith('WJ'):
            found = False
            for i, ch in enumerate(text):
                if ch in VALID_PROVINCES and len(text) - i >= 6:
                    text = text[i:]
                    found = True
                    break
            if not found:
                return ""

        # --- 数字/字母混淆修复（保护第3位新能源D/F） ---
        char_confusion = str.maketrans({
            'O': '0', 'I': '1', 'L': '1', 'Q': '0',
            'B': '8', 'S': '5', 'Z': '2', 'A': '4',
            'G': '6', 'T': '7',
        })
        if len(text) >= 4:
            text_fixed = text[:3] + text[3:].translate(char_confusion)
        elif len(text) >= 3:
            text_fixed = text[:2] + text[2:].translate(char_confusion)
        else:
            text_fixed = text

        # --- 正则校验 ---
        pattern_normal = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4}[A-Z0-9挂学警港澳]$'
        pattern_new_energy = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-HJ-NP-Z][DF][A-HJ-NP-Z0-9]{5}$'
        pattern_embassy = r'^使\d{6}$'
        pattern_wujing = r'^WJ[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]?\d{4,5}[A-Z]?$'
        all_patterns = [pattern_normal, pattern_new_energy, pattern_embassy, pattern_wujing]

        for p in all_patterns:
            m = re.match(p, text)
            if m:
                return m.group(0)

        if text_fixed != text:
            for p in all_patterns:
                m = re.match(p, text_fixed)
                if m:
                    print(f"[OCR] 混淆修复: '{text}' -> '{m.group(0)}'")
                    return m.group(0)

        # --- 宽松匹配 ---
        loose = re.search(
            r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z0-9][A-HJ-NP-Z0-9]{4,7}[A-HJ-NP-Z0-9挂学警港澳]',
            text_fixed
        )
        if loose:
            c = loose.group(0)
            if len(c) == 7 and re.match(pattern_normal, c):
                print(f"[OCR] 宽松匹配: '{text}' -> '{c}'")
                return c
            if len(c) == 8 and re.match(pattern_new_energy, c):
                print(f"[OCR] 宽松匹配: '{text}' -> '{c}'")
                return c

        # --- 模糊修复 ---
        repaired = self._fuzzy_repair(text_fixed)
        if repaired:
            for p in all_patterns:
                m = re.match(p, repaired)
                if m:
                    print(f"[OCR] 模糊修复: '{text}' -> '{m.group(0)}'")
                    return m.group(0)

        return ""

    def _fuzzy_repair(self, text):
        import re
        if not text or len(text) < 6:
            return None

        VALID_PROVINCES = set('京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领')
        if text[0] not in VALID_PROVINCES and not text.startswith('WJ'):
            return None

        # 修复城市代码位
        if len(text) >= 2 and text[1] in 'O0I1QDSB89':
            for code in 'ABCDEFGHJKLMNPQRSTUVWXYZ':
                candidate = text[0] + code + text[2:]
                if len(candidate) == 7:
                    p = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4}[A-Z0-9挂学警港澳]$'
                elif len(candidate) == 8:
                    p = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-HJ-NP-Z][DF][A-HJ-NP-Z0-9]{5}$'
                else:
                    continue
                if re.match(p, candidate):
                    return candidate

        # 修复新能源D/F位
        if len(text) >= 4:
            prefix, mid, suffix = text[:2], text[2:4], text[4:]
            mid_fix = {'0': 'D', 'O': 'D', 'Q': 'D', 'E': 'F', 'P': 'F'}
            if len(mid) >= 1 and mid[0] in mid_fix:
                candidate = prefix + mid_fix[mid[0]] + mid[1:] + suffix
                p = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-HJ-NP-Z][DF][A-HJ-NP-Z0-9]{5}$'
                if re.match(p, candidate):
                    return candidate

        return None
