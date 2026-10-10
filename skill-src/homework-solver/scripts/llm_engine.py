#!/usr/bin/env python3
"""
Stage 3b: 国产大模型推理引擎 (Domestic LLM Reasoning Engine)
================================================================
C4C 的核心迁移点：starter kit 的解题推理依赖 Claude，这里换成国产大模型。

支持（全部走 OpenAI 兼容的 /chat/completions 协议，只换 base_url + model）：

    provider     base_url                                      env key
    ---------    ------------------------------------------    -------------------
    deepseek     https://api.deepseek.com/v1                  DEEPSEEK_API_KEY
    qwen         https://dashscope.aliyuncs.com/compatible-mode/v1
                                                              DASHSCOPE_API_KEY
    kimi         https://api.moonshot.cn/v1                   MOONSHOT_API_KEY
    openai-compatible  由 LLM_BASE_URL 指定                     LLM_API_KEY

设计要点
--------
1. **零依赖**：只用标准库 urllib，不装 openai SDK 也能跑（服务器上常见）。
2. **可复现**：所有响应落盘缓存（`.llm_cache/`）。同一 prompt 第二次直接读缓存，
   离线也能重跑出完全一样的 PDF。`--no-cache` 可强制刷新。
3. **优雅降级**：没有 API Key 时不报错，返回 None，流水线自动退回纯 SymPy 路径，
   并在报告里标注哪些题是「未配置 LLM 而未求解」。
4. **结构化输出**：要求模型返回 JSON（steps / answer_latex / confidence / needs），
   解析失败会做一次修复性重试，再失败则把原始文本作为答案兜底。

用法（命令行自检）:
    python llm_engine.py --check
    python llm_engine.py --ask "求 lim_{x->0} sin(3x)/x"
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ─────────────────────────────────────────────────────────────
# Provider 注册表
# ─────────────────────────────────────────────────────────────

@dataclass
class ProviderSpec:
    name: str
    base_url: str
    default_model: str
    env_keys: tuple
    label: str = ""


PROVIDERS: dict[str, ProviderSpec] = {
    "deepseek": ProviderSpec(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        env_keys=("DEEPSEEK_API_KEY", "LLM_API_KEY"),
        label="DeepSeek (深度求索)",
    ),
    "qwen": ProviderSpec(
        name="qwen",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-plus",
        env_keys=("DASHSCOPE_API_KEY", "QWEN_API_KEY", "LLM_API_KEY"),
        label="Qwen (通义千问)",
    ),
    "kimi": ProviderSpec(
        name="kimi",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
        env_keys=("MOONSHOT_API_KEY", "KIMI_API_KEY", "LLM_API_KEY"),
        label="Kimi (月之暗面)",
    ),
    "openai-compatible": ProviderSpec(
        name="openai-compatible",
        base_url=os.environ.get("LLM_BASE_URL", ""),
        default_model=os.environ.get("LLM_MODEL", "gpt-3.5-turbo"),
        env_keys=("LLM_API_KEY",),
        label="任意 OpenAI 兼容端点",
    ),
}

# provider 探测优先级（有 key 的第一个胜出）
DETECT_ORDER = ("deepseek", "qwen", "kimi", "openai-compatible")


# ─────────────────────────────────────────────────────────────
# 提示词（Prompt）—— 这是 C4C 里最关键的「迁移资产」
# ─────────────────────────────────────────────────────────────
# 从 Claude 版本迁移到国产模型时踩的坑（见 ai-log）：
#   1. Claude 习惯直接给答案；国产模型若不强制 JSON，会夹带大量寒暄和 markdown 围栏。
#   2. 中文题干下，模型倾向用中文叙述、英文公式混排 → 必须显式要求 LaTeX 且用 $...$。
#   3. 「不要用 \frac 以外的花哨宏」这条必须写死，否则报告里会出现渲染不了的自定义命令。

SYSTEM_PROMPT_ZH = """你是一位严谨的大学理工科助教，负责批改和解答作业。

硬性规则：
1. 只输出一个 JSON 对象，不要 markdown 围栏，不要任何解释性的前后缀。
2. 数学表达式一律用 LaTeX，行内公式用 $...$，独立公式用 $$...$$。
3. 只用标准 LaTeX 数学宏（frac/sqrt/sum/int/lim/begin{pmatrix} 等），
   禁止 \\newcommand、\\def 或自定义宏。
4. 推导步骤要一步一行，每行是一个可独立核对的中文/公式混合句子。
5. 如果题目信息不足（缺条件、缺数值、表述有歧义），不要硬猜：
   把 "confidence" 设为 0.0~0.3，并在 "needs" 里写清缺什么。
6. 如果这题超出了你的能力，把 "solved" 设为 false，不要编造答案。

输出 JSON 的字段：
{
  "solved": true/false,
  "subject": "微积分/线性代数/微分方程/大学物理/概率统计/其他",
  "steps": ["第一步...", "第二步..."],
  "answer_latex": "最终答案的 LaTeX（行内公式，不含 $）",
  "confidence": 0.0~1.0,
  "needs": "如果需要补充信息，在这里说明；否则空字符串"
}
"""

SYSTEM_PROMPT_EN = """You are a rigorous university STEM teaching assistant who solves homework.

Hard rules:
1. Output exactly one JSON object. No markdown fences, no prose before or after.
2. All math must be LaTeX: inline $...$, display $$...$$.
3. Use only standard LaTeX math macros. Never use \\newcommand, \\def or custom macros.
4. Each derivation step is one line, independently checkable.
5. If the problem is under-specified or ambiguous, do NOT guess: set "confidence" to 0.0-0.3
   and state what is missing in "needs".
6. If you cannot solve it, set "solved" to false rather than inventing an answer.

JSON schema:
{
  "solved": true/false,
  "subject": "string",
  "steps": ["step 1", "step 2"],
  "answer_latex": "final answer as LaTeX (inline, no $ signs)",
  "confidence": 0.0-1.0,
  "needs": "missing info, or empty string"
}
"""


def _looks_chinese(text: str) -> bool:
    return bool(re.search(r"[一-鿿]", text or ""))


def build_solve_prompt(problem: dict) -> str:
    """把一道题渲染成给模型的用户消息。

    ⚠️ 这里是迁移过程中最贵的一课（见 ai-log B5/迭代 4）：
    PDF 拆出来的小问常常只有半句话——
        (b) A normal to your answer in 2a is __________?
        (b) All 3x3 matrices whose 9 entries add to 1.
    单独把这一行丢给模型，它只能拒绝回答（因为真的缺信息）。
    所以必须把**大题原文**和**兄弟小问**一起带上，让模型看到上下文。
    加固前后的求解率对比见 `verify.py` 生成的报告（迭代 4 vs 迭代 3）。
    """
    text = problem.get("text", "")
    subs = problem.get("sub_problems") or []
    lines = [f"课程/科目提示: {problem.get('subject_hint') or problem.get('type') or '未指定'}"]

    parent = (problem.get("parent_text") or "").strip()
    if parent and parent != text.strip():
        lines.append("【这道题所属的大题原文】")
        lines.append(parent)
        lines.append("（上面的小问是这道大题的一部分，务必结合大题的要求作答。"
                     "如果大题要求「回答 yes/no 并说明」，就先用 yes 或 no 开头。）")

    siblings = problem.get("sibling_texts") or []
    if siblings:
        lines.append("\n【同一大题下的其他小问（供理解上下文）】")
        for lbl, stxt in siblings:
            lines.append(f"  ({lbl}) {stxt}")

    lines.append(f"\n【需要你解答的这一问】\n{text.strip()}")
    if subs:
        lines.append("它包含的子问:")
        for s in subs:
            lines.append(f"  ({s.get('label', '?')}) {s.get('text', '').strip()}")
    if problem.get("math_exprs"):
        lines.append("已解析出的数学表达式（供参考，可能有误）: " + "; ".join(problem["math_exprs"]))
    lines.append("\n请解答。只返回 JSON。")
    return "\n".join(lines)


def build_verify_prompt(problem: dict, candidate_answer: str, candidate_steps: list) -> str:
    """让模型交叉复核一个候选答案（用于 LLM 自检 / SymPy 结果复核）。"""
    steps_txt = "\n".join(f"{i+1}. {s}" for i, s in enumerate(candidate_steps or []))
    return (
        f"题目:\n{problem.get('text', '').strip()}\n\n"
        f"候选答案: {candidate_answer}\n\n"
        f"候选推导:\n{steps_txt or '(无)'}\n\n"
        "请独立地重新计算一遍，然后判断候选答案是否正确。只返回 JSON：\n"
        '{"verdict": "correct"|"incorrect"|"uncertain", '
        '"corrected_answer_latex": "如果错了，给出正确答", '
        '"reason": "一句话理由", "confidence": 0.0-1.0}'
    )


# ─────────────────────────────────────────────────────────────
# 响应缓存（可复现性的关键）
# ─────────────────────────────────────────────────────────────

class ResponseCache:
    """把 (provider, model, prompt) 的响应存成磁盘文件。

    为什么必须缓存：C4C 要求「结果可复现」。LLM 是随机的，
    同一份作业今天跑和明天跑会得到不同文字。缓存让第二次之后完全一致，
    也让没有 API Key 的评审者能直接看到当时的真实响应。
    """

    def __init__(self, root: Optional[Path] = None, enabled: bool = True):
        if root is None:
            root = Path(__file__).resolve().parent.parent / ".llm_cache"
        self.root = Path(root)
        self.enabled = enabled
        self.hits = 0
        self.misses = 0
        if enabled:
            self.root.mkdir(parents=True, exist_ok=True)

    def _key(self, provider: str, model: str, prompt: str, system: str) -> str:
        h = hashlib.sha256()
        # 顺序必须保持 (provider, model, prompt, system)，改了会让已有缓存全部失效
        for part in (provider, model, prompt, system):
            h.update((part or "").encode("utf-8"))  # provider 在离线模式下是 None
            h.update(b"\x00")
        return h.hexdigest()[:24]

    def get(self, provider: str, model: str, prompt: str, system: str):
        if not self.enabled:
            return None
        p = self.root / f"{self._key(provider, model, prompt, system)}.json"
        if p.exists():
            try:
                self.hits += 1
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def put(self, provider: str, model: str, prompt: str, system: str, payload: dict):
        if not self.enabled:
            return
        self.misses += 1
        p = self.root / f"{self._key(provider, model, prompt, system)}.json"
        try:
            p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# JSON 抽取（国产模型最常见的失败模式就是多写了一段话）
# ─────────────────────────────────────────────────────────────

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Optional[dict]:
    """从模型回复里尽力抠出一个 JSON 对象。

    依次尝试：直接 parse → 去 markdown 围栏 → 取第一个平衡的 {...} 块。
    """
    if not text:
        return None
    text = text.strip()

    for candidate in (text,):
        try:
            obj = json.loads(candidate)
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass

    m = _JSON_FENCE.search(text)
    if m:
        try:
            obj = json.loads(m.group(1).strip())
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 扫描第一个平衡花括号块（跳过字符串里的花括号）
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


# ─────────────────────────────────────────────────────────────
# 客户端
# ─────────────────────────────────────────────────────────────

class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    ok: bool
    raw: str = ""
    data: Optional[dict] = None
    provider: str = ""
    model: str = ""
    cached: bool = False
    error: str = ""
    elapsed: float = 0.0
    usage: dict = field(default_factory=dict)


class LLMEngine:
    """国产大模型客户端。默认自动探测可用的 provider。"""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 180,
        max_retries: int = 2,
        cache: Optional[ResponseCache] = None,
        temperature: float = 0.0,
        enabled: bool = True,
        verbose: bool = False,
    ):
        self.verbose = verbose
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature
        self.cache = cache if cache is not None else ResponseCache(enabled=True)
        self.enabled = enabled

        self.provider, self.api_key, spec = self._resolve(provider, api_key)
        self.spec = spec
        self.base_url = (base_url or (spec.base_url if spec else "") or "").rstrip("/")
        self.model = model or (spec.default_model if spec else "unknown")
        self.requests_made = 0

    # ── provider / key 探测 ──────────────────────────────
    @staticmethod
    def _resolve(provider: Optional[str], api_key: Optional[str]):
        if provider:
            spec = PROVIDERS.get(provider)
            if spec is None:
                raise LLMError(f"未知 provider: {provider}（可选: {', '.join(PROVIDERS)}）")
            if api_key is None:
                for k in spec.env_keys:
                    v = os.environ.get(k)
                    if v:
                        api_key = v
                        break
            return provider, api_key, spec

        for name in DETECT_ORDER:
            spec = PROVIDERS[name]
            for k in spec.env_keys:
                v = os.environ.get(k)
                if v:
                    return name, v, spec
        return None, None, None

    def _cache_populated(self) -> bool:
        try:
            return self.cache.enabled and any(self.cache.root.glob("*.json"))
        except Exception:
            return False

    def _cache_pairs(self) -> list:
        """扫缓存目录，收集当初真正用过 (provider, model) 组合。只扫一次。"""
        if getattr(self, "_cache_pairs_cache", None) is not None:
            return self._cache_pairs_cache
        pairs = []
        try:
            for f in self.cache.root.glob("*.json"):
                try:
                    d = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                p, m = d.get("provider"), d.get("model")
                if p and m and (p, m) not in pairs:
                    pairs.append((p, m))
        except Exception:
            pass
        self._cache_pairs_cache = pairs
        return pairs

    def available(self) -> bool:
        """能不能干活。

        ⚠️ 这里必须把「缓存里有历史响应」也算作可用（见 ai-log B13）：
        评审者手上多半没有 API Key，但他应该能复现出我们当时生成的那份 PDF。
        只要缓存命中就不需要联网，也不需要 Key。
        """
        if not self.enabled:
            return False
        if self.api_key and self.base_url:
            return True
        return self._cache_populated()

    @property
    def offline(self) -> bool:
        """没有 Key，只能吃缓存。"""
        return not (self.api_key and self.base_url)

    def describe(self) -> str:
        if not self.available():
            return "LLM 未启用（未检测到 API Key，且响应缓存为空）"
        if self.offline:
            return (f"{self.spec.label if self.spec else self.provider} / {self.model}"
                    f"（离线模式：只读响应缓存，{len(list(self.cache.root.glob('*.json')))} 条）")
        return f"{self.spec.label if self.spec else self.provider} / {self.model}"

    # ── HTTP ────────────────────────────────────────────
    def _post(self, payload: dict) -> dict:
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def chat(self, prompt: str, system: Optional[str] = None, max_tokens: int = 2048) -> LLMResult:
        """发一轮对话，返回解析好的结构化结果。"""
        if system is None:
            system = SYSTEM_PROMPT_ZH if _looks_chinese(prompt) else SYSTEM_PROMPT_EN

        # 缓存优先：命中就完全不碰网络，也不需要 API Key（离线复现的关键）
        cached = self.cache.get(self.provider, self.model, prompt, system)
        if cached is None and self.provider is None:
            # 离线时不知道当初用的是哪个 provider/model，逐个试缓存里出现过的组合
            for prov, mdl in self._cache_pairs():
                cached = self.cache.get(prov, mdl, prompt, system)
                if cached is not None:
                    break
        if cached is not None:
            # provider/model/usage 一律从缓存记录里取，保证在线跑和离线复跑的
            # 解答 JSON 完全一致（连 token 用量都对得上）
            return LLMResult(
                ok=True, raw=cached.get("raw", ""), data=cached.get("data"),
                provider=cached.get("provider") or self.provider or "",
                model=cached.get("model") or self.model,
                usage=cached.get("usage", {}) or {},
                cached=True,
            )

        if not self.available():
            return LLMResult(ok=False, error="no API key and cache miss",
                             provider=self.provider or "", model=self.model)
        if self.offline:
            return LLMResult(ok=False, error="offline (cache-only) and cache miss",
                             provider=self.provider or "", model=self.model)

        last_err = ""
        for attempt in range(self.max_retries + 1):
            t0 = time.time()
            try:
                resp = self._post({
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": self.temperature,
                    "max_tokens": max_tokens,
                    "stream": False,
                })
                self.requests_made += 1
                raw = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
                data = extract_json(raw)
                payload = {"raw": raw, "data": data, "model": self.model,
                           "provider": self.provider, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "usage": resp.get("usage", {})}
                self.cache.put(self.provider, self.model, prompt, system, payload)
                return LLMResult(ok=True, raw=raw, data=data, provider=self.provider,
                                 model=self.model, elapsed=time.time() - t0,
                                 usage=resp.get("usage", {}))
            except urllib.error.HTTPError as e:
                detail = ""
                try:
                    detail = e.read().decode("utf-8", "ignore")[:300]
                except Exception:
                    pass
                last_err = f"HTTP {e.code}: {detail}"
                if e.code in (429, 500, 502, 503, 504):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                break  # 4xx（鉴权/参数错）重试没意义
            except Exception as e:  # noqa: BLE001 —— 网络层什么都可能抛
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(1.0 * (attempt + 1))

        return LLMResult(ok=False, error=last_err, provider=self.provider or "", model=self.model)

    # ── 高层 API ────────────────────────────────────────
    def solve(self, problem: dict, max_tokens: int = 2048) -> LLMResult:
        """解一道题。"""
        return self.chat(build_solve_prompt(problem), max_tokens=max_tokens)

    def verify(self, problem: dict, answer: str, steps: list, max_tokens: int = 900) -> Optional[dict]:
        """请模型独立复核一个候选答案。返回 dict 或 None。"""
        if not self.available():
            return None
        res = self.chat(build_verify_prompt(problem, answer, steps), max_tokens=max_tokens)
        return res.data if res.ok else None


# ─────────────────────────────────────────────────────────────
# CLI 自检
# ─────────────────────────────────────────────────────────────

def main(argv=None):
    import argparse

    ap = argparse.ArgumentParser(description="国产大模型引擎自检 / 单题试跑")
    ap.add_argument("--provider", default=None, help=f"可选: {', '.join(PROVIDERS)}")
    ap.add_argument("--model", default=None)
    ap.add_argument("--check", action="store_true", help="只检测连通性与鉴权")
    ap.add_argument("--ask", default=None, help="直接问一道题")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args(argv)

    eng = LLMEngine(provider=args.provider, model=args.model,
                    cache=ResponseCache(enabled=not args.no_cache), verbose=True)

    print(f"provider : {eng.provider}")
    print(f"model    : {eng.model}")
    print(f"base_url : {eng.base_url or '(未设置)'}")
    print(f"api_key  : {'已配置 (***' + eng.api_key[-4:] + ')' if eng.api_key else '未配置'}")

    if not eng.available():
        print("\n⚠️  未检测到任何国产模型 API Key。")
        print("   设置其一即可：DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / MOONSHOT_API_KEY")
        print("   流水线在无 Key 时会自动退回纯 SymPy 路径，不会崩。")
        return 0

    prompt = args.ask or "求极限 lim_{x->0} sin(3x)/x。只返回 JSON。"
    res = eng.solve({"text": prompt, "sub_problems": []})
    print(f"\ncached   : {res.cached}")
    print(f"elapsed  : {res.elapsed:.2f}s")
    print(f"ok       : {res.ok}  {res.error}")
    if res.data:
        print("data     : " + json.dumps(res.data, ensure_ascii=False)[:600])
    else:
        print("raw      : " + res.raw[:600])
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
