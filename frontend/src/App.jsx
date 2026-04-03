import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import {
  Send,
  User,
  Bot,
  Loader2,
  Building2,
  Settings2,
  BarChart3,
  Code2,
  Briefcase,
  Wrench,
  Headphones,
  PlusSquare,
  ChevronRight,
  Workflow,
  MessagesSquare,
  Sparkles,
  PlayCircle,
  X,
  BrainCircuit,
  Network,
  Zap,
  Database,
  Search,
  Save,
  Upload,
  FileText,
  SlidersHorizontal,
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const KB_SUPPORTED_EXTENSIONS = ['TXT', 'MD', 'MARKDOWN', 'MDX', 'CSV', 'JSON', 'HTML', 'HTM', 'VTT', 'PROPERTIES', 'PDF', 'DOCX', 'XLSX', 'XLS'];
const KB_FILE_ACCEPT = '.txt,.md,.markdown,.mdx,.csv,.json,.html,.htm,.vtt,.properties,.pdf,.docx,.xlsx,.xls';
const KB_TEXT_PREVIEW_EXTENSIONS = new Set(['txt', 'md', 'markdown', 'mdx', 'csv', 'json', 'html', 'htm', 'vtt', 'properties']);

const DEPARTMENTS = [
  { id: 'CEO', name: 'CEO 总智能体', icon: Building2, summary: '跨部门总控与任务拆解' },
  { id: 'MARKET', name: '市场部部长', icon: BarChart3, summary: '需求分析与宣传内容编排' },
  { id: 'TECH', name: '星核StarCore', icon: Code2, summary: '产品、开发、测试、运维编排' },
  { id: 'SALES', name: '业务部部长', icon: Briefcase, summary: '服务咨询、方案设计、实施计划' },
  { id: 'REPAIR', name: '运维部部长', icon: Wrench, summary: '派单、问题诊断、现场执行' },
  { id: 'CS', name: '客服部部长', icon: Headphones, summary: 'FAQ、应急响应、人工兜底' },
  { id: 'USER', name: '用户端部长', icon: User, summary: '服务状态与申报入口' },
];

const DEPARTMENT_LABEL_MAP = {
  CEO: 'CEO 总智能体',
  MARKET: '市场部部长',
  TECH: '星核StarCore',
  SALES: '业务部部长',
  REPAIR: '运维部部长',
  CS: '客服部部长',
  USER: '用户端部长',
};

const LEAD_TO_DEPARTMENT_MAP = {
  市场部部长: 'MARKET',
  星核StarCore: 'TECH',
  业务部部长: 'SALES',
  运维部部长: 'REPAIR',
  客服部部长: 'CS',
  用户端部长: 'USER',
};

const DEPARTMENT_NAME_TO_CODE = {
  市场部: 'MARKET',
  技术部: 'TECH',
  业务部: 'SALES',
  运维部: 'REPAIR',
  客服部: 'CS',
  用户端: 'USER',
};

const GUIDE_DEMO_STEPS = [
  {
    id: 'ceo',
    title: 'CEO 总控',
    text: 'CEO 先理解用户目标，决定要调用哪些部门，以及调用顺序。',
  },
  {
    id: 'cs_lead',
    title: '客服部部长',
    text: '如果是紧急求助，客服部长会优先分配到紧急救援智能体，而不是走 FAQ。',
  },
  {
    id: 'emergency',
    title: '紧急救援智能体',
    text: '先安抚用户、确认风险等级，再把关键信息回传给 CEO。',
  },
  {
    id: 'repair_lead',
    title: '运维部部长',
    text: '运维部长接到 CEO 调度后，继续拆成派单、诊断、现场处理三个环节。',
  },
  {
    id: 'worker',
    title: '运维人员智能体',
    text: '最后由现场执行智能体完成任务闭环，CEO 再输出总总结。',
  },
];

const GUIDE_DEMO_FLASH_LINES = [
  'CEO 正在解析用户目标: 公共设施应急响应',
  'CEO 下发客服部协作指令，优先启动应急响应链路',
  '客服部部长切换到紧急救援模式，跳过 FAQ 分流',
  '紧急救援智能体已生成安抚话术并回传风险等级',
  'CEO 将高优先级工单继续转派给运维部',
  '运维部部长拆分为派单、诊断、现场执行三段流程',
  '派单经理已锁定最近工程师与到场时效',
  '问题诊断专家已完成问题推断并回写风险建议',
  '运维人员智能体进入现场闭环处理，等待 CEO 汇总',
];

function findSubAgentMeta(registry, agentId) {
  for (const [deptId, agents] of Object.entries(registry)) {
    const found = agents.find((agent) => agent.id === agentId);
    if (found) {
      return { ...found, deptId };
    }
  }
  return null;
}

function getSubAgentLabel(registry, agentId) {
  const found = findSubAgentMeta(registry, agentId);
  return found?.name || agentId;
}

function parsePlanSteps(status = '') {
  const match = status.match(/[:：]\s*(.+)$/);
  if (!match) return [];
  return match[1]
    .split('->')
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildExecutionTree(conversation, registry) {
  if (!conversation) return null;

  const root = {
    id: 'root',
    label: conversation.label,
    meta: conversation.modeLabel,
    children: [],
  };

  if (conversation.targetType === 'agent') {
    return root;
  }

  const deptNodes = {};

  const ensureDeptNode = (deptKey) => {
    if (!deptNodes[deptKey]) {
      const node = {
        id: `dept_${deptKey}`,
        label: DEPARTMENT_LABEL_MAP[deptKey] || deptKey,
        children: [],
      };
      deptNodes[deptKey] = node;
      root.children.push(node);
    }
    return deptNodes[deptKey];
  };

  if (conversation.targetAgent !== 'CEO') {
    root.label = conversation.label;
  }

  for (const log of conversation.executionLog || []) {
    if (conversation.targetAgent === 'CEO') {
      if (log.agent === 'CEO 总智能体' && log.status?.includes('正在调派')) {
        const match = log.status.match(/正在调派\s+(.+?)\s+执行任务/);
        if (match) {
          const deptCode = DEPARTMENT_NAME_TO_CODE[match[1]] || match[1];
          ensureDeptNode(deptCode);
        }
      }

      if (LEAD_TO_DEPARTMENT_MAP[log.agent] && log.status?.startsWith('制定内部子计划')) {
        const deptKey = LEAD_TO_DEPARTMENT_MAP[log.agent];
        const deptNode = ensureDeptNode(deptKey);
        const steps = parsePlanSteps(log.status);
        if (steps.length) {
          deptNode.children = steps.map((step, index) => ({
            id: `${deptKey}_${step}_${index}`,
            label: getSubAgentLabel(registry, step),
            children: [],
          }));
        }
      }
    } else if (log.agent === conversation.label && log.status?.startsWith('制定内部子计划')) {
      const steps = parsePlanSteps(log.status);
      if (steps.length) {
        root.children = steps.map((step, index) => ({
          id: `sub_${step}_${index}`,
          label: getSubAgentLabel(registry, step),
          children: [],
        }));
      }
    }
  }

  return root;
}

function TreeNode({ node, level = 0 }) {
  const isRoot = level === 0;
  const isDepartment = level === 1;
  const isSubAgent = level === 2;

  // 根据层级设置不同的样式
  const getNodeStyle = () => {
    if (isRoot) {
      return {
        container: 'border-2 border-sky-400 bg-gradient-to-br from-sky-50 to-blue-50 shadow-[0_20px_40px_rgba(56,189,248,0.18)]',
        text: 'text-sky-700 font-black text-base',
        badge: 'bg-sky-100 text-sky-700',
        icon: '🎯'
      };
    }
    if (isDepartment) {
      return {
        container: 'border-2 border-violet-300 bg-gradient-to-br from-violet-50 to-purple-50 shadow-[0_16px_32px_rgba(139,92,246,0.14)]',
        text: 'text-violet-700 font-bold text-sm',
        badge: 'bg-violet-100 text-violet-700',
        icon: '🏢'
      };
    }
    return {
      container: 'border border-slate-300 bg-white shadow-[0_12px_24px_rgba(148,163,184,0.1)]',
      text: 'text-slate-700 font-semibold text-sm',
      badge: 'bg-slate-100 text-slate-600',
      icon: '⚙️'
    };
  };

  const style = getNodeStyle();

  return (
    <div className="flex flex-col items-center">
      {/* 节点卡片 */}
      <div
        className={`relative rounded-2xl px-5 py-3.5 text-center transition-all hover:scale-105 ${style.container}`}
        style={{ minWidth: isRoot ? '200px' : isDepartment ? '160px' : '140px' }}
      >
        {/* 层级标识 */}
        <div className={`absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full text-xs ${style.badge}`}>
          {style.icon}
        </div>

        {/* 节点标签 */}
        <div className={style.text}>{node.label}</div>

        {/* 元信息 */}
        {node.meta && (
          <div className="mt-1.5 text-[10px] font-medium uppercase tracking-wider text-slate-400">
            {node.meta}
          </div>
        )}

        {/* 子节点数量提示 */}
        {node.children?.length > 0 && (
          <div className="mt-2 flex items-center justify-center gap-1 text-[10px] font-bold text-slate-400">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-400"></span>
            <span>{node.children.length} 个子节点</span>
          </div>
        )}
      </div>

      {/* 子节点连接线和布局 */}
      {node.children?.length > 0 && (
        <div className="relative mt-6 flex flex-col items-center">
          {/* 垂直连接线 */}
          <div className="absolute -top-6 h-6 w-0.5 bg-gradient-to-b from-sky-300 to-sky-200"></div>

          {/* 子节点容器 */}
          <div className="relative flex flex-wrap items-start justify-center gap-8 pt-6">
            {/* 水平连接线（多个子节点时） */}
            {node.children.length > 1 && (
              <div className="absolute left-[10%] right-[10%] top-0 h-0.5 bg-gradient-to-r from-transparent via-sky-300 to-transparent"></div>
            )}

            {/* 渲染子节点 */}
            {node.children.map((child, index) => (
              <div key={child.id} className="relative flex flex-col items-center">
                {/* 子节点的垂直连接线 */}
                {node.children.length > 1 && (
                  <div className="absolute -top-6 h-6 w-0.5 bg-gradient-to-b from-sky-300 to-sky-200"></div>
                )}

                {/* 子节点序号标识 */}
                <div className="absolute -top-9 flex h-5 w-5 items-center justify-center rounded-full bg-sky-100 text-[10px] font-black text-sky-600 shadow-sm">
                  {index + 1}
                </div>

                {/* 递归渲染子节点 */}
                <TreeNode node={child} level={level + 1} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function buildConversationMeta(registry, targetAgent, targetType, departmentHint) {
  if (targetAgent === 'CEO') {
    return {
      label: 'CEO 总智能体',
      subtitle: '跨部门编排',
      department: 'CEO',
      modeLabel: 'CEO 编排模式',
      greeting:
        '这里是 CEO 独立会话。适合直接提跨部门任务，比如“先分析市场，再输出方案，再安排维修”。',
    };
  }

  if (targetType === 'orchestrator') {
    const dept = DEPARTMENTS.find((item) => item.id === targetAgent);
    return {
      label: dept?.name || targetAgent,
      subtitle: dept?.summary || '部门内部编排',
      department: targetAgent,
      modeLabel: '部门长编排模式',
      greeting: `这里是 ${dept?.name || targetAgent} 的独立会话。你只需要提目标，这个部门长会自己调度下面的小智能体。`,
    };
  }

  const subAgent = findSubAgentMeta(registry, targetAgent);
  return {
    label: subAgent?.name || targetAgent,
    subtitle: subAgent?.description || '直接问答',
    department: departmentHint || subAgent?.deptId || 'CEO',
    modeLabel: '子智能体直聊模式',
    greeting: `这里已经直接连到 ${subAgent?.name || targetAgent}。这个会话不会经过部门长，你可以直接和它问答。`,
  };
}

function createConversation(registry, targetAgent, targetType, departmentHint) {
  const meta = buildConversationMeta(registry, targetAgent, targetType, departmentHint);
  return {
    id: `conv_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    targetAgent,
    targetType,
    department: meta.department,
    label: meta.label,
    subtitle: meta.subtitle,
    modeLabel: meta.modeLabel,
    title: `${meta.label} 对话`,
    loading: false,
    activeDept: meta.department,
    activeAgent: meta.label,
    executionLog: [],
    // Task lifecycle tracking
    taskPhase: 'idle',
    requirementConfirmationStatus: 'pending',
    currentExecutor: '',
    originalRequirement: '',
    // Confirmation flow
    awaitingConfirmation: false,
    confirmationMeta: null,
    messages: [
      {
        id: `msg_${Date.now()}_welcome`,
        role: 'assistant',
        content: meta.greeting,
        targetContent: meta.greeting,
        department: meta.label,
        isAnimating: false,
        isStreaming: false,
      },
    ],
  };
}

function createAnimatedAssistantMessage({ content = '', targetContent = '', department, node, isStreaming = false }) {
  return {
    id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
    role: 'assistant',
    content,
    targetContent,
    department,
    node,
    isAnimating: targetContent.length > content.length,
    isStreaming,
  };
}

function isDepartmentSpeaking(conversation, deptName) {
  if (!conversation?.activeAgent) return false;
  return conversation.activeAgent === deptName && conversation.loading;
}

function TutorialDemo({ stepIndex }) {
  const activeId = GUIDE_DEMO_STEPS[stepIndex]?.id;
  const isActive = (id) => activeId === id;
  const isComplete = (id) => GUIDE_DEMO_STEPS.findIndex((step) => step.id === id) < stepIndex;
  const flashStart = Math.max(0, stepIndex + 1 - 4);
  const flashLines = GUIDE_DEMO_FLASH_LINES.slice(flashStart, stepIndex + 1);

  const getNodeClass = (id, palette) => {
    if (isActive(id)) return `${palette} scale-[1.02] shadow-[0_18px_45px_rgba(59,130,246,0.18)]`;
    if (isComplete(id)) return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    return 'border-slate-200 bg-white text-slate-500';
  };

  return (
    <div className="overflow-hidden rounded-[28px] border border-sky-100 bg-[linear-gradient(145deg,rgba(255,255,255,0.98),rgba(240,249,255,0.92))] p-5 shadow-[0_20px_50px_rgba(56,189,248,0.12)]">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-[11px] font-black uppercase tracking-[0.18em] text-sky-600">协作演示</div>
          <div className="mt-1 text-sm font-semibold text-slate-900">本地模拟多智能体跳转，不调用真实系统</div>
        </div>
        <div className="rounded-2xl bg-sky-100 px-3 py-2 text-xs font-bold text-sky-700">
          Step {stepIndex + 1}/{GUIDE_DEMO_STEPS.length}
        </div>
      </div>

      <div className="space-y-4">
        <div className="relative overflow-hidden rounded-[26px] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8fbff_100%)] p-5">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(56,189,248,0.16),_transparent_28%),linear-gradient(90deg,transparent,rgba(255,255,255,0.5),transparent)]"></div>
          <div className="absolute inset-y-0 left-[-20%] w-1/3 animate-[pulse_1.4s_ease-in-out_infinite] bg-[linear-gradient(90deg,transparent,rgba(56,189,248,0.18),transparent)] blur-xl"></div>
          <div className="relative">
            <div className="flex items-center justify-between">
              <div className="text-[11px] font-black uppercase tracking-[0.2em] text-sky-600">实时信号流</div>
              <div className="flex items-center gap-2 text-[11px] text-emerald-600">
                <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-400"></span>
                模拟协作中
              </div>
            </div>

            <div className="mt-4 space-y-2">
              {flashLines.map((line, index) => {
                const isLatest = index === flashLines.length - 1;
                return (
                  <div
                    key={`${line}-${index}`}
                    className={`rounded-2xl border px-4 py-3 text-sm transition-all ${
                      isLatest
                        ? 'border-sky-200 bg-[linear-gradient(90deg,#eff6ff,#ffffff)] text-sky-700 shadow-[0_0_26px_rgba(56,189,248,0.18)]'
                        : 'border-slate-200 bg-white/80 text-slate-500 opacity-60'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`inline-flex h-2 w-2 rounded-full ${isLatest ? 'animate-pulse bg-sky-500' : 'bg-slate-300'}`}></span>
                      <span className={`${isLatest ? 'font-semibold' : ''}`}>{line}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="rounded-[26px] border border-slate-200 bg-white px-4 py-5 shadow-[0_10px_24px_rgba(148,163,184,0.08)]">
          <div className="flex flex-col items-center">
            <div className={`min-w-[120px] rounded-2xl border px-4 py-3 text-sm font-bold transition-all ${getNodeClass('ceo', 'border-sky-300 bg-sky-50 text-sky-700')}`}>
              CEO 总控
            </div>
            <div className="mt-4 h-6 w-px bg-sky-200"></div>
            <div className="relative flex w-full justify-center gap-8 pt-5">
              <div className="absolute left-[22%] right-[22%] top-0 h-px bg-sky-200"></div>

              <div className="relative flex w-[210px] flex-col items-center">
                <div className="absolute -top-5 h-5 w-px bg-sky-200"></div>
                <div className={`w-full rounded-2xl border px-4 py-3 text-center text-sm font-bold transition-all ${getNodeClass('cs_lead', 'border-violet-300 bg-violet-50 text-violet-700')}`}>
                  客服部部长
                </div>
                <div className="mt-4 h-5 w-px bg-sky-200"></div>
                <div className={`w-[170px] rounded-2xl border px-4 py-3 text-center text-sm font-semibold transition-all ${getNodeClass('emergency', 'border-amber-300 bg-amber-50 text-amber-700')}`}>
                  紧急救援智能体
                </div>
              </div>

              <div className="relative flex w-[320px] flex-col items-center">
                <div className="absolute -top-5 h-5 w-px bg-sky-200"></div>
                <div className={`w-[180px] rounded-2xl border px-4 py-3 text-center text-sm font-bold transition-all ${getNodeClass('repair_lead', 'border-cyan-300 bg-cyan-50 text-cyan-700')}`}>
                  运维部部长
                </div>
                <div className="mt-4 h-5 w-px bg-sky-200"></div>
                <div className="relative flex w-full justify-center gap-4 pt-5">
                  <div className="absolute left-[14%] right-[14%] top-0 h-px bg-sky-200"></div>
                  {[
                    ['manager', '派单经理'],
                    ['master', '问题诊断专家'],
                    ['worker', '运维人员'],
                  ].map(([id, label]) => (
                    <div key={id} className="relative flex flex-col items-center">
                      <div className="absolute -top-5 h-5 w-px bg-sky-200"></div>
                      <div className={`w-[90px] rounded-2xl border px-3 py-3 text-center text-sm font-semibold transition-all ${getNodeClass(id, 'border-emerald-300 bg-emerald-50 text-emerald-700')}`}>
                        {label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm leading-6 text-slate-600">
          <div className="font-bold text-slate-900">{GUIDE_DEMO_STEPS[stepIndex]?.title}</div>
          <div className="mt-1">{GUIDE_DEMO_STEPS[stepIndex]?.text}</div>
        </div>
      </div>
    </div>
  );
}

const TASK_PHASE_CONFIG = {
  requirement_analysis: { label: '需求分析中', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  requirement_clarification: { label: '等待需求确认', color: 'bg-amber-100 text-amber-700 border-amber-200' },
  sub_plan_generation: { label: '制定执行计划', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  dispatch_execution: { label: '执行中', color: 'bg-sky-100 text-sky-700 border-sky-200' },
  test_reflow: { label: '检测回流', color: 'bg-orange-100 text-orange-700 border-orange-200' },
  ops_finish: { label: '运维收尾', color: 'bg-indigo-100 text-indigo-700 border-indigo-200' },
  completed: { label: '已完成', color: 'bg-emerald-100 text-emerald-700 border-emerald-200' },
};

const EXECUTOR_NAMES = {
  product: '蓝图BlueForm',
  developer: '灵码SmartCode',
  tester: '检博士CheckDoc',
  devops: '运小盾OpsShield',
};

function TaskPhaseBar({ taskPhase, requirementConfirmationStatus, currentExecutor }) {
  const config = TASK_PHASE_CONFIG[taskPhase];
  if (!config) return null;

  const executorLabel = currentExecutor ? EXECUTOR_NAMES[currentExecutor] || currentExecutor : '';

  return (
    <div className={`flex items-center gap-3 rounded-2xl border px-4 py-2.5 text-sm font-semibold ${config.color}`}>
      {taskPhase === 'completed' ? (
        <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
      ) : taskPhase === 'requirement_clarification' ? (
        <span className="inline-block h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
      ) : (
        <Loader2 size={14} className="animate-spin" />
      )}
      <span>{config.label}</span>
      {executorLabel && taskPhase === 'dispatch_execution' && (
        <span className="text-xs font-medium opacity-70">({executorLabel})</span>
      )}
    </div>
  );
}

function ConfirmationActionBar({ meta, onContinue, onRegenerate, onModify }) {
  const [feedback, setFeedback] = useState('');
  const [showInput, setShowInput] = useState(false);

  return (
    <div className="border-t border-sky-100 bg-white/35 px-8 py-6 backdrop-blur-2xl">
      <div className="rounded-[30px] border border-sky-100 bg-white/92 p-4 shadow-[0_22px_60px_rgba(148,163,184,0.14)]">
        <div className="mb-3 text-sm text-slate-600">
          <span className="font-bold text-slate-800">{meta.completedAgent}</span> 已完成
          {meta.nextAgent && !meta.isFinalNode && (
            <span>，下一步: <span className="font-bold text-sky-600">{meta.nextAgent}</span></span>
          )}
          {meta.isFinalNode && <span className="font-bold text-emerald-600"> — 全部流程已完成</span>}
        </div>

        {showInput && (
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && feedback.trim()) {
                e.preventDefault();
                onModify(feedback.trim());
                setFeedback('');
                setShowInput(false);
              }
            }}
            placeholder="请输入修改建议..."
            className="mb-3 min-h-[80px] w-full resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm leading-6 text-slate-800 outline-none focus:border-sky-300 placeholder:text-slate-400"
          />
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={onContinue}
            className="inline-flex items-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-bold text-white shadow-[0_16px_32px_rgba(37,99,235,0.2)] transition hover:-translate-y-0.5"
          >
            {meta.isFinalNode ? '完成' : '继续'}
          </button>
          <button
            onClick={onRegenerate}
            className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-slate-400"
          >
            重新生成
          </button>
          <button
            onClick={() => {
              if (showInput && feedback.trim()) {
                onModify(feedback.trim());
                setFeedback('');
                setShowInput(false);
              } else {
                setShowInput(!showInput);
              }
            }}
            className="inline-flex items-center gap-2 rounded-2xl border border-amber-300 bg-amber-50 px-5 py-3 text-sm font-bold text-amber-700 shadow-sm transition hover:-translate-y-0.5 hover:border-amber-400"
          >
            {showInput && feedback.trim() ? '提交修改' : '修改建议'}
          </button>
        </div>
      </div>
    </div>
  );
}

function getRequestErrorMessage(error, fallback) {
  return error?.response?.data?.detail || error?.response?.data?.message || error?.message || fallback;
}

function KnowledgeBaseManager({ externalSelectedKbId, onSelectedKbChange }) {
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKbId, setSelectedKbId] = useState(externalSelectedKbId || null);
  const [selectedKb, setSelectedKb] = useState(null);
  const [activeTab, setActiveTab] = useState('documents');
  const [loading, setLoading] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    icon: '🤖',
    description: '',
  });
  const [settingsForm, setSettingsForm] = useState({
    name: '',
    icon: '🤖',
    description: '',
    permission: '只有我',
    segment_mode: 'general',
    index_mode: 'high_quality',
    retrieval_mode: 'hybrid',
    separator: '\n\n',
    chunk_size: 800,
    chunk_overlap: 100,
    semantic_weight: 0.7,
    keyword_weight: 0.3,
    top_k: 5,
    score_threshold: 0.2,
    embedding_model: 'text-embedding-v4',
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewSource, setPreviewSource] = useState('');
  const [previewChunks, setPreviewChunks] = useState([]);
  const [recallQuery, setRecallQuery] = useState('');
  const [recallResults, setRecallResults] = useState([]);
  const [recallHistory, setRecallHistory] = useState([]);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [uploadStep, setUploadStep] = useState(1);
  const [documentChunkDrawer, setDocumentChunkDrawer] = useState({
    open: false,
    title: '',
    chunks: [],
  });

  const loadKnowledgeBases = async () => {
    const { data } = await axios.get(`${API_URL}/knowledge-bases`);
    setKnowledgeBases(data);
    if (!selectedKbId && data[0]) {
      setSelectedKbId(data[0].id);
    }
  };

  const loadKnowledgeBaseDetail = async (kbId) => {
    const { data } = await axios.get(`${API_URL}/knowledge-bases/${kbId}`);
    setSelectedKb(data);
    setSettingsForm({
      name: data.name,
      icon: data.icon,
      description: data.description,
      permission: data.permission,
      segment_mode: data.segment_mode,
      index_mode: data.index_mode,
      retrieval_mode: data.retrieval_mode,
      separator: data.chunk_config?.separator ?? '\n\n',
      chunk_size: data.chunk_config?.chunk_size ?? 800,
      chunk_overlap: data.chunk_config?.chunk_overlap ?? 100,
      semantic_weight: data.retrieval_config?.semantic_weight ?? 0.7,
      keyword_weight: data.retrieval_config?.keyword_weight ?? 0.3,
      top_k: data.retrieval_config?.top_k ?? 5,
      score_threshold: data.retrieval_config?.score_threshold ?? 0.2,
      embedding_model: data.retrieval_config?.embedding_model ?? 'text-embedding-v4',
    });
    setRecallHistory(data.recall_history || []);
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  useEffect(() => {
    if (externalSelectedKbId) {
      setSelectedKbId(externalSelectedKbId);
    }
  }, [externalSelectedKbId]);

  useEffect(() => {
    if (selectedKbId) {
      onSelectedKbChange?.(selectedKbId);
      loadKnowledgeBaseDetail(selectedKbId);
    }
  }, [selectedKbId, onSelectedKbChange]);

  const handleCreateKb = async () => {
    if (!createForm.name.trim()) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const { data } = await axios.post(`${API_URL}/knowledge-bases`, createForm);
      setCreateForm({ name: '', icon: '🤖', description: '' });
      await loadKnowledgeBases();
      setSelectedKbId(data.id);
      setStatusMessage(`知识库“${data.name}”已创建`);
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '知识库创建失败'));
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewChunks = async () => {
    if (!previewSource.trim()) return;
    setErrorMessage('');
    setStatusMessage('');
    try {
      const { data } = await axios.post(`${API_URL}/knowledge-bases/chunk-preview`, {
        text: previewSource,
        separator: settingsForm.separator,
        chunk_size: Number(settingsForm.chunk_size),
        chunk_overlap: Number(settingsForm.chunk_overlap),
      });
      setPreviewChunks(data.chunks || []);
      setStatusMessage(`已生成 ${data.chunks?.length || 0} 个预览块`);
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '分块预览失败'));
    }
  };

  const handleResetPreview = () => {
    setPreviewSource('');
    setPreviewChunks([]);
    setSelectedFile(null);
    setUploadStep(1);
    setStatusMessage('');
    setErrorMessage('');
  };

  const handleFilePick = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setErrorMessage('');
    setStatusMessage('');
    try {
      setSelectedFile(file);
      setUploadStep(2);
      const extension = file.name.split('.').pop()?.toLowerCase() || '';
      if (KB_TEXT_PREVIEW_EXTENSIONS.has(extension)) {
        const text = await file.text();
        setPreviewSource(text.slice(0, 12000));
        setStatusMessage(`已载入文件：${file.name}`);
      } else {
        setPreviewSource('');
        setStatusMessage(`已选择文件：${file.name}。该类型将在上传后解析，可直接进入下一步设置分段。`);
      }
    } catch (error) {
      setSelectedFile(null);
      setPreviewSource('');
      setUploadStep(1);
      setErrorMessage(getRequestErrorMessage(error, '文件读取失败，请尝试文本类文件'));
    }
  };

  const handleUpload = async () => {
    if (!selectedKbId || !selectedFile) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('separator', settingsForm.separator);
      formData.append('chunk_size', String(settingsForm.chunk_size));
      formData.append('chunk_overlap', String(settingsForm.chunk_overlap));
      const { data } = await axios.post(`${API_URL}/knowledge-bases/${selectedKbId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await loadKnowledgeBaseDetail(selectedKbId);
      await loadKnowledgeBases();
      handleResetPreview();
      setStatusMessage(`处理完成：${data.name}，共写入 ${data.chunks || 0} 个分块`);
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '文件处理失败'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedKbId) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      await axios.put(`${API_URL}/knowledge-bases/${selectedKbId}`, settingsForm);
      await loadKnowledgeBaseDetail(selectedKbId);
      await loadKnowledgeBases();
      setStatusMessage('知识库设置已保存');
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '知识库设置保存失败'));
    } finally {
      setLoading(false);
    }
  };

  const handleRecallTest = async () => {
    if (!selectedKbId || !recallQuery.trim()) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const { data } = await axios.post(`${API_URL}/knowledge-bases/${selectedKbId}/recall-test`, {
        query: recallQuery,
        top_k: Number(settingsForm.top_k),
      });
      setRecallResults(data.results || []);
      setRecallHistory(data.records || []);
      await loadKnowledgeBaseDetail(selectedKbId);
      await loadKnowledgeBases();
      setStatusMessage(`召回测试完成，返回 ${data.results?.length || 0} 条结果`);
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '召回测试失败'));
    } finally {
      setLoading(false);
    }
  };

  const handleViewDocumentChunks = async (doc) => {
    if (!selectedKbId || !doc?.id) return;
    setLoading(true);
    setErrorMessage('');
    setStatusMessage('');
    try {
      const { data } = await axios.get(`${API_URL}/knowledge-bases/${selectedKbId}/documents/${doc.id}/chunks`);
      setDocumentChunkDrawer({
        open: true,
        title: doc.name,
        chunks: data.chunks || [],
      });
      setStatusMessage(`已加载 ${doc.name} 的 ${data.chunks?.length || 0} 个分段`);
    } catch (error) {
      setErrorMessage(getRequestErrorMessage(error, '文档分段读取失败'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full min-h-0">
      <aside className="w-[320px] border-r border-sky-100 bg-white/75 p-6 backdrop-blur-2xl">
        <div className="flex items-center gap-3">
          <div className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] p-3 text-white shadow-[0_18px_40px_rgba(37,99,235,0.18)]">
            <Database size={18} />
          </div>
          <div>
            <div className="text-sm font-black text-slate-900">知识库管理</div>
            <div className="text-xs text-slate-500">多个知识库，分别存放不同数据</div>
          </div>
        </div>

        <div className="mt-6 rounded-3xl border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#eff6ff)] p-4 shadow-[0_20px_45px_rgba(56,189,248,0.10)]">
          <div className="text-[11px] font-black uppercase tracking-[0.18em] text-sky-600">新建知识库</div>
          <div className="mt-3 space-y-3">
            <input
              value={createForm.name}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="输入知识库名称"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-sky-300"
            />
            <input
              value={createForm.description}
              onChange={(e) => setCreateForm((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="描述"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-sky-300"
            />
            <button
              onClick={handleCreateKb}
              disabled={loading}
              className="w-full rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-4 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(37,99,235,0.18)]"
            >
              创建知识库
            </button>
          </div>
        </div>

        <div className="mt-6">
          <div className="mb-3 text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">知识库列表</div>
          <div className="space-y-2">
            {knowledgeBases.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelectedKbId(kb.id)}
                className={`w-full rounded-2xl border p-4 text-left transition ${
                  selectedKbId === kb.id
                    ? 'border-sky-300 bg-[linear-gradient(145deg,#ffffff,#eff8ff)] shadow-[0_18px_36px_rgba(56,189,248,0.14)]'
                    : 'border-slate-200 bg-white hover:border-sky-200'
                }`}
              >
                <div className="text-sm font-bold text-slate-900">{kb.icon} {kb.name}</div>
                <div className="mt-1 text-xs text-slate-500">{kb.documents?.length || 0} 个文档</div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="flex-1 min-w-0 overflow-y-auto p-8">
        {!selectedKb ? (
          <div className="rounded-[32px] border border-dashed border-sky-200 bg-white/80 p-12 text-center text-slate-500">
            先创建或选择一个知识库
          </div>
        ) : (
          <div className="space-y-6">
            <div className="rounded-[32px] border border-sky-100 bg-white/92 p-6 shadow-[0_20px_50px_rgba(56,189,248,0.10)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs font-black uppercase tracking-[0.2em] text-sky-600">Knowledge Base</div>
                  <h2 className="mt-2 text-2xl font-black text-slate-900">{selectedKb.icon} {selectedKb.name}</h2>
                  <p className="mt-2 text-sm text-slate-500">{selectedKb.description || '暂未填写描述'}</p>
                </div>
                <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-xs text-sky-700">
                  {selectedKb.documents?.length || 0} 文档
                </div>
              </div>

              <div className="mt-6 flex gap-2">
                {[
                  ['documents', '文档'],
                  ['recall', '召回测试'],
                  ['settings', '设置'],
                ].map(([key, label]) => (
                  <button
                    key={key}
                    onClick={() => setActiveTab(key)}
                    className={`rounded-2xl px-4 py-2 text-sm font-semibold transition ${
                      activeTab === key
                        ? 'bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)]'
                        : 'border border-slate-200 bg-white text-slate-600'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {(statusMessage || errorMessage) && (
              <div
                className={`rounded-[24px] border px-5 py-4 text-sm shadow-[0_10px_30px_rgba(148,163,184,0.08)] ${
                  errorMessage
                    ? 'border-rose-200 bg-rose-50 text-rose-700'
                    : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                }`}
              >
                {errorMessage || statusMessage}
              </div>
            )}

            {activeTab === 'documents' && (
              <div className="space-y-6">
                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-sky-100 p-3 text-sky-600"><Upload size={18} /></div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">添加文件</div>
                        <div className="text-xs text-slate-500">先上传文件，再进入分段设置</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {[['1', '上传文件'], ['2', '分段设置']].map(([step, label]) => (
                        <div
                          key={step}
                          className={`rounded-2xl px-4 py-2 text-xs font-bold ${
                            uploadStep === Number(step)
                              ? 'bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)]'
                              : 'border border-slate-200 bg-white text-slate-500'
                          }`}
                        >
                          {step}. {label}
                        </div>
                      ))}
                    </div>
                  </div>

                  {uploadStep === 1 ? (
                    <div className="mt-6 rounded-[28px] border border-dashed border-slate-200 bg-[linear-gradient(180deg,#ffffff,#f8fbff)] p-5">
                      <div className="rounded-[22px] border border-slate-200 bg-white px-4 py-5">
                        <div className="text-sm font-bold text-slate-900">上传文本文件</div>
                        <div className="mt-3 text-sm text-slate-500">支持 {KB_SUPPORTED_EXTENSIONS.join('、')}</div>
                        <div className="mt-1 text-xs text-slate-400">
                          文本类文件可在下一步直接预览分块；PDF、DOCX、XLSX、XLS 会在上传后自动解析。
                        </div>

                        <div className="mt-5 flex flex-wrap items-center gap-3">
                          <label className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 cursor-pointer hover:border-sky-200">
                            <input type="file" accept={KB_FILE_ACCEPT} className="hidden" onChange={handleFilePick} />
                            选择文件
                          </label>
                          <button
                            onClick={() => selectedFile && setUploadStep(2)}
                            disabled={!selectedFile}
                            className={`rounded-2xl px-5 py-3 text-sm font-black ${
                              selectedFile ? 'bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] text-white' : 'bg-slate-100 text-slate-300'
                            }`}
                          >
                            下一步
                          </button>
                        </div>

                        {selectedFile && (
                          <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                            已选择文件：{selectedFile.name}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mt-6 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
                      <div className="rounded-[28px] border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#f9fcff)] p-5">
                        <div className="mb-2 text-sm font-semibold text-slate-800">分段设置</div>
                        <div className="grid gap-4 md:grid-cols-2">
                          <label className="space-y-2">
                            <span className="text-xs text-slate-500">分段标识符</span>
                            <input
                              value={settingsForm.separator}
                              onChange={(e) => setSettingsForm((prev) => ({ ...prev, separator: e.target.value }))}
                              className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                            />
                          </label>
                          <label className="space-y-2">
                            <span className="text-xs text-slate-500">分段最大长度 characters</span>
                            <input
                              type="number"
                              value={settingsForm.chunk_size}
                              onChange={(e) => setSettingsForm((prev) => ({ ...prev, chunk_size: Number(e.target.value) }))}
                              className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                            />
                          </label>
                          <label className="space-y-2">
                            <span className="text-xs text-slate-500">分段重叠长度 characters</span>
                            <input
                              type="number"
                              value={settingsForm.chunk_overlap}
                              onChange={(e) => setSettingsForm((prev) => ({ ...prev, chunk_overlap: Number(e.target.value) }))}
                              className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                            />
                          </label>
                        </div>

                        <div className="mt-5 flex flex-wrap gap-3">
                          <button
                            onClick={() => setUploadStep(1)}
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700"
                          >
                            上一步
                          </button>
                          <button
                            onClick={handlePreviewChunks}
                            disabled={!previewSource.trim() || loading}
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700"
                          >
                            {loading ? '处理中...' : '预览块'}
                          </button>
                          <button
                            onClick={handleResetPreview}
                            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700"
                          >
                            重置
                          </button>
                          <button
                            onClick={handleUpload}
                            disabled={!selectedFile || loading}
                            className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white"
                          >
                            {loading ? '处理中...' : '保存并处理'}
                          </button>
                        </div>

                        {selectedFile && (
                          <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                            已选择文件：{selectedFile.name}
                          </div>
                        )}
                        {!previewSource.trim() && selectedFile && (
                          <div className="mt-3 rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                            当前文件类型不支持前端直接预览文本，上传后可在文档列表点击“查看分段”查看解析结果。
                          </div>
                        )}
                      </div>

                      <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                        <div className="flex items-center gap-3">
                          <div className="rounded-2xl bg-violet-100 p-3 text-violet-600"><SlidersHorizontal size={18} /></div>
                          <div>
                            <div className="text-sm font-bold text-slate-900">分块预览</div>
                            <div className="text-xs text-slate-500">查看当前分段策略下的内容切块</div>
                          </div>
                        </div>

                        <textarea
                          value={previewSource}
                          onChange={(e) => setPreviewSource(e.target.value)}
                          placeholder="文本类文件会自动读取到这里，也可以直接粘贴源文本进行预览"
                          className="mt-5 h-40 w-full rounded-2xl border border-slate-200 px-4 py-4 text-sm outline-none focus:border-sky-300"
                        />

                        <div className="mt-5 space-y-3 max-h-[360px] overflow-y-auto">
                          {previewChunks.length === 0 ? (
                            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                              预览块将展示在这里
                            </div>
                          ) : (
                            previewChunks.map((chunk) => (
                              <div key={chunk.index} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
                                <div className="text-xs font-black uppercase tracking-[0.18em] text-sky-600">块 {chunk.index} · {chunk.length} chars</div>
                                <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{chunk.content}</div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="text-sm font-bold text-slate-900">文档</div>
                      <div className="text-xs text-slate-500">知识库的所有文件都在这里显示</div>
                    </div>
                    <div className="rounded-2xl border border-sky-100 bg-sky-50 px-4 py-3 text-xs text-sky-700">
                      {selectedKb.documents?.length || 0} 个文档
                    </div>
                  </div>

                  <div className="mt-5 overflow-hidden rounded-3xl border border-slate-200">
                    <table className="min-w-full bg-white text-sm">
                      <thead className="bg-slate-50 text-slate-500">
                        <tr>
                          <th className="px-4 py-3 text-left">名称</th>
                          <th className="px-4 py-3 text-left">分段模式</th>
                          <th className="px-4 py-3 text-left">字符数</th>
                          <th className="px-4 py-3 text-left">召回次数</th>
                          <th className="px-4 py-3 text-left">上传时间</th>
                          <th className="px-4 py-3 text-left">状态</th>
                          <th className="px-4 py-3 text-left">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(selectedKb.documents || []).map((doc) => (
                          <tr key={doc.id} className="border-t border-slate-100">
                            <td className="px-4 py-3 font-semibold text-slate-800">{doc.name}</td>
                            <td className="px-4 py-3 text-slate-600">{doc.segment_mode}</td>
                            <td className="px-4 py-3 text-slate-600">{doc.characters}</td>
                            <td className="px-4 py-3 text-slate-600">{doc.recall_count}</td>
                            <td className="px-4 py-3 text-slate-600">{doc.uploaded_at}</td>
                            <td className="px-4 py-3 text-emerald-600">{doc.status}</td>
                            <td className="px-4 py-3">
                              <button
                                onClick={() => handleViewDocumentChunks(doc)}
                                className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-xs font-bold text-sky-700 transition hover:bg-sky-100"
                              >
                                查看分段
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {documentChunkDrawer.open && (
                  <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="text-sm font-bold text-slate-900">分段详情</div>
                        <div className="text-xs text-slate-500">{documentChunkDrawer.title}</div>
                      </div>
                      <button
                        onClick={() => setDocumentChunkDrawer({ open: false, title: '', chunks: [] })}
                        className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600"
                      >
                        收起
                      </button>
                    </div>

                    <div className="mt-5 space-y-3 max-h-[560px] overflow-y-auto">
                      {documentChunkDrawer.chunks.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                          当前文档还没有可展示的分段内容
                        </div>
                      ) : (
                        documentChunkDrawer.chunks.map((chunk) => (
                          <div key={`${documentChunkDrawer.title}-${chunk.index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
                            <div className="text-xs font-black uppercase tracking-[0.18em] text-sky-600">块 {chunk.index} · {chunk.length} chars</div>
                            <div className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">{chunk.content}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'recall' && (
              <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-600"><Search size={18} /></div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">召回测试</div>
                      <div className="text-xs text-slate-500">根据给定的查询文本测试知识的召回效果</div>
                    </div>
                  </div>

                  <textarea
                    value={recallQuery}
                    onChange={(e) => setRecallQuery(e.target.value.slice(0, 200))}
                    placeholder="输入查询文本"
                    className="mt-5 h-40 w-full rounded-2xl border border-slate-200 px-4 py-4 text-sm outline-none focus:border-sky-300"
                  />

                  <div className="mt-2 text-right text-xs text-slate-400">{recallQuery.length}/200</div>

                  <button
                    onClick={handleRecallTest}
                    disabled={!recallQuery.trim() || loading}
                    className="mt-4 rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white"
                  >
                    测试
                  </button>

                  <div className="mt-6">
                    <div className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">记录</div>
                    <div className="mt-3 space-y-2">
                      {recallHistory.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                          最近无查询结果
                        </div>
                      ) : (
                        recallHistory.map((item, index) => (
                          <div key={`${item.tested_at}-${index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                            <div className="text-sm font-semibold text-slate-800">{item.query}</div>
                            <div className="mt-1 text-xs text-slate-500">{item.tested_at} · {item.results_count} 条结果</div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                  <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-violet-100 p-3 text-violet-600"><FileText size={18} /></div>
                    <div>
                      <div className="text-sm font-bold text-slate-900">召回测试结果</div>
                      <div className="text-xs text-slate-500">召回测试结果将展示在这里</div>
                    </div>
                  </div>

                  <div className="mt-5 space-y-3 max-h-[620px] overflow-y-auto">
                    {recallResults.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                        暂无结果
                      </div>
                    ) : (
                      recallResults.map((result, index) => (
                        <div key={`${result.source}-${index}`} className="rounded-2xl border border-slate-200 bg-white px-4 py-4">
                          <div className="flex items-center justify-between gap-4">
                            <div className="text-sm font-bold text-slate-900">{result.source}</div>
                            <div className="rounded-full bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700">
                              score {result.score}
                            </div>
                          </div>
                          <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">{result.content}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-sky-100 p-3 text-sky-600"><Settings2 size={18} /></div>
                  <div>
                    <div className="text-sm font-bold text-slate-900">知识库设置</div>
                    <div className="text-xs text-slate-500">在这里配置知识库名称、模型和检索参数</div>
                  </div>
                </div>

                <div className="mt-6 grid gap-5 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-xs text-slate-500">名称</span>
                    <input
                      value={settingsForm.name}
                      onChange={(e) => setSettingsForm((prev) => ({ ...prev, name: e.target.value }))}
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs text-slate-500">图标</span>
                    <input
                      value={settingsForm.icon}
                      onChange={(e) => setSettingsForm((prev) => ({ ...prev, icon: e.target.value }))}
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                    />
                  </label>
                  <label className="space-y-2 md:col-span-2">
                    <span className="text-xs text-slate-500">描述</span>
                    <textarea
                      value={settingsForm.description}
                      onChange={(e) => setSettingsForm((prev) => ({ ...prev, description: e.target.value }))}
                      className="h-28 w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                    />
                  </label>
                  <label className="space-y-2">
                    <span className="text-xs text-slate-500">Embedding 模型</span>
                    <input
                      value={settingsForm.embedding_model}
                      onChange={(e) => setSettingsForm((prev) => ({ ...prev, embedding_model: e.target.value }))}
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-sky-300"
                    />
                  </label>
                </div>

                <div className="mt-6 rounded-[26px] border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#f8fbff)] p-5">
                  <div className="text-sm font-bold text-slate-900">混合检索</div>
                  <div className="mt-1 text-xs text-slate-500">在这里调整召回偏好与结果数量</div>
                  <div className="mt-4 grid gap-4 md:grid-cols-3">
                    <label className="space-y-2">
                      <span className="text-xs text-slate-500">语义权重</span>
                      <input
                        type="number"
                        step="0.1"
                        value={settingsForm.semantic_weight}
                        onChange={(e) => setSettingsForm((prev) => ({ ...prev, semantic_weight: Number(e.target.value) }))}
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-xs text-slate-500">Top K</span>
                      <input
                        type="number"
                        value={settingsForm.top_k}
                        onChange={(e) => setSettingsForm((prev) => ({ ...prev, top_k: Number(e.target.value) }))}
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                      />
                    </label>
                    <label className="space-y-2">
                      <span className="text-xs text-slate-500">Score 阈值</span>
                      <input
                        type="number"
                        step="0.1"
                        value={settingsForm.score_threshold}
                        onChange={(e) => setSettingsForm((prev) => ({ ...prev, score_threshold: Number(e.target.value) }))}
                        className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm"
                      />
                    </label>
                  </div>
                </div>

                <button
                  onClick={handleSaveSettings}
                  disabled={loading}
                  className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white"
                >
                  <Save size={16} />
                  保存
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

function App() {
  // --- 单部门模式：解析 URL 参数 ?mode=department&dept=TECH ---
  const urlParams = useMemo(() => new URLSearchParams(window.location.search), []);
  const standaloneDept = useMemo(() => {
    if (urlParams.get('mode') === 'department') {
      const dept = (urlParams.get('dept') || '').toUpperCase();
      return DEPARTMENTS.find((d) => d.id === dept && d.id !== 'CEO') || null;
    }
    return null;
  }, [urlParams]);
  const isStandaloneMode = !!standaloneDept;
  const standaloneBrand = urlParams.get('brand') || (standaloneDept ? `${standaloneDept.name}智能助手` : '');

  const visibleDepartments = useMemo(
    () => (isStandaloneMode ? DEPARTMENTS.filter((d) => d.id === standaloneDept.id) : DEPARTMENTS),
    [isStandaloneMode, standaloneDept]
  );

  const [appMode, setAppMode] = useState('agent');
  const [registry, setRegistry] = useState({});
  const [knowledgeBases, setKnowledgeBases] = useState([]);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState(null);
  const [agentKbConfig, setAgentKbConfig] = useState({ open: false, agent: null, selectedKbIds: [] });
  const [input, setInput] = useState('');
  const [expandedDept, setExpandedDept] = useState(isStandaloneMode ? standaloneDept.id : '');
  const [showExecutionPanel, setShowExecutionPanel] = useState(true);
  const [showGuide, setShowGuide] = useState(!isStandaloneMode);
  const [guideStepIndex, setGuideStepIndex] = useState(0);
  const [conversations, setConversations] = useState(() => {
    if (isStandaloneMode) {
      return [createConversation({}, standaloneDept.id, 'orchestrator', standaloneDept.id)];
    }
    return [createConversation({}, 'CEO', 'orchestrator', 'CEO')];
  });
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    axios.get(`${API_URL}/registry`).then((res) => setRegistry(res.data));
  }, []);

  useEffect(() => {
    axios.get(`${API_URL}/knowledge-bases`).then((res) => setKnowledgeBases(res.data));
  }, []);

  useEffect(() => {
    if (!currentConversationId && conversations[0]) {
      setCurrentConversationId(conversations[0].id);
    }
  }, [conversations, currentConversationId]);

  const currentConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === currentConversationId) || conversations[0],
    [conversations, currentConversationId]
  );

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages, currentConversation?.loading]);

  useEffect(() => {
    if (!showGuide) return;
    const timer = setInterval(() => {
      setGuideStepIndex((prev) => (prev + 1) % GUIDE_DEMO_STEPS.length);
    }, 1800);
    return () => clearInterval(timer);
  }, [showGuide]);

  useEffect(() => {
    const timer = setInterval(() => {
      setConversations((prev) => {
        let changed = false;

        const next = prev.map((conversation) => {
          let conversationChanged = false;
          const messages = conversation.messages.map((message) => {
            if (!message.isAnimating || !message.targetContent) {
              return message;
            }

            if (message.content.length >= message.targetContent.length) {
              if (!message.isAnimating) return message;
              conversationChanged = true;
              changed = true;
              return { ...message, isAnimating: false, isStreaming: message.isStreaming };
            }

            const step = Math.max(1, Math.ceil((message.targetContent.length - message.content.length) / 18));
            const nextContent = message.targetContent.slice(0, message.content.length + step);
            conversationChanged = true;
            changed = true;

            return {
              ...message,
              content: nextContent,
              isAnimating: nextContent.length < message.targetContent.length,
            };
          });

          if (!conversationChanged) {
            return conversation;
          }

          return { ...conversation, messages };
        });

        return changed ? next : prev;
      });
    }, 24);

    return () => clearInterval(timer);
  }, []);

  const updateConversation = (conversationId, updater) => {
    setConversations((prev) =>
      prev.map((conversation) =>
        conversation.id === conversationId ? updater(conversation) : conversation
      )
    );
  };

  const openConversationForTarget = (targetAgent, targetType, departmentHint) => {
    if (
      currentConversation &&
      currentConversation.targetAgent === targetAgent &&
      currentConversation.targetType === targetType
    ) {
      setExpandedDept(departmentHint || targetAgent);
      return;
    }

    const nextConversation = createConversation(registry, targetAgent, targetType, departmentHint);
    setConversations((prev) => [nextConversation, ...prev]);
    setCurrentConversationId(nextConversation.id);
    setExpandedDept(departmentHint || targetAgent);
    setInput('');
  };

  // Shared SSE stream processor used by handleSend and handleConfirmation
  const processSSEStream = async (response, conversationId) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmedLine = line.trim();
        if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue;

        try {
          const data = JSON.parse(trimmedLine.slice(6));

          if (data.type === 'stream') {
            updateConversation(conversationId, (conversation) => {
              const lastMessage = conversation.messages[conversation.messages.length - 1];
              if (lastMessage && lastMessage.role === 'assistant' && lastMessage.node === data.node && lastMessage.isStreaming) {
                const newContent = (lastMessage.content || '') + data.content;
                return {
                  ...conversation,
                  activeAgent: data.active_agent,
                  messages: [
                    ...conversation.messages.slice(0, -1),
                    { ...lastMessage, department: data.active_agent, content: newContent, targetContent: newContent, isAnimating: false },
                  ],
                };
              }
              return {
                ...conversation,
                activeAgent: data.active_agent,
                messages: [
                  ...conversation.messages,
                  createAnimatedAssistantMessage({ content: data.content, targetContent: data.content, department: data.active_agent, node: data.node, isStreaming: true }),
                ],
              };
            });
          } else if (data.type === 'update') {
            updateConversation(conversationId, (conversation) => {
              let messages = conversation.messages;
              const lastMessage = messages[messages.length - 1];
              if (data.partial_content) {
                if (lastMessage && lastMessage.role === 'assistant' && lastMessage.node === data.node_name) {
                  if ((lastMessage.targetContent || lastMessage.content || '').trim() === data.partial_content.trim()) {
                    return { ...conversation, activeDept: data.current_department || conversation.activeDept, activeAgent: data.active_agent || conversation.activeAgent, executionLog: data.execution_log?.length ? [...conversation.executionLog, ...data.execution_log] : conversation.executionLog, messages };
                  }
                  messages = [...messages.slice(0, -1), { ...lastMessage, department: data.active_agent || lastMessage.department, content: data.partial_content, targetContent: data.partial_content, isAnimating: false, isStreaming: false }];
                } else {
                  messages = [...messages, createAnimatedAssistantMessage({ content: data.partial_content, targetContent: data.partial_content, department: data.active_agent || conversation.label, node: data.node_name, isStreaming: false })];
                }
              }
              return { ...conversation, activeDept: data.current_department || conversation.activeDept, activeAgent: data.active_agent || conversation.activeAgent, executionLog: data.execution_log?.length ? [...conversation.executionLog, ...data.execution_log] : conversation.executionLog, messages };
            });
          } else if (data.type === 'phase_update') {
            updateConversation(conversationId, (conversation) => ({
              ...conversation,
              taskPhase: data.task_phase || conversation.taskPhase,
              requirementConfirmationStatus: data.requirement_confirmation_status || conversation.requirementConfirmationStatus,
              currentExecutor: data.current_executor || conversation.currentExecutor,
            }));
          } else if (data.type === 'awaiting_confirmation') {
            updateConversation(conversationId, (conversation) => ({
              ...conversation,
              loading: false,
              awaitingConfirmation: true,
              confirmationMeta: {
                completedNode: data.completed_node,
                completedAgent: data.completed_agent,
                nextNode: data.next_node,
                nextAgent: data.next_agent,
                isFinalNode: data.is_final_node,
              },
            }));
          } else if (data.type === 'final') {
            updateConversation(conversationId, (conversation) => {
              let messages = conversation.messages.map((m) => ({ ...m, isStreaming: false }));
              const lastMessage = messages[messages.length - 1];
              const lastRendered = lastMessage?.targetContent || lastMessage?.content || '';
              if (data.response && lastRendered.trim() !== data.response.trim()) {
                messages = [...messages, createAnimatedAssistantMessage({ content: '', targetContent: data.response, department: conversation.label, node: data.node || 'final', isStreaming: false })];
              }
              return { ...conversation, loading: false, activeAgent: conversation.label, taskPhase: data.task_phase || conversation.taskPhase, requirementConfirmationStatus: data.requirement_confirmation_status || conversation.requirementConfirmationStatus, awaitingConfirmation: false, confirmationMeta: null, messages };
            });
          } else if (data.type === 'error') {
            throw new Error(data.message);
          }
        } catch (error) {
          console.error('Failed to parse stream chunk:', error);
        }
      }
    }
  };

  // Handle user confirmation actions (continue / regenerate / modify)
  const handleConfirmation = async (action, feedback = '') => {
    if (!currentConversation) return;
    const conversationId = currentConversation.id;

    // If final node and user clicks "完成", just clear the confirmation state
    if (action === 'continue' && currentConversation.confirmationMeta?.isFinalNode) {
      updateConversation(conversationId, (conv) => ({
        ...conv,
        awaitingConfirmation: false,
        confirmationMeta: null,
      }));
      return;
    }

    updateConversation(conversationId, (conv) => ({
      ...conv,
      awaitingConfirmation: false,
      confirmationMeta: null,
      loading: true,
    }));

    if (action === 'modify' && feedback) {
      updateConversation(conversationId, (conv) => ({
        ...conv,
        messages: [...conv.messages, { id: `msg_${Date.now()}_modify`, role: 'user', content: `[修改建议] ${feedback}` }],
      }));
    }

    if (action === 'regenerate') {
      // Mark the last assistant message's node as stale so new stream creates a fresh bubble
      updateConversation(conversationId, (conv) => {
        const msgs = [...conv.messages];
        for (let i = msgs.length - 1; i >= 0; i--) {
          if (msgs[i].role === 'assistant') {
            msgs[i] = { ...msgs[i], node: `prev_${msgs[i].node}_${Date.now()}`, isStreaming: false };
            break;
          }
        }
        return { ...conv, messages: msgs };
      });
    }

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: action === 'modify' ? feedback : '',
          user_id: 'web_user',
          session_id: conversationId,
          target_agent: currentConversation.targetAgent,
          target_type: currentConversation.targetType,
          confirmation_action: action,
          modification_feedback: action === 'modify' ? feedback : null,
        }),
      });
      await processSSEStream(response, conversationId);
    } catch (error) {
      console.error('Confirmation error:', error);
      updateConversation(conversationId, (conv) => ({
        ...conv,
        loading: false,
        messages: [...conv.messages, { id: `msg_${Date.now()}_error`, role: 'assistant', content: '抱歉，系统响应出错，请稍后再试。', targetContent: '抱歉，系统响应出错，请稍后再试。', department: '系统提示', isAnimating: false, isStreaming: false }],
      }));
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !currentConversation || currentConversation.loading) return;

    const query = input.trim();
    const conversationId = currentConversation.id;
    const history = currentConversation.messages.map((message) => ({
      role: message.role,
      content: message.targetContent || message.content,
    }));

    // Track original requirement: set on first user message
    const isFirstUserTurn = !currentConversation.messages.some((m) => m.role === 'user');
    const originalRequirement = isFirstUserTurn ? query : currentConversation.originalRequirement;

    setInput('');

    updateConversation(conversationId, (conversation) => {
      const firstUserTurn = !conversation.messages.some((message) => message.role === 'user');
      return {
        ...conversation,
        title: firstUserTurn ? `${conversation.label} · ${query.slice(0, 20)}` : conversation.title,
        loading: true,
        activeDept: conversation.department,
        activeAgent: conversation.label,
        executionLog: [],
        originalRequirement: originalRequirement || conversation.originalRequirement,
        messages: [
          ...conversation.messages,
          {
            id: `msg_${Date.now()}_user`,
            role: 'user',
            content: query,
          },
        ],
      };
    });

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          user_id: 'web_user',
          session_id: conversationId,
          target_agent: currentConversation.targetAgent,
          target_type: currentConversation.targetType,
          history,
          task_phase: currentConversation.taskPhase || null,
          original_requirement: originalRequirement || null,
        }),
      });

      await processSSEStream(response, conversationId);
    } catch (error) {
      console.error('Streaming error:', error);
      updateConversation(conversationId, (conversation) => ({
        ...conversation,
        loading: false,
        messages: [
          ...conversation.messages,
          {
            id: `msg_${Date.now()}_error`,
            role: 'assistant',
            content: '抱歉，系统响应出错，请稍后再试。',
            targetContent: '抱歉，系统响应出错，请稍后再试。',
            department: '系统提示',
            isAnimating: false,
            isStreaming: false,
          },
        ],
      }));
    }
  };

  const currentDeptSelection =
    currentConversation?.targetType === 'agent'
      ? currentConversation.department
      : currentConversation?.targetAgent || 'CEO';

  const currentAgentSelection =
    currentConversation?.targetType === 'agent' ? currentConversation.targetAgent : null;
  const executionTree = buildExecutionTree(currentConversation, registry);
  const refreshRegistry = async () => {
    const { data } = await axios.get(`${API_URL}/registry`);
    setRegistry(data);
  };

  const refreshKnowledgeBases = async () => {
    const { data } = await axios.get(`${API_URL}/knowledge-bases`);
    setKnowledgeBases(data);
  };

  const openAgentKbConfig = (sub) => {
    setAgentKbConfig({
      open: true,
      agent: sub,
      selectedKbIds: (sub.knowledge_bases || []).map((kb) => kb.id),
    });
  };

  const saveAgentKbConfig = async () => {
    if (!agentKbConfig.agent) return;
    await axios.put(`${API_URL}/agent-kb-bindings/${agentKbConfig.agent.id}`, {
      kb_ids: agentKbConfig.selectedKbIds,
    });
    await refreshRegistry();
    await refreshKnowledgeBases();
    setAgentKbConfig({ open: false, agent: null, selectedKbIds: [] });
  };

  const jumpToKnowledgeBase = (kbId) => {
    setSelectedKnowledgeBaseId(kbId);
    setAppMode('knowledge');
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.16),_transparent_24%),radial-gradient(circle_at_top_right,_rgba(45,212,191,0.12),_transparent_28%),linear-gradient(180deg,#f8fcff_0%,#eef6ff_48%,#f7fbff_100%)] text-slate-800">
      {showGuide && !isStandaloneMode && (
        <div className="fixed inset-0 z-50 bg-[rgba(241,245,249,0.72)] backdrop-blur-md">
          <div className="mx-auto flex h-full max-w-7xl items-center justify-center px-6">
            <div className="grid w-full gap-6 lg:grid-cols-[1.05fr_1.15fr]">
              <div className="rounded-[34px] border border-sky-100 bg-white/92 p-8 shadow-[0_30px_80px_rgba(56,189,248,0.14)]">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="inline-flex items-center gap-2 rounded-full bg-sky-50 px-3 py-2 text-[11px] font-black uppercase tracking-[0.18em] text-sky-700">
                      <PlayCircle size={14} />
                      新手教程
                    </div>
                    <h2 className="mt-4 text-3xl font-black tracking-tight text-slate-900">
                      OrgAgents — 万象智团多智能体协作系统
                    </h2>
                    <p className="mt-3 text-base leading-7 text-slate-600">
                      这个系统不是“一个机器人做所有事”，而是把一家公司的协作方式抽象成多层智能体网络：
                      CEO 负责理解目标和跨部门调度，部门长负责内部编排，子智能体负责完成具体任务。
                    </p>
                  </div>

                  <button
                    onClick={() => setShowGuide(false)}
                    className="rounded-2xl border border-slate-200 bg-white p-3 text-slate-400 transition hover:border-slate-300 hover:text-slate-700"
                  >
                    <X size={18} />
                  </button>
                </div>

                <div className="mt-8 grid gap-4">
                  <div className="rounded-3xl border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#eff6ff)] p-5 shadow-[0_15px_40px_rgba(56,189,248,0.10)]">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-sky-100 p-3 text-sky-700">
                        <BrainCircuit size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">第一层：CEO 总控</div>
                        <div className="mt-1 text-sm leading-6 text-slate-600">
                          负责理解用户到底要什么，判断是否要调用多个部门，以及先做什么后做什么。
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-3xl border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#f5f3ff)] p-5 shadow-[0_15px_40px_rgba(139,92,246,0.08)]">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-violet-100 p-3 text-violet-700">
                        <Network size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">第二层：部门长编排</div>
                        <div className="mt-1 text-sm leading-6 text-slate-600">
                          每个部门长拿到任务后，不直接胡乱回答，而是根据任务类型拆成内部步骤，再调下面的小智能体。
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-3xl border border-sky-100 bg-[linear-gradient(145deg,#ffffff,#ecfdf5)] p-5 shadow-[0_15px_40px_rgba(16,185,129,0.08)]">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-emerald-100 p-3 text-emerald-700">
                        <Zap size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">第三层：子智能体执行</div>
                        <div className="mt-1 text-sm leading-6 text-slate-600">
                          子智能体只做自己最擅长的一步，比如紧急救援、派单、诊断、写代码、测试或部署，然后把结果继续传递。
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-8 flex flex-wrap gap-3">
                  <button
                    onClick={() => setShowGuide(false)}
                    className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(37,99,235,0.18)] transition hover:-translate-y-0.5"
                  >
                    我知道了，进入系统
                  </button>
                  <button
                    onClick={() => setGuideStepIndex((prev) => (prev + 1) % GUIDE_DEMO_STEPS.length)}
                    className="rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-sky-200 hover:bg-sky-50"
                  >
                    查看下一步演示
                  </button>
                </div>
              </div>

              <div className="space-y-5">
                <TutorialDemo stepIndex={guideStepIndex} />

                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-6 shadow-[0_25px_60px_rgba(56,189,248,0.10)]">
                  <div className="text-[11px] font-black uppercase tracking-[0.18em] text-sky-600">系统思路</div>
                  <div className="mt-4 space-y-3 text-sm leading-7 text-slate-600">
                    <p>
                      当你和 <span className="font-bold text-slate-900">CEO</span> 对话时，你是在用“公司总控模式”下达任务，
                      它会决定要不要跨部门协作。
                    </p>
                    <p>
                      当你和 <span className="font-bold text-slate-900">部门长</span> 对话时，你是在把问题直接交给某个部门，
                      由它自己安排内部流程。
                    </p>
                    <p>
                      当你和 <span className="font-bold text-slate-900">子智能体</span> 对话时，就是单点直连，
                      不再经过部长编排，更适合深入处理某一个具体环节。
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex h-screen overflow-hidden">
        <aside className="w-[360px] border-r border-sky-200/70 bg-white/72 backdrop-blur-2xl flex flex-col shadow-[20px_0_60px_rgba(148,163,184,0.12)]">
          <div className="px-6 pt-6 pb-5 border-b border-sky-100">
            <div className="flex items-center gap-3">
              <div className="rounded-2xl bg-[linear-gradient(135deg,#0f172a,#2563eb)] p-3 text-white shadow-[0_18px_40px_rgba(37,99,235,0.22)]">
                <MessagesSquare size={20} />
              </div>
              <div>
                <div className="text-sm font-black tracking-[0.12em] text-slate-900">{isStandaloneMode ? standaloneBrand : 'Agent Launcher'}</div>
                <div className="text-xs text-slate-500">{isStandaloneMode ? '选择对话模式开始使用' : '先创建对话，再进入对应线程'}</div>
              </div>
            </div>
          </div>

          <div className="p-5 border-b border-sky-100">
            <div className="rounded-3xl border border-sky-200 bg-[linear-gradient(145deg,rgba(255,255,255,0.95),rgba(240,249,255,0.9))] p-4 shadow-[0_25px_60px_rgba(56,189,248,0.12)]">
              <div className="mb-4 flex gap-2">
                <button
                  onClick={() => setAppMode('agent')}
                  className={`flex-1 rounded-2xl px-4 py-2 text-sm font-bold transition ${
                    appMode === 'agent'
                      ? 'bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)]'
                      : 'border border-slate-200 bg-white text-slate-600'
                  }`}
                >
                  智能体工作台
                </button>
                <button
                  onClick={() => setAppMode('knowledge')}
                  className={`flex-1 rounded-2xl px-4 py-2 text-sm font-bold transition ${
                    appMode === 'knowledge'
                      ? 'bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] text-white shadow-[0_12px_24px_rgba(37,99,235,0.18)]'
                      : 'border border-slate-200 bg-white text-slate-600'
                  }`}
                >
                  知识库管理
                </button>
              </div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-xs font-black uppercase tracking-[0.18em] text-sky-600">快速开始</div>
                  <div className="mt-2 text-sm font-semibold text-slate-900">{isStandaloneMode ? '两种对话模式' : '三种对话模式'}</div>
                </div>
                <Sparkles size={18} className="text-sky-500" />
              </div>
              <div className="mt-3 space-y-2 text-xs text-slate-600 leading-5">
                {isStandaloneMode ? (
                  <>
                    <div>1. `部门长`：该部门内部自动编排</div>
                    <div>2. `子智能体`：直接单聊，不经过部长</div>
                  </>
                ) : (
                  <>
                    <div>1. `CEO`：跨部门总控</div>
                    <div>2. `部门长`：该部门内部自动编排</div>
                    <div>3. `子智能体`：直接单聊，不经过部长</div>
                  </>
                )}
              </div>
              <button
                onClick={() => {
                  if (isStandaloneMode) {
                    openConversationForTarget(standaloneDept.id, 'orchestrator', standaloneDept.id);
                  } else {
                    openConversationForTarget('CEO', 'orchestrator', 'CEO');
                  }
                }}
                className="mt-4 w-full rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-4 py-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:shadow-[0_16px_30px_rgba(37,99,235,0.22)]"
              >
                <span className="inline-flex items-center gap-2">
                  <PlusSquare size={16} />
                  {isStandaloneMode ? `新建 ${standaloneDept.name} 对话` : '新建 CEO 对话'}
                </span>
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-5">
            {appMode === 'knowledge' ? (
              <div className="rounded-[28px] border border-sky-100 bg-white/92 p-5 shadow-[0_18px_40px_rgba(148,163,184,0.10)]">
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-sky-100 p-3 text-sky-700"><Database size={18} /></div>
                  <div>
                    <div className="text-sm font-bold text-slate-900">知识库模式</div>
                    <div className="text-xs text-slate-500">左侧只保留模式切换，管理页会在主区域展开</div>
                  </div>
                </div>
              </div>
            ) : (
              <>
            <div className="mb-3 text-[11px] font-black uppercase tracking-[0.22em] text-slate-400">新建对话</div>
            <div className="space-y-4">
              {visibleDepartments.filter((dept) => dept.id !== 'CEO').map((dept) => {
                const Icon = dept.icon;
                const isExpanded = expandedDept === dept.id;
                const isSelected = currentDeptSelection === dept.id && !currentAgentSelection;

                return (
                  <div key={dept.id} className={`rounded-3xl border p-4 transition-all duration-300 ${
                    isSelected
                      ? 'border-sky-300 bg-[linear-gradient(145deg,#ffffff,#eff8ff)] shadow-[0_20px_50px_rgba(56,189,248,0.18)]'
                      : 'border-slate-200/90 bg-white/88 shadow-[0_14px_35px_rgba(148,163,184,0.12)]'
                  }`}>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div className={`relative rounded-2xl p-2.5 transition-all ${
                          isSelected
                            ? 'bg-sky-100 text-sky-600 shadow-[0_12px_30px_rgba(14,165,233,0.18)]'
                            : 'bg-slate-100 text-slate-500'
                        }`}>
                          {isDepartmentSpeaking(currentConversation, dept.name) && (
                            <span className="absolute -right-1 -top-1 flex h-3 w-3">
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60"></span>
                              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500"></span>
                            </span>
                          )}
                          <Icon size={18} />
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-900">{dept.name}</div>
                          <div className="mt-1 text-xs text-slate-500">{dept.summary}</div>
                        </div>
                      </div>
                      <button
                        onClick={() => setExpandedDept(isExpanded ? '' : dept.id)}
                        className="rounded-full border border-slate-200 bg-white p-1.5 text-slate-400 transition hover:border-sky-200 hover:text-sky-600"
                      >
                        <ChevronRight size={16} className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </button>
                    </div>

                    <button
                      onClick={() => openConversationForTarget(dept.id, 'orchestrator', dept.id)}
                      className="mt-4 w-full rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-700 transition hover:bg-sky-100 hover:shadow-[0_10px_24px_rgba(14,165,233,0.12)]"
                    >
                      新建部门长对话
                    </button>

                    {isExpanded && registry[dept.id] && (
                      <div className="mt-4 space-y-2">
                        <div className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">子智能体直聊</div>
                        {registry[dept.id].map((sub) => {
                          const active = currentAgentSelection === sub.id;
                          return (
                            <div
                              key={sub.id}
                              className={`w-full rounded-2xl border px-3.5 py-3 text-left transition ${
                                active
                                  ? 'border-violet-300 bg-violet-50 shadow-[0_12px_24px_rgba(139,92,246,0.14)]'
                                  : 'border-slate-200 bg-slate-50/80 hover:border-sky-200 hover:bg-white'
                              }`}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <button
                                  onClick={() => openConversationForTarget(sub.id, 'agent', dept.id)}
                                  className="flex-1 text-left"
                                >
                                  <div className="text-sm font-semibold text-slate-800">{sub.name}</div>
                                  <div className="mt-1 text-xs leading-5 text-slate-500">{sub.description}</div>
                                </button>
                                <button
                                  onClick={() => openAgentKbConfig(sub)}
                                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 hover:border-sky-200 hover:text-sky-700"
                                >
                                  配置
                                </button>
                              </div>

                              {(sub.knowledge_bases || []).length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                  {(sub.knowledge_bases || []).map((kb) => (
                                    <button
                                      key={kb.id}
                                      onClick={() => jumpToKnowledgeBase(kb.id)}
                                      className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-bold text-sky-700 hover:bg-sky-100"
                                    >
                                      {kb.icon} {kb.name}
                                    </button>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
              </>
            )}
          </div>
        </aside>

        <main className="flex-1 flex flex-col">
          {appMode === 'knowledge' ? (
            <>
              <header className="border-b border-sky-100 bg-white/72 px-8 py-6 backdrop-blur-2xl">
                <div className="flex items-start justify-between gap-6">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] p-3 text-white shadow-[0_18px_40px_rgba(37,99,235,0.18)]">
                        <Database size={22} />
                      </div>
                      <div>
                        <div className="text-[11px] font-black uppercase tracking-[0.2em] text-sky-600">
                          数据管理
                        </div>
                        <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
                          可视检索向量知识库
                        </h1>
                      </div>
                    </div>
                    <div className="mt-4 rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-sm text-slate-600 shadow-[0_10px_24px_rgba(148,163,184,0.08)]">
                      支持多个知识库、分段预览、文件处理、召回测试和知识库设置。
                    </div>
                  </div>
                </div>
              </header>
              <div className="flex-1 min-h-0">
                <KnowledgeBaseManager
                  externalSelectedKbId={selectedKnowledgeBaseId}
                  onSelectedKbChange={setSelectedKnowledgeBaseId}
                />
              </div>
            </>
          ) : (
            <>
          <header className="border-b border-sky-100 bg-white/72 px-8 py-6 backdrop-blur-2xl">
            <div className="flex items-start justify-between gap-6">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                    <div className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] p-3 text-white shadow-[0_18px_40px_rgba(37,99,235,0.18)]">
                      <Workflow size={22} />
                    </div>
                    <div>
                    <div className="text-[11px] font-black uppercase tracking-[0.2em] text-sky-600">
                      当前会话
                    </div>
                    <h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">
                      {currentConversation?.label || '未选择对话'}
                    </h1>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 shadow-[0_10px_24px_rgba(148,163,184,0.08)]">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">模式</div>
                    <div className="mt-1 text-sm font-semibold text-slate-800">{currentConversation?.modeLabel}</div>
                  </div>
                  <div className="rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 shadow-[0_10px_24px_rgba(148,163,184,0.08)]">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">规则</div>
                    <div className="mt-1 text-sm font-semibold text-slate-800">一个会话只绑定一个智能体</div>
                  </div>
                  <div className="rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 shadow-[0_10px_24px_rgba(148,163,184,0.08)]">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-slate-400">切换方式</div>
                    <div className="mt-1 text-sm font-semibold text-slate-800">要换对象，请新建对话</div>
                  </div>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <button
                  onClick={() => setShowGuide(true)}
                  className="rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-sm font-semibold text-slate-700 shadow-[0_10px_24px_rgba(148,163,184,0.08)] transition hover:border-sky-200 hover:bg-white"
                >
                  新手教程
                </button>

                <div className="relative hidden overflow-hidden rounded-[28px] border border-sky-100 bg-white/90 px-5 py-4 shadow-[0_18px_40px_rgba(56,189,248,0.12)] md:block">
                  <div className="absolute -right-2 -top-2 h-10 w-10 animate-pulse rounded-full bg-sky-100 blur-xl"></div>
                  <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(56,189,248,0.16),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(14,165,233,0.08),_transparent_30%)]"></div>
                  <div className="flex items-center gap-4">
                    <div className="relative flex h-14 w-14 items-center justify-center rounded-[22px] bg-[linear-gradient(135deg,#ecfeff,#dbeafe)] text-sky-700 shadow-inner">
                      <span className="absolute inset-1 rounded-[18px] border border-white/80"></span>
                      <span className="absolute h-20 w-20 animate-pulse rounded-full border border-sky-200/70"></span>
                      <span className="absolute h-24 w-24 animate-[spin_9s_linear_infinite] rounded-full border border-transparent border-t-sky-300/70 border-r-cyan-200/60"></span>
                      <span className="absolute h-28 w-28 animate-[spin_13s_linear_infinite_reverse] rounded-full border border-transparent border-b-blue-200/70 border-l-sky-200/70"></span>
                      <span className="absolute -right-1 top-1 h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.7)]"></span>
                      <span className="absolute bottom-0 left-0 h-2 w-2 animate-bounce rounded-full bg-sky-400 shadow-[0_0_10px_rgba(56,189,248,0.6)] [animation-duration:1.8s]"></span>
                      <Bot size={26} className="relative z-10" />
                    </div>
                    <div className="relative z-10">
                      <div className="text-[11px] font-black uppercase tracking-[0.18em] text-sky-600">AI Control Core</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">{isStandaloneMode ? standaloneBrand : 'OrgAgents 万象智团协作中枢'}</div>
                      <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-500">
                        <span className="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-400"></span>
                        <span>实时编排中</span>
                      </div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => setShowExecutionPanel((prev) => !prev)}
                  className="rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-sm font-semibold text-slate-700 shadow-[0_10px_24px_rgba(148,163,184,0.08)] transition hover:border-sky-200 hover:bg-white"
                >
                  {showExecutionPanel ? '隐藏执行过程' : '查看执行过程'}
                </button>
              </div>
            </div>
          </header>

          <div className="flex flex-1 min-h-0">
            <section className="flex-1 min-w-0 flex flex-col">
              <div className="px-8 pt-6">
                <div className="rounded-3xl border border-sky-100 bg-[linear-gradient(145deg,rgba(255,255,255,0.95),rgba(239,246,255,0.92))] px-5 py-4 text-sm text-slate-600 shadow-[0_20px_45px_rgba(148,163,184,0.12)]">
                  <span className="font-bold text-slate-900">怎么用最顺：</span>
                  {isStandaloneMode
                    ? `想让 ${standaloneDept.name} 自动编排内部流程，就新建部门长对话；想直接问某个岗位，就从左侧展开后新建子智能体直聊。`
                    : '想跨部门协作就新建 `CEO` 对话；想让某个部门自己安排内部流程，就新建对应 `部门长` 对话；想直接问某个岗位，就从左侧展开部门后新建 `子智能体直聊`。'
                  }
                </div>
              </div>

              <div className="flex-1 overflow-y-auto px-8 py-8 space-y-7">
                {/* Task Phase Status Bar */}
                {currentConversation && currentConversation.taskPhase && currentConversation.taskPhase !== 'idle' && (
                  <TaskPhaseBar
                    taskPhase={currentConversation.taskPhase}
                    requirementConfirmationStatus={currentConversation.requirementConfirmationStatus}
                    currentExecutor={currentConversation.currentExecutor}
                  />
                )}
                {(currentConversation?.messages || []).map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex max-w-[78%] gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                      <div className={`mt-1 flex h-11 w-11 items-center justify-center rounded-2xl shadow-lg transition-all ${
                        msg.role === 'user'
                          ? 'bg-[linear-gradient(135deg,#0f172a,#334155)] text-white shadow-slate-300/20'
                          : (msg.isStreaming || msg.isAnimating)
                            ? 'border border-sky-200 bg-sky-50 text-sky-600 shadow-[0_0_24px_rgba(56,189,248,0.18)]'
                            : 'border border-slate-200 bg-white text-sky-600 shadow-slate-200/60'
                      }`}>
                        {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                      </div>

                      <div className={msg.role === 'user' ? 'items-end' : 'items-start'}>
                        <div className={`mb-2 flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                          <span className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                            {msg.role === 'user' ? 'Operator' : msg.department}
                          </span>
                          {msg.role === 'assistant' && (msg.isStreaming || msg.isAnimating) && (
                            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-600 shadow-[0_10px_20px_rgba(16,185,129,0.12)]">
                              <Loader2 size={10} className="animate-spin" />
                              输出中
                            </span>
                          )}
                        </div>

                        <div
                          className={`rounded-[28px] px-5 py-4 text-[15px] leading-7 shadow-xl transition-all ${
                            msg.role === 'user'
                              ? 'rounded-tr-md border border-slate-200 bg-[linear-gradient(145deg,#0f172a,#334155)] text-white shadow-[0_18px_40px_rgba(15,23,42,0.18)]'
                              : (msg.isStreaming || msg.isAnimating)
                                ? 'rounded-tl-md border border-sky-200 bg-[linear-gradient(145deg,#ffffff,#f0f9ff)] text-slate-800 shadow-[0_18px_40px_rgba(56,189,248,0.16)]'
                                : 'rounded-tl-md border border-slate-200 bg-white text-slate-800 shadow-[0_18px_40px_rgba(148,163,184,0.12)]'
                          }`}
                        >
                          <span className="whitespace-pre-wrap">{msg.content}</span>
                          {msg.role === 'assistant' && (msg.isStreaming || msg.isAnimating) && (
                            <span className="ml-1 inline-block h-5 w-[2px] translate-y-1 animate-pulse bg-sky-500 align-middle" />
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {currentConversation?.loading && !currentConversation.messages.some((message) => message.isStreaming || message.isAnimating) && (
                  <div className="flex justify-start">
                    <div className="flex max-w-[78%] gap-4">
                      <div className="mt-1 flex h-11 w-11 items-center justify-center rounded-2xl border border-sky-100 bg-white text-sky-600 shadow-lg shadow-sky-100">
                        <Bot size={20} />
                      </div>
                      <div>
                        <div className="mb-2 text-[11px] font-black uppercase tracking-[0.18em] text-slate-400">
                          {currentConversation.activeAgent}
                        </div>
                        <div className="rounded-[28px] rounded-tl-md border border-slate-200 bg-white px-5 py-4 text-sm text-slate-500 shadow-xl">
                          正在准备回复...
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {currentConversation?.awaitingConfirmation ? (
                <ConfirmationActionBar
                  meta={currentConversation.confirmationMeta}
                  onContinue={() => handleConfirmation('continue')}
                  onRegenerate={() => handleConfirmation('regenerate')}
                  onModify={(fb) => handleConfirmation('modify', fb)}
                />
              ) : (
              <div className="border-t border-sky-100 bg-white/35 px-8 py-6 backdrop-blur-2xl">
                <div className="rounded-[30px] border border-sky-100 bg-white/92 p-3 shadow-[0_22px_60px_rgba(148,163,184,0.14)]">
                  <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    placeholder={`继续和 ${currentConversation?.label || '当前智能体'} 对话...`}
                    className="min-h-[110px] w-full resize-none rounded-[22px] border-0 bg-transparent px-4 py-4 text-[15px] leading-7 text-slate-800 outline-none placeholder:text-slate-400"
                  />
                  <div className="flex items-center justify-between px-2 pt-2">
                    <div className="text-xs text-slate-400">
                      `Enter` 发送，`Shift + Enter` 换行
                    </div>
                    <button
                      onClick={handleSend}
                      disabled={currentConversation?.loading || !input.trim()}
                      className="inline-flex items-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white shadow-[0_16px_32px_rgba(37,99,235,0.2)] transition hover:-translate-y-0.5 hover:shadow-[0_20px_36px_rgba(37,99,235,0.24)] disabled:bg-slate-200 disabled:text-slate-400"
                    >
                      <Send size={16} />
                      发送
                    </button>
                  </div>
                </div>
              </div>
              )}
            </section>

            <aside className="w-[360px] border-l border-sky-100 bg-white/72 p-6 backdrop-blur-2xl overflow-y-auto shadow-[-20px_0_60px_rgba(148,163,184,0.08)]">
              <div>
                <div className="flex items-center gap-3">
                  <div className="rounded-2xl bg-[linear-gradient(135deg,#0f172a,#2563eb)] p-2.5 text-white shadow-[0_16px_28px_rgba(37,99,235,0.14)]">
                    <MessagesSquare size={18} />
                  </div>
                  <div>
                    <div className="text-sm font-bold text-slate-900">会话列表</div>
                    <div className="text-xs text-slate-500">切换已创建的独立线程</div>
                  </div>
                </div>

                <div className="mt-5 space-y-2">
                  {conversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      onClick={() => {
                        setCurrentConversationId(conversation.id);
                        setExpandedDept(
                          conversation.targetType === 'agent' ? conversation.department : conversation.targetAgent
                        );
                      }}
                      className={`w-full rounded-2xl border p-3.5 text-left transition ${
                        currentConversationId === conversation.id
                          ? 'border-sky-300 bg-[linear-gradient(145deg,#ffffff,#eff6ff)] shadow-[0_20px_45px_rgba(56,189,248,0.14)]'
                          : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-bold text-slate-800">{conversation.title}</div>
                          <div className="mt-1 truncate text-[11px] uppercase tracking-[0.16em] text-slate-400">
                            {conversation.modeLabel}
                          </div>
                        </div>
                        {conversation.loading && <Loader2 size={14} className="animate-spin text-sky-500" />}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {showExecutionPanel && (
                <div className="mt-8">
                  <div>
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-gradient-to-br from-sky-500 to-blue-600 p-2.5 text-white shadow-lg shadow-sky-200">
                        <Workflow size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">流程树</div>
                        <div className="text-xs text-slate-500">按思维导图方式看当前会话编排</div>
                      </div>
                    </div>

                    <div className="mt-5 rounded-2xl border border-sky-100 bg-gradient-to-br from-sky-50/50 to-blue-50/30 p-6 shadow-inner">
                      {executionTree ? (
                        <div className="overflow-x-auto">
                          <TreeNode node={executionTree} />
                        </div>
                      ) : (
                        <div className="rounded-2xl border border-dashed border-slate-300 bg-white/60 px-4 py-8 text-center text-sm text-slate-500">
                          <div className="mb-2 text-2xl">🌳</div>
                          <div className="font-medium">当前会话暂时还没有可视化流程</div>
                          <div className="mt-1 text-xs">开始对话后，这里会显示智能体协作的树形结构</div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-8">
                    <div className="flex items-center gap-3">
                      <div className="rounded-2xl bg-violet-100 p-2.5 text-violet-600">
                        <Workflow size={18} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-slate-900">执行过程</div>
                        <div className="text-xs text-slate-500">当前会话的实时链路</div>
                      </div>
                    </div>

                    <div className="mt-5 space-y-3">
                      {!currentConversation?.executionLog?.length ? (
                        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                          当前会话还没有执行记录。开始对话后，这里会显示各个智能体的处理轨迹。
                        </div>
                      ) : (
                        currentConversation.executionLog.map((log, index) => {
                          // 根据智能体类型设置不同的样式
                          const isCEO = log.agent === 'CEO 总智能体';
                          const isDepartmentLead = log.agent.includes('部长');
                          const isSubAgent = !isCEO && !isDepartmentLead;

                          const getLogStyle = () => {
                            if (isCEO) {
                              return {
                                border: 'border-sky-300',
                                bg: 'bg-gradient-to-br from-sky-50 to-blue-50',
                                icon: '🎯',
                                iconBg: 'bg-sky-100',
                                iconColor: 'text-sky-600',
                                textColor: 'text-sky-700',
                                badge: 'bg-sky-500 text-white'
                              };
                            }
                            if (isDepartmentLead) {
                              return {
                                border: 'border-violet-300',
                                bg: 'bg-gradient-to-br from-violet-50 to-purple-50',
                                icon: '🏢',
                                iconBg: 'bg-violet-100',
                                iconColor: 'text-violet-600',
                                textColor: 'text-violet-700',
                                badge: 'bg-violet-500 text-white'
                              };
                            }
                            return {
                              border: 'border-slate-200',
                              bg: 'bg-white',
                              icon: '⚙️',
                              iconBg: 'bg-slate-100',
                              iconColor: 'text-slate-600',
                              textColor: 'text-slate-700',
                              badge: 'bg-slate-500 text-white'
                            };
                          };

                          const style = getLogStyle();

                          return (
                            <div
                              key={`${log.agent}-${index}`}
                              className={`relative rounded-2xl border ${style.border} ${style.bg} px-4 py-3.5 shadow-sm transition-all hover:shadow-md`}
                            >
                              {/* 序号标识 */}
                              <div className={`absolute -left-2 -top-2 flex h-6 w-6 items-center justify-center rounded-full ${style.badge} text-[10px] font-black shadow-sm`}>
                                {index + 1}
                              </div>

                              {/* 图标和智能体名称 */}
                              <div className="flex items-start gap-3">
                                <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl ${style.iconBg} text-base`}>
                                  {style.icon}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className={`text-sm font-bold ${style.textColor}`}>
                                    {log.agent}
                                  </div>
                                  <div className="mt-1.5 text-xs leading-relaxed text-slate-600">
                                    {log.status}
                                  </div>

                                  {/* 部门标识 */}
                                  {log.department && (
                                    <div className="mt-2 inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600">
                                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-slate-400"></span>
                                      {log.department}
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* 连接线（非最后一个） */}
                              {index < currentConversation.executionLog.length - 1 && (
                                <div className="absolute -bottom-3 left-1/2 h-3 w-0.5 -translate-x-1/2 bg-gradient-to-b from-slate-300 to-transparent"></div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>
                </div>
              )}
            </aside>
          </div>
            </>
          )}
        </main>
      </div>

      {agentKbConfig.open && agentKbConfig.agent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/20 px-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-[28px] border border-sky-100 bg-white p-6 shadow-[0_30px_80px_rgba(15,23,42,0.16)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-black text-slate-900">{agentKbConfig.agent.name} 知识库配置</div>
                <div className="mt-1 text-xs text-slate-500">
                  只对小智能体生效。CEO 和部门长只负责任务编排，不接知识库。
                </div>
              </div>
              <button
                onClick={() => setAgentKbConfig({ open: false, agent: null, selectedKbIds: [] })}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600"
              >
                关闭
              </button>
            </div>

            <div className="mt-5 grid gap-3 max-h-[420px] overflow-y-auto">
              {knowledgeBases.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
                  当前还没有知识库，先去知识库管理中新建。
                </div>
              ) : (
                knowledgeBases.map((kb) => {
                  const checked = agentKbConfig.selectedKbIds.includes(kb.id);
                  return (
                    <label
                      key={kb.id}
                      className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-4 transition ${
                        checked ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-white'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          setAgentKbConfig((prev) => ({
                            ...prev,
                            selectedKbIds: e.target.checked
                              ? [...prev.selectedKbIds, kb.id]
                              : prev.selectedKbIds.filter((item) => item !== kb.id),
                          }));
                        }}
                        className="mt-1 h-4 w-4 rounded border-slate-300 text-sky-600"
                      />
                      <div>
                        <div className="text-sm font-bold text-slate-900">{kb.icon} {kb.name}</div>
                        <div className="mt-1 text-xs text-slate-500">{kb.description || '暂无描述'}</div>
                      </div>
                    </label>
                  );
                })
              )}
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setAgentKbConfig({ open: false, agent: null, selectedKbIds: [] })}
                className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700"
              >
                取消
              </button>
              <button
                onClick={saveAgentKbConfig}
                className="rounded-2xl bg-[linear-gradient(135deg,#0ea5e9,#2563eb)] px-5 py-3 text-sm font-black text-white"
              >
                保存配置
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
