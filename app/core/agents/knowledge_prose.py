"""将诊断链路中的结构化字段改写为可直接喂给大模型的中文知识叙述（避免 JSON/键名堆砌）。"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.core.caption.presentation import localize_caption_payload
from app.core.caption.schema import CaptionSchema

_SYM_LABELS: dict[str, str] = {
    "color": "色泽印象",
    "tissue_state": "组织变化",
    "spot_shape": "病斑形态",
    "boundary": "边界特征",
    "distribution_position": "分布部位",
    "distribution_pattern": "扩展与分布方式",
    "morph_change": "整叶形态",
    "pest_cues": "虫害线索",
    "co_signs": "环境伴随",
}


def caption_to_knowledge_narrative(caption: CaptionSchema) -> str:
    """把 CaptionSchema 转成若干段可读知识，不输出 JSON。"""
    parts: list[str] = [caption.visual_summary.strip()]

    loc = localize_caption_payload(caption.model_dump(mode="json"))
    sym = loc.get("symptoms") if isinstance(loc.get("symptoms"), dict) else {}
    chips: list[str] = []
    for key, label in _SYM_LABELS.items():
        vals = sym.get(key) if isinstance(sym, dict) else None
        if not isinstance(vals, list) or not vals:
            continue
        cn = [str(v).strip() for v in vals[:5] if str(v).strip()]
        if cn:
            chips.append(f"{label}「{'、'.join(cn)}」")
    if chips:
        parts.append("从标签化视觉语义看，还可以这样理解这片叶子：" + "；".join(chips) + "。")

    n = caption.numeric
    parts.append(
        f"量化侧写：病损大约占单叶面积的 {n.area_ratio * 100:.1f}%，"
        f"严重度指数约 {n.severity_score:.2f}（0–1）；"
        f"模型对本帧归类的主观置信约 {caption.confidence * 100:.1f}%。"
    )
    if float(caption.ood_score) >= 0.2:
        parts.append(
            f"图像与训练常见样貌的偏离度（OOD）约 {caption.ood_score:.2f}，"
            "写作时宜保留「可能属于不典型表现」的余地，不要写成铁口直断。"
        )
    fq = [str(x).strip() for x in caption.followup_questions if str(x).strip()]
    if fq:
        parts.append("若田间还能补充信息，优先澄清：" + "；".join(fq[:6]) + "。")
    return "\n\n".join(parts)


def uncertainty_management_to_prose(um: dict[str, Any] | None) -> str:
    if not isinstance(um, dict) or not um:
        return "（当前无不确性与冲突的专门整理；可依据多智能体摘要自行把握审慎语气。）"
    paragraphs: list[str] = []
    cp = um.get("conflict_point")
    if isinstance(cp, dict):
        oi = str(cp.get("overall_impression", "")).strip()
        li = str(cp.get("local_lesion_impression", "")).strip()
        cs = str(cp.get("conflict_summary", "")).strip()
        ms = str(cp.get("model_score_interpretation", "")).strip()
        ec = str(cp.get("evidence_ceiling", "")).strip()
        if oi or li:
            paragraphs.append(
                "整体印象与局部病斑读数之间可能存在张力："
                + (f"整体倾向可概括为「{oi}」。" if oi else "")
                + (f"局部病斑侧写：{li}" if li else "")
            )
        if cs:
            paragraphs.append(f"冲突该如何理解（供你内化，勿照抄）：{cs}")
        if ms:
            paragraphs.append(ms)
        if ec:
            paragraphs.append(f"证据上限（知识层面）：{ec}")

    kds = um.get("key_discriminators")
    if isinstance(kds, list) and kds:
        paragraphs.append(
            "哪些观察最能「撬动」排序——从知识角度应这样看："
        )
        for item in kds[:6]:
            if not isinstance(item, dict):
                continue
            gap = str(item.get("gap", "")).strip()
            dv = str(item.get("diagnostic_value", "")).strip()
            ns = str(item.get("next_step", "")).strip()
            rh = str(item.get("rank_shift_hint", "")).strip()
            if not gap:
                continue
            seg = f"若关心「{gap}」：它对判断的价值在于{dv or '…'}。"
            if ns:
                seg += f" 田间可尝试：{ns}"
            if rh:
                seg += f" {rh}"
            paragraphs.append(seg)
    return "\n\n".join(paragraphs) if paragraphs else "（材料为空。）"


def decision_support_to_prose(ds: dict[str, Any] | None) -> str:
    if not isinstance(ds, dict) or not ds:
        return "（当前无分阶段决策与阈值提示；可依据防治与环境专家摘录写作。）"
    paragraphs: list[str] = []

    cur = ds.get("current_stage_actions")
    if isinstance(cur, list) and cur:
        paragraphs.append(
            "当下阶段在知识上通常优先考虑的田间动作包括："
            + "；".join(str(x).strip() for x in cur[:6] if str(x).strip())
            + "。"
        )

    obs = ds.get("observe_24_48h")
    if isinstance(obs, list) and obs:
        lines: list[str] = []
        for row in obs[:6]:
            if isinstance(row, dict):
                it = str(row.get("item", "")).strip()
                th = str(row.get("threshold_hint", "")).strip()
                if it:
                    lines.append(f"{it}" + (f"（阈值提示：{th}）" if th else ""))
            elif str(row).strip():
                lines.append(str(row).strip())
        if lines:
            paragraphs.append("24–48 小时窗口内值得盯的信号：" + "；".join(lines) + "。")

    up = ds.get("upgrade_conditions")
    if isinstance(up, list) and up:
        paragraphs.append(
            "出现下列情况时，知识上应倾向「提高处理与复核强度」："
            + "；".join(str(x).strip() for x in up[:5] if str(x).strip())
            + "。"
        )
    down = ds.get("downgrade_conditions")
    if isinstance(down, list) and down:
        paragraphs.append(
            "若观察到这些走向，则可考虑维持或下调强度："
            + "；".join(str(x).strip() for x in down[:4] if str(x).strip())
            + "。"
        )

    pro = ds.get("prohibited_actions")
    if isinstance(pro, list) and pro:
        paragraphs.append(
            "边界上不宜做的事："
            + "；".join(str(x).strip() for x in pro[:5] if str(x).strip())
            + "。"
        )

    rev = ds.get("review_nodes")
    if isinstance(rev, list) and rev:
        paragraphs.append(
            "复查与时间节点上的知识提醒："
            + "；".join(str(x).strip() for x in rev[:5] if str(x).strip())
            + "。"
        )

    br = ds.get("post_review_branches")
    if isinstance(br, list) and br:
        paragraphs.append(
            "补证之后常见的两条叙事分支："
            + " ".join(str(x).strip() for x in br[:4] if str(x).strip())
        )

    return "\n\n".join(paragraphs) if paragraphs else "（材料为空。）"


def _bundle_visual_only(b: dict[str, Any]) -> str:
    vs = str(b.get("visual_summary", "")).strip()
    morph = b.get("morphology_cues")
    ext = str(b.get("extent_note", "")).strip()
    co = str(b.get("conflict_one_liner", "")).strip()
    wn = str(b.get("writing_note", "")).strip()
    segs = []
    if vs:
        segs.append(vs)
    if isinstance(morph, list) and morph:
        segs.append("形态线索可记为：" + "、".join(str(x) for x in morph[:6] if str(x).strip()) + "。")
    if ext:
        segs.append(ext)
    if co:
        segs.append(f"与模型整体印象相关的张力：{co}")
    if wn:
        segs.append(wn)
    return "\n".join(segs) if segs else ""


def section_facts_to_knowledge_narrative(facts: Any, section_title: str) -> str:
    """按章节把 section_facts 翻成知识段落，供本章撰稿专用。"""
    if not isinstance(facts, dict) or not facts:
        return "（本节没有单独附带的要点包；请依赖全局协作脉络与视觉知识叙述完成本章。）"

    st = str(section_title or "").strip()
    out: list[str] = []

    if st == "病例摘要":
        vb = facts.get("visual_only_bundle")
        if isinstance(vb, dict):
            prose = _bundle_visual_only(vb)
            if prose:
                out.append(prose)
        morph = facts.get("morphology")
        if isinstance(morph, list) and morph:
            out.append("可见形态词汇：" + "、".join(str(x) for x in morph[:8] if str(x).strip()) + "。")
        vs = str(facts.get("visual_summary", "")).strip()
        if vs and not (isinstance(vb, dict) and vb.get("visual_summary") == vs):
            out.append(vs)
        for key, label in [
            ("stage_hint", "生育期或病程阶段提示"),
            ("consistency_note", "与文字描述是否对得上"),
            ("classification_policy_note", "分类结果应如何理解"),
        ]:
            t = str(facts.get(key, "")).strip()
            if t:
                out.append(f"{label}：{t}")

    elif st == "诊断判断与置信说明":
        pd = str(facts.get("primary_diagnosis", "")).strip()
        sd = str(facts.get("secondary_differential", "")).strip()
        if pd:
            out.append(
                f"当前知识站位上，首位待写明的对象是「{pd}」。"
                + (f"与之最常并排比较的是「{sd}」。" if sd else "")
            )
            out.append(
                f"田间决策策略（须写入正文）：建议先按「{pd}」**疑似病例**路径组织**基础防控**（降湿、标记、补证等），"
                + (f"同时明确保留与「{sd}」等的鉴别空间，避免一口咬死。" if sd else "同时保留鉴别空间，避免一口咬死。")
            )
        dst = str(facts.get("diagnosis_statement", "")).strip()
        if dst:
            out.append(f"系统内对病名的语句化概括（请改写后使用）：{dst}")
        cl = str(facts.get("confidence_label", "")).strip()
        msn = str(facts.get("model_score_note", "")).strip()
        if cl or msn:
            out.append(
                "置信应写成层级或倾向，而不是确诊："
                + (f"{cl}。" if cl else "")
                + (f" {msn}" if msn else "")
            )
        cb = facts.get("confidence_boundary")
        if isinstance(cb, list) and cb:
            out.append("边界句素材：" + " ".join(str(x).strip() for x in cb[:6] if str(x).strip()))
        req = str(facts.get("disease_entity_writing_requirement", "")).strip()
        if req:
            out.append(req)
        snippets = facts.get("disease_context_snippets")
        if isinstance(snippets, list) and snippets:
            out.append(
                "知识库中与病名相关的摘录（融入叙述，勿罗列出处）："
                + " ".join(_clip(str(s), 400) for s in snippets[:5] if str(s).strip())
            )
        scb = str(facts.get("second_candidate_brief", "")).strip()
        if scb:
            out.append(scb)
        db = facts.get("diagnosis_board")
        if isinstance(db, dict):
            diffs = db.get("differentials")
            if isinstance(diffs, list) and diffs:
                out.append("鉴别上，知识层面建议这样对照：")
                for d in diffs[:4]:
                    if not isinstance(d, dict):
                        continue
                    nm = str(d.get("name", "")).strip()
                    if not nm:
                        continue
                    ws = str(d.get("why_supported", "")).strip()
                    wn = str(d.get("why_not_primary", "")).strip()
                    out.append(f"「{nm}」仍值得考虑，因为{ws or '…'}；暂未压过首位，主要由于{wn or '…'}。")

    elif st == "复查与补证建议":
        gis = facts.get("gap_items")
        if isinstance(gis, list) and gis:
            out.append("从证据链角度，最值得补的几件事（含「补到能改变什么」）：")
            for g in gis[:6]:
                if not isinstance(g, dict):
                    continue
                gap = str(g.get("gap", "")).strip()
                dv = str(g.get("diagnostic_value", "")).strip()
                ns = str(g.get("next_step", "")).strip()
                if gap:
                    out.append(f"- {gap}。{dv} {ns}".strip())
        tf = facts.get("berry_focus")
        if isinstance(tf, list) and tf:
            out.append("水稻生产上常盯的观察点：" + "；".join(str(x) for x in tf[:5] if str(x).strip()) + "。")
        cap_ans = facts.get("caption_answer_confidences")
        if isinstance(cap_ans, list) and cap_ans:
            out.append("视觉问答里带置信度的线索：" + "；".join(str(x) for x in cap_ans[:5] if str(x).strip()) + "。")
        wn = str(facts.get("writing_note", "")).strip()
        if wn:
            out.append(wn)
        um = facts.get("uncertainty_management")
        if isinstance(um, dict):
            out.append(uncertainty_management_to_prose(um))

    elif st == "救治建议与实施路径":
        ta = facts.get("today_actions")
        if isinstance(ta, list) and ta:
            out.append("今日可动起来的事（知识优先级）：" + "；".join(str(x) for x in ta[:6] if str(x).strip()) + "。")
        co = facts.get("control_options")
        if isinstance(co, list) and co:
            out.append(
                "防治层面可写的路径（类别与原则，具体药剂由线下复核）："
                + "；".join(str(x) for x in co[:5] if str(x).strip())
                + "。"
            )
        o48 = facts.get("observe_48h")
        if isinstance(o48, list) and o48:
            out.append("近两日观察：" + "；".join(str(x) for x in o48[:5] if str(x).strip()) + "。")
        esc = facts.get("escalation_conditions")
        if isinstance(esc, list) and esc:
            out.append("升级或送检的触发知识：" + "；".join(str(x) for x in esc[:4] if str(x).strip()) + "。")
        tl = facts.get("timeline")
        if isinstance(tl, list) and tl:
            out.append("时间线参考：" + " → ".join(str(x) for x in tl[:6] if str(x).strip()) + "。")
        ds = facts.get("decision_support")
        if isinstance(ds, dict):
            out.append(decision_support_to_prose(ds))
        lcp = facts.get("leaf_clinical_profile")
        if isinstance(lcp, dict):
            tier = str(lcp.get("damage_tier", "")).strip()
            rp = str(lcp.get("ratio_percent_text", "")).strip()
            if tier or rp:
                out.append(f"受害层级与面积语言：{tier or ''} {rp or ''}".strip())

    elif st == "风险边界、预后与复查":
        pa = facts.get("prohibited_actions")
        if isinstance(pa, list) and pa:
            out.append("不宜之事：" + "；".join(str(x) for x in pa[:6] if str(x).strip()) + "。")
        sn = facts.get("safety_notes")
        if isinstance(sn, list) and sn:
            out.append("风险与信号：" + "；".join(str(x) for x in sn[:6] if str(x).strip()) + "。")
        rf = facts.get("required_followups")
        if isinstance(rf, list) and rf:
            out.append("复查节点：" + "；".join(str(x) for x in rf[:6] if str(x).strip()) + "。")
        pn = str(facts.get("prognosis_note", "")).strip()
        if pn:
            out.append(f"预后读法：{pn}")
        ds = facts.get("decision_support")
        if isinstance(ds, dict):
            out.append(decision_support_to_prose(ds))

    else:
        for k, v in list(facts.items())[:15]:
            if isinstance(v, str) and v.strip():
                out.append(f"{k}：{v.strip()}")
            elif isinstance(v, list) and v:
                out.append(f"{k}：" + "；".join(str(x).strip() for x in v[:8] if str(x).strip()))

    text = "\n\n".join(x for x in out if str(x).strip())
    return text if len(text) > 40 else text + "\n\n（内容较短，请结合全局 briefing 展开。）"


def _clip(s: str, n: int) -> str:
    t = str(s).strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def build_decision_one_pager_markdown(
    report_packet: dict[str, Any],
    caption: Optional[CaptionSchema] = None,
) -> str:
    """
    报告最前「一页决策卡」：诊断倾向、严重度、是否立即处理、量化阈值、不确定点、下一步。
    使用加粗与列表，不出现 ##，以免干扰五章校验。
    """
    if not isinstance(report_packet, dict):
        return ""

    ctx = report_packet.get("report_context")
    ctx = ctx if isinstance(ctx, dict) else {}
    primary = str(ctx.get("primary_diagnosis", "") or "").strip() or "叶部病害（待复核）"
    conf_lbl = str(ctx.get("confidence_label", "") or "").strip()
    model_note = str(ctx.get("model_score_note", "") or "").strip()
    conf_line = (
        "、".join(x for x in (conf_lbl, model_note) if x) or "照片分类仅供参考，需田间补证"
    )
    if model_note and re.search(r"\d", model_note):
        conf_line = (
            f"{conf_line}（**说明**：百分数表示分类更像哪一类，**不是**病理确诊概率；与「需补证」同时成立。）"
        )

    lcp = report_packet.get("leaf_clinical_profile")
    lcp = lcp if isinstance(lcp, dict) else {}
    ratio_txt = str(lcp.get("ratio_percent_text", "") or "").strip()
    tier = str(lcp.get("damage_tier", "") or "").strip()
    area_ratio = 0.0
    sev = 0.0
    if caption is not None:
        try:
            area_ratio = float(caption.numeric.area_ratio)
            sev = float(caption.numeric.severity_score)
        except (TypeError, ValueError):
            area_ratio, sev = 0.0, 0.0
    if not ratio_txt and area_ratio > 0:
        ratio_txt = f"约 {area_ratio * 100:.1f}% 叶面积受累"
    sev_human = tier or (
        "中–重度（建议按活跃病害处理）"
        if area_ratio >= 0.35 or sev >= 0.55
        else "轻–中度（仍建议主动管理）"
        if area_ratio >= 0.12 or sev >= 0.3
        else "相对局限（仍需观察是否扩展）"
    )
    severity_block = "、".join(x for x in (ratio_txt, sev_human) if x) or "严重度见正文"

    immediate = area_ratio >= 0.25 or sev >= 0.45
    need_now = "**是** — 建议**今日内**启动隔离、降湿、记录与补证，避免拖成整田扩散。" if immediate else (
        "**建议尽快处理** — 先完成补拍与标记，按观察结果决定是否升级。"
    )

    eb = report_packet.get("evidence_board")
    eb = eb if isinstance(eb, dict) else {}
    missing = eb.get("missing_evidence") or []
    missing = missing if isinstance(missing, list) else []

    ap = report_packet.get("action_plan")
    ap = ap if isinstance(ap, dict) else {}
    today_actions = ap.get("actions") or []
    today_actions = today_actions if isinstance(today_actions, list) else []
    top_actions = [_clip(str(x), 72) for x in today_actions[:4] if str(x).strip()]

    if not top_actions:
        top_actions = ["隔离或标记病株，减少人为触碰健康叶", "加强通风、控制叶面持水时间", "准备叶背/整株补拍"]

    risk_line = (
        "病损占叶面积已较高或严重度指数偏高时，**48 小时内**若外扩 **>20%**、或叶背出现典型霉层/水浸扩展，应视为**升级信号**；"
        "若 **48 小时内**几乎无扩展、叶背关键征象持续阴性，可**暂不强化用药**，仍以环境与记录为主。"
    )

    um = report_packet.get("uncertainty_management")
    unc_lines: list[str] = []
    if isinstance(um, dict):
        cp = um.get("conflict_point")
        if isinstance(cp, dict):
            for key, lab in (
                ("local_lesion_impression", "局部病斑读数"),
                ("conflict_summary", "整体与局部分歧"),
            ):
                t = str(cp.get(key, "")).strip()
                if t:
                    unc_lines.append(f"- **{lab}**：{_clip(t, 100)}")
        for kd in (um.get("key_discriminators") or [])[:4]:
            if not isinstance(kd, dict):
                continue
            gap = str(kd.get("gap", "")).strip()
            if gap:
                unc_lines.append(f"- **是否已看清**：{_clip(gap, 90)}（未看清则结论可能变）")
    if not unc_lines:
        unc_lines = [
            "- **叶背典型征象**（如霉层、浸润方式）是否出现仍未知。",
            "- **整株是否系统性扩展**仍未知。",
        ]

    prio_lines: list[str] = []
    if missing:
        for i, m in enumerate(missing[:3], 1):
            label = "（必须）" if i == 1 else "（强烈建议）" if i == 2 else "（辅助）"
            prio_lines.append(f"{i}. {_clip(str(m), 85)} {label}")
    else:
        prio_lines = [
            "1. **叶背近景**（必须）— 区分霉层/轮纹/水渍等关键征象",
            "2. **整株与邻株**（强烈建议）— 判断是否系统性扩散",
            "3. **湿度与通风记录**（辅助）— 解释是否利于孢子萌发",
        ]

    next_core = [
        f"**诊断倾向（农户可读）**：按「**{primary}** 首位疑似」准备田间动作；{conf_line}。",
        f"**严重程度**：{severity_block}。",
        f"**是否需要立即处理**：{need_now}",
        "**核心风险（量化）**：" + risk_line,
        "**下一步最关键动作（按优先级）**：",
        *prio_lines,
        "**今日可先执行（示例，具体以正文为准）**：",
        *[f"- {a}" for a in top_actions],
        "**当前关键不确定点（会改变结论）**：",
        *unc_lines,
    ]
    body = "\n".join(next_core)
    return f"**决策摘要**（先读：要不要动、先干什么、看什么要加码）\n\n{body}"
