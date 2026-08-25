from __future__ import annotations

import re
from typing import Any

from app.core.agents.prompts import REQUIRED_REPORT_SECTIONS


REQUIRED_SECTIONS = list(REQUIRED_REPORT_SECTIONS)

SECTION_ALIASES = {
    "复查与补证建议": ("复查与补证建议", "证据缺口与进一步检查", "证据缺口与进一步判断"),
}

MIN_MARKDOWN_CHARS = 300
MAX_LIST_LINE_RATIO = 0.70
MIN_NARRATIVE_LINES = 4
MIN_NARRATIVE_CHARS = 220
INTERNAL_PROCESS_PATTERNS = (
    r"所有专家一致(?:认为|认定)",
    r"专家一致(?:认为|认定)",
    r"支持点",
    r"矛盾点",
    r"会诊摘要",
    r"内部(?:讨论|会诊)",
)

_WEAK_SENTENCE_PATTERNS = (
    re.compile(r"建议结合后续观察"),
    re.compile(r"图像线索存在分歧"),
)

_CONCRETE_SIGNAL_PATTERN = re.compile(
    r"(病斑|叶片|叶背|边界|黄化|坏死|霉层|分布|受害|主诊断|鉴别|证据|缺口|补证|复拍|观察|复查|可选|进一步|48\s*小时|今天|升级|避免|禁止|风险|节点|预后)"
)
_PERCENT_PATTERN = re.compile(r"\d+(?:\.\d+)?%")
_HIGH_RISK_MEDICATION_PATTERN = re.compile(
    r"(喷施|喷雾|药剂|杀菌剂|杀虫剂|铜制剂|抗生素|化学防治|对症用药|药液)"
)
_NEGATIVE_DIRECTIVE_PATTERN = re.compile(r"(暂不|不建议|不要|不宜|先不|避免|谨慎)")


def _is_list_line(line: str) -> bool:
    return line.startswith(("- ", "* ", "+ ")) or bool(re.match(r"^\d+\.\s+", line))


def _is_heading_line(line: str) -> bool:
    return line.startswith("#")


def _find_section_position(text: str, section: str) -> int:
    aliases = SECTION_ALIASES.get(section, (section,))
    positions = [text.find(alias) for alias in aliases]
    valid_positions = [position for position in positions if position >= 0]
    return min(valid_positions) if valid_positions else -1


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _split_sentences(text: str) -> list[str]:
    raw_sentences = re.split(r"[。！？!?；;]\s*", _normalize_text(text))
    return [sentence for sentence in raw_sentences if len(sentence) >= 18]


def _repeated_sentences(current: str, previous_sections: list[dict[str, str]] | None = None) -> list[str]:
    if not previous_sections:
        return []
    previous_sentences: set[str] = set()
    for item in previous_sections:
        previous_text = _normalize_text(item.get("markdown", ""))
        previous_sentences.update(_split_sentences(previous_text))
    return [sentence for sentence in _split_sentences(current) if sentence in previous_sentences]


def _weak_information_sentences(text: str) -> list[str]:
    weak: list[str] = []
    for sentence in _split_sentences(text):
        normalized = _normalize_text(sentence)
        if any(pattern.search(normalized) for pattern in _WEAK_SENTENCE_PATTERNS):
            weak.append(normalized)
    return weak


def validate_report_section(
    section_title: str,
    markdown: str,
    *,
    report_packet: dict[str, Any] | None = None,
    previous_sections: list[dict[str, str]] | None = None,
) -> None:
    if re.search(r"【[^】]*】", str(markdown or "")):
        raise ValueError(f"章节“{section_title}”不得使用【】标签式小标题")
    text = _normalize_text(markdown)
    if len(text) < 60:
        raise ValueError(f"章节“{section_title}”内容过短")

    repeated = _repeated_sentences(text, previous_sections)
    if len(repeated) >= 2:
        raise ValueError(f"章节“{section_title}”与前文重复：{repeated[0]}")

    weak_sentences = _weak_information_sentences(text)
    if len(weak_sentences) > 3:
        raise ValueError(f"章节“{section_title}”过度使用泛化不确定表述：{weak_sentences[0]}")
    if weak_sentences and not _CONCRETE_SIGNAL_PATTERN.search(weak_sentences[0]):
        raise ValueError(f"章节“{section_title}”出现缺乏具体信息的泛化句：{weak_sentences[0]}")

    context = report_packet.get("report_context", {}) if isinstance(report_packet, dict) else {}
    primary_diagnosis = _normalize_text(context.get("primary_diagnosis", ""))
    secondary_differential = _normalize_text(context.get("secondary_differential", ""))
    differential_names = [
        _normalize_text(name)
        for name in (context.get("differential_names", []) if isinstance(context, dict) else [])
        if _normalize_text(name)
    ]

    summary_title, diagnosis_title, followup_title, action_title, risk_title = REQUIRED_SECTIONS

    if section_title == summary_title:
        if re.search(r"(已确诊|明确诊断|无需复核)", text):
            raise ValueError("病例摘要应保持审慎，不应写成确诊口径")
        if re.search(r"(置信度|概率|模型分数|高置信|低置信)", text):
            raise ValueError("病例摘要不应展开置信度说明，应聚焦视觉观察事实")
        if primary_diagnosis and primary_diagnosis in text and not re.search(r"(视觉|分类|模型|图像判读)", text):
            raise ValueError("病例摘要如提到病名，只能作为视觉分类结果呈现，不能写成诊断结论")
        if _PERCENT_PATTERN.search(text) and not re.search(r"(面积|受损|病损|占|分割)", text):
            raise ValueError("病例摘要中的百分比应服务于描述受害范围，而不是替代诊断结论")
        return

    if section_title == diagnosis_title:
        if primary_diagnosis and primary_diagnosis not in text:
            raise ValueError("诊断判断章节必须点明主诊断或首位疑似")
        if not re.search(
            r"(倾向|审慎|边界|鉴别|候选|依据|理由|不像|首位|模型|分类|得分|概率|照片|图像|更像|区分|排除)",
            text,
        ):
            raise ValueError("诊断判断章节须交代边界、依据或鉴别方向（可用农户表述）")
        if re.search(r"(当前诊断为|综上所述.*诊断为|确诊为)", text):
            raise ValueError("诊断判断章节不应使用确诊式句型")
        if _PERCENT_PATTERN.search(text):
            if not re.search(r"(模型|分类|视觉).*(倾向|得分|分数|结果|排序)", text):
                raise ValueError("诊断判断章节的百分比必须解释为模型倾向分数")
            if re.search(r"(确诊概率|诊断概率)", text):
                raise ValueError("诊断判断章节不应把模型分数直接写成确诊概率")
        return

    if section_title == followup_title:
        if not re.search(
            r"(复查|复拍|补拍|补充|进一步|观察|记录|叶背|整株|送检|同叶位|可选|建议|若条件允许)",
            text,
        ):
            raise ValueError("复查与补证章节应给出可执行的补证或观察方向")
        if not re.search(r"(帮助|利于|便于|区分|核实|对齐|校准|影响|推进|明确)", text):
            raise ValueError("复查与补证章节应说明补证价值，避免只堆「缺口」而无指向")
        return

    if section_title == action_title:
        if not re.search(r"(立即|今天|当天|优先|先|首先|分区|摘除|检查|隔离|改善|清理|记录)", text):
            raise ValueError("救治建议章节必须包含立即执行动作")
        if not re.search(
            r"(复查|观察|记录|监测|复拍|每\s*\d|\d+\s*(小时|天|周)|持续跟踪|定期|追踪|后续)",
            text,
        ):
            raise ValueError("救治建议章节必须包含后续监测或复查指引")
        if not re.search(r"(若|如果|一旦|出现|满足|达到|升级|提高处理强度|补治)", text):
            raise ValueError("救治建议章节必须包含升级触发条件")
        if _HIGH_RISK_MEDICATION_PATTERN.search(text) and not _NEGATIVE_DIRECTIVE_PATTERN.search(text):
            raise ValueError("救治建议章节不应在证据不足时直接给出药剂处方")
        return

    if section_title == risk_title:
        if not re.search(r"(避免|不要|不宜|不建议)", text):
            raise ValueError("风险边界章节必须包含禁忌或谨慎动作")
        if not re.search(r"(复查|观察|24|48|几天|节点|时间)", text):
            raise ValueError("风险边界章节必须包含复查时间点")
        if not re.search(r"(预后|恢复|新叶|扩展|加重|趋稳|不可逆)", text):
            raise ValueError("风险边界章节应说明预后观察点或风险后果")
        return


def validate_markdown_report(markdown: str) -> None:
    text = str(markdown or "").strip()
    if len(text) < MIN_MARKDOWN_CHARS:
        raise ValueError("报告长度不足，未达到证据级输出要求")

    previous_pos = -1
    for section in REQUIRED_SECTIONS:
        position = _find_section_position(text, section)
        if position < 0:
            raise ValueError(f"缺少必填章节：{section}")
        if position < previous_pos:
            raise ValueError("必填章节顺序错误")
        previous_pos = position

    for pattern in INTERNAL_PROCESS_PATTERNS:
        match = re.search(pattern, text)
        if match:
            raise ValueError(f"报告暴露了内部讨论过程表述：{match.group(0)}")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("报告正文为空")

    list_lines = 0
    for line in lines:
        if _is_list_line(line):
            list_lines += 1
    if list_lines / len(lines) > MAX_LIST_LINE_RATIO:
        raise ValueError("报告列表化过重，叙述性不足")

    narrative_lines = [line for line in lines if not _is_heading_line(line) and not _is_list_line(line)]
    if len(narrative_lines) < MIN_NARRATIVE_LINES or sum(len(line) for line in narrative_lines) < MIN_NARRATIVE_CHARS:
        raise ValueError("报告缺少段落级叙述整合")

    narrative_blocks = []
    for block in re.split(r"\n\s*\n", text):
        normalized = re.sub(r"\s+", " ", block.strip())
        if not normalized or normalized.startswith("#"):
            continue
        if len(normalized) >= 80:
            narrative_blocks.append(normalized)
    repeated_blocks = {block for block in narrative_blocks if narrative_blocks.count(block) >= 2}
    if repeated_blocks:
        raise ValueError("报告在不同章节重复了同一段内容")

    json_like_lines = 0
    for line in lines:
        if re.match(r"^[\{\[]", line) or re.match(r'^\s*"\w+"\s*:\s*', line):
            json_like_lines += 1
    if json_like_lines >= max(4, int(len(lines) * 0.2)):
        raise ValueError("报告呈现为结构化键值样式，而非叙述性正文")
