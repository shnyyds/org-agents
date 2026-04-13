#!/usr/bin/env bash
# install_openclaw_agents.sh
# 一键注册 org-agents 的 27 个 Agent 到 OpenClaw。
# 兼容 macOS 自带 bash 3.2（不使用 declare -A）。
# 用法: bash backend/scripts/install_openclaw_agents.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/../agents" && pwd)"
OPENCLAW_BIN="${OPENCLAW_BIN:-openclaw}"
OPENCLAW_HOME="${OPENCLAW_HOME:-$HOME/.openclaw}"
OPENCLAW_CONFIG="$OPENCLAW_HOME/openclaw.json"

# ── 颜色 ──
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── 1. 检查依赖 ──
if ! command -v "$OPENCLAW_BIN" &>/dev/null; then
    error "openclaw CLI not found. Please install OpenClaw first."
fi
info "OpenClaw CLI found: $(command -v "$OPENCLAW_BIN")"

if ! command -v jq &>/dev/null; then
    error "jq not found. Install with: brew install jq"
fi

if [ ! -f "$OPENCLAW_CONFIG" ]; then
    error "openclaw.json not found at $OPENCLAW_CONFIG"
fi

# ── 2. Agent 列表 ──
AGENTS=(
    org_ceo
    org_chief_assistant org_strategy_hub org_review_board
    org_market_lead org_tech_lead org_sales_lead org_repair_lead org_cs_lead org_user_lead
    org_faq org_emergency org_human
    org_lead_gen org_quote org_cad
    org_manager org_master org_worker
    org_device org_repair_portal
    org_analyze_industry org_generate_content
    org_product org_developer org_tester org_devops
)

# ── 3. Tools profile（case 查表）──
# coding = group:fs + group:runtime + group:sessions(含sessions_spawn) + group:memory + image
get_tools_profile() {
    case "$1" in
        org_chief_assistant|org_strategy_hub|org_review_board|\
        org_tech_lead|org_market_lead|org_sales_lead|\
        org_repair_lead|org_cs_lead|org_user_lead|org_ceo)
            echo "coding" ;;
        *)
            echo "coding" ;;
    esac
}

# ── 4. Subagent 白名单（case 查表，兼容 bash 3.2）──
get_whitelist() {
    case "$1" in
        org_ceo)                echo "org_market_lead,org_tech_lead,org_sales_lead,org_repair_lead,org_cs_lead,org_user_lead" ;;
        org_chief_assistant)    echo "org_strategy_hub" ;;
        org_strategy_hub)       echo "org_review_board,org_tech_lead" ;;
        org_review_board)       echo "org_strategy_hub,org_tech_lead" ;;
        org_market_lead)        echo "org_analyze_industry,org_generate_content" ;;
        org_tech_lead)          echo "org_strategy_hub,org_review_board,org_product,org_developer,org_tester,org_devops" ;;
        org_sales_lead)         echo "org_lead_gen,org_quote,org_cad" ;;
        org_repair_lead)        echo "org_manager,org_master,org_worker" ;;
        org_cs_lead)            echo "org_faq,org_emergency,org_human" ;;
        org_user_lead)          echo "org_device,org_repair_portal" ;;
        org_faq|org_emergency|org_human)           echo "org_cs_lead" ;;
        org_lead_gen|org_quote|org_cad)            echo "org_sales_lead" ;;
        org_manager|org_master|org_worker)         echo "org_repair_lead" ;;
        org_device|org_repair_portal)              echo "org_user_lead" ;;
        org_analyze_industry|org_generate_content) echo "org_market_lead" ;;
        org_product|org_developer|org_tester|org_devops) echo "org_tech_lead" ;;
        *)                      echo "" ;;
    esac
}

# ── 4. 创建 workspace 并注册到 agents.list ──
REGISTERED=0
SKIPPED=0

for agent_id in "${AGENTS[@]}"; do
    ws_dir="$OPENCLAW_HOME/workspace-${agent_id}"
    soul_src="$AGENTS_DIR/${agent_id}/SOUL.md"

    if [ ! -f "$soul_src" ]; then
        warn "SOUL.md not found for $agent_id, skipping."
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # 创建 workspace 并复制 SOUL.md
    mkdir -p "$ws_dir"
    cp "$soul_src" "$ws_dir/SOUL.md"

    # 复制全局规则 GLOBAL.md → AGENTS.md，并追加 SOUL.md 内容
    # （OpenClaw subagent 模式只读 AGENTS.md，不读 SOUL.md）
    global_src="$AGENTS_DIR/GLOBAL.md"
    if [ -f "$global_src" ]; then
        cp "$global_src" "$ws_dir/AGENTS.md"
        printf '\n---\n\n' >> "$ws_dir/AGENTS.md"
        cat "$soul_src" >> "$ws_dir/AGENTS.md"
    else
        cp "$soul_src" "$ws_dir/AGENTS.md"
    fi

    # 覆盖 OpenClaw 默认模板文件（gateway 会自动重建，所以不能删，只能覆盖）
    cat > "$ws_dir/BOOTSTRAP.md" << 'TMPL'
# 已配置完成
本智能体已完成配置，请直接按照 SOUL.md 和 AGENTS.md 中的角色定义执行任务。
不需要进行任何初始化、自我介绍或身份设置流程。直接开始工作。
TMPL
    cat > "$ws_dir/IDENTITY.md" << 'TMPL'
# 身份信息
本智能体是星核StarCore系统的组成部分。具体角色和职责请参见 SOUL.md。
不需要询问用户关于身份、名字、语气等问题。
TMPL
    cat > "$ws_dir/USER.md" << 'TMPL'
# 用户信息
用户是星核StarCore系统的使用者。不需要询问用户的名字、偏好、时区等个人信息。
直接按照任务要求执行即可。
TMPL
    cat > "$ws_dir/TOOLS.md" << 'TMPL'
# 工具说明
使用系统提供的工具完成任务。
TMPL
    cat > "$ws_dir/HEARTBEAT.md" << 'TMPL'
# 心跳
无需执行心跳检查。专注于当前任务。
TMPL

    # 构建白名单 JSON 数组内容
    whitelist="$(get_whitelist "$agent_id")"
    if [ -n "$whitelist" ]; then
        allow_json=$(echo "$whitelist" | tr ',' '\n' | sed 's/.*/"&"/' | paste -sd, -)
    else
        allow_json=""
    fi

    tools_profile="$(get_tools_profile "$agent_id")"

    # 检查是否已注册（在 .agents.list[] 中查找）
    existing=$(jq -r --arg id "$agent_id" '.agents.list[]? | select(.id == $id) | .id' "$OPENCLAW_CONFIG" 2>/dev/null || true)

    if [ "$existing" = "$agent_id" ]; then
        # 已存在 → 更新 workspace、白名单和 tools profile
        jq --arg id "$agent_id" --arg ws "$ws_dir" --argjson wl "[${allow_json}]" --arg tp "$tools_profile" \
            '(.agents.list[] | select(.id == $id)) |= (.workspace = $ws | .subagents.allowAgents = $wl | .tools.profile = $tp)' \
            "$OPENCLAW_CONFIG" > "${OPENCLAW_CONFIG}.tmp" && mv "${OPENCLAW_CONFIG}.tmp" "$OPENCLAW_CONFIG"
        info "Updated: $agent_id"
    else
        # 新增 → 追加到 .agents.list
        jq --arg id "$agent_id" --arg ws "$ws_dir" --argjson wl "[${allow_json}]" --arg tp "$tools_profile" \
            '.agents.list += [{"id": $id, "name": $id, "workspace": $ws, "subagents": {"allowAgents": $wl}, "tools": {"profile": $tp}}]' \
            "$OPENCLAW_CONFIG" > "${OPENCLAW_CONFIG}.tmp" && mv "${OPENCLAW_CONFIG}.tmp" "$OPENCLAW_CONFIG"
        info "Registered: $agent_id"
    fi
    REGISTERED=$((REGISTERED + 1))
done

info "Done. Registered: $REGISTERED, Skipped: $SKIPPED"

# ── 5. 重启 gateway ──
info "Restarting OpenClaw gateway..."
if "$OPENCLAW_BIN" gateway restart 2>/dev/null; then
    info "Gateway restarted successfully."
else
    warn "Gateway restart failed or not running. Start manually: $OPENCLAW_BIN gateway start"
fi

echo ""
info "=== Installation Complete ==="
info "To use OpenClaw backend, set in your .env:"
info "  LLM_BACKEND=openclaw"