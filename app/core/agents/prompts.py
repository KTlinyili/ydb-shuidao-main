from __future__ import annotations

import base64
import json
from typing import Any

from app.core.agents.knowledge_prose import caption_to_knowledge_narrative
from app.core.caption.schema import CaptionSchema


REQUIRED_REPORT_SECTIONS = [
    "病例摘要",
    "诊断判断与置信说明",
    "复查与补证建议",
    "救治建议与实施路径",
    "风险边界、预后与复查",
]


def get_expert_definitions() -> list[dict[str, str]]:
    return [
        {
            "agent_name": "diagnosis_evidence_officer",
            "role": (
                "病理推理专家（单图假设构建者）。"
                "将当前图像可见征象翻译为简练的病理语言，提出 1–3 个候选病因假设及对应支持点。"
                "不描述图像中未出现的部位或过程；不展开长段机制推演。"
                "绝对不做：治疗与环境处方、最终诊断裁决、编造未见信息。"
            ),
        },
        {
            "agent_name": "differential_officer",
            "role": (
                "鉴别排除专家（逻辑质检员）。"
                "你的独特视角：你是系统的'魔鬼代言人'，专门质疑和证伪假设。"
                "你不关心病害'像什么'，只关心'缺什么'和'矛盾什么'。"
                "对每个候选假设进行必要条件校验，挖掘矛盾点，必要时提出竞争性假设。"
                "绝对不做：不构建初始假设、不给防治建议、不做环境管理建议。"
            ),
        },
        {
            "agent_name": "berry_qa_expert",
            "role": (
                "水稻防治专家（防治方案制定者）。"
                "你拥有水稻病虫害防治的专业知识，重点关注稻瘟病、纹枯病、白叶枯病、褐斑病、细菌性条斑病、稻飞虱、稻纵卷叶螟和二化螟，能给出具体、可操作的防治方案。"
                "针对疑似病害给出具体的防治步骤，包括今日可执行动作、药剂与生防选择、"
                "24-48 小时观察重点和升级触发条件。"
                "绝对不做：不做诊断排序、不做环境改造建议、不自称裁决者。"
            ),
        },
        {
            "agent_name": "cultivation_management_officer",
            "role": (
                "农艺环境专家（环境管理师）。"
                "你的独特视角：你关注的不是具体用什么药，而是植物生长环境如何调控。"
                "提供不依赖特定诊断结果的通用环境管理措施：温湿度调控、通风改善、"
                "灌溉管理、病株隔离、复查时间节点。"
                "这些措施即使诊断有误也不会造成损害。"
                "绝对不做：不做诊断推理、不推荐专性药剂、不重复病斑描述。"
            ),
        },
    ]


def _caption_payload(caption: CaptionSchema) -> dict[str, Any]:
    return caption.model_dump(mode="json")


def _compact_turn(turn: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_name": turn.get("agent_name", ""),
        "role": turn.get("role", ""),
        "visible_findings": list(turn.get("visible_findings", []))[:5],
        "negative_findings": list(turn.get("negative_findings", []))[:4],
        "candidate_causes": list(turn.get("candidate_causes", []))[:4],
        "evidence_strength": turn.get("evidence_strength", ""),
        "ranked_differentials": list(turn.get("ranked_differentials", []))[:4],
        "why_primary": list(turn.get("why_primary", []))[:4],
        "why_not_primary": list(turn.get("why_not_primary", []))[:4],
        "decisive_missing_evidence": list(turn.get("decisive_missing_evidence", []))[:4],
        "today_actions": list(turn.get("today_actions", []))[:4],
        "control_options": list(turn.get("control_options", []))[:4],
        "observe_48h": list(turn.get("observe_48h", []))[:4],
        "escalation_triggers": list(turn.get("escalation_triggers", []))[:4],
        "management_timeline": list(turn.get("management_timeline", []))[:4],
        "low_risk_actions": list(turn.get("low_risk_actions", []))[:4],
        "environment_adjustments": list(turn.get("environment_adjustments", []))[:4],
        "followup_nodes": list(turn.get("followup_nodes", []))[:4],
        "prohibited_actions": list(turn.get("prohibited_actions", []))[:4],
        "overtreatment_risks": list(turn.get("overtreatment_risks", []))[:4],
        "undertreatment_risks": list(turn.get("undertreatment_risks", []))[:4],
        "confidence_boundary": list(turn.get("confidence_boundary", []))[:4],
        "citations": list(turn.get("citations", []))[:5],
    }


def _compact_shared_state(shared_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "consensus": list(shared_state.get("consensus", []))[:5],
        "conflicts": list(shared_state.get("conflicts", []))[:5],
        "unique_points": list(shared_state.get("unique_points", []))[:5],
        "next_focus": list(shared_state.get("next_focus", []))[:5],
        "safety_flags": list(shared_state.get("safety_flags", []))[:5],
        "working_diagnoses": list(shared_state.get("working_diagnoses", []))[:5],
        "open_questions": list(shared_state.get("open_questions", []))[:5],
        "evidence_gaps": list(shared_state.get("evidence_gaps", []))[:5],
        "uncertainty_score": shared_state.get("uncertainty_score", 0.5),
        "diagnosis_board": shared_state.get("diagnosis_board", {}),
        "evidence_board": shared_state.get("evidence_board", {}),
        "action_board": shared_state.get("action_board", {}),
        "risk_board": shared_state.get("risk_board", {}),
        "action_focus": list(shared_state.get("action_focus", []))[:5],
        "verification_tasks": list(shared_state.get("verification_tasks", []))[:5],
        "uncertainty_triggers": list(shared_state.get("uncertainty_triggers", []))[:5],
    }


def _expert_round_shared_state(shared_state: dict[str, Any], round_idx: int) -> dict[str, Any]:
    """专家提示用共享状态：第 2 轮起不再塞入「共识」长列表，避免每轮炒冷饭；从不包含 evidence_sufficiency 复读。"""
    boards = {
        "diagnosis_board": shared_state.get("diagnosis_board", {}),
        "evidence_board": shared_state.get("evidence_board", {}),
        "action_board": shared_state.get("action_board", {}),
        "risk_board": shared_state.get("risk_board", {}),
        "diagnosis_evidence": list(shared_state.get("diagnosis_evidence", []))[:8]
        if isinstance(shared_state.get("diagnosis_evidence"), list)
        else [],
    }
    core = {
        "working_diagnoses": list(shared_state.get("working_diagnoses", []))[:3],
        "next_focus": list(shared_state.get("next_focus", []))[:6],
        "conflicts": list(shared_state.get("conflicts", []))[:6],
        "open_questions": list(shared_state.get("open_questions", []))[:5],
        "uncertainty_score": shared_state.get("uncertainty_score", 0.5),
        **boards,
    }
    if round_idx <= 1:
        core["consensus"] = list(shared_state.get("consensus", []))[:5]
        core["unique_points"] = list(shared_state.get("unique_points", []))[:5]
    else:
        core["增量提示"] = (
            "以下为协调器更新后的板与子焦点。请只输出相对上一轮的新增推理、对分歧的回应或需要修正的点；"
            "不要复述已对齐的共识段落。"
        )
    return core


def _expert_output_spec(agent_name: str) -> dict[str, Any]:
    if agent_name == "diagnosis_evidence_officer":
        return {
            "required_fields": [
                "agent_name",
                "role",
                "visible_findings",
                "negative_findings",
                "candidate_causes",
                "evidence_strength",
                "citations",
            ],
            "field_rules": {
                "visible_findings": "只写肉眼可见或从输入事实明确得到的阳性观察。",
                "negative_findings": "只写缺失的关键征象或明确未观察到的线索。",
                "candidate_causes": "1 到 5 个候选，每个元素包含 name、why_like、why_unlike。",
                "evidence_strength": "一句话概括当前证据强弱与局限。",
            },
        }
    if agent_name == "differential_officer":
        return {
            "required_fields": [
                "agent_name",
                "role",
                "ranked_differentials",
                "why_primary",
                "why_not_primary",
                "decisive_missing_evidence",
                "citations",
            ],
            "field_rules": {
                "ranked_differentials": "1 到 5 个候选，按当前优先级排序，每个元素包含 name、why_supported、why_not_primary。",
                "why_primary": "支撑当前首选排第一的关键理由。",
                "why_not_primary": "说明其他候选为什么目前没有排第一。",
                "decisive_missing_evidence": "只写真正会改变当前排序的缺口。",
            },
        }
    if agent_name == "berry_qa_expert":
        return {
            "required_fields": [
                "agent_name",
                "role",
                "today_actions",
                "control_options",
                "observe_48h",
                "escalation_triggers",
                "citations",
            ],
            "field_rules": {
                "today_actions": "只写今天就能执行的低风险动作。",
                "control_options": "写病种相关的防治方案，可含药剂、生防、栽培配套和轮换提醒。",
                "observe_48h": "写 24 到 48 小时内要重点观察的变化。",
                "escalation_triggers": "写需要升级处理、复检或送检的触发条件。",
            },
        }
    if agent_name == "cultivation_management_officer":
        return {
            "required_fields": [
                "agent_name",
                "role",
                "management_timeline",
                "low_risk_actions",
                "environment_adjustments",
                "followup_nodes",
                "citations",
            ],
            "field_rules": {
                "management_timeline": "按先后顺序写管理节奏。",
                "low_risk_actions": "只写低风险、可逆、当下能落地的动作。",
                "environment_adjustments": "只写环境管理调整，如通风、湿度、灌溉、隔离。",
                "followup_nodes": "写后续复查节点和观察指标。",
            },
        }
    return {
        "required_fields": [
            "agent_name",
            "role",
            "citations",
        ],
        "field_rules": {},
    }


def _expert_special_rules(agent_name: str, round_idx: int = 1) -> list[str]:
    common = [
        "必须只返回严格 JSON，不要输出解释、标题、前后缀或 Markdown 代码块。",
        "所有用户可见内容必须使用中文。",
        "不要暴露任何内部模型名、组件名、路径、调试信息或系统术语。",
        "不要编造未在输入里出现的实验、化验、环境信息或病史。",
        "你是多智能体讨论的一员，请从自己的独特视角出发，给出其他专家无法替代的分析。",
        "不要在输出中反复铺陈「仅一张图/证据不足」等元叙事；系统已记录该约束。",
    ]
    single_image_rule = [
        "单张图像下只做可见形态与候选假设，不扩写未看见部位（如叶背、整株、茎果）。",
    ]
    role_rules = {
        "diagnosis_evidence_officer": [
            *(single_image_rule if round_idx <= 1 else []),
            "病理因果链保持简练，每条假设对应可见征象即可，勿写长段推演。",
            "不要给出治疗建议、环境管理建议或最终诊断结论。",
            "若病例库有相似案例，用短句引用佐证；无则不要编造。",
        ],
        "differential_officer": [
            "你的独特价值是证伪：检查假设的必要条件是否满足，找出矛盾点。",
            "必须把排序理由和未排第一的理由分开写。",
            "不要输出具体处置动作或通用管理建议。",
            "当你发现矛盾时，必须指出具体缺失了哪个关键特征。",
        ],
        "berry_qa_expert": [
            "你的独特价值是防治专业知识：给出具体可执行的防治方案。",
            "优先输出今日可执行动作和防治方案，观察重点和升级条件次之。",
            "不要输出最终主诊断排序，不要把自己写成裁决者。",
        ],
        "cultivation_management_officer": [
            "你的独特价值是环境管理：关注温湿度、通风、灌溉等环境因素。",
            "优先输出低风险、即使诊断有误也不会造成损害的管理措施。",
            "不要重复病斑形态描述，不要重做诊断排序，不要推荐专性药剂。",
        ],
    }
    return common + role_rules.get(agent_name, [])


def build_expert_messages(
    *,
    expert: dict[str, str],
    case_text: str,
    caption: CaptionSchema,
    kb_evidence: list[dict[str, Any]],
    round_idx: int,
    shared_state: dict[str, Any],
) -> list[dict[str, str]]:
    agent_name = str(expert.get("agent_name", "")).strip()
    output_spec = _expert_output_spec(agent_name)
    round_context = (
        "这是第一轮讨论，请基于输入信息进行独立分析。"
        if round_idx == 1
        else (
            f"这是第 {round_idx} 轮讨论。请依据共享状态中的各「板」、分歧点与 next_focus 做增量分析："
            "补充新推理、回应质疑或收敛争议；不要整段复述上一轮已对齐的共识话术。"
        )
    )
    system = (
        "你是水稻病虫害多智能体诊断系统中的一位专家。\n"
        "系统由多位专家从不同视角分析同一病例，通过讨论形成诊断共识。\n"
        f"你的角色：{expert.get('role', '')}\n\n"
        f"{round_context}\n"
        "你必须从自己的独特视角出发，提供其他专家无法替代的分析。\n"
        "你必须只返回严格 JSON，字段必须符合给定输出协议，且不要出现任何额外字段。\n"
        "当输入证据有限时，可以保持审慎，但仍要给出当前角色范围内最具体的输出。"
    )
    session_boundary = ""
    if round_idx <= 1:
        session_boundary = (
            "【会话边界】当前通常仅有一张可用图像，系统已记录该客观限制；"
            "请勿在 JSON 各字段里反复陈述「只有一张图/证据不足」，把字数用在其体专业内容上。"
        )
    user = {
        "任务": f"第 {round_idx} 轮专家分析",
        "角色信息": expert,
        "病例描述": case_text,
        "视觉摘要": _caption_payload(caption),
        "知识库证据": kb_evidence,
        "共享状态摘要": _expert_round_shared_state(shared_state, round_idx),
        "输出协议": output_spec,
        "硬性约束": _expert_special_rules(agent_name, round_idx),
        "补充要求": [
            req
            for req in [
                session_boundary,
                "如果引用知识库或输入证据，请把可追溯短句放进 citations。",
                "如果当前信息不足，也不要返回空对象，至少完成本角色最核心字段。",
                "除 JSON 外不要输出任何说明文字。",
            ]
            if req
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def build_round_summary_messages(
    *,
    round_turns: list[dict[str, Any]],
    round_idx: int,
    shared_state: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你是多智能体轮次协调器，负责汇总本轮各专家的讨论结果。\n"
        "你必须只返回严格 JSON，字段必须符合 CoordinatorSummarySchema。\n"
        "\n"
        "与此前版本不同：请做「增量汇总」，避免炒冷饭。\n"
        "- consensus：只写**本轮新形成或新加强**的一致判断（0–3 条短句）；若与上一轮相比无新共识，可留空列表。\n"
        "- conflicts：具体写出仍存分歧的点（可含专家视角差异），避免空泛。\n"
        "- unique_points：只收录本轮**新出现**的独立见解，不要重复上一轮已记录过的句子。\n"
        "- next_focus：只列**仍未解决**且值得下一轮继续推进的 1–4 条，不要把已闭合的话题再抄一遍。\n"
        "- evidence_sufficiency：不要每轮重复「单张图证据不足」套话；若无新的证据边界变化可填空字符串。\n"
        "各 board 字段应收敛为板载结构化信息，不要整段复述专家原文。"
    )
    user = {
        "任务": f"汇总第 {round_idx} 轮专家输出",
        "上一轮共享状态": _compact_shared_state(shared_state),
        "本轮专家输出": [_compact_turn(turn) for turn in round_turns],
        "汇总规则": [
            "working_diagnoses 只保留当前最主要的诊断名称，去重后输出。",
            "diagnosis_board 只放诊断链相关内容，不要混入管理动作。",
            "evidence_board 只放会改变排序或处理强度的缺口。",
            "action_board 只放今天动作、防治方案、48 小时观察和升级条件。",
            "risk_board 只放禁止动作、风险标记和置信边界。",
            "不要把「无法判断」之类空泛短句直接扩散到多个字段，除非绑定具体对象。",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def build_final_messages(
    *,
    case_text: str,
    caption: CaptionSchema,
    decision_packet: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你是最终诊断整合器。\n"
        "你必须根据给定决策包生成严格 JSON，字段必须符合 FinalDiagnosisSchema。\n"
        "输出要明确、审慎、可执行，所有用户可见内容必须使用中文。"
    )
    user = {
        "病例描述": case_text,
        "视觉摘要": _caption_payload(caption),
        "最终决策包": decision_packet,
        "生成要求": [
            "top_diagnosis 给出当前首选诊断和置信表述。",
            "candidates 只保留与当前判断最相关的候选。",
            "symptom_summary 只写观察归纳，不要重复完整报告。",
            "actions、monitoring_plan、prohibited_actions 要能直接执行。",
            "report_outline 必须覆盖以下五个固定章节：" + "、".join(REQUIRED_REPORT_SECTIONS),
            "confidence_statement 和 evidence_sufficiency 要清楚表达证据边界。",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def build_safety_messages(*, final_result: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "你是安全审查员。\n"
        "你只负责审查最终建议中的安全边界，不负责重做诊断。\n"
        "你必须只返回严格 JSON，字段必须符合 SafetyReviewSchema。"
    )
    user = {
        "待审查结果": final_result,
        "审查重点": [
            "是否存在过于激进、不可逆或明显越权的动作。",
            "是否遗漏了必要的复查节点、禁做事项或风险提示。",
            "如需修正 revised_actions，应优先给出更保守、更低风险的替代方案。",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def build_multi_agent_report_messages(
    *,
    case_text: str,
    caption: CaptionSchema,
    report_packet: dict[str, Any],
) -> list[dict[str, str]]:
    system = (
        "你是农业病害报告写手。\n"
        "你需要根据给定材料生成完整 Markdown 报告。\n"
        "报告必须覆盖固定五节，语言具体、克制、中文自然。"
    )
    user = {
        "病例描述": case_text,
        "视觉摘要": _caption_payload(caption),
        "报告材料": report_packet,
        "章节要求": REQUIRED_REPORT_SECTIONS,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def build_multi_agent_report_section_messages(
    *,
    case_text: str,
    caption: CaptionSchema,
    section_packet: dict[str, Any],
    section_title: str,
    section_instruction: str,
    completed_sections: list[dict[str, str]],
) -> list[dict[str, str]]:
    system = (
        "你是农业病害报告的章节撰稿人。\n"
        "你当前只负责一个章节，只返回 JSON，字段需符合 MarkdownSectionSchema。\n"
        "section_markdown 必须为本节**完整正文**：至少两个自然段，由你自行安排叙述顺序、过渡与重点，"
        "把章节材料里的信息**内化**为连贯口语化书面语，不要逐字段复述或写成填空式清单。\n"
        "除「救治建议与实施路径」外尽量少用编号列表；如需列表，嵌入段落语境中，不要整节只有条目。"
    )
    user = {
        "病例描述": case_text,
        "视觉摘要": _caption_payload(caption),
        "章节标题": section_title,
        "章节指令": section_instruction,
        "章节材料": section_packet,
        "已完成章节": completed_sections,
        "固定要求": [
            "只写当前章节，不越界扩写其他章节职责。",
            "参考 section_facts 与 shared_context，但用你自己的句子组织，避免照搬材料键名或 JSON 腔。",
            "段与段之间要有因果或递进，读起来像一篇报告的一节，而不是要点堆砌。",
            "诊断相关使用“首位疑似/候选方向”等审慎表述，不写确诊句式。",
            "救治建议先写可立即执行的低风险田间措施，证据不足时不写具体药剂配方。",
            "所有用户可见内容必须使用中文。",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def _section_formatting_hint(section_title: str) -> str:
    """客观、短段、易扫读；五章各司其职。"""
    _para = (
        "版式硬约束：**每一段中文不超过约 6–8 句或 160 字以内**（择严），段与段之间**必须空一行**；"
        "本节至少 **3 个自然段**（病例摘要可 2 段）。避免单段占满半屏。"
    )
    _tone = (
        "语气：**客观、书面、克制**，像农技简报而非推销文案。"
        "少用第二人称堆砌（少用通篇「你」）；少用感叹与口号。"
        "禁用俗套口语/鸡汤式收尾，例如：「记住」「牢牢」「主动权」「心里有数」「盯哨」「做扎实了心里就有底」等。"
        "描述症状用中性词（如「黄化、坏死、边缘不清」），避免「黄一块坏一块」类口语。"
    )
    hints = {
        "病例摘要": (
            _tone
            + _para
            + "本节只写**画面上可见**的病斑形态、分布与单张图证据上限；三到六句为宜。"
            "严重度与是否立即处理留给后文专节。禁止【】标签。"
        ),
        "诊断判断与置信说明": (
            _tone
            + _para
            + "写**这种病田间一般特征**、**当前影像为何更像 A 而非 B**，短句、可带少量列表。"
            "分类百分数须解释为「照片分类更靠近哪一类」，并点明**不等于田间确诊**。"
            "禁止后台腔（支持链、模型倾向、鉴别要点等）。至少两条「若…则…」。禁止【】标签。"
        ),
        "复查与补证建议": (
            _tone
            + _para
            + "执行细节：怎么拍、看什么；与救治节勿整段重复。每条尽量「若观察到 A → 则 B」。"
            "可用「必须 / 建议 / 可量力」分级。禁止【】标签。"
        ),
        "救治建议与实施路径": (
            _tone
            + _para
            + "按**今天 / 24 小时内 / 观察期**分块，块内短列表+短段，勿一块连续超过两段不分段。"
            "至少三条「若…则…」；不写具体药剂配方。禁止【】标签。"
        ),
        "风险边界、预后与复查": (
            _tone
            + _para
            + "禁忌、预后指标、维持/加码条件；「若…则…」与救治节阈值呼应。禁止【】标签。"
        ),
    }
    return hints.get(
        section_title.strip(),
        _tone + _para + "五章分工；短段+空行；禁止【】。",
    )


def build_narrative_report_section_messages(
    *,
    case_text: str,
    caption: CaptionSchema,
    section_title: str,
    section_instruction: str,
    global_briefing: str,
    section_focus_markdown: str,
    prior_sections_excerpt: str,
) -> list[dict[str, str]]:
    """章节撰稿：自然语言材料 + 纯文本输出（由调用方约定不得输出 JSON）。"""
    system = (
        "你是农业植保技术简报撰稿人，读者含农户与一线植保；只撰写一个章节的中文正文。\n"
        "结构原则：五章顺排、无开篇决策卡；各节各司其职，**禁止**把同一套总述在每一节长篇重复。"
        "本章只写本节独占信息：病例=可见事实；诊断=病类知识与像/不像；后三节=补证、处置时间轴、风险边界。\n"
        "文风必须**客观、中性、书面**：陈述可观察事实与可执行条件，**避免**宣传腔、鸡汤句、通篇「你」的说教口吻。"
        "禁用俗套表达（含但不限于）：「记住」「牢牢」「主动权」「心里有数」「盯哨」「做扎实了心里就有底」「别走弯路」等。\n"
        "分段硬约束：**每段不超过约 6–8 句或 160 字**（择严），**段之间必须空一行**；禁止单段超长「一滚到底」（网页端会显成大块文字）。\n"
        "分数口径：分类分数高仅表示**照片更像哪一类**；与「需补证」写在同一段逻辑里，避免割裂。\n"
        "禁止输出 JSON、禁止 ##、禁止代码围栏；勿重复章节标题（系统已加 ##）。禁止成品中出现【】标签式小标题。\n"
        "禁用后台腔：支持链、鉴别要点、模型倾向、排序、会诊摘要等；改为「依据在照片上的哪些特征」「与何病区分」「未看清何细节则结论可能变」。\n"
        "可用加粗短语标题、`- ` 短列表；救治与观察用动词开头短句，并多写「若…则…」。\n"
        "诊断用「首位疑似/更像」等审慎表述，避免「确诊」、避免把分类分数写成病原确诊概率。\n"
        "多角色讨论材料请**内化改写**为中性田间表述，勿照抄内部结构或小标题。"
    )
    cap_vis = caption_to_knowledge_narrative(caption)
    if len(cap_vis) > 5000:
        cap_vis = cap_vis[:4980] + "…"
    fmt_hint = _section_formatting_hint(section_title)
    user_body = "\n".join(
        [
            f"章节标题：{section_title}",
            f"写作指令：{section_instruction}",
            "",
            "版式与分工（供你遵守，勿原样输出本段标题）：",
            fmt_hint,
            "",
            "硬性要求：材料中的阈值/条件可写，勿编造数字；前文已写过的句子勿整段复述；全节须明显分段（空行），避免墙式长段。",
            "",
            "病例描述：",
            (case_text or "（无）").strip(),
            "",
            "图像与模型侧（叙述体）：",
            cap_vis,
            "",
            "全局参考（含知识库与讨论摘录，请改写为客观、可执行的田间表述，勿抄内部用词）：",
            global_briefing.strip(),
            "",
            "本章专用知识段落（内化后写入本节，勿照抄）：",
            section_focus_markdown.strip() or "（无）",
            "",
            "已完成的前文节选（承上启下，避免重复）：",
            prior_sections_excerpt.strip() or "（本节为首节）",
        ]
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_body},
    ]


def build_baseline_report_messages(
    *,
    case_text: str,
    caption: CaptionSchema,
    kb_evidence: list[dict[str, Any]],
    image_bytes: bytes | None = None,
) -> list[dict[str, str]]:
    system = (
        "你是单模型基线诊断与报告生成器。\n"
        "你必须只返回严格 JSON，字段必须符合 BaselineOutputSchema。\n"
        "请根据病例描述、视觉摘要、知识库证据生成一个完整、可读的中文基线结果。"
    )
    user_payload: dict[str, Any] = {
        "病例描述": case_text,
        "视觉摘要": _caption_payload(caption),
        "知识库证据": kb_evidence,
        "输出要求": [
            "top_diagnosis 必须明确，不能写 unknown。",
            "report_outline 必须覆盖以下五个固定章节：" + "、".join(REQUIRED_REPORT_SECTIONS),
            "markdown_report 必须是完整中文 Markdown 报告。",
            "actions、risks、key_evidence 必须尽量具体。",
        ],
    }
    if image_bytes:
        user_payload["附加图像"] = {
            "encoding": "base64",
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
    ]
