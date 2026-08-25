(() => {
  const refs = {
    workspace: document.getElementById("workspace"),
    form: document.getElementById("run-form"),
    imageInput: document.getElementById("image"),
    submitBtn: document.getElementById("submit-btn"),
    status: document.getElementById("status"),
    indicator: document.getElementById("top-run-indicator"),
    topPage: document.querySelector(".top-page"),
    runMeta: document.getElementById("run-meta"),
    runLookup: document.getElementById("run_id_lookup"),
    loadBtn: document.getElementById("load-btn"),
    flowCanvasScroll: document.getElementById("flow-canvas-scroll"),
    flowBoardView: document.getElementById("flow-board-view"),
    flowCanvas: document.getElementById("flow-canvas"),
    flowBoard: document.getElementById("flow-board"),
    flowEdges: document.getElementById("flow-edges"),
    flowZoomOutBtn: document.getElementById("flow-zoom-out-btn"),
    flowZoomInBtn: document.getElementById("flow-zoom-in-btn"),
    flowFitBtn: document.getElementById("flow-fit-btn"),
    flowResetBtn: document.getElementById("flow-reset-btn"),
    flowBoardBtn: document.getElementById("flow-board-btn"),
    flowZoomLabel: document.getElementById("flow-zoom-label"),
    flowToolbarText: document.querySelector(".flow-toolbar-text"),
    inspector: document.getElementById("node-inspector"),
    reportBoard: document.getElementById("report-board"),
    reportViewBtn: document.getElementById("report-view-btn"),
    dialogueViewBtn: document.getElementById("dialogue-view-btn"),
    clearKbBtn: document.getElementById("clear-kb-btn"),
    kbTarget: document.getElementById("kb-target"),
    kbStatus: document.getElementById("kb-status"),
    dashPage: document.getElementById("page-dashboard"),
    runsPage: document.getElementById("page-runs"),
    casesPage: document.getElementById("page-cases"),
    kbPage: document.getElementById("page-kb"),
    runsList: document.getElementById("runs-list"),
    runsRefreshBtn: document.getElementById("runs-refresh-btn"),
    casesList: document.getElementById("cases-list"),
    casesVerifiedCount: document.getElementById("cases-verified-count"),
    casesUnverifiedCount: document.getElementById("cases-unverified-count"),
    kbStatsArea: document.getElementById("kb-stats-area"),
    kbTabs: Array.from(document.querySelectorAll(".kb-tab")),
    kbTarget2: document.getElementById("kb-target2"),
    clearKbBtn2: document.getElementById("clear-kb-btn2"),
    kbStatus2: document.getElementById("kb-status2"),
    kbUploadForm: document.getElementById("kb-upload-form"),
    kbUploadTitle: document.getElementById("kb-upload-title"),
    kbUploadText: document.getElementById("kb-upload-text"),
    kbUploadFile: document.getElementById("kb-upload-file"),
    kbUploadBtn: document.getElementById("kb-upload-btn"),
    kbUploadStatus: document.getElementById("kb-upload-status"),
    kbDocsList: document.getElementById("kb-docs-list"),
    heroAgentIcons: Array.from(document.querySelectorAll(".expert-avatar[data-agent]")),
    navButtons: Array.from(document.querySelectorAll(".nav-item[data-page]")),
  };

  const PAGE_TITLES = {
    dashboard: "数据大屏",
    diagnosis: "决策台",
    runs: "运行记录",
    cases: "病例库",
    kb: "知识库",
  };

  const FLOW_STATUS_TEXT = {
    pending: "待触发",
    active: "生成中",
    complete: "已完成",
    error: "异常",
  };

  const FLOW_WORLD_MIN_WIDTH = 3600;
  const FLOW_WORLD_MIN_HEIGHT = 2200;
  const FLOW_WORLD_PADDING = 360;
  const FLOW_VIEWPORT_PADDING = 120;
  const FLOW_VIEWPORT_OVERSCAN = 220;

  const AGENT_META = {
    human: {
      label: "图像输入",
      short: "输入",
      iconKey: "human",
      color: "human",
      description: "上传的叶片原图与本次运行上下文。",
    },
    caption: {
      label: "视觉解读",
      short: "图像",
      iconKey: "caption",
      color: "cyan",
      description: "将原图压缩成结构化症状摘要。",
    },
    retrieval: {
      label: "证据检索",
      short: "检索",
      iconKey: "retrieval",
      color: "kb",
      description: "从知识库召回与当前病例最接近的历史证据。",
    },
    diagnosis_evidence_officer: {
      label: "病理推理专家",
      short: "病理",
      iconKey: "diagnosis",
      color: "cyan",
      description: "将视觉特征翻译为病理机制，构建病因假设与因果推理链。",
    },
    differential_officer: {
      label: "鉴别排除专家",
      short: "鉴别",
      iconKey: "differential",
      color: "violet",
      description: "质疑与证伪假设，检查必要条件缺失，提出竞争性假设。",
    },
    cultivation_management_officer: {
      label: "农艺环境专家",
      short: "环境",
      iconKey: "cultivation",
      color: "leaf",
      description: "环境因素分析与低风险栽培管理措施。",
    },
    berry_qa_expert: {
      label: "草莓防治专家",
      short: "防治",
      iconKey: "berry",
      color: "rose",
      description: "基于专业知识给出具体可执行的草莓病害防治方案。",
    },
    summary: {
      label: "证据板汇总",
      short: "汇总",
      iconKey: "summary",
      color: "coord",
      description: "汇总本轮专家共识、证据板、补证任务和报告优先级。",
    },
    final: {
      label: "最终救治结论",
      short: "结论",
      iconKey: "final",
      color: "final",
      description: "产出诊断结论、证据板和救治实施路径。",
    },
    safety: {
      label: "安全审校",
      short: "审校",
      iconKey: "safety",
      color: "amber",
      description: "对最终动作做安全和合规复核，并决定是否需要降级或补证。",
    },
    report: {
      label: "救治报告",
      short: "报告",
      iconKey: "report",
      color: "report",
      description: "把最终结论整理成专业救治 Markdown 报告。",
    },
    unknown: {
      label: "专家节点",
      short: "专家",
      iconKey: "unknown",
      color: "coord",
      description: "通用专家节点。",
    },
  };

  const ICON_LIBRARY = {
    human: [
      '<circle class="glyph-stroke" cx="32" cy="21" r="7" />',
      '<path class="glyph-stroke" d="M19 46c2.7-7.4 8.2-11 13-11s10.3 3.6 13 11" />',
      '<path class="glyph-accent" d="M25 15c2-2.2 4.4-3.3 7-3.3 2.8 0 5.2 1.1 7.2 3.3" />',
    ],
    caption: [
      '<rect class="glyph-stroke" x="14" y="18" width="36" height="24" rx="7" />',
      '<path class="glyph-stroke" d="M20 37l8-8 6 6 7-7 5 9" />',
      '<circle class="glyph-solid" cx="23" cy="25" r="2.4" />',
      '<path class="glyph-accent" d="M47 16l1.5 3 3 1.5-3 1.5-1.5 3-1.5-3-3-1.5 3-1.5z" />',
    ],
    retrieval: [
      '<rect class="glyph-stroke" x="16" y="18" width="18" height="26" rx="4" />',
      '<rect class="glyph-stroke" x="30" y="14" width="18" height="30" rx="4" />',
      '<path class="glyph-accent" d="M23 24h5M23 29h5M37 21h6M37 26h6M37 31h6" />',
    ],
    diagnosis: [
      '<circle class="glyph-stroke" cx="28" cy="29" r="10" />',
      '<path class="glyph-stroke" d="M35 36l8 8" />',
      '<path class="glyph-accent" d="M23 31c5-8 11-9 13-9-2 5-5 9-13 9z" />',
    ],
    differential: [
      '<path class="glyph-stroke" d="M32 17v30" />',
      '<path class="glyph-stroke" d="M19 24h10M35 24h10" />',
      '<path class="glyph-accent" d="M32 22c-7 0-12 4-12 10s5 10 12 10" />',
      '<path class="glyph-accent" d="M32 22c7 0 12 4 12 10s-5 10-12 10" />',
    ],
    cultivation: [
      '<path class="glyph-stroke" d="M22 44h20" />',
      '<path class="glyph-stroke" d="M26 44c0-6 3-10 6-10s6 4 6 10" />',
      '<path class="glyph-accent" d="M32 34V20" />',
      '<path class="glyph-accent" d="M32 24c-6 0-9-4-9-9 6 0 9 3 9 9z" />',
      '<path class="glyph-accent" d="M32 27c6 0 9-4 9-9-6 0-9 3-9 9z" />',
    ],
    risk: [
      '<path class="glyph-stroke" d="M32 14l14 5v10c0 9-6 16-14 20-8-4-14-11-14-20V19z" />',
      '<path class="glyph-accent" d="M25 31l5 5 9-10" />',
    ],
    tomato: [
      '<circle class="glyph-stroke" cx="32" cy="34" r="14" />',
      '<path class="glyph-accent" d="M26 18c1-4 4-6 6-6 2 0 5 2 6 6" />',
      '<path class="glyph-accent" d="M24 18c2 2 4 3 8 3 4 0 6-1 8-3" />',
      '<circle class="glyph-solid" cx="27" cy="31" r="1.8" />',
      '<circle class="glyph-solid" cx="37" cy="31" r="1.8" />',
      '<path class="glyph-stroke" d="M27 39c2 2 4 3 5 3s3-1 5-3" />',
      '<path class="glyph-stroke" d="M46 20h5c3 0 5 2 5 5s-2 5-5 5h-2l-4 3v-3" />',
    ],
    summary: [
      '<circle class="glyph-stroke" cx="20" cy="24" r="5" />',
      '<circle class="glyph-stroke" cx="44" cy="24" r="5" />',
      '<circle class="glyph-solid" cx="32" cy="40" r="5.2" />',
      '<path class="glyph-accent" d="M24 27l6 8M40 27l-6 8" />',
    ],
    final: [
      '<circle class="glyph-stroke" cx="32" cy="28" r="10" />',
      '<path class="glyph-accent" d="M26 29l4 4 8-9" />',
      '<path class="glyph-stroke" d="M26 37l-3 10 9-5 9 5-3-10" />',
    ],
    safety: [
      '<path class="glyph-stroke" d="M32 14l14 5v10c0 9-6 16-14 20-8-4-14-11-14-20V19z" />',
      '<path class="glyph-accent" d="M25 31l5 5 9-10" />',
      '<path class="glyph-accent" d="M32 22v1" />',
    ],
    report: [
      '<path class="glyph-stroke" d="M22 14h15l9 9v27H22z" />',
      '<path class="glyph-stroke" d="M37 14v10h9" />',
      '<path class="glyph-accent" d="M28 31h12M28 36h12M28 41h8" />',
    ],
    unknown: [
      '<rect class="glyph-stroke" x="19" y="19" width="26" height="20" rx="7" />',
      '<circle class="glyph-solid" cx="28" cy="29" r="2" />',
      '<circle class="glyph-solid" cx="36" cy="29" r="2" />',
      '<path class="glyph-accent" d="M28 39v6M36 39v6M19 29h-4M49 29h-4" />',
    ],
  };

  const state = {
    activePage: "dashboard",
    currentView: "dialogue",
    reportMode: "multi",
    runId: "",
    currentStage: "initial",
    isRunning: false,
    finalResp: {},
    trace: { rounds: [] },
    lastResult: null,
    casesData: {
      verified: [],
      unverified: [],
      documents: [],
      total_verified: 0,
      total_unverified: 0,
      total_documents: 0,
    },
    kbDocuments: [],
    caseActiveTab: "verified",
    revealProgress: {},
    revealTimers: {},
    inspectorView: {
      nodeId: "",
      scrollTop: 0,
    },
    flowViewport: {
      scale: 1,
      minScale: 0.34,
      maxScale: 2.6,
      offsetX: 36,
      offsetY: 36,
      dragPointerId: null,
      dragStartX: 0,
      dragStartY: 0,
      startOffsetX: 0,
      startOffsetY: 0,
      contentWidth: 1280,
      contentHeight: 680,
      graphBounds: null,
      userAdjusted: false,
      focusPendingNodeId: "",
      detailNodeId: "",
      detailScrollTop: 0,
    },
    boardView: {
      open: false,
      source: "inspector",
      title: "",
      scale: 1,
      minScale: 0.45,
      maxScale: 2.4,
      offsetX: 0,
      offsetY: 0,
      dragPointerId: null,
      dragStartX: 0,
      dragStartY: 0,
      startOffsetX: 0,
      startOffsetY: 0,
    },
    flow: createEmptyFlow(),
  };

  function normalizeKnowledgeTargetOptions() {
    const options = [
      { value: "all", label: "全部知识文档" },
      { value: "documents", label: "仅知识文档" },
    ];
    for (const selectEl of [refs.kbTarget, refs.kbTarget2]) {
      if (!selectEl) {
        continue;
      }
      clearElement(selectEl);
      for (const option of options) {
        const node = document.createElement("option");
        node.value = option.value;
        node.textContent = option.label;
        selectEl.append(node);
      }
    }
  }

  const boardRefs = {
    root: null,
    title: null,
    viewport: null,
    content: null,
    zoomLabel: null,
  };

  const flowDetailRefs = {
    root: null,
    title: null,
    body: null,
  };

  function createEmptyFlow() {
    return {
      problemName: "",
      caseText: "",
      selectedNodeId: "",
      followLiveSelection: true,
      activeNodeId: "",
      nodes: {
        human: makeNode("human", "human", { kind: "human" }),
        caption: makeNode("caption", "caption", { kind: "caption" }),
        retrieval: makeNode("retrieval", "retrieval", { kind: "retrieval" }),
        final: makeNode("final", "final", { kind: "final" }),
        safety: makeNode("safety", "safety", { kind: "safety" }),
        report: makeNode("report", "report", { kind: "report" }),
      },
      rounds: [],
    };
  }

  function makeNode(id, metaKey, extra = {}) {
    const meta = AGENT_META[metaKey] || AGENT_META.unknown;
    return {
      id,
      metaKey,
      kind: extra.kind || metaKey,
      agentName: extra.agentName || metaKey,
      label: extra.label || meta.label,
      short: extra.short || meta.short,
      iconKey: extra.iconKey || meta.iconKey || metaKey,
      colorClass: `node-color-${meta.color}`,
      description: extra.description || meta.description,
      round: extra.round || null,
      status: extra.status || "pending",
      visible: Boolean(extra.visible),
      data: extra.data || null,
    };
  }

  function glyphMarkup(iconKey) {
    const parts = ICON_LIBRARY[iconKey] || ICON_LIBRARY.unknown;
    return [
      '<svg class="agent-glyph" viewBox="0 0 64 64" aria-hidden="true" fill="none">',
      ...parts,
      "</svg>",
    ].join("");
  }

  function createAgentGlyph(iconKey) {
    const wrap = document.createElement("span");
    wrap.innerHTML = glyphMarkup(iconKey);
    return wrap.firstElementChild;
  }

  function hydrateHeroAgentIcons() {
    refs.heroAgentIcons.forEach((element) => {
      const agentName = element.dataset.agent || "unknown";
      const meta = AGENT_META[agentName] || AGENT_META.unknown;
      clearElement(element);
      element.append(createAgentGlyph(meta.iconKey || "unknown"));
    });
  }

  function getRoundNodeId(roundIdx, agentName) {
    return `round-${roundIdx}-${agentName}`;
  }

  function asList(value) {
    return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && `${item}`.trim()) : [];
  }

  function uniq(values) {
    return Array.from(new Set(asList(values).map((item) => `${item}`.trim()).filter(Boolean)));
  }

  function clearElement(target) {
    if (!target) {
      return;
    }
    while (target.firstChild) {
      target.removeChild(target.firstChild);
    }
  }

  function escapeHtml(value) {
    return `${value ?? ""}`
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  let imageUploadPreviewUrl = "";

  function formatBytes(bytes) {
    const value = Number(bytes || 0);
    if (!Number.isFinite(value) || value <= 0) {
      return "0 B";
    }
    if (value < 1024) {
      return `${value} B`;
    }
    if (value < 1024 * 1024) {
      return `${(value / 1024).toFixed(1)} KB`;
    }
    return `${(value / (1024 * 1024)).toFixed(2)} MB`;
  }

  function ensureImageUploadFeedback() {
    const wrapper = refs.imageInput?.closest(".file-upload-wrapper");
    if (!wrapper) {
      return null;
    }
    let feedback = wrapper.querySelector(".image-upload-feedback");
    if (!feedback) {
      feedback = el("div", "image-upload-feedback");
      feedback.hidden = true;
      const preview = document.createElement("img");
      preview.className = "image-upload-thumb";
      preview.alt = "已选择图片预览";
      const meta = el("div", "image-upload-meta");
      const name = el("div", "image-upload-name");
      const size = el("div", "image-upload-size");
      const tip = el("div", "image-upload-tip");
      meta.append(name, size, tip);
      feedback.append(preview, meta);
      wrapper.append(feedback);
    }
    const preview = feedback.querySelector(".image-upload-thumb");
    const name = feedback.querySelector(".image-upload-name");
    const size = feedback.querySelector(".image-upload-size");
    const tip = feedback.querySelector(".image-upload-tip");
    return { feedback, preview, name, size, tip };
  }

  function clearImageUploadFeedback() {
    const ui = ensureImageUploadFeedback();
    if (!ui) {
      return;
    }
    if (imageUploadPreviewUrl) {
      URL.revokeObjectURL(imageUploadPreviewUrl);
      imageUploadPreviewUrl = "";
    }
    ui.feedback.hidden = true;
    if (ui.preview) {
      ui.preview.removeAttribute("src");
    }
    if (ui.name) {
      ui.name.textContent = "";
    }
    if (ui.size) {
      ui.size.textContent = "";
    }
    if (ui.tip) {
      ui.tip.textContent = "";
    }
  }

  function updateImageUploadFeedback(file) {
    if (!file) {
      clearImageUploadFeedback();
      return;
    }
    const ui = ensureImageUploadFeedback();
    if (!ui) {
      return;
    }
    if (imageUploadPreviewUrl) {
      URL.revokeObjectURL(imageUploadPreviewUrl);
      imageUploadPreviewUrl = "";
    }
    if (ui.name) {
      ui.name.textContent = file.name || "已选择图片";
    }
    if (ui.size) {
      ui.size.textContent = `${formatBytes(file.size)} · ${file.type || "image/*"}`;
    }
    if (ui.tip) {
      ui.tip.textContent = "图片已选中，提交后会上传到后端并进入视觉分析。";
    }
    if (ui.preview) {
      imageUploadPreviewUrl = URL.createObjectURL(file);
      ui.preview.src = imageUploadPreviewUrl;
    }
    ui.feedback.hidden = false;
  }

  function createChip(label, active = false) {
    const chip = el("button", `chip${active ? " chip-active" : ""}`, label);
    chip.type = "button";
    return chip;
  }

  function createEmptyState(icon, title, desc) {
    const wrap = el("div", "empty-state");
    wrap.append(el("div", "empty-state-icon", icon));
    wrap.append(el("div", "empty-state-title", title));
    wrap.append(el("div", "empty-state-desc", desc));
    return wrap;
  }

  function createErrorCard(title, body) {
    const wrap = el("div", "error-card");
    wrap.append(el("div", "error-card-icon", "⚠️"));
    wrap.append(el("div", "error-card-title", title));
    wrap.append(el("div", "error-card-body", body));
    return wrap;
  }

  function createGhostButton(label, onClick) {
    const button = el("button", "copy-btn copy-btn-ghost", label);
    button.type = "button";
    if (onClick) {
      button.addEventListener("click", onClick);
    }
    return button;
  }

  function displayAgentName(name) {
    return (AGENT_META[name] || AGENT_META.unknown).label;
  }

  function formatIsoTime(value) {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return `${value}`;
    }
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  }

  function setIndicator(kind, text) {
    refs.indicator.classList.remove("idle", "running", "done", "error");
    refs.indicator.classList.add(kind);
    refs.status.textContent = text;
  }

  function setStatus(text, kind = "idle") {
    setIndicator(kind, text);
  }

  function setBusy(isBusy) {
    refs.submitBtn.disabled = isBusy;
    refs.loadBtn.disabled = isBusy;
  }

  function setKbStatus(target, text, isError = false) {
    if (!target) {
      return;
    }
    target.textContent = text;
    target.classList.toggle("status-error", Boolean(isError));
  }

  function getFinalPayload() {
    return state.finalResp || {};
  }

  function getReportsPayload() {
    return getFinalPayload().reports || {};
  }

  function getExecutionMeta() {
    return getFinalPayload().execution_meta || state.trace.execution_meta || {};
  }

  function getSafetyPayload() {
    return state.trace.safety || (state.lastResult && state.lastResult.safety) || {};
  }

  function getNode(nodeId) {
    return state.flow.nodes[nodeId] || null;
  }

  function setSelectedNode(nodeId) {
    if (!nodeId || !getNode(nodeId)) {
      return;
    }
    state.flow.selectedNodeId = nodeId;
    state.inspectorView.nodeId = nodeId;
    state.inspectorView.scrollTop = 0;
    if (refs.inspector) {
      refs.inspector.scrollTop = 0;
    }
  }

  function ensureVisibleNode(nodeId) {
    const node = getNode(nodeId);
    if (node) {
      node.visible = true;
    }
  }

  function setNodeStatus(nodeId, status) {
    const node = getNode(nodeId);
    if (!node) {
      return;
    }
    node.visible = true;
    node.status = status;
    if (status === "active") {
      state.flow.activeNodeId = nodeId;
      if (state.flow.followLiveSelection || !state.flow.selectedNodeId) {
        setSelectedNode(nodeId);
      }
    } else if (state.flow.activeNodeId === nodeId && status !== "error") {
      state.flow.activeNodeId = "";
    }
  }

  function ensureRound(roundIdx, activeAgents = []) {
    let round = state.flow.rounds.find((item) => item.round === roundIdx);
    if (!round) {
      const summaryNodeId = `round-${roundIdx}-summary`;
      state.flow.nodes[summaryNodeId] = makeNode(summaryNodeId, "summary", {
        kind: "summary",
        label: `第 ${roundIdx} 轮汇总`,
        short: `R${roundIdx}`,
        round: roundIdx,
        visible: true,
      });
      round = {
        round: roundIdx,
        activeAgents: [],
        expertNodeIds: [],
        summaryNodeId,
      };
      state.flow.rounds.push(round);
      state.flow.rounds.sort((a, b) => a.round - b.round);
    }
    round.activeAgents = uniq([...(round.activeAgents || []), ...activeAgents]);
    asList(activeAgents).forEach((agentName) => ensureExpert(roundIdx, agentName));
    return round;
  }

  function ensureExpert(roundIdx, agentName) {
    const round = ensureRound(roundIdx);
    const nodeId = getRoundNodeId(roundIdx, agentName);
    if (!state.flow.nodes[nodeId]) {
      const meta = AGENT_META[agentName] || AGENT_META.unknown;
      state.flow.nodes[nodeId] = makeNode(nodeId, agentName, {
        kind: "expert",
        agentName,
        label: meta.label,
        short: meta.short,
        round: roundIdx,
        visible: true,
      });
    }
    if (!round.expertNodeIds.includes(nodeId)) {
      round.expertNodeIds.push(nodeId);
    }
    if (!round.activeAgents.includes(agentName)) {
      round.activeAgents.push(agentName);
    }
    return state.flow.nodes[nodeId];
  }

  function ensureRoundTrace(roundIdx) {
    if (!Array.isArray(state.trace.rounds)) {
      state.trace.rounds = [];
    }
    let round = state.trace.rounds.find((item) => Number(item.round) === Number(roundIdx));
    if (!round) {
      round = { round: roundIdx, active_agents: [], expert_turns: [] };
      state.trace.rounds.push(round);
      state.trace.rounds.sort((a, b) => Number(a.round) - Number(b.round));
    }
    if (!Array.isArray(round.expert_turns)) {
      round.expert_turns = [];
    }
    return round;
  }

  function resetCurrentRun(problemName, caseText) {
    Object.values(state.revealTimers).forEach((timerId) => window.clearTimeout(timerId));
    state.revealTimers = {};
    state.revealProgress = {};
    state.trace = { rounds: [] };
    state.finalResp = {};
    state.lastResult = null;
    state.flow = createEmptyFlow();
    state.flow.problemName = problemName || "";
    state.flow.caseText = caseText || "";
    const human = getNode("human");
    human.visible = true;
    human.status = "complete";
    human.data = { problem_name: problemName || "", case_text: caseText || "" };
    const caption = getNode("caption");
    caption.visible = true;
    caption.status = "active";
    setSelectedNode("human");
    state.flow.followLiveSelection = true;
    state.flowViewport.scale = 1;
    state.flowViewport.offsetX = 36;
    state.flowViewport.offsetY = 36;
    state.flowViewport.userAdjusted = false;
    state.flowViewport.focusPendingNodeId = "";
    state.flowViewport.detailNodeId = "";
    state.flowViewport.detailScrollTop = 0;
  }

  function hydrateFlowFromSavedRun() {
    const finalPayload = getFinalPayload();
    const trace = state.trace || { rounds: [] };
    const previousProblemName = state.flow.problemName;
    const previousCaseText = state.flow.caseText;
    Object.values(state.revealTimers).forEach((timerId) => window.clearTimeout(timerId));
    state.revealTimers = {};
    state.revealProgress = {};
    state.flow = createEmptyFlow();
    state.flow.problemName = finalPayload.problem_name || previousProblemName || "历史运行";
    state.flow.caseText = finalPayload.case_text || previousCaseText || "";
    const human = getNode("human");
    human.visible = true;
    human.status = "complete";
    human.data = {
      problem_name: state.flow.problemName,
      case_text: state.flow.caseText,
    };
    const captionSeed = getNode("caption");
    captionSeed.visible = true;
    captionSeed.status = "pending";
    state.flow.followLiveSelection = false;
    setSelectedNode("human");
    state.flowViewport.scale = 1;
    state.flowViewport.offsetX = 36;
    state.flowViewport.offsetY = 36;
    state.flowViewport.userAdjusted = false;
    state.flowViewport.focusPendingNodeId = "";
    state.flowViewport.detailNodeId = "";
    state.flowViewport.detailScrollTop = 0;

    const captionNode = getNode("caption");
    if (trace.caption) {
      captionNode.data = {
        caption: trace.caption,
        slot_extraction: trace.slot_extraction || {},
        image_analysis: trace.image_analysis || finalPayload.image_analysis || {},
        image_analysis_display: trace.image_analysis_display || finalPayload.image_analysis_display || {},
        vision_result: trace.vision_result || finalPayload.vision_result || {},
      };
      setNodeStatus("caption", "complete");
    }

    const retrievalNode = getNode("retrieval");
    if (trace.kb_evidence) {
      retrievalNode.data = { kb_evidence: trace.kb_evidence, kb_evidence_count: trace.kb_evidence.length };
      setNodeStatus("retrieval", "complete");
    }

    for (const roundItem of asList(trace.rounds)) {
      const activeAgents = uniq([
        ...asList(roundItem.active_agents),
        ...asList(roundItem.expert_turns).map((turn) => turn.agent_name),
      ]);
      const round = ensureRound(Number(roundItem.round), activeAgents);
      for (const agentName of activeAgents) {
        ensureExpert(Number(roundItem.round), agentName);
      }
      for (const turn of asList(roundItem.expert_turns)) {
        const node = ensureExpert(Number(roundItem.round), turn.agent_name);
        node.data = turn;
        setNodeStatus(node.id, turn.invalid_turn ? "error" : "complete");
      }
      const summaryNode = getNode(round.summaryNodeId);
      summaryNode.visible = true;
      summaryNode.data = {
        summary: roundItem.summary || {},
        shared_state: roundItem.shared_state || {},
        active_agents: round.activeAgents,
      };
      if (roundItem.summary) {
        setNodeStatus(round.summaryNodeId, "complete");
      }
    }

    const finalNode = getNode("final");
    if (trace.final || finalPayload.top_diagnosis) {
      finalNode.data = {
        final: trace.final || finalPayload,
        shared_state: trace.shared_state || finalPayload.shared_state || {},
        meta: trace.final_meta || {},
      };
      setNodeStatus("final", "complete");
    }

    const safetyNode = getNode("safety");
    if (trace.safety) {
      safetyNode.data = { safety: trace.safety, meta: trace.safety_meta || {} };
      setNodeStatus("safety", "complete");
    }

    const reportNode = getNode("report");
    if (finalPayload.reports) {
      reportNode.data = {
        reports: finalPayload.reports,
        final: finalPayload,
        comparison_summary: finalPayload.comparison_summary || {},
      };
      setNodeStatus("report", "complete");
      setSelectedNode("report");
    } else if (trace.safety) {
      safetyNode.visible = true;
      setSelectedNode("final");
    }

    state.flow.followLiveSelection = false;
  }

  function updateFlowFromStreamEvent(event) {
    switch (event.type) {
      case "run_started": {
        resetCurrentRun(event.problem_name || "", event.case_text || "");
        state.currentStage = event.stage || "initial";
        break;
      }
      case "caption_ready": {
        const captionNode = getNode("caption");
        captionNode.data = {
          caption: event.caption || {},
          slot_extraction: event.slot_extraction || {},
          image_analysis: event.image_analysis || {},
          image_analysis_display: event.image_analysis_display || {},
          vision_result: event.vision_result || {},
        };
        setNodeStatus("caption", "complete");
        ensureVisibleNode("retrieval");
        setNodeStatus("retrieval", "active");
        break;
      }
      case "image_processing_started": {
        const captionNode = getNode("caption");
        ensureVisibleNode("caption");
        captionNode.data = {
          ...(captionNode.data || {}),
          processing_message: event.message || "已接收图片，正在执行视觉分析。",
        };
        setNodeStatus("caption", "active");
        break;
      }
      case "slot_extraction_ready": {
        const captionNode = getNode("caption");
        captionNode.data = {
          ...(captionNode.data || {}),
          slot_extraction: event.slot_extraction || {},
        };
        break;
      }
      case "image_analysis_ready": {
        const captionNode = getNode("caption");
        captionNode.data = {
          ...(captionNode.data || {}),
          image_analysis: event.image_analysis || {},
          image_analysis_display: event.display || {},
        };
        break;
      }
      case "kb_ready": {
        const retrievalNode = getNode("retrieval");
        retrievalNode.data = {
          kb_evidence: event.kb_evidence || [],
          kb_evidence_count: Number(event.kb_evidence_count || asList(event.kb_evidence).length),
        };
        setNodeStatus("retrieval", "complete");
        break;
      }
      case "round_started": {
        const round = ensureRound(Number(event.round), event.active_agents || []);
        const summaryNode = getNode(round.summaryNodeId);
        summaryNode.visible = true;
        summaryNode.status = "pending";
        summaryNode.data = {
          shared_state_before: event.shared_state || {},
          active_agents: round.activeAgents,
        };
        for (const agentName of round.activeAgents) {
          const node = ensureExpert(round.round, agentName);
          node.visible = true;
          if (node.status !== "complete") {
            node.status = "pending";
          }
        }
        break;
      }
      case "expert_started": {
        const node = ensureExpert(Number(event.round), event.agent_name);
        node.data = {
          ...(node.data || {}),
          shared_state_before: event.shared_state || {},
          active_agents: event.active_agents || [],
        };
        setNodeStatus(node.id, "active");
        break;
      }
      case "expert_turn": {
        const node = ensureExpert(Number(event.round), event.agent_name || (event.turn && event.turn.agent_name) || "unknown");
        node.data = event.turn || {};
        setNodeStatus(node.id, node.data.invalid_turn ? "error" : "complete");
        break;
      }
      case "round_summary_started": {
        const round = ensureRound(Number(event.round), event.active_agents || []);
        const node = getNode(round.summaryNodeId);
        node.data = {
          ...(node.data || {}),
          shared_state_before: event.shared_state || {},
          active_agents: event.active_agents || [],
        };
        setNodeStatus(node.id, "active");
        break;
      }
      case "round_summary": {
        const round = ensureRound(Number(event.round), event.active_agents || []);
        const node = getNode(round.summaryNodeId);
        node.data = {
          summary: event.summary || {},
          shared_state: event.shared_state || {},
          stop_after_round: Boolean(event.stop_after_round),
          meta: event.meta || {},
          active_agents: event.active_agents || [],
        };
        setNodeStatus(node.id, "complete");
        break;
      }
      case "final_started": {
        const node = getNode("final");
        node.data = { shared_state: event.shared_state || {} };
        setNodeStatus("final", "active");
        break;
      }
      case "final_result": {
        const node = getNode("final");
        node.data = {
          final: event.final || {},
          shared_state: event.shared_state || {},
          meta: event.meta || {},
        };
        setNodeStatus("final", "complete");
        break;
      }
      case "safety_started": {
        const node = getNode("safety");
        node.data = { final: event.final || {} };
        setNodeStatus("safety", "active");
        break;
      }
      case "safety_result": {
        const node = getNode("safety");
        node.data = { safety: event.safety || {}, meta: event.meta || {} };
        setNodeStatus("safety", "complete");
        break;
      }
      case "reports_started": {
        const node = getNode("report");
        node.data = { reports: getReportsPayload() };
        setNodeStatus("report", "active");
        break;
      }
      case "reports_ready": {
        const node = getNode("report");
        node.data = {
          ...(node.data || {}),
          multi_agent_meta: event.multi_agent_meta || {},
          baseline_meta: event.baseline_meta || {},
        };
        break;
      }
      case "complete": {
        const node = getNode("report");
        node.data = {
          reports: event.result && event.result.reports ? event.result.reports : getReportsPayload(),
          final: event.result && event.result.final ? event.result.final : getFinalPayload(),
          comparison_summary:
            event.result && event.result.final ? event.result.final.comparison_summary || {} : getFinalPayload().comparison_summary || {},
        };
        setNodeStatus("report", "complete");
        break;
      }
      case "error": {
        markActiveNodeAsError(event.detail || {});
        break;
      }
      default:
        break;
    }
  }

  function markActiveNodeAsError(detail) {
    const nodeId = state.flow.activeNodeId || state.flow.selectedNodeId || "human";
    const node = getNode(nodeId);
    if (!node) {
      return;
    }
    node.data = {
      ...(node.data || {}),
      error: detail,
    };
    setNodeStatus(nodeId, "error");
    setSelectedNode(nodeId);
  }

  function renderRunMeta() {
    clearElement(refs.runMeta);
    if (!state.runId && !state.flow.problemName) {
      return;
    }
    const stageLabelMap = {
      initial: "初诊",
      final: "复核",
    };
    const stageLabel = stageLabelMap[state.currentStage] || state.currentStage || "初诊";
    const bits = [];
    bits.push(`运行 ${state.runId || "未开始"}`);
    bits.push(`阶段 ${stageLabel}`);
    const rounds = Array.isArray(state.trace.rounds) ? state.trace.rounds.length : 0;
    bits.push(`轮次 ${rounds}`);
    const executionMeta = getExecutionMeta();
    if (typeof executionMeta.fallback_used === "boolean") {
      bits.push(`兜底 ${executionMeta.fallback_used ? "是" : "否"}`);
    }
    const top = getFinalPayload().top_diagnosis;
    if (top && top.name) {
      bits.push(`主结论 ${top.name}`);
    }
    refs.runMeta.textContent = bits.join("  ·  ");
  }

  function setView(view) {
    state.currentView = view;
    refs.dialogueViewBtn.classList.toggle("active", view === "dialogue");
    refs.reportViewBtn.classList.toggle("active", view === "report");
    refs.flowBoardView.style.display = view === "dialogue" ? "grid" : "none";
    refs.reportBoard.style.display = view === "report" ? "block" : "none";
    renderCurrentRun();
  }

  function parseInline(text) {
    return escapeHtml(text)
      .replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*]+)\*/g, "<em>$1</em>");
  }

  function appendMarkdown(container, markdown) {
    const root = el("div", "markdown-body");
    const lines = `${markdown || ""}`.replace(/\r\n/g, "\n").split("\n");
    let paragraph = [];
    let listItems = [];
    let inCode = false;
    let codeLines = [];

    function flushParagraph() {
      if (!paragraph.length) {
        return;
      }
      const p = el("p");
      // 连续非空行合并为一段时，用 <br> 保留模型输出的换行，避免网页端「一坨长段」
      const html = paragraph
        .map((line) => parseInline(line))
        .join("<br>\n");
      p.innerHTML = html;
      root.append(p);
      paragraph = [];
    }

    function flushList() {
      if (!listItems.length) {
        return;
      }
      const ul = el("ul", "md-list");
      for (const item of listItems) {
        const li = el("li");
        li.innerHTML = parseInline(item);
        ul.append(li);
      }
      root.append(ul);
      listItems = [];
    }

    function flushCode() {
      if (!codeLines.length) {
        return;
      }
      const pre = el("pre", "md-code");
      pre.textContent = codeLines.join("\n");
      root.append(pre);
      codeLines = [];
    }

    for (const line of lines) {
      if (line.trim().startsWith("```")) {
        if (inCode) {
          flushCode();
          inCode = false;
        } else {
          flushParagraph();
          flushList();
          inCode = true;
        }
        continue;
      }

      if (inCode) {
        codeLines.push(line);
        continue;
      }

      const headingMatch = line.match(/^(#{1,4})\s+(.*)$/);
      if (headingMatch) {
        flushParagraph();
        flushList();
        const level = Math.min(4, headingMatch[1].length);
        const heading = el(`h${level}`);
        heading.innerHTML = parseInline(headingMatch[2]);
        root.append(heading);
        continue;
      }

      const listMatch = line.match(/^\s*(?:[-*]|\d+\.)\s+(.*)$/);
      if (listMatch) {
        flushParagraph();
        listItems.push(listMatch[1]);
        continue;
      }

      if (!line.trim()) {
        flushParagraph();
        flushList();
        continue;
      }

      paragraph.push(line.trim());
    }

    flushParagraph();
    flushList();
    flushCode();
    container.append(root);
  }

  function currentReportText() {
    const reports = getReportsPayload();
    if (state.reportMode === "baseline") {
      return reports.baseline_markdown || "";
    }
    if (state.reportMode === "compare") {
      return [
        "# 多智能体救治报告",
        reports.multi_agent_markdown || "",
        "",
        "# 单模型救治报告",
        reports.baseline_markdown || "",
      ].join("\n");
    }
    return reports.multi_agent_markdown || "";
  }

  async function copyText(text) {
    if (!text) {
      return;
    }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const area = document.createElement("textarea");
        area.value = text;
        document.body.append(area);
        area.select();
        document.execCommand("copy");
        area.remove();
      }
      setStatus("当前报告已复制", "done");
    } catch (err) {
      setStatus(`复制失败: ${safeErrorText(err)}`, "error");
    }
  }

  const SAFETY_ACTION_LEVEL_LABELS = {
    fully_supported: "证据充分，可执行完整方案",
    full_plan: "证据充分，可执行完整方案",
    "conservative-only": "仅建议保守方案",
    conservative_only: "仅建议保守方案",
    conservative: "仅建议保守方案",
    escalation_review: "建议升级处理或线下复核",
    escalation: "建议升级处理或线下复核",
    "offline-review": "建议升级处理或线下复核",
    offline_review: "建议升级处理或线下复核",
  };

  function localizeSafetyActionLevel(level) {
    const raw = `${level || ""}`.trim();
    if (!raw) {
      return "";
    }
    const normalized = raw.toLowerCase().replace(/\s+/g, "_");
    return SAFETY_ACTION_LEVEL_LABELS[normalized] || SAFETY_ACTION_LEVEL_LABELS[raw.toLowerCase()] || raw;
  }

  function localizeSafetyText(value) {
    return `${value || ""}`.trim();
  }

  function localizeSafetyList(items) {
    return asList(items).map((item) => localizeSafetyText(item)).filter(Boolean);
  }

  function clampFlowScale(scale) {
    return Math.min(state.flowViewport.maxScale, Math.max(state.flowViewport.minScale, scale));
  }

  function clampFlowOffsets() {
    if (!refs.flowCanvasScroll) {
      return;
    }
    const viewportRect = refs.flowCanvasScroll.getBoundingClientRect();
    const scaledWidth = Math.max(1, (state.flowViewport.contentWidth || 0) * state.flowViewport.scale);
    const scaledHeight = Math.max(1, (state.flowViewport.contentHeight || 0) * state.flowViewport.scale);

    if (scaledWidth + FLOW_VIEWPORT_OVERSCAN * 2 <= viewportRect.width) {
      state.flowViewport.offsetX = (viewportRect.width - scaledWidth) / 2;
    } else {
      const minX = viewportRect.width - scaledWidth - FLOW_VIEWPORT_OVERSCAN;
      const maxX = FLOW_VIEWPORT_OVERSCAN;
      state.flowViewport.offsetX = Math.min(maxX, Math.max(minX, state.flowViewport.offsetX));
    }

    if (scaledHeight + FLOW_VIEWPORT_OVERSCAN * 2 <= viewportRect.height) {
      state.flowViewport.offsetY = (viewportRect.height - scaledHeight) / 2;
    } else {
      const minY = viewportRect.height - scaledHeight - FLOW_VIEWPORT_OVERSCAN;
      const maxY = FLOW_VIEWPORT_OVERSCAN;
      state.flowViewport.offsetY = Math.min(maxY, Math.max(minY, state.flowViewport.offsetY));
    }
  }

  function applyFlowTransform() {
    if (!refs.flowCanvas) {
      return;
    }
    clampFlowOffsets();
    refs.flowCanvas.style.transform = `translate(${state.flowViewport.offsetX}px, ${state.flowViewport.offsetY}px) scale(${state.flowViewport.scale})`;
    if (refs.flowZoomLabel) {
      refs.flowZoomLabel.textContent = `${Math.round(state.flowViewport.scale * 100)}%`;
    }
  }

  function fitFlowViewport({ preserveUserMode = false } = {}) {
    if (!refs.flowCanvasScroll) {
      return;
    }
    const viewportRect = refs.flowCanvasScroll.getBoundingClientRect();
    const bounds = state.flowViewport.graphBounds || {
      minX: 0,
      minY: 0,
      maxX: Math.max(state.flowViewport.contentWidth || 0, 640),
      maxY: Math.max(state.flowViewport.contentHeight || 0, 420),
    };
    const contentWidth = Math.max(bounds.maxX - bounds.minX, 640);
    const contentHeight = Math.max(bounds.maxY - bounds.minY, 420);
    const scale = clampFlowScale(
      Math.min(
        (viewportRect.width - FLOW_VIEWPORT_PADDING) / contentWidth,
        (viewportRect.height - FLOW_VIEWPORT_PADDING) / contentHeight,
        1
      )
    );
    state.flowViewport.scale = scale;
    const contentCenterX = (bounds.minX + bounds.maxX) / 2;
    const contentCenterY = (bounds.minY + bounds.maxY) / 2;
    state.flowViewport.offsetX = viewportRect.width / 2 - contentCenterX * scale;
    state.flowViewport.offsetY = viewportRect.height / 2 - contentCenterY * scale;
    if (!preserveUserMode) {
      state.flowViewport.userAdjusted = false;
    }
    applyFlowTransform();
  }

  function zoomFlowViewport(multiplier, anchorClientX = null, anchorClientY = null) {
    if (!refs.flowCanvasScroll) {
      return;
    }
    const viewportRect = refs.flowCanvasScroll.getBoundingClientRect();
    const anchorX = anchorClientX === null ? viewportRect.width / 2 : anchorClientX - viewportRect.left;
    const anchorY = anchorClientY === null ? viewportRect.height / 2 : anchorClientY - viewportRect.top;
    const prevScale = state.flowViewport.scale;
    const nextScale = clampFlowScale(prevScale * multiplier);
    if (Math.abs(nextScale - prevScale) < 0.001) {
      return;
    }
    const contentX = (anchorX - state.flowViewport.offsetX) / prevScale;
    const contentY = (anchorY - state.flowViewport.offsetY) / prevScale;
    state.flowViewport.scale = nextScale;
    state.flowViewport.offsetX = anchorX - contentX * nextScale;
    state.flowViewport.offsetY = anchorY - contentY * nextScale;
    state.flowViewport.userAdjusted = true;
    applyFlowTransform();
  }

  function initFlowViewport() {
    if (!refs.flowCanvasScroll) {
      return;
    }

    refs.flowZoomOutBtn?.addEventListener("click", () => zoomFlowViewport(0.9));
    refs.flowZoomInBtn?.addEventListener("click", () => zoomFlowViewport(1.1));
    refs.flowFitBtn?.addEventListener("click", () => fitFlowViewport());
    refs.flowBoardBtn?.addEventListener("click", () => openBoardView("flow"));
    refs.flowResetBtn?.addEventListener("click", () => {
      const graph = buildGraph();
      state.flowViewport.focusPendingNodeId = "";
      resetFlowViewport(graph);
    });

    refs.flowCanvasScroll.addEventListener("wheel", (event) => {
      event.preventDefault();
      const multiplier = event.deltaY < 0 ? 1.08 : 0.92;
      zoomFlowViewport(multiplier, event.clientX, event.clientY);
    }, { passive: false });

    refs.flowCanvasScroll.addEventListener("pointerdown", (event) => {
      if (event.button !== 0 || event.target.closest(".flow-node")) {
        return;
      }
      state.flowViewport.dragPointerId = event.pointerId;
      state.flowViewport.dragStartX = event.clientX;
      state.flowViewport.dragStartY = event.clientY;
      state.flowViewport.startOffsetX = state.flowViewport.offsetX;
      state.flowViewport.startOffsetY = state.flowViewport.offsetY;
      refs.flowCanvasScroll.classList.add("dragging");
      refs.flowCanvasScroll.setPointerCapture(event.pointerId);
    });

    refs.flowCanvasScroll.addEventListener("pointermove", (event) => {
      if (state.flowViewport.dragPointerId !== event.pointerId) {
        return;
      }
      state.flowViewport.offsetX = state.flowViewport.startOffsetX + (event.clientX - state.flowViewport.dragStartX);
      state.flowViewport.offsetY = state.flowViewport.startOffsetY + (event.clientY - state.flowViewport.dragStartY);
      state.flowViewport.userAdjusted = true;
      applyFlowTransform();
    });

    const stopDragging = (event) => {
      if (state.flowViewport.dragPointerId !== event.pointerId) {
        return;
      }
      state.flowViewport.dragPointerId = null;
      refs.flowCanvasScroll.classList.remove("dragging");
      if (refs.flowCanvasScroll.hasPointerCapture(event.pointerId)) {
        refs.flowCanvasScroll.releasePointerCapture(event.pointerId);
      }
    };

    refs.flowCanvasScroll.addEventListener("pointerup", stopDragging);
    refs.flowCanvasScroll.addEventListener("pointercancel", stopDragging);

    window.addEventListener("resize", () => {
      if (state.flowViewport.userAdjusted) {
        applyFlowTransform();
      } else {
        fitFlowViewport();
      }
    });
  }

  function currentBoardTitle(source = state.boardView.source) {
    if (source === "flow") {
      return "救治决策流程图白板";
    }
    if (source === "report") {
      if (state.reportMode === "baseline") {
        return "单模型救治报告白板";
      }
      if (state.reportMode === "compare") {
        return "救治报告对照白板";
      }
      return "多智能体救治报告白板";
    }
    const node = getNode(state.flow.selectedNodeId || state.flow.activeNodeId || "human");
    return node ? `${node.label} 白板查看` : "会诊白板";
  }

  function currentBoardHtml(source = state.boardView.source) {
    if (source === "flow") {
      return "";
    }
    if (source === "report") {
      return refs.reportBoard ? refs.reportBoard.innerHTML : "";
    }
    return refs.inspector ? refs.inspector.innerHTML : "";
  }

  function clampBoardScale(scale) {
    return Math.min(state.boardView.maxScale, Math.max(state.boardView.minScale, scale));
  }

  function applyBoardTransform() {
    if (!boardRefs.content) {
      return;
    }
    boardRefs.content.style.transform = `translate(${state.boardView.offsetX}px, ${state.boardView.offsetY}px) scale(${state.boardView.scale})`;
    if (boardRefs.zoomLabel) {
      boardRefs.zoomLabel.textContent = `${Math.round(state.boardView.scale * 100)}%`;
    }
  }

  function fitBoardView() {
    if (!boardRefs.viewport || !boardRefs.content) {
      return;
    }
    const viewportRect = boardRefs.viewport.getBoundingClientRect();
    const contentWidth = Math.max(boardRefs.content.scrollWidth, 420);
    const contentHeight = Math.max(boardRefs.content.scrollHeight, 280);
    const scale = clampBoardScale(
      Math.min(
        (viewportRect.width - 120) / contentWidth,
        (viewportRect.height - 120) / contentHeight,
        1
      )
    );
    state.boardView.scale = scale;
    state.boardView.offsetX = Math.max(48, (viewportRect.width - contentWidth * scale) / 2);
    state.boardView.offsetY = Math.max(36, (viewportRect.height - contentHeight * scale) / 2);
    applyBoardTransform();
  }

  function syncBoardViewContent({ fit = false } = {}) {
    if (!state.boardView.open || !boardRefs.root || !boardRefs.content) {
      return;
    }
    const source = state.boardView.source || "inspector";
    boardRefs.title.textContent = currentBoardTitle(source);
    boardRefs.content.classList.toggle("source-flow", source === "flow");
    boardRefs.content.classList.toggle("source-inspector", source === "inspector");
    boardRefs.content.classList.toggle("source-report", source === "report");
    if (source === "flow") {
      clearElement(boardRefs.content);
      if (refs.flowCanvas) {
        const clone = refs.flowCanvas.cloneNode(true);
        clone.style.transform = "";
        clone.style.width = `${state.flowViewport.contentWidth}px`;
        clone.style.height = `${state.flowViewport.contentHeight}px`;
        clone.querySelectorAll(".flow-node").forEach((node) => {
          node.disabled = true;
          node.tabIndex = -1;
        });
        boardRefs.content.style.width = `${state.flowViewport.contentWidth}px`;
        boardRefs.content.style.height = `${state.flowViewport.contentHeight}px`;
        boardRefs.content.append(clone);
      } else {
        boardRefs.content.innerHTML = '<div class="board-view-empty">暂无内容</div>';
      }
    } else {
      boardRefs.content.style.width = "";
      boardRefs.content.style.height = "";
      boardRefs.content.innerHTML = currentBoardHtml(source) || '<div class="board-view-empty">暂无内容</div>';
    }
    if (fit) {
      window.requestAnimationFrame(() => fitBoardView());
      return;
    }
    applyBoardTransform();
  }

  function closeBoardView() {
    if (!boardRefs.root) {
      return;
    }
    state.boardView.open = false;
    state.boardView.dragPointerId = null;
    boardRefs.root.classList.remove("open");
    document.body.classList.remove("board-open");
  }

  function zoomBoardView(multiplier, anchorClientX = null, anchorClientY = null) {
    if (!boardRefs.viewport || !boardRefs.content) {
      return;
    }
    const viewportRect = boardRefs.viewport.getBoundingClientRect();
    const anchorX = anchorClientX === null ? viewportRect.width / 2 : anchorClientX - viewportRect.left;
    const anchorY = anchorClientY === null ? viewportRect.height / 2 : anchorClientY - viewportRect.top;
    const prevScale = state.boardView.scale;
    const nextScale = clampBoardScale(prevScale * multiplier);
    if (Math.abs(nextScale - prevScale) < 0.001) {
      return;
    }
    const contentX = (anchorX - state.boardView.offsetX) / prevScale;
    const contentY = (anchorY - state.boardView.offsetY) / prevScale;
    state.boardView.scale = nextScale;
    state.boardView.offsetX = anchorX - contentX * nextScale;
    state.boardView.offsetY = anchorY - contentY * nextScale;
    applyBoardTransform();
  }

  function ensureBoardView() {
    if (boardRefs.root) {
      return;
    }
    const root = el("div", "board-view");
    const backdrop = el("div", "board-view-backdrop");
    const panel = el("div", "board-view-panel");
    const toolbar = el("div", "board-view-toolbar");
    const title = el("div", "board-view-title", "白板查看");
    const controls = el("div", "board-view-controls");
    const zoomLabel = el("span", "board-view-zoom", "100%");
    const zoomOutBtn = createGhostButton("缩小", () => zoomBoardView(0.9));
    const zoomInBtn = createGhostButton("放大", () => zoomBoardView(1.1));
    const fitBtn = createGhostButton("适配", () => fitBoardView());
    const resetBtn = createGhostButton("重置", () => {
      state.boardView.scale = 1;
      state.boardView.offsetX = 72;
      state.boardView.offsetY = 48;
      applyBoardTransform();
    });
    const closeBtn = createGhostButton("关闭", () => closeBoardView());
    controls.append(zoomOutBtn, zoomLabel, zoomInBtn, fitBtn, resetBtn, closeBtn);
    toolbar.append(title, controls);

    const viewport = el("div", "board-view-viewport");
    const stage = el("div", "board-view-stage");
    const content = el("div", "board-view-content source-inspector");
    stage.append(content);
    viewport.append(stage);
    panel.append(toolbar, viewport);
    root.append(backdrop, panel);
    document.body.append(root);

    backdrop.addEventListener("click", closeBoardView);
    viewport.addEventListener("wheel", (event) => {
      event.preventDefault();
      const multiplier = event.deltaY < 0 ? 1.08 : 0.92;
      zoomBoardView(multiplier, event.clientX, event.clientY);
    }, { passive: false });
    viewport.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) {
        return;
      }
      state.boardView.dragPointerId = event.pointerId;
      state.boardView.dragStartX = event.clientX;
      state.boardView.dragStartY = event.clientY;
      state.boardView.startOffsetX = state.boardView.offsetX;
      state.boardView.startOffsetY = state.boardView.offsetY;
      viewport.classList.add("dragging");
      viewport.setPointerCapture(event.pointerId);
    });
    viewport.addEventListener("pointermove", (event) => {
      if (state.boardView.dragPointerId !== event.pointerId) {
        return;
      }
      state.boardView.offsetX = state.boardView.startOffsetX + (event.clientX - state.boardView.dragStartX);
      state.boardView.offsetY = state.boardView.startOffsetY + (event.clientY - state.boardView.dragStartY);
      applyBoardTransform();
    });
    const stopDragging = (event) => {
      if (state.boardView.dragPointerId !== event.pointerId) {
        return;
      }
      state.boardView.dragPointerId = null;
      viewport.classList.remove("dragging");
      if (viewport.hasPointerCapture(event.pointerId)) {
        viewport.releasePointerCapture(event.pointerId);
      }
    };
    viewport.addEventListener("pointerup", stopDragging);
    viewport.addEventListener("pointercancel", stopDragging);

    boardRefs.root = root;
    boardRefs.title = title;
    boardRefs.viewport = viewport;
    boardRefs.content = content;
    boardRefs.zoomLabel = zoomLabel;
  }

  function openBoardView(source = "inspector") {
    ensureBoardView();
    state.boardView.source = source;
    state.boardView.open = true;
    state.boardView.title = currentBoardTitle(source);
    boardRefs.root.classList.add("open");
    document.body.classList.add("board-open");
    syncBoardViewContent({ fit: true });
  }

  function renderReportModeSwitch(container) {
    const switcher = el("div", "report-mode-switch");
    const modes = [
      { key: "multi", label: "会诊报告" },
      { key: "baseline", label: "单模型报告" },
      { key: "compare", label: "对照查看" },
    ];
    for (const mode of modes) {
      const chip = createChip(mode.label, state.reportMode === mode.key);
      chip.addEventListener("click", () => {
        state.reportMode = mode.key;
        renderReportView();
      });
      switcher.append(chip);
    }
    container.append(switcher);
  }

  function renderReportHero(finalPayload, reports) {
    const hero = el("section", "report-hero");

    const lead = el("div", "report-hero-lead");
    lead.append(el("div", "report-kicker", "会诊主结论"));
    lead.append(el("h2", "report-hero-title", finalPayload.top_diagnosis?.name || "待生成"));
    lead.append(
      el(
        "p",
        "report-hero-copy",
        finalPayload.confidence_statement
          || finalPayload.evidence_sufficiency
          || "当前报告将优先展示结论、证据边界和后续复核建议。"
      )
    );
    hero.append(lead);

    const facts = el("div", "report-hero-facts");
    const confidenceCard = el("article", "report-fact-card");
    confidenceCard.append(el("div", "report-fact-label", "结论强度"));
    confidenceCard.append(el("div", "report-fact-value accent", finalPayload.top_diagnosis?.confidence || "待定"));
    confidenceCard.append(
      el(
        "div",
        "report-fact-note",
        finalPayload.reject_flag || "当前展示的是最终会诊结论，不是中间过程日志。"
      )
    );
    facts.append(confidenceCard);

    const baselineCard = el("article", "report-fact-card");
    baselineCard.append(el("div", "report-fact-label", "单模型对照"));
    if (reports.baseline_error) {
      baselineCard.append(el("div", "report-fact-value muted", "不可用"));
      baselineCard.append(el("div", "report-fact-note", "基线 API 当前不可访问，但不会影响主报告。"));
    } else {
      baselineCard.append(
        el("div", "report-fact-value", finalPayload.comparison_summary?.baseline_top_diagnosis?.name || "-")
      );
      baselineCard.append(
        el(
          "div",
          "report-fact-note",
          finalPayload.comparison_summary?.same_top_diagnosis ? "与多智能体一致" : "与多智能体不同"
        )
      );
    }
    facts.append(baselineCard);

    const evidenceCard = el("article", "report-fact-card");
    evidenceCard.append(el("div", "report-fact-label", "证据状态"));
    evidenceCard.append(el("div", "report-fact-value soft", finalPayload.evidence_sufficiency ? "待复核" : "处理中"));
    evidenceCard.append(
      el(
        "div",
        "report-fact-note",
        finalPayload.evidence_sufficiency || "系统会在报告生成后补充证据完整性说明。"
      )
    );
    facts.append(evidenceCard);

    hero.append(facts);
    return hero;
  }

  function renderReportAlerts(reports) {
    const fragment = document.createDocumentFragment();

    if (reports.baseline_error && reports.baseline_error.message) {
      const card = el("article", "report-alert-card warning");
      card.append(el("div", "report-alert-title", "单模型对照不可用"));
      card.append(el("p", "report-alert-copy", reports.baseline_error.message));
      fragment.append(card);
    }

    if (Array.isArray(reports.quality_issues) && reports.quality_issues.length) {
      const card = el("article", "report-alert-card");
      card.append(el("div", "report-alert-title", "报告提示"));
      const list = el("ul", "md-list");
      for (const item of reports.quality_issues) {
        const text = item && typeof item === "object"
          ? [item.source, item.message].filter(Boolean).join(" · ")
          : `${item}`;
        list.append(el("li", "", text));
      }
      card.append(list);
      fragment.append(card);
    }

    return fragment;
  }

  function renderMarkdownCard(title, markdown, meta) {
    const card = el("article", "report-card report-article-card");
    const head = el("div", "report-card-head");
    head.append(el("h3", "", title));
    if (meta && Object.keys(meta).length) {
      const metaRow = el("div", "report-meta-row");
      if (meta.provider) {
        metaRow.append(el("span", "report-meta-chip", meta.provider));
      }
      if (meta.model) {
        metaRow.append(el("span", "report-meta-chip", meta.model));
      }
      if (meta.latency_ms) {
        metaRow.append(el("span", "report-meta-chip", `${meta.latency_ms} 毫秒`));
      }
      if (metaRow.childNodes.length) {
        head.append(metaRow);
      }
    }
    card.append(head);
    if (meta && meta.error && meta.error.message) {
      card.append(el("p", "report-inline-error", `生成失败：${meta.error.message}`));
    }
    appendMarkdown(card, markdown || "暂无内容");
    return card;
  }

  function renderReportView() {
    clearElement(refs.reportBoard);
    const reports = getReportsPayload();
    const finalPayload = getFinalPayload();
    const reportNode = getNode("report");

    if (!Object.keys(reports).length) {
      if (state.isRunning || (reportNode && reportNode.status === "active")) {
        refs.reportBoard.append(
          createEmptyState("⏳", "救治报告生成中", "会诊流程已进入收尾阶段，救治报告会在所有节点完成后出现在这里。")
        );
      } else {
        refs.reportBoard.append(
          createEmptyState("📄", "暂无救治报告", "先提交一个病例，或从右上角输入运行ID加载历史结果。")
        );
      }
      return;
    }

    renderReportModeSwitch(refs.reportBoard);

    const toolbar = el("div", "report-toolbar");
    const boardBtn = createGhostButton("白板模式", () => openBoardView("report"));
    const copyBtn = el("button", "copy-btn", "复制当前报告");
    copyBtn.type = "button";
    copyBtn.addEventListener("click", () => copyText(currentReportText()));
    toolbar.append(boardBtn, copyBtn);
    refs.reportBoard.append(toolbar);
    refs.reportBoard.append(renderReportHero(finalPayload, reports));
    refs.reportBoard.append(renderReportAlerts(reports));

    if (state.reportMode === "compare") {
      const grid = el("div", "report-compare-grid");
      grid.append(renderMarkdownCard("多智能体救治报告", reports.multi_agent_markdown || "", reports.multi_agent_meta || {}));
      grid.append(renderMarkdownCard("单模型救治报告", reports.baseline_markdown || "", reports.baseline_meta || {}));
      refs.reportBoard.append(grid);
      return;
    }

    if (state.reportMode === "baseline") {
      refs.reportBoard.append(renderMarkdownCard("单模型救治报告", reports.baseline_markdown || "", reports.baseline_meta || {}));
      return;
    }

    refs.reportBoard.append(renderMarkdownCard("多智能体救治报告", reports.multi_agent_markdown || "", reports.multi_agent_meta || {}));
  }

  function isNodeVisible(node) {
    return Boolean(node && node.visible);
  }

  function buildGraph() {
    const centerY = 320;
    const topPadding = 96;
    const bottomPadding = 120;
    const nodes = [];
    const edges = [];
    const pills = [];
    const positions = {};
    const visibleRounds = state.flow.rounds.filter((round) => {
      const summaryNode = getNode(round.summaryNodeId);
      const visibleExperts = round.expertNodeIds.filter((id) => isNodeVisible(getNode(id)));
      return visibleExperts.length || isNodeVisible(summaryNode);
    });

    const baseNodeIds = ["human", "caption", "retrieval"];
    let lastBaseX = 130;
    let maxX = lastBaseX;
    for (const nodeId of baseNodeIds) {
      const node = getNode(nodeId);
      if (!isNodeVisible(node)) {
        continue;
      }
      const x = nodeId === "human" ? 130 : nodeId === "caption" ? 340 : 550;
      positions[nodeId] = { x, y: centerY };
      nodes.push(node);
      lastBaseX = x;
      maxX = Math.max(maxX, x);
    }

    if (isNodeVisible(getNode("caption"))) {
      edges.push({ from: "human", to: "caption" });
    }
    if (isNodeVisible(getNode("retrieval"))) {
      edges.push({ from: "caption", to: "retrieval" });
    }

    let sourceId = isNodeVisible(getNode("retrieval")) ? "retrieval" : isNodeVisible(getNode("caption")) ? "caption" : "human";
    let cursorX = Math.max(760, lastBaseX + 210);
    let roundAnchorX = cursorX;

    for (const round of visibleRounds) {
      const visibleExperts = round.expertNodeIds.filter((id) => isNodeVisible(getNode(id)));
      const count = visibleExperts.length;
      const useSplitColumns = count > 3;
      let summaryX = cursorX + 220;
      let pillX = cursorX;
      let pillY = centerY - 170;

      if (count > 0) {
        if (useSplitColumns) {
          const columnGap = 178;
          const rowGap = 142;
          const leftCount = Math.ceil(count / 2);
          const rightCount = count - leftCount;
          const leftTopY = centerY - ((leftCount - 1) * rowGap) / 2;
          const rightTopY = centerY - ((Math.max(1, rightCount) - 1) * rowGap) / 2;

          visibleExperts.forEach((nodeId, index) => {
            const rightColumn = index >= leftCount;
            const rowIndex = rightColumn ? index - leftCount : index;
            const topY = rightColumn ? rightTopY : leftTopY;
            const x = cursorX + (rightColumn ? columnGap : 0);
            const y = topY + rowGap * rowIndex;
            positions[nodeId] = { x, y };
            nodes.push(getNode(nodeId));
            edges.push({ from: sourceId, to: nodeId });
            maxX = Math.max(maxX, x);
          });

          pillX = cursorX + columnGap / 2;
          pillY = Math.min(leftTopY, rightTopY) - 102;
          summaryX = cursorX + 392;
          cursorX += 620;
        } else {
          const gap = 138;
          const totalHeight = gap * (count - 1);
          const topY = centerY - totalHeight / 2;
          pillX = cursorX;
          pillY = topY - 96;

          visibleExperts.forEach((nodeId, index) => {
            const y = topY + gap * index;
            positions[nodeId] = { x: cursorX, y };
            nodes.push(getNode(nodeId));
            edges.push({ from: sourceId, to: nodeId });
            maxX = Math.max(maxX, cursorX);
          });

          summaryX = cursorX + 230;
          cursorX += 430;
        }
      } else {
        cursorX += 430;
      }

      pills.push({ x: pillX, y: pillY, text: `第 ${round.round} 轮` });

      const summaryNode = getNode(round.summaryNodeId);
      if (isNodeVisible(summaryNode)) {
        positions[round.summaryNodeId] = { x: summaryX, y: centerY };
        nodes.push(summaryNode);
        for (const nodeId of visibleExperts) {
          edges.push({ from: nodeId, to: round.summaryNodeId });
        }
        if (!visibleExperts.length) {
          edges.push({ from: sourceId, to: round.summaryNodeId });
        }
        sourceId = round.summaryNodeId;
        maxX = Math.max(maxX, summaryX);
      }
      roundAnchorX = cursorX;
    }

    const tailNodeIds = ["final", "safety", "report"];
    const tailStep = 220;
    let tailX = roundAnchorX;
    for (const nodeId of tailNodeIds) {
      const node = getNode(nodeId);
      if (!isNodeVisible(node)) {
        continue;
      }
      positions[nodeId] = { x: tailX, y: centerY };
      nodes.push(node);
      edges.push({ from: sourceId, to: nodeId });
      sourceId = nodeId;
      maxX = Math.max(maxX, tailX);
      tailX += tailStep;
    }

    let minVisualY = centerY - 86;
    let maxVisualY = centerY + 96;
    for (const position of Object.values(positions)) {
      minVisualY = Math.min(minVisualY, position.y - 86);
      maxVisualY = Math.max(maxVisualY, position.y + 96);
    }
    for (const pill of pills) {
      minVisualY = Math.min(minVisualY, pill.y - 24);
      maxVisualY = Math.max(maxVisualY, pill.y + 24);
    }

    const verticalShift = minVisualY < topPadding ? topPadding - minVisualY : 0;
    if (verticalShift > 0) {
      Object.values(positions).forEach((position) => {
        position.y += verticalShift;
      });
      pills.forEach((pill) => {
        pill.y += verticalShift;
      });
      maxVisualY += verticalShift;
    }

    const naturalWidth = Math.max(1280, maxX + 220);
    const naturalHeight = Math.max(640, maxVisualY + bottomPadding);

    const contentBounds = {
      minX: Math.min(...Object.values(positions).map((position) => position.x - 110), 80),
      minY: Math.min(...Object.values(positions).map((position) => position.y - 110), topPadding),
      maxX: Math.max(...Object.values(positions).map((position) => position.x + 110), naturalWidth - 80),
      maxY: Math.max(...Object.values(positions).map((position) => position.y + 110), naturalHeight - bottomPadding),
    };
    for (const pill of pills) {
      contentBounds.minX = Math.min(contentBounds.minX, pill.x - 80);
      contentBounds.minY = Math.min(contentBounds.minY, pill.y - 28);
      contentBounds.maxX = Math.max(contentBounds.maxX, pill.x + 80);
      contentBounds.maxY = Math.max(contentBounds.maxY, pill.y + 28);
    }

    const width = Math.max(FLOW_WORLD_MIN_WIDTH, naturalWidth + FLOW_WORLD_PADDING * 2);
    const height = Math.max(FLOW_WORLD_MIN_HEIGHT, naturalHeight + FLOW_WORLD_PADDING * 2);
    const contentCenterX = (contentBounds.minX + contentBounds.maxX) / 2;
    const contentCenterY = (contentBounds.minY + contentBounds.maxY) / 2;
    const shiftX = width / 2 - contentCenterX;
    const shiftY = height / 2 - contentCenterY;

    Object.values(positions).forEach((position) => {
      position.x += shiftX;
      position.y += shiftY;
    });
    pills.forEach((pill) => {
      pill.x += shiftX;
      pill.y += shiftY;
    });

    const bounds = {
      minX: contentBounds.minX + shiftX,
      minY: contentBounds.minY + shiftY,
      maxX: contentBounds.maxX + shiftX,
      maxY: contentBounds.maxY + shiftY,
    };
    return { nodes, edges, pills, positions, width, height, bounds };
  }

  function edgeStatus(targetNode) {
    if (!targetNode) {
      return "pending";
    }
    if (targetNode.status === "active") {
      return "active";
    }
    if (targetNode.status === "complete") {
      return "complete";
    }
    if (targetNode.status === "error") {
      return "error";
    }
    return "pending";
  }

  function curvePath(from, to) {
    const dx = Math.max(80, (to.x - from.x) * 0.48);
    return `M ${from.x} ${from.y} C ${from.x + dx} ${from.y}, ${to.x - dx} ${to.y}, ${to.x} ${to.y}`;
  }

  function createFlowNodeElement(node, position) {
    const button = el("button", `flow-node status-${node.status}${state.flow.selectedNodeId === node.id ? " selected" : ""}`);
    button.type = "button";
    button.style.left = `${position.x}px`;
    button.style.top = `${position.y}px`;
    button.setAttribute("aria-label", node.label);

    const core = el("div", "flow-node-core");
    core.append(el("div", "flow-node-ring"));
    core.append(el("div", "flow-node-orbit"));
    const icon = el("div", `flow-node-icon ${node.colorClass}`);
    icon.append(createAgentGlyph(node.iconKey));
    core.append(icon);
    button.append(core);
    button.append(el("div", "flow-node-label", node.label));

    const metaText = node.kind === "expert" ? `第 ${node.round} 轮` : node.kind === "summary" ? `第 ${node.round} 轮` : node.short;
    button.append(el("div", "flow-node-meta", metaText));
    button.append(el("div", "flow-node-state", FLOW_STATUS_TEXT[node.status] || FLOW_STATUS_TEXT.pending));

    button.addEventListener("click", () => {
      state.flow.followLiveSelection = false;
      state.flowViewport.detailNodeId = node.id;
      state.flowViewport.detailScrollTop = 0;
      state.flowViewport.focusPendingNodeId = node.id;
      setSelectedNode(node.id);
      renderFlowBoard();
    });

    return button;
  }

  function renderFlowBoard() {
    clearElement(refs.flowBoard);
    clearElement(refs.flowEdges);

    const visibleNodes = Object.values(state.flow.nodes).filter((node) => isNodeVisible(node));
    if (!visibleNodes.length) {
      refs.flowCanvas.style.width = "100%";
      refs.flowCanvas.style.height = "100%";
      state.flowViewport.contentWidth = refs.flowCanvasScroll ? Math.max(refs.flowCanvasScroll.clientWidth, 960) : 1280;
      state.flowViewport.contentHeight = refs.flowCanvasScroll ? Math.max(refs.flowCanvasScroll.clientHeight, 560) : 680;
      state.flowViewport.graphBounds = null;
      refs.flowBoard.append(
        createEmptyState("🪐", "流程待命", "提交图片后，这里会按 图像输入 → 检索 → 专家 → 汇总 → 救治报告 的顺序点亮整条流程。")
      );
      renderInspector();
      renderFlowDetailOverlay();
      window.requestAnimationFrame(() => fitFlowViewport());
      return;
    }

    const graph = buildGraph();
    const canvasWidth = graph.width;
    const canvasHeight = graph.height;
    refs.flowCanvas.style.width = `${canvasWidth}px`;
    refs.flowCanvas.style.height = `${canvasHeight}px`;
    refs.flowEdges.setAttribute("viewBox", `0 0 ${canvasWidth} ${canvasHeight}`);
    refs.flowEdges.setAttribute("width", `${canvasWidth}`);
    refs.flowEdges.setAttribute("height", `${canvasHeight}`);

    for (const pill of graph.pills) {
      const pillEl = el("div", "flow-group-pill", pill.text);
      pillEl.style.left = `${pill.x}px`;
      pillEl.style.top = `${pill.y}px`;
      refs.flowBoard.append(pillEl);
    }

    for (const edge of graph.edges) {
      const from = graph.positions[edge.from];
      const to = graph.positions[edge.to];
      if (!from || !to) {
        continue;
      }
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", curvePath(from, to));
      path.setAttribute("class", `flow-edge ${edgeStatus(getNode(edge.to))}`);
      refs.flowEdges.append(path);
    }

    for (const node of graph.nodes) {
      const position = graph.positions[node.id];
      if (!position) {
        continue;
      }
      refs.flowBoard.append(createFlowNodeElement(node, position));
    }

    renderInspector();
    renderFlowDetailOverlay();
    state.flowViewport.contentWidth = canvasWidth;
    state.flowViewport.contentHeight = canvasHeight;
    state.flowViewport.graphBounds = graph.bounds || computeGraphViewportBounds(graph);
    window.requestAnimationFrame(() => {
      if (state.flowViewport.focusPendingNodeId) {
        focusFlowViewport(graph);
      } else if (state.flowViewport.userAdjusted) {
        applyFlowTransform();
      } else {
        fitFlowViewport();
      }
    });
  }

  function computeGraphViewportBounds(graph) {
    if (graph?.bounds) {
      return graph.bounds;
    }
    const points = [];
    for (const position of Object.values(graph.positions || {})) {
      points.push({ x: position.x - 110, y: position.y - 110 });
      points.push({ x: position.x + 110, y: position.y + 110 });
    }
    for (const pill of graph.pills || []) {
      points.push({ x: pill.x - 80, y: pill.y - 28 });
      points.push({ x: pill.x + 80, y: pill.y + 28 });
    }
    if (!points.length) {
      return { minX: 0, minY: 0, maxX: graph.width, maxY: graph.height };
    }
    return {
      minX: Math.min(...points.map((item) => item.x)),
      minY: Math.min(...points.map((item) => item.y)),
      maxX: Math.max(...points.map((item) => item.x)),
      maxY: Math.max(...points.map((item) => item.y)),
    };
  }

  function resetFlowViewport(graph) {
    if (!refs.flowCanvasScroll) {
      return;
    }
    const viewportRect = refs.flowCanvasScroll.getBoundingClientRect();
    const bounds = computeGraphViewportBounds(graph);
    state.flowViewport.scale = 1;
    const contentCenterX = (bounds.minX + bounds.maxX) / 2;
    const contentCenterY = (bounds.minY + bounds.maxY) / 2;
    state.flowViewport.offsetX = viewportRect.width / 2 - contentCenterX;
    state.flowViewport.offsetY = viewportRect.height / 2 - contentCenterY;
    state.flowViewport.userAdjusted = false;
    applyFlowTransform();
  }

  function focusFlowViewport(graph) {
    const nodeId = state.flowViewport.focusPendingNodeId;
    const position = graph.positions[nodeId];
    state.flowViewport.focusPendingNodeId = "";
    if (!position || !refs.flowCanvasScroll) {
      resetFlowViewport(graph);
      return;
    }

    const viewportRect = refs.flowCanvasScroll.getBoundingClientRect();
    const overlayWidth = flowDetailRefs.root && flowDetailRefs.root.classList.contains("open")
      ? flowDetailRefs.root.getBoundingClientRect().width + 18
      : 0;
    const usableWidth = Math.max(240, viewportRect.width - overlayWidth);
    const preferredScale = clampFlowScale(Math.max(state.flowViewport.scale, 1));
    state.flowViewport.scale = preferredScale;
    const targetCenterX = usableWidth / 2;
    const targetCenterY = viewportRect.height / 2;
    state.flowViewport.offsetX = targetCenterX - position.x * preferredScale + 24;
    state.flowViewport.offsetY = targetCenterY - position.y * preferredScale;
    state.flowViewport.userAdjusted = true;
    applyFlowTransform();
  }

  function ensureFlowDetailOverlay() {
    if (flowDetailRefs.root || !refs.flowBoardView) {
      return;
    }
    const root = el("div", "flow-detail-overlay");
    const panel = el("div", "flow-detail-panel");
    const head = el("div", "flow-detail-head");
    const title = el("div", "flow-detail-title", "节点详情");
    const actions = el("div", "flow-detail-actions");
    const boardBtn = createGhostButton("白板模式", () => openBoardView("inspector"));
    const closeBtn = createGhostButton("关闭", () => {
      state.flowViewport.detailNodeId = "";
      state.flowViewport.detailScrollTop = 0;
      renderFlowDetailOverlay();
    });
    actions.append(boardBtn, closeBtn);
    head.append(title, actions);

    const body = el("div", "flow-detail-body");
    body.addEventListener("scroll", () => {
      state.flowViewport.detailScrollTop = body.scrollTop;
    });

    panel.append(head, body);
    root.append(panel);
    refs.flowBoardView.append(root);

    flowDetailRefs.root = root;
    flowDetailRefs.title = title;
    flowDetailRefs.body = body;
  }

  function renderFlowDetailOverlay() {
    ensureFlowDetailOverlay();
    if (!flowDetailRefs.root || !flowDetailRefs.body) {
      return;
    }
    const detailNode = getNode(state.flowViewport.detailNodeId || "");
    const sourceCard = refs.inspector?.firstElementChild;
    if (!detailNode || !isNodeVisible(detailNode) || !sourceCard) {
      flowDetailRefs.root.classList.remove("open");
      clearElement(flowDetailRefs.body);
      return;
    }

    flowDetailRefs.root.classList.add("open");
    flowDetailRefs.title.textContent = `${detailNode.label} · 节点详情`;
    clearElement(flowDetailRefs.body);
    const clone = sourceCard.cloneNode(true);
    clone.querySelectorAll(".inspector-head-actions").forEach((item) => item.remove());
    clone.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
      button.tabIndex = -1;
    });
    flowDetailRefs.body.append(clone);
    window.requestAnimationFrame(() => {
      if (flowDetailRefs.body) {
        flowDetailRefs.body.scrollTop = state.flowViewport.detailScrollTop;
      }
    });
  }

  function inspectorBlock(title, content) {
    const block = el("section", "inspector-block");
    block.append(el("div", "inspector-block-title", title));
    if (typeof content === "string") {
      const p = el("div", content ? "inspector-block-text" : "empty-inline", content || "暂无内容");
      block.append(p);
      return block;
    }
    block.append(content);
    return block;
  }

  function paragraphNode(text) {
    return el("div", text ? "inspector-block-text" : "empty-inline", text || "暂无内容");
  }

  function listNode(items) {
    const clean = uniq(items);
    if (!clean.length) {
      return el("div", "empty-inline", "暂无内容");
    }
    const ul = el("ul", "inspector-list");
    for (const item of clean) {
      ul.append(el("li", "", item));
    }
    return ul;
  }

  function codeNode(payload) {
    const pre = el("pre", "inspector-code");
    pre.textContent = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    return pre;
  }

  function collapsibleCodeBlock(title, payload, open = false) {
    const details = el("details", "inspector-collapse");
    details.open = open;
    const summary = el("summary", "", title);
    const body = el("div", "inspector-collapse-body");
    body.append(codeNode(payload));
    details.append(summary);
    details.append(body);
    return details;
  }

  function revealSlotKey(nodeId, key, text) {
    return `${nodeId}:${key}:${text.length}:${text.slice(0, 36)}`;
  }

  function scheduleReveal(slotKey, textLength) {
    if (state.revealTimers[slotKey] || state.revealProgress[slotKey] >= textLength) {
      return;
    }
    state.revealTimers[slotKey] = window.setTimeout(() => {
      delete state.revealTimers[slotKey];
      const current = state.revealProgress[slotKey] || 0;
      const step = Math.max(6, Math.ceil(textLength / 30));
      state.revealProgress[slotKey] = Math.min(textLength, current + step);
      renderInspector();
      if (state.revealProgress[slotKey] < textLength) {
        scheduleReveal(slotKey, textLength);
      }
    }, 24);
  }

  function progressiveTextNode(nodeId, key, text, isActive = false) {
    const block = el("div", "stream-block");
    const content = `${text || ""}`.trim();
    if (!content) {
      const placeholder = el("div", "stream-text stream-placeholder", "正在等待结构化输出...");
      if (isActive) {
        placeholder.append(el("span", "stream-caret", "|"));
      }
      block.append(placeholder);
      return block;
    }

    const slotKey = revealSlotKey(nodeId, key, content);
    if (state.revealProgress[slotKey] === undefined) {
      state.revealProgress[slotKey] = isActive ? Math.max(10, Math.ceil(content.length * 0.35)) : 0;
    }
    scheduleReveal(slotKey, content.length);

    const shown = content.slice(0, Math.min(content.length, state.revealProgress[slotKey]));
    const textEl = el("div", "stream-text", shown);
    if (state.revealProgress[slotKey] < content.length || isActive) {
      textEl.append(el("span", "stream-caret", "|"));
    }
    block.append(textEl);
    return block;
  }

  function composeNodeNarration(node) {
    if (!node) {
      return "";
    }
    if (node.kind === "human") {
      return `已上传草莓病害原图并启动自动诊断。当前任务：${state.flow.problemName || node.data?.problem_name || "草莓病害图像诊断报告"}`;
    }
    if (node.kind === "caption") {
      const display = node.data?.image_analysis_display || {};
      if (display.摘要) {
        return display.摘要;
      }
      if (node.data?.processing_message) {
        return node.data.processing_message;
      }
      const caption = node.data?.caption || {};
      return caption.visual_summary || "视觉节点正在把原图压缩成结构化症状证据。";
    }
    if (node.kind === "retrieval") {
      const count = node.data?.kb_evidence_count ?? asList(node.data?.kb_evidence).length;
      if (!count) {
        return "检索节点正在比对知识库里的历史病例和证据片段。";
      }
      return `检索节点已召回 ${count} 条近似病例证据，供后续专家会诊引用。`;
    }
    if (node.kind === "expert") {
      const turn = node.data || {};
      const top = asList(turn.top_k_causes)[0];
      const topName = top && top.name ? top.name : "尚未给出主候选病因";
      const action = asList(turn.actions)[0] || "等待处置建议";
      return `${node.label} 当前主看法是 ${topName}。当前优先处置：${action}。`;
    }
    if (node.kind === "summary") {
      const summary = node.data?.summary || {};
      const consensus = asList(summary.consensus)[0] || "暂无共识";
      const sharedState = node.data?.shared_state || {};
      const focus = asList(summary.next_focus)[0] || asList(sharedState.report_priority)[0] || asList(summary.report_priority)[0] || "暂无下一轮焦点";
      const sufficiency = sharedState.evidence_sufficiency || summary.evidence_sufficiency || "尚未给出证据充分度";
      return `本轮会诊共识：${consensus}。证据充分度：${sufficiency}。下一步聚焦：${focus}。`;
    }
    if (node.kind === "final") {
      const finalData = node.data?.final || {};
      const topName = finalData.top_diagnosis?.name || "尚未得出最终救治结论";
      const action = asList(finalData.actions)[0]
        || (Array.isArray(finalData.rescue_plan) && finalData.rescue_plan[0] ? asList(finalData.rescue_plan[0].actions)[0] : "")
        || "暂无处置建议";
      const sufficiency = finalData.evidence_sufficiency || "未说明";
      return `最终结论节点给出的主判断是 ${topName}。优先处置：${action}。证据充分度：${sufficiency}。`;
    }
    if (node.kind === "safety") {
      const safety = node.data?.safety || {};
      if (typeof safety.safety_passed !== "boolean") {
        return "安全审校节点正在检查动作边界与风险提示。";
      }
      const actionLevel = localizeSafetyActionLevel(safety.action_level || "conservative_only");
      const firstFlag = localizeSafetyText(asList(safety.flags)[0] || "");
      return safety.safety_passed
        ? `安全审校通过，动作级别：${actionLevel || "证据充分，可执行完整方案"}。`
        : `安全审校未通过，动作级别：${actionLevel || "仅建议保守方案"}，风险提示：${firstFlag || "存在待修订动作"}。`;
    }
    if (node.kind === "report") {
      const reports = node.data?.reports || {};
      if (!reports.multi_agent_markdown) {
        return "报告节点正在把多轮会诊结论整理成结构化救治报告。";
      }
      return `救治报告已生成。多智能体版本 ${reports.multi_agent_markdown.length} 字符，单模型版本 ${(`${reports.baseline_markdown || ""}`).length} 字符。`;
    }
    return node.description || "";
  }

  function renderInspectorHead(node) {
    const head = el("div", "inspector-head");
    const icon = el("div", `inspector-icon ${node.colorClass}`);
    icon.append(createAgentGlyph(node.iconKey));
    head.append(icon);

    const body = el("div", "inspector-head-body");
    body.append(el("h3", "inspector-title", node.label));
    const subtitleText = node.kind === "expert"
      ? `第 ${node.round} 轮 · ${displayAgentName(node.agentName)}`
      : node.kind === "summary"
        ? `第 ${node.round} 轮汇总节点`
        : node.description;
    body.append(el("div", "inspector-subtitle", subtitleText));
    const status = el("div", `inspector-status status-pill-${node.status}`, FLOW_STATUS_TEXT[node.status] || FLOW_STATUS_TEXT.pending);
    body.append(status);

    head.append(body);
    const actions = el("div", "inspector-head-actions");
    actions.append(createGhostButton("白板模式", () => openBoardView("inspector")));
    head.append(actions);
    return head;
  }

  function evidenceBoardLines(board) {
    if (!Array.isArray(board)) {
      return [];
    }
    return board.map((item) => {
      const diagnosis = item?.diagnosis || "未命名候选";
      const support = asList(item?.supporting).slice(0, 2).join("；") || "无支持证据";
      const counter = asList(item?.counter).slice(0, 1).join("；") || "无明显反证";
      const missing = asList(item?.missing).slice(0, 1).join("；") || "无额外补证要求";
      return `${diagnosis}｜支持: ${support}｜反证: ${counter}｜待补证: ${missing}`;
    });
  }

  function rescuePlanLines(plan) {
    if (!Array.isArray(plan)) {
      return [];
    }
    return plan.map((item) => {
      const phase = item?.phase || "未命名阶段";
      const objective = item?.objective || "未填写目标";
      const actions = asList(item?.actions).join("；") || "暂无动作";
      const risk = item?.risk_level || "未标记风险级别";
      return `${phase}｜目标: ${objective}｜动作: ${actions}｜风险: ${risk}`;
    });
  }

  function qualityIssueLines(items) {
    if (!Array.isArray(items)) {
      return [];
    }
    return items.map((item) => {
      if (!item || typeof item !== "object") {
        return `${item || ""}`.trim();
      }
      const source = item.source || item.code || "report";
      const message = item.message || JSON.stringify(item);
      return `${source}｜${message}`;
    }).filter(Boolean);
  }

  function renderInspector() {
    const node = getNode(state.flow.selectedNodeId || state.flow.activeNodeId || "human");
    const sameNode = Boolean(node && state.inspectorView.nodeId === node.id);
    const preservedScrollTop = sameNode && refs.inspector ? refs.inspector.scrollTop : 0;
    clearElement(refs.inspector);
    if (!node || !isNodeVisible(node)) {
      state.inspectorView.nodeId = "";
      state.inspectorView.scrollTop = 0;
      const empty = el("div", "inspector-empty");
      empty.append(el("div", "inspector-empty-icon", "🍓"));
      empty.append(el("div", "inspector-empty-title", "流程已就绪"));
      empty.append(el("div", "inspector-empty-text", "点击任意节点查看它的职责、输入来源和当前输出。"));
      refs.inspector.append(empty);
      renderFlowDetailOverlay();
      return;
    }

    const card = el("article", "inspector-card");
    card.append(renderInspectorHead(node));
    card.append(
      inspectorBlock(
        "流式摘录",
        progressiveTextNode(node.id, "stream", composeNodeNarration(node), node.status === "active")
      )
    );

    if (node.kind === "human") {
      card.append(inspectorBlock("任务名称", paragraphNode(state.flow.problemName || node.data?.problem_name || "-")));
      card.append(
        inspectorBlock(
          "输入方式",
          paragraphNode("当前流程默认只接收草莓病害图片，由系统自动分析原图并生成诊断报告。")
        )
      );
    } else if (node.kind === "caption") {
      const caption = node.data?.caption || {};
      const slotExtraction = node.data?.slot_extraction || {};
      const imageAnalysis = node.data?.image_analysis || {};
      const imageDisplay = node.data?.image_analysis_display || {};
      const visionResult = node.data?.vision_result || {};
      const lesion = slotExtraction?.image_evidence?.lesions?.[0] || {};
      const leafLevel = slotExtraction?.leaf_level || {};
      const formatSlotLine = (label, slot) => {
        if (!slot || typeof slot !== "object") {
          return `${label}: -`;
        }
        const value = `${slot.value ?? "-"}`.trim() || "-";
        const confidence = slot.confidence ?? "-";
        return `${label}: ${value} (置信度 ${confidence})`;
      };
      if (imageDisplay.摘要) {
        card.append(inspectorBlock("图像综合判断", paragraphNode(imageDisplay.摘要)));
      }
      if (imageDisplay["结论卡片"]) {
        const displayLines = Object.entries(imageDisplay["结论卡片"]).map(([key, value]) => `${key}: ${value}`);
        card.append(inspectorBlock("图像结论卡片", listNode(displayLines)));
      }
      card.append(inspectorBlock("视觉摘要", paragraphNode(caption.visual_summary || "正在等待视觉结构化结果...")));
      const slotLines = [
        formatSlotLine("病斑颜色", lesion.color),
        formatSlotLine("组织状态", lesion.tissue_state),
        formatSlotLine("斑点形态", lesion.shape),
        formatSlotLine("边界特征", lesion.boundary),
        formatSlotLine("分布位置", lesion.distribution_position),
        formatSlotLine("分布模式", lesion.distribution_pattern),
        formatSlotLine("叶片形态变化", leafLevel.morph_change),
        formatSlotLine("虫害或机械损伤线索", leafLevel.pest_or_mechanical_hint),
        formatSlotLine("其他可见表现", leafLevel.other_visible_signs),
      ];
      if (slotLines.length) {
        card.append(inspectorBlock("槽位抽取", listNode(slotLines)));
      }
      const symptomLines = [];
      const symptomLabelMap = {
        color: "病斑颜色",
        tissue_state: "组织状态",
        spot_shape: "斑点形态",
        boundary: "边界特征",
        distribution_position: "分布位置",
        distribution_pattern: "分布模式",
        morph_change: "叶片形态变化",
        pest_cues: "虫害或机械损伤线索",
        co_signs: "伴随线索",
      };
      if (caption.symptoms) {
        for (const [key, value] of Object.entries(caption.symptoms)) {
          const label = symptomLabelMap[key] || key;
          symptomLines.push(`${label}: ${asList(value).join("，")}`);
        }
      }
      card.append(inspectorBlock("症状结构", listNode(symptomLines)));
      const numeric = caption.numeric || {};
      const numericLines = [
        `置信度: ${caption.confidence ?? "-"}`,
        `OOD 分数: ${caption.ood_score ?? "-"}`,
        `病斑面积比: ${numeric.area_ratio ?? "-"}`,
        `严重度: ${numeric.severity_score ?? "-"}`,
      ];
      card.append(inspectorBlock("数值特征", listNode(numericLines)));
      card.append(inspectorBlock("内部关注点", listNode(caption.followup_questions || [])));
      if (Object.keys(slotExtraction).length) {
        card.append(collapsibleCodeBlock("槽位抽取 JSON", slotExtraction, false));
      }
      if (Object.keys(imageAnalysis).length) {
        card.append(collapsibleCodeBlock("分类与分割 JSON", imageAnalysis, false));
      }
      if (Object.keys(visionResult).length) {
        card.append(collapsibleCodeBlock("融合结果 JSON", visionResult, false));
      }
    } else if (node.kind === "retrieval") {
      const kb = node.data?.kb_evidence || [];
      card.append(inspectorBlock("检索状态", paragraphNode(node.status === "active" ? "正在从知识库召回病例证据..." : `共召回 ${node.data?.kb_evidence_count ?? kb.length} 条证据`)));
      const lines = kb.map((item, index) => {
        const top = item.top_diagnosis?.name || item.problem_name || item.run_id || `证据_${index + 1}`;
        return `${top} · ${item.run_id || "无运行ID"}`;
      });
      card.append(inspectorBlock("召回证据", listNode(lines)));
    } else if (node.kind === "expert") {
      const turn = node.data || {};
      const causes = asList(turn.top_k_causes).map((item) => `${item.name}: ${item.why_like || ""}`.trim());
      card.append(inspectorBlock("角色职责", paragraphNode(turn.role || node.description)));
      card.append(inspectorBlock("主候选病因", listNode(causes)));
      card.append(inspectorBlock("支持证据", listNode(turn.supporting_evidence || [])));
      card.append(inspectorBlock("反证", listNode(turn.counter_evidence || [])));
      card.append(inspectorBlock("处置建议", listNode(turn.actions || [])));
      card.append(inspectorBlock("关键判断问题", listNode(turn.questions_to_ask || [])));
      const metaLines = [];
      if (turn.confidence !== undefined) {
        metaLines.push(`置信度: ${turn.confidence}`);
      }
      if (turn.meta) {
        metaLines.push(`服务商: ${turn.meta.provider}`);
        metaLines.push(`模型: ${turn.meta.model}`);
        metaLines.push(`时延: ${turn.meta.latency_ms} 毫秒`);
        metaLines.push(`兜底: ${turn.meta.used_fallback ? "是" : "否"}`);
      }
      card.append(inspectorBlock("执行元数据", listNode(metaLines)));
    } else if (node.kind === "summary") {
      const summary = node.data?.summary || {};
      const sharedState = node.data?.shared_state || {};
      card.append(inspectorBlock("共识", listNode(summary.consensus || [])));
      card.append(inspectorBlock("冲突", listNode(summary.conflicts || [])));
      card.append(inspectorBlock("下一轮焦点", listNode(summary.next_focus || [])));
      card.append(inspectorBlock("当前病因假设", listNode(sharedState.working_diagnoses || summary.working_diagnoses || [])));
      card.append(inspectorBlock("当前未定判断点", listNode(sharedState.open_questions || summary.open_questions || [])));
      card.append(inspectorBlock("证据板", listNode(evidenceBoardLines(sharedState.evidence_board || summary.evidence_board || []))));
      card.append(inspectorBlock("处置焦点", listNode(sharedState.action_focus || summary.action_focus || [])));
      card.append(inspectorBlock("补证任务", listNode(sharedState.verification_tasks || summary.verification_tasks || [])));
      card.append(inspectorBlock("报告优先级", listNode(sharedState.report_priority || summary.report_priority || [])));
      const extra = [
        `不确定性评分: ${sharedState.uncertainty_score ?? summary.uncertainty_score ?? "-"}`,
        `停止信号: ${(sharedState.stop_signal ?? summary.stop_signal) ? "是" : "否"}`,
      ];
      extra.push(`不确定性触发点: ${asList(sharedState.uncertainty_triggers || summary.uncertainty_triggers || []).join("；") || "-"}`);
      extra.push(`证据充分度: ${sharedState.evidence_sufficiency || summary.evidence_sufficiency || "-"}`);
      card.append(inspectorBlock("会诊状态", listNode(extra)));
    } else if (node.kind === "final") {
      const finalData = node.data?.final || getFinalPayload();
      card.append(inspectorBlock("最终结论", paragraphNode(finalData.top_diagnosis?.name ? `${finalData.top_diagnosis.name} · ${finalData.top_diagnosis.confidence}` : "正在等待最终结论...")));
      const candidates = asList(finalData.candidates).map((item) => `${item.name}: ${item.why_like || ""}`.trim());
      card.append(inspectorBlock("鉴别对象", listNode(candidates)));
      card.append(inspectorBlock("病例摘要素材", listNode(finalData.symptom_summary || [])));
      card.append(inspectorBlock("视觉证据", listNode(finalData.visual_evidence || [])));
      card.append(inspectorBlock("反证", listNode(finalData.counter_evidence || [])));
      card.append(inspectorBlock("证据板", listNode(evidenceBoardLines(finalData.evidence_board || []))));
      card.append(inspectorBlock("救治实施路径", listNode(rescuePlanLines(finalData.rescue_plan || []))));
      card.append(inspectorBlock("处置动作", listNode(finalData.actions || [])));
      card.append(inspectorBlock("补充证据", listNode(finalData.evidence_to_collect || [])));
      card.append(inspectorBlock("禁忌动作", listNode(finalData.prohibited_actions || [])));
      card.append(inspectorBlock("复查与监测", listNode(finalData.monitoring_plan || [])));
      card.append(inspectorBlock("报告大纲", listNode(finalData.report_outline || [])));
      card.append(inspectorBlock("证据充分度", paragraphNode(finalData.evidence_sufficiency || "未提供证据充分度说明")));
      card.append(inspectorBlock("可信度声明", paragraphNode(finalData.confidence_statement || "未提供可信度声明")));
      card.append(inspectorBlock("安全备注", listNode(finalData.safety_notes || [])));
    } else if (node.kind === "safety") {
      const safety = node.data?.safety || getSafetyPayload();
      const safetyText = typeof safety.safety_passed === "boolean" ? (safety.safety_passed ? "已通过" : "未通过") : "等待审校结果";
      card.append(inspectorBlock("审校结论", paragraphNode(safetyText)));
      card.append(inspectorBlock("动作级别", paragraphNode(localizeSafetyActionLevel(safety.action_level) || "未分级")));
      card.append(inspectorBlock("证据充分度", paragraphNode(localizeSafetyText(safety.evidence_sufficiency) || "未说明")));
      card.append(inspectorBlock("审校摘要", paragraphNode(localizeSafetyText(safety.review_summary) || "未提供审校摘要")));
      card.append(inspectorBlock("风险标记", listNode(localizeSafetyList(safety.flags || []))));
      card.append(inspectorBlock("修订动作", listNode(safety.revised_actions || [])));
      card.append(inspectorBlock("禁忌动作", listNode(safety.prohibited_actions || [])));
      card.append(inspectorBlock("追加补证要求", listNode(localizeSafetyList(safety.required_followups || []))));
    } else if (node.kind === "report") {
      const reports = node.data?.reports || getReportsPayload();
      const qualityIssues = Array.isArray(reports.quality_issues)
        ? reports.quality_issues.map((item) => (item && typeof item === "object" ? [item.source, item.message].filter(Boolean).join(" · ") : `${item}`))
        : [];
      card.append(inspectorBlock("多智能体救治报告", paragraphNode(reports.multi_agent_markdown ? `长度 ${reports.multi_agent_markdown.length} 字符` : "正在生成...")));
      card.append(inspectorBlock("单模型救治报告", paragraphNode(reports.baseline_markdown ? `长度 ${reports.baseline_markdown.length} 字符` : "正在生成...")));
      card.append(inspectorBlock("质量提示", listNode(qualityIssues)));
    }

    if (node.data) {
      card.append(collapsibleCodeBlock("原始 JSON", node.data, false));
    }

    refs.inspector.append(card);
    state.inspectorView.nodeId = node.id;
    state.inspectorView.scrollTop = sameNode ? preservedScrollTop : 0;
    window.requestAnimationFrame(() => {
      if (refs.inspector) {
        refs.inspector.scrollTop = state.inspectorView.scrollTop;
      }
    });
    renderFlowDetailOverlay();
  }

  function renderCurrentRun() {
    renderRunMeta();
    renderFlowBoard();
    renderReportView();
    if (state.boardView.open) {
      syncBoardViewContent();
    }
  }

  function readErrorMessage(detail) {
    if (!detail) {
      return "未知错误";
    }
    if (typeof detail === "string") {
      return detail;
    }
    if (detail.message) {
      return detail.message;
    }
    if (detail.detail) {
      return readErrorMessage(detail.detail);
    }
    if (detail.code) {
      return `${detail.code}${detail.stage ? ` @ ${detail.stage}` : ""}`;
    }
    return JSON.stringify(detail);
  }

  function safeErrorText(err) {
    if (err instanceof Error) {
      return err.message;
    }
    return readErrorMessage(err);
  }

  function handleStreamEvent(event) {
    if (!event || !event.type) {
      return;
    }
    if (event.run_id) {
      state.runId = event.run_id;
      refs.runLookup.value = event.run_id;
    }

    switch (event.type) {
      case "run_started": {
        state.trace = { rounds: [] };
        state.finalResp = {};
        state.lastResult = null;
        state.currentStage = event.stage || "initial";
        setStatus(`图像诊断已启动 · ${event.problem_name || "草莓病害图像诊断报告"}`, "running");
        break;
      }
      case "caption_ready": {
        state.trace.caption = event.caption || {};
        state.trace.slot_extraction = event.slot_extraction || {};
        state.trace.image_analysis = event.image_analysis || {};
        state.trace.image_analysis_display = event.image_analysis_display || {};
        state.trace.vision_result = event.vision_result || {};
        setStatus("视觉摘要与图像分析已完成", "running");
        break;
      }
      case "image_processing_started": {
        setStatus(event.message || "已接收图片，正在执行视觉分析", "running");
        break;
      }
      case "slot_extraction_ready": {
        state.trace.slot_extraction = event.slot_extraction || {};
        break;
      }
      case "image_analysis_ready": {
        state.trace.image_analysis = event.image_analysis || {};
        state.trace.image_analysis_display = event.display || {};
        break;
      }
      case "kb_ready": {
        state.trace.kb_evidence = event.kb_evidence || [];
        setStatus(`知识库召回完成 · ${event.kb_evidence_count || asList(event.kb_evidence).length} 条证据`, "running");
        break;
      }
      case "round_started": {
        const round = ensureRoundTrace(event.round);
        round.active_agents = event.active_agents || [];
        round.shared_state_before = event.shared_state || {};
        setStatus(`第 ${event.round} 轮启动`, "running");
        break;
      }
      case "expert_started": {
        const round = ensureRoundTrace(event.round);
        round.active_agents = uniq([...(round.active_agents || []), ...asList(event.active_agents)]);
        setStatus(`${displayAgentName(event.agent_name)} 正在生成`, "running");
        break;
      }
      case "expert_turn": {
        const round = ensureRoundTrace(event.round);
        round.active_agents = uniq([...(round.active_agents || []), ...asList(event.active_agents)]);
        round.expert_turns = asList(round.expert_turns).filter((item) => item.agent_name !== event.agent_name);
        round.expert_turns.push(event.turn || {});
        setStatus(`${displayAgentName(event.agent_name)} 已完成`, "running");
        break;
      }
      case "round_summary_started": {
        setStatus(`第 ${event.round} 轮汇总中`, "running");
        break;
      }
      case "round_summary": {
        const round = ensureRoundTrace(event.round);
        round.summary = event.summary || {};
        round.shared_state = event.shared_state || {};
        state.trace.shared_state = event.shared_state || {};
        setStatus(`第 ${event.round} 轮汇总完成`, "running");
        break;
      }
      case "final_started": {
        setStatus("最终救治结论生成中", "running");
        break;
      }
      case "final_result": {
        state.trace.final = event.final || {};
        state.trace.final_meta = event.meta || {};
        state.trace.shared_state = event.shared_state || {};
        setStatus(`最终救治结论已产出 · ${event.final?.top_diagnosis?.name || "未命名结果"}`, "running");
        break;
      }
      case "safety_started": {
        setStatus("安全审校中", "running");
        break;
      }
      case "safety_result": {
        state.trace.safety = event.safety || {};
        state.trace.safety_meta = event.meta || {};
        setStatus(event.safety?.safety_passed ? "安全审校通过" : "安全审校已返回修订", "running");
        break;
      }
      case "reports_started": {
        setStatus("救治报告生成中", "running");
        break;
      }
      case "reports_ready": {
        state.trace.report_meta = {
          multi_agent_meta: event.multi_agent_meta || {},
          baseline_meta: event.baseline_meta || {},
        };
        setStatus("报告元数据已就绪", "running");
        break;
      }
      case "complete": {
        state.lastResult = event.result || null;
        state.finalResp = (event.result && event.result.final) || {};
        state.trace = (event.result && event.result.trace) || state.trace;
        state.isRunning = false;
        hydrateFlowFromSavedRun();
        setBusy(false);
        setStatus(`运行完成 · ${state.finalResp.top_diagnosis?.name || "已生成结果"}`, "done");
        break;
      }
      case "error": {
        state.isRunning = false;
        setBusy(false);
        setStatus(`运行失败 · ${readErrorMessage(event.detail)}`, "error");
        break;
      }
      default:
        break;
    }

    updateFlowFromStreamEvent(event);
    renderCurrentRun();
  }

  async function runDiagnosisStream(formData) {
    const response = await fetch("/api/v1/diagnosis/run_stream", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `请求失败（HTTP ${response.status}）`);
    }

    if (!response.body) {
      const text = await response.text();
      for (const line of text.split(/\r?\n/)) {
        if (line.trim()) {
          handleStreamEvent(JSON.parse(line));
        }
      }
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex = buffer.indexOf("\n");
      while (newlineIndex >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (line) {
          handleStreamEvent(JSON.parse(line));
        }
        newlineIndex = buffer.indexOf("\n");
      }
    }

    const tail = buffer.trim();
    if (tail) {
      handleStreamEvent(JSON.parse(tail));
    }
  }

  async function loadRun(runId) {
    const cleanId = `${runId || ""}`.trim();
    if (!cleanId) {
      setStatus("请输入有效的运行ID", "error");
      return;
    }

    setBusy(true);
    setStatus(`正在加载 ${cleanId}...`, "running");
    try {
      const [traceResp, finalResp] = await Promise.all([
        fetch(`/api/v1/runs/${encodeURIComponent(cleanId)}/trace`),
        fetch(`/api/v1/runs/${encodeURIComponent(cleanId)}`),
      ]);
      if (!traceResp.ok || !finalResp.ok) {
        const message = !traceResp.ok ? await traceResp.text() : await finalResp.text();
        throw new Error(message || "加载运行失败");
      }
      const tracePayload = await traceResp.json();
      const finalPayload = await finalResp.json();
      state.runId = cleanId;
      state.trace = tracePayload.trace || { rounds: [] };
      state.finalResp = finalPayload.final || {};
      state.lastResult = null;
      state.currentStage = state.finalResp.stage || "initial";
      state.isRunning = false;
      hydrateFlowFromSavedRun();
      navigateTo("diagnosis");
      renderCurrentRun();
      setStatus(`已加载 ${cleanId}`, "done");
      refs.runLookup.value = cleanId;
    } catch (err) {
      setStatus(`加载失败 · ${safeErrorText(err)}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function clearKnowledgeBase(target, targetStatusEl) {
    const body = JSON.stringify({ target });
    setKbStatus(targetStatusEl, "正在清理知识库...");
    try {
      const response = await fetch("/api/v1/knowledge/clear", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      setKbStatus(
        targetStatusEl,
        `已清理 ${payload.cleared_total} 条记录 (${payload.target})`
      );
      await Promise.all([loadCasesData(), loadKnowledgeDocuments()]);
      if (state.activePage === "cases") {
        renderCasesTab(state.caseActiveTab);
      }
      if (state.activePage === "kb") {
        renderKbPage();
      }
    } catch (err) {
      setKbStatus(targetStatusEl, `清理失败: ${safeErrorText(err)}`, true);
    }
  }

  function navigateTo(page) {
    state.activePage = page;
    refs.navButtons.forEach((button) => button.classList.toggle("active", button.dataset.page === page));
    refs.topPage.textContent = PAGE_TITLES[page] || PAGE_TITLES.diagnosis;

    refs.workspace.style.display = page === "diagnosis" ? "flex" : "none";
    refs.dashPage.style.display = page === "dashboard" ? "flex" : "none";
    refs.runsPage.style.display = page === "runs" ? "flex" : "none";
    refs.casesPage.style.display = page === "cases" ? "flex" : "none";
    refs.kbPage.style.display = page === "kb" ? "flex" : "none";

    if (page === "dashboard") {
      void loadDashboardData();
    } else if (page === "runs") {
      void loadRunsList();
    } else if (page === "cases") {
      void loadCasesPage();
    } else if (page === "kb") {
      void loadKbPage();
    }
  }

  async function deleteRun(runId) {
    const cleanId = `${runId || ""}`.trim();
    if (!cleanId) {
      return;
    }
    const confirmed = window.confirm(`确认删除运行记录 ${cleanId} 吗？对应病例库摘要也会一并删除。`);
    if (!confirmed) {
      return;
    }
    try {
      const response = await fetch(`/api/v1/runs/${encodeURIComponent(cleanId)}`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      await Promise.all([loadRunsList(), loadCasesData()]);
      if (state.activePage === "cases") {
        renderCasesTab(state.caseActiveTab || "verified");
      }
      if (state.activePage === "kb") {
        renderKbPage();
      }
      setStatus(`已删除运行记录 ${cleanId}`, "done");
    } catch (err) {
      setStatus(`删除失败 · ${safeErrorText(err)}`, "error");
    }
  }

  async function deleteCaseRecord(runId) {
    const cleanId = `${runId || ""}`.trim();
    if (!cleanId) {
      return;
    }
    const confirmed = window.confirm(`确认从病例库删除 ${cleanId} 吗？此操作不会删除运行记录文件。`);
    if (!confirmed) {
      return;
    }
    try {
      const response = await fetch(`/api/v1/cases/${encodeURIComponent(cleanId)}`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      await Promise.all([loadCasesData(), loadKnowledgeDocuments()]);
      if (state.activePage === "cases") {
        renderCasesTab(state.caseActiveTab || "verified");
      }
      if (state.activePage === "kb") {
        renderKbPage();
      }
      setStatus(`已从病例库删除 ${cleanId}`, "done");
    } catch (err) {
      setStatus(`病例删除失败 · ${safeErrorText(err)}`, "error");
    }
  }

  function renderRunList(items) {
    clearElement(refs.runsList);
    if (!items.length) {
      refs.runsList.append(createEmptyState("🗂️", "暂无运行记录", "先跑一条病例，历史记录才会出现在这里。"));
      return;
    }
    for (const item of items) {
      const row = el("article", "list-row list-row-shell");
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.append(el("div", "list-row-icon", "🧾"));
      const body = el("div", "list-row-body");
      body.append(el("div", "list-row-title", item.problem_name || item.run_id || "未命名运行"));
      body.append(el("div", "list-row-sub", [item.top_diagnosis?.name || "图像直传诊断", item.run_id || ""].filter(Boolean).join(" · ")));
      row.append(body);
      const right = el("div", "list-row-right");
      right.append(el("div", "list-row-time", formatIsoTime(item.timestamp)));
      const tag = el("span", "tag tag-neutral", `第 ${item.n_rounds || "-"} 轮`);
      right.append(tag);
      const deleteBtn = el("button", "btn-danger btn-sm list-row-delete", "删除");
      deleteBtn.type = "button";
      deleteBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        void deleteRun(item.run_id);
      });
      right.append(deleteBtn);
      row.append(right);
      row.addEventListener("click", () => void loadRun(item.run_id));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          void loadRun(item.run_id);
        }
      });
      refs.runsList.append(row);
    }
  }

  function updateDashboardStats() {
    var dashRuns = document.getElementById("dash-total-runs");
    var dashVerified = document.getElementById("dash-verified-cases");
    var dashUnverified = document.getElementById("dash-unverified-cases");
    var dashDocCount = document.getElementById("dash-doc-count");
    var dashCasesVerified = document.getElementById("dash-cases-verified");
    var dashCasesUnverified = document.getElementById("dash-cases-unverified");
    var dashKbDocs = document.getElementById("dash-kb-docs");
    var dashKbTotal = document.getElementById("dash-kb-total");

    if (dashVerified) dashVerified.textContent = state.casesData.total_verified;
    if (dashUnverified) dashUnverified.textContent = state.casesData.total_unverified;
    if (dashDocCount) dashDocCount.textContent = state.kbDocuments.length;
    if (dashCasesVerified) dashCasesVerified.textContent = state.casesData.total_verified;
    if (dashCasesUnverified) dashCasesUnverified.textContent = state.casesData.total_unverified;
    if (dashKbDocs) dashKbDocs.textContent = state.kbDocuments.length;
    if (dashKbTotal) dashKbTotal.textContent = state.casesData.total_verified + state.casesData.total_unverified + state.kbDocuments.length;
  }

  async function loadDashboardData() {
    var dashRuns = document.getElementById("dash-total-runs");
    var dashRecent = document.getElementById("dash-recent-runs");

    try {
      var response = await fetch("/api/v1/runs");
      if (response.ok) {
        var payload = await response.json();
        var runs = payload.runs || [];
        if (dashRuns) dashRuns.textContent = runs.length;

        if (dashRecent) {
          clearElement(dashRecent);
          if (runs.length === 0) {
            dashRecent.append(createEmptyStateMini("暂无运行记录"));
          } else {
            var shown = runs.slice(0, 5);
            shown.forEach(function (r) {
              var item = document.createElement("div");
              item.className = "dash-list-item";
              var runId = r.run_id || "";
              item.innerHTML =
                '<span class="dash-list-item-icon">📋</span>' +
                '<span class="dash-list-item-body">' + escapeHtml(runId) + '</span>' +
                '<span class="dash-list-item-time">' + escapeHtml(formatIsoTime(r.timestamp)) + '</span>';
              dashRecent.append(item);
            });
          }
        }
      }
    } catch (_) {
      if (dashRuns) dashRuns.textContent = "--";
    }

    try { await loadCasesData(); } catch (_) {}
    try { await loadKnowledgeDocuments(); } catch (_) {}
    updateDashboardStats();
  }

  function createEmptyStateMini(text) {
    var div = document.createElement("div");
    div.className = "dash-list-empty";
    div.textContent = text;
    return div;
  }

  async function loadRunsList() {
    clearElement(refs.runsList);
    refs.runsList.append(createEmptyState("⏳", "加载运行记录", "正在读取本地保存的历史运行。"));
    try {
      const response = await fetch("/api/v1/runs");
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      renderRunList(Array.isArray(payload) ? payload : []);
    } catch (err) {
      clearElement(refs.runsList);
      refs.runsList.append(createErrorCard("运行记录加载失败", safeErrorText(err)));
    }
  }

  function renderCasesTab(tab) {
    state.caseActiveTab = tab;
    refs.kbTabs.forEach((button) => button.classList.toggle("active", button.dataset.target === tab));
    refs.casesVerifiedCount.textContent = `${state.casesData.total_verified || 0}`;
    refs.casesUnverifiedCount.textContent = `${state.casesData.total_unverified || 0}`;
    clearElement(refs.casesList);

    const items = Array.isArray(state.casesData[tab]) ? state.casesData[tab] : [];
    if (!items.length) {
      refs.casesList.append(createEmptyState("🧪", `暂无${tab === "verified" ? "已核实" : "待核实"}病例`, "病例库里还没有符合条件的病例摘要。"));
      return;
    }

    for (const item of items) {
      const row = el("article", "list-row list-row-shell");
      row.tabIndex = 0;
      row.setAttribute("role", "button");
      row.append(el("div", "list-row-icon", tab === "verified" ? "✅" : "🕓"));
      const body = el("div", "list-row-body");
      body.append(el("div", "list-row-title", item.problem_name || item.run_id || "未命名病例"));
      const sub = [item.top_diagnosis?.name || "未给出主结论", item.run_id || ""].filter(Boolean).join(" · ");
      body.append(el("div", "list-row-sub", sub));
      row.append(body);
      const right = el("div", "list-row-right");
      right.append(el("div", "list-row-time", formatIsoTime(item.timestamp)));
      right.append(el("span", item.safety_passed ? "tag tag-good" : "tag tag-neutral", item.safety_passed ? "已通过" : "待审校"));
      if (item.run_id) {
        const deleteBtn = el("button", "btn-danger btn-sm list-row-delete", "删除");
        deleteBtn.type = "button";
        deleteBtn.addEventListener("click", (event) => {
          event.stopPropagation();
          void deleteCaseRecord(item.run_id);
        });
        right.append(deleteBtn);
      }
      row.append(right);
      row.addEventListener("click", () => {
        if (item.run_id) {
          void loadRun(item.run_id);
        }
      });
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          if (item.run_id) {
            void loadRun(item.run_id);
          }
        }
      });
      refs.casesList.append(row);
    }
  }

  async function loadCasesData() {
    const response = await fetch("/api/v1/cases");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const payload = await response.json();
    state.casesData = {
      verified: Array.isArray(payload.verified) ? payload.verified : [],
      unverified: Array.isArray(payload.unverified) ? payload.unverified : [],
      documents: [],
      total_verified: Number(payload.total_verified || 0),
      total_unverified: Number(payload.total_unverified || 0),
      total_documents: Number(state.casesData.total_documents || 0),
    };
  }

  async function loadKnowledgeDocuments() {
    const response = await fetch("/api/v1/knowledge/documents");
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const payload = await response.json();
    state.kbDocuments = Array.isArray(payload.documents) ? payload.documents : [];
    state.casesData.total_documents = Number(payload.total_documents || state.kbDocuments.length || 0);
  }

  async function loadCasesPage() {
    clearElement(refs.casesList);
    refs.casesList.append(createEmptyState("⏳", "加载病例库", "正在读取自动沉淀的病例摘要。"));
    try {
      await loadCasesData();
      renderCasesTab(state.caseActiveTab || "verified");
    } catch (err) {
      clearElement(refs.casesList);
      refs.casesList.append(createErrorCard("病例库加载失败", safeErrorText(err)));
    }
  }

  function renderKbPage() {
    clearElement(refs.kbStatsArea);
    if (refs.kbDocsList) {
      clearElement(refs.kbDocsList);
    }
    const total = (state.casesData.total_verified || 0) + (state.casesData.total_unverified || 0);
    const totalDocuments = state.casesData.total_documents || state.kbDocuments.length || 0;
    const cards = [
      { label: "病例总数", value: `${total}`, hint: "病例库沉淀的诊断案例", cls: "" },
      { label: "已核实病例", value: `${state.casesData.total_verified || 0}`, hint: "已通过安全校验的病例摘要", cls: "green" },
      { label: "待核实病例", value: `${state.casesData.total_unverified || 0}`, hint: "待复核或安全未通过的病例摘要", cls: "amber" },
      { label: "知识文档", value: `${totalDocuments}`, hint: "外部上传的文本 / Markdown 文档资料", cls: "blue" },
    ];
    for (const item of cards) {
      const card = el("article", "stat-card");
      card.append(el("div", "stat-label", item.label));
      card.append(el("div", `stat-value ${item.cls}`.trim(), item.value));
      card.append(el("div", "stat-hint", item.hint));
      refs.kbStatsArea.append(card);
    }
    renderKnowledgeDocuments();
  }

  async function loadKbPage() {
    clearElement(refs.kbStatsArea);
    if (refs.kbDocsList) {
      clearElement(refs.kbDocsList);
    }
    refs.kbStatsArea.append(createEmptyState("⏳", "加载知识库统计", "正在读取病例库统计和外部知识文档。"));
    if (refs.kbDocsList) {
      refs.kbDocsList.append(createEmptyState("⏳", "加载已上传文档", "正在读取文本和 Markdown 文档条目。"));
    }
    try {
      await Promise.all([loadCasesData(), loadKnowledgeDocuments()]);
      renderKbPage();
    } catch (err) {
      clearElement(refs.kbStatsArea);
      refs.kbStatsArea.append(createErrorCard("知识库统计加载失败", safeErrorText(err)));
      if (refs.kbDocsList) {
        clearElement(refs.kbDocsList);
        refs.kbDocsList.append(createErrorCard("知识条目加载失败", safeErrorText(err)));
      }
    }
  }

  function renderKnowledgeDocuments() {
    if (!refs.kbDocsList) {
      return;
    }
    clearElement(refs.kbDocsList);
    const items = Array.isArray(state.kbDocuments) ? state.kbDocuments : [];
    if (!items.length) {
      refs.kbDocsList.append(createEmptyState("📚", "暂无知识条目", "可以直接粘贴纯文本，或上传 .txt / .md / .markdown 文件。"));
      return;
    }

    for (const item of items) {
      const row = el("article", "list-row kb-doc-row");
      row.append(el("div", "list-row-icon", item.content_format === "md" ? "MD" : "TXT"));

      const body = el("div", "list-row-body");
      body.append(el("div", "list-row-title", item.title || item.source_name || "未命名知识条目"));
      const metaParts = [
        item.source_name || "手动输入",
        `${Number(item.char_count || 0)} 字`,
      ].filter(Boolean);
      body.append(el("div", "list-row-sub", metaParts.join(" · ")));
      if (item.preview) {
        body.append(el("div", "kb-doc-preview", item.preview));
      }
      row.append(body);

      const right = el("div", "list-row-right");
      right.append(el("div", "list-row-time", formatIsoTime(item.timestamp)));
      right.append(el("span", item.content_format === "md" ? "tag tag-info" : "tag tag-neutral", item.content_format === "md" ? "Markdown 文档" : "纯文本"));
      row.append(right);

      refs.kbDocsList.append(row);
    }
  }

  async function uploadKnowledgeDocument(event) {
    event.preventDefault();
    const title = `${refs.kbUploadTitle?.value || ""}`.trim();
    const textContent = `${refs.kbUploadText?.value || ""}`.trim();
    const file = refs.kbUploadFile?.files?.[0] || null;

    if (!textContent && !file) {
      setKbStatus(refs.kbUploadStatus, "请输入文本或选择一个 .txt / .md 文件。", true);
      return;
    }

    const formData = new FormData();
    formData.append("title", title);
    formData.append("text_content", textContent);
    if (file) {
      formData.append("file", file);
    }

    setKbStatus(refs.kbUploadStatus, "正在上传知识条目...");
    if (refs.kbUploadBtn) {
      refs.kbUploadBtn.disabled = true;
    }
    try {
      const response = await fetch("/api/v1/knowledge/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = await response.json();
      setKbStatus(refs.kbUploadStatus, `已上传 ${payload.title || "知识条目"}`);
      refs.kbUploadForm?.reset();
      await Promise.all([loadCasesData(), loadKnowledgeDocuments()]);
      if (state.activePage === "kb") {
        renderKbPage();
      }
    } catch (err) {
      setKbStatus(refs.kbUploadStatus, `上传失败: ${safeErrorText(err)}`, true);
    } finally {
      if (refs.kbUploadBtn) {
        refs.kbUploadBtn.disabled = false;
      }
    }
  }

  refs.imageInput?.addEventListener("change", () => {
    const file = refs.imageInput?.files?.[0] || null;
    updateImageUploadFeedback(file);
  });

  normalizeKnowledgeTargetOptions();

  if (refs.flowToolbarText) {
    refs.flowToolbarText.textContent = "滚轮缩放，按住空白处拖拽平移，点击适配回到流程中心。";
  }

  refs.form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(refs.form);
    const problemName = `${formData.get("problem_name") || ""}`.trim() || "草莓病害图像诊断报告";
    const caseText = "";
    const selectedImage = refs.imageInput?.files?.[0] || null;
    if (!selectedImage) {
      setStatus("请先上传草莓病害图片", "error");
      return;
    }
    state.reportMode = "multi";
    state.isRunning = true;
    navigateTo("diagnosis");
    resetCurrentRun(problemName, caseText);
    setView("dialogue");
    renderCurrentRun();
    setBusy(true);
    setStatus(`已选择图片 ${selectedImage.name}，正在上传并启动图像诊断...`, "running");

    try {
      await runDiagnosisStream(formData);
      if (state.isRunning) {
        state.isRunning = false;
        setBusy(false);
      }
    } catch (err) {
      state.isRunning = false;
      setBusy(false);
      markActiveNodeAsError({ message: safeErrorText(err) });
      renderCurrentRun();
      setStatus(`运行失败 · ${safeErrorText(err)}`, "error");
    }
  });

  refs.loadBtn.addEventListener("click", () => void loadRun(refs.runLookup.value));
  refs.runLookup.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void loadRun(refs.runLookup.value);
    }
  });

  refs.reportViewBtn.addEventListener("click", () => setView("report"));
  refs.dialogueViewBtn.addEventListener("click", () => setView("dialogue"));

  refs.clearKbBtn.addEventListener("click", () => void clearKnowledgeBase(refs.kbTarget.value, refs.kbStatus));
  refs.clearKbBtn2.addEventListener("click", () => void clearKnowledgeBase(refs.kbTarget2.value, refs.kbStatus2));
  refs.kbUploadForm?.addEventListener("submit", (event) => void uploadKnowledgeDocument(event));

  refs.kbTabs.forEach((button) => {
    button.addEventListener("click", () => renderCasesTab(button.dataset.target || "verified"));
  });

  refs.runsRefreshBtn.addEventListener("click", () => void loadRunsList());
  refs.navButtons.forEach((button) => {
    button.addEventListener("click", () => navigateTo(button.dataset.page || "diagnosis"));
  });

  document.querySelectorAll(".dash-panel[data-nav]").forEach((panel) => {
    panel.addEventListener("click", (event) => {
      if (event.target.closest("button, input, select, textarea, .btn-primary, .btn-sm, .btn-danger")) {
        return;
      }
      var target = panel.dataset.nav;
      if (target) navigateTo(target);
    });
  });

  document.querySelectorAll(".back-dash-btn[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      var target = btn.dataset.nav;
      if (target) navigateTo(target);
    });
  });

  refs.inspector?.addEventListener("scroll", () => {
    const currentNodeId = state.flow.selectedNodeId || state.flow.activeNodeId || "human";
    state.inspectorView.nodeId = currentNodeId;
    state.inspectorView.scrollTop = refs.inspector.scrollTop;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.boardView.open) {
      closeBoardView();
    }
  });

  initFlowViewport();
  ensureBoardView();
  hydrateHeroAgentIcons();
  setView(state.currentView);
  navigateTo("dashboard");
  renderCurrentRun();
})();
