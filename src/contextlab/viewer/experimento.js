// Página Experimento do site: gráficos e tabelas do experimento do TCC.
// Os dados vêm de DATA.experiment (gerado no build a partir de experimento-tcc/); todo texto entra por textContent.
(function () {
  "use strict";
  const EXP = DATA.experiment;
  if (!DATA.site || !EXP) return;
  const C = ["L", "R", "A"], NAME = {L: "Local", R: "Recuperado", A: "Autônomo"};
  const NS = "http://www.w3.org/2000/svg";
  const att = EXP.attempts;
  const nf = (v, d = 0) => v.toLocaleString("pt-BR", {minimumFractionDigits: d, maximumFractionDigits: d});
  const mil = v => v >= 1e6 ? nf(v / 1e6, 1) + " mi" : v >= 1000 ? nf(v / 1000, 1) + " mil" : nf(v);
  const usd = (v, d = 3) => "US$ " + nf(v, d);
  const pct = v => nf(v * 100) + "%";
  const mean = xs => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  const num = xs => xs.filter(x => typeof x === "number");
  const by = c => att.filter(a => a.condition === c);
  const color = c => `var(--ch-${c})`;

  function s(tag, attrs, parent) {
    const node = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    if (parent) parent.append(node);
    return node;
  }
  function txt(parent, x, y, value, attrs) { const t = s("text", {x, y, ...attrs}, parent); t.textContent = value; return t; }

  // ---- Dica (tooltip): valor em destaque, rótulo depois; também no foco do teclado.
  const tip = el("div", {class: "exp-tip", hidden: true});
  document.body.append(tip);
  function show(evt, lines, key) {
    tip.replaceChildren(...lines.map((line, i) => i === 0
      ? el("strong", {}, key ? el("i", {class: "key", style: `--c: ${color(key)}`}) : null, line) : el("span", {text: line})));
    tip.hidden = false;
    const r = evt.clientX !== undefined && evt.clientX !== 0 ? {x: evt.clientX, y: evt.clientY} : (() => { const b = evt.target.getBoundingClientRect(); return {x: b.right, y: b.top}; })();
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.min(r.x + 14, innerWidth - w - 8) + "px";
    tip.style.top = Math.max(8, Math.min(r.y + 14, innerHeight - h - 8)) + "px";
  }
  const hide = () => { tip.hidden = true; };
  function hover(node, lines, key) {
    node.setAttribute("tabindex", "0");
    node.setAttribute("aria-label", lines.join(", "));
    node.addEventListener("pointermove", e => show(e, lines, key));
    node.addEventListener("pointerleave", hide);
    node.addEventListener("focus", e => show(e, lines, key));
    node.addEventListener("blur", hide);
  }
  const table = (head, rows, numCols = []) => el("table", {},
    el("thead", {}, el("tr", {}, head.map((h, i) => el("th", {class: numCols.includes(i) ? "num" : "", text: h})))),
    el("tbody", {}, rows.map(r => el("tr", {}, r.map((v, i) => el("td", {class: numCols.includes(i) ? "num" : "", text: v}))))));

  // ---- Dados derivados
  const targets = EXP.projects.flatMap(p => p.targets.map(t => ({...t, project: p.name, projectId: p.id})));
  const short = sym => sym.split(".").slice(-2).join(".").replace(/^(budgets|group_entries|file|version_config|serialization|models|parser|variables|main|cpf|isbn|nif)\./, "");
  const label = t => ({br_cpf_validate: "br.cpf.validate", isbn_validate: "isbn.validate", es_nif_validate: "es.nif.validate",
                       version_config_parse: "VersionConfig.parse", get_version_from_tag: "get_version_from_tag"}[t.id] || short(t.symbol));
  const stats = {};
  for (const c of C) {
    const xs = by(c), ok = xs.filter(a => a.approved);
    const tok = num(xs.map(a => a.input_tokens)), cost = num(xs.map(a => a.cost));
    stats[c] = {n: xs.length, ok: ok.length, rate: ok.length / xs.length, tok, cost,
      missing: xs.filter(a => a.input_tokens === null).length,
      perOk: {tokens: tok.reduce((a, b) => a + b, 0) / ok.length, cost: cost.reduce((a, b) => a + b, 0) / ok.length}};
  }
  const okAll = att.filter(a => a.approved);

  // ---- Cabeçalho e indicadores
  const cfg = EXP.config;
  document.getElementById("exp-tags").replaceChildren(
    ...[cfg.model, cfg.client, "ContextLab " + cfg.contextlab].map(t => el("span", {class: "tag tag-mono", text: t})));
  const totalCost = num(att.map(a => a.cost)).reduce((a, b) => a + b, 0);
  const missing = att.filter(a => a.input_tokens === null).length;
  const kpi = (label, value, sub) => el("div", {class: "stat"}, el("span", {class: "stat-label", text: label}), el("strong", {text: value}),
    el("div", {class: "split"}, sub));
  const splitBy = f => C.map(c => el("span", {}, el("b", {text: c, style: `color: ${color(c)}`}), f(c)));
  document.getElementById("exp-kpis").replaceChildren(
    kpi("Tentativas", nf(att.length), splitBy(c => nf(stats[c].n))),
    kpi("Suítes aprovadas", `${okAll.length} (${pct(okAll.length / att.length)})`, splitBy(c => `${stats[c].ok}/${stats[c].n}`)),
    kpi("Cobertura e detecção nas aprovadas", pct(mean(okAll.map(a => a.line_rate))),
        [el("span", {text: `${okAll.reduce((n, a) => n + a.defects_detected, 0)} de ${okAll.reduce((n, a) => n + a.defects_total, 0)} defeitos detectados`})]),
    kpi("Tokens de entrada", mil(num(att.map(a => a.input_tokens)).reduce((a, b) => a + b, 0)), splitBy(c => mil(stats[c].tok.reduce((a, b) => a + b, 0)))),
    kpi("Custo estimado (preço de API)", "≥ " + usd(totalCost, 2), splitBy(c => usd(stats[c].cost.reduce((a, b) => a + b, 0), 2))));

  // ---- 1. Aprovação por estratégia: barras horizontais, valor na ponta
  function drawApproval() {
    const box = document.getElementById("exp-approval"), W = Math.max(300, box.clientWidth - 32), row = 46, left = 96, right = 92;
    const svg = s("svg", {viewBox: `0 0 ${W} ${row * 3 + 26}`, role: "img", "aria-label": "Taxa de aprovação por estratégia"});
    const x = v => left + v * (W - left - right);
    for (const t of [0, .25, .5, .75, 1]) {
      s("line", {class: "grid", x1: x(t), x2: x(t), y1: 0, y2: row * 3}, svg);
      txt(svg, x(t), row * 3 + 18, pct(t), {"text-anchor": "middle"});
    }
    C.forEach((c, i) => {
      const y = i * row + (row - 22) / 2, st = stats[c], w = x(st.rate) - left;
      txt(svg, 0, y + 15, `${c} · ${NAME[c]}`, {class: "ink"});
      const g = s("g", {class: "mark"}, svg);
      s("path", {d: `M${left},${y} h${w - 4} a4,4 0 0 1 4,4 v14 a4,4 0 0 1 -4,4 h${-(w - 4)} z`, fill: color(c)}, g);
      s("rect", {class: "hit", x: left, y: y - 10, width: W - left, height: 42}, g);
      hover(g, [`${pct(st.rate)} aprovadas`, `${NAME[c]}: ${st.ok} de ${st.n} tentativas`], c);
      txt(svg, x(st.rate) + 8, y + 15, `${pct(st.rate)} · ${st.ok}/${st.n}`, {class: "ink"});
    });
    box.replaceChildren(svg);
  }
  document.getElementById("exp-approval-note").textContent =
    "A aprovação exige passar no código original, executar a função e ser aceita na revisão humana. Toda suíte aprovada cobriu 100% da função e detectou todos os defeitos controlados dela: as estratégias diferiram só aqui.";

  // ---- 2. Mapa de calor: aprovadas por função (escala sequencial de uma cor, 0 a 3)
  (function drawHeat() {
    const heat = document.getElementById("exp-heat"), nodes = [el("div", {}), ...C.map(c => el("div", {class: "h", text: c}))];
    let project = null;
    for (const t of targets) {
      if (t.project !== project) { project = t.project; nodes.push(el("div", {class: "proj", text: project})); }
      nodes.push(el("div", {class: "fn", text: label(t), title: t.symbol}));
      for (const c of C) {
        const xs = att.filter(a => a.target === t.id && a.condition === c), ok = xs.filter(a => a.approved).length;
        const causes = [...new Set(xs.filter(a => !a.approved).map(a => a.outcome))];
        const cell = el("div", {class: `hc v${ok}`, role: "cell", text: String(ok)});
        hover(cell, [`${ok} de ${xs.length} aprovadas`, `${label(t)} · ${NAME[c]}`, ...(causes.length ? ["Falhas: " + causes.join(", ")] : [])], c);
        nodes.push(cell);
      }
    }
    heat.replaceChildren(...nodes);
    document.getElementById("exp-heat-scale").replaceChildren(el("span", {text: "0"}),
      ...[0, 1, 2, 3].map(v => el("b", {class: `v${v}`, style: v === 0 ? "background: var(--panel-2)" : v === 3 ? "background: var(--seq)" :
        `background: color-mix(in srgb, var(--seq) ${v === 1 ? 30 : 62}%, var(--panel))`})), el("span", {text: "3 aprovadas"}));
  })();

  // ---- 3. Tokens por tentativa: um ponto por tentativa, anel para não aprovada, traço na média
  function drawTokens() {
    const box = document.getElementById("exp-tokens"), W = Math.max(320, box.clientWidth - 32), row = 70, left = 96, right = 16;
    const all = num(att.map(a => a.input_tokens)), max = Math.ceil(Math.max(...all) / 50000) * 50000;
    const x = v => left + v / max * (W - left - right);
    const svg = s("svg", {viewBox: `0 0 ${W} ${row * 3 + 26}`, role: "img", "aria-label": "Tokens de entrada de cada tentativa, por estratégia"});
    for (let t = 0; t <= max; t += 50000) {
      s("line", {class: "grid", x1: x(t), x2: x(t), y1: 0, y2: row * 3}, svg);
      txt(svg, x(t), row * 3 + 18, t ? nf(t / 1000) + " mil" : "0", {"text-anchor": "middle"});
    }
    C.forEach((c, i) => {
      const yc = i * row + row / 2;
      txt(svg, 0, yc + 4, `${c} · ${NAME[c]}`, {class: "ink"});
      by(c).filter(a => a.input_tokens !== null).sort((a, b) => a.order - b.order).forEach((a, k) => {
        const jitter = ((k * 37) % 9 - 4) * 2.4, g = s("g", {class: "mark"}, svg);
        s("circle", {cx: x(a.input_tokens), cy: yc + jitter, r: 12, class: "hit"}, g);
        s("circle", {cx: x(a.input_tokens), cy: yc + jitter, r: 4.5, fill: a.approved ? color(c) : "var(--panel)",
          stroke: a.approved ? "var(--panel)" : color(c), "stroke-width": 2}, g);
        hover(g, [`${nf(a.input_tokens)} tokens`, `${label(targets.find(t => t.id === a.target))} · ${NAME[c]} · repetição ${a.repetition}`,
          a.approved ? "aprovada" : a.outcome], c);
      });
      const m = mean(stats[c].tok);
      s("line", {x1: x(m), x2: x(m), y1: yc - 16, y2: yc + 16, stroke: "var(--ink)", "stroke-width": 2}, svg);
      txt(svg, x(m), yc + 30, "média " + mil(m), {class: "ink", "text-anchor": "middle"});
    });
    box.replaceChildren(svg);
  }
  document.getElementById("exp-tokens-note").textContent =
    `Nas tentativas com medição, A consumiu em média ${nf(mean(stats.A.tok) / mean(stats.L.tok), 1)} vezes os tokens de entrada de L, mas ${pct(num(by("A").map(a => a.cached_input_tokens)).reduce((x, y) => x + y, 0) / stats.A.tok.reduce((x, y) => x + y, 0))} deles vieram do cache, que custa vinte vezes menos. ` +
    `${missing} tentativas de A atingiram o limite de contexto sem informar tokens e não aparecem aqui: as médias de A descrevem as demais, e as somas e razões por suíte aprovada de A são limites inferiores.`;

  // ---- 4. Esforço por suíte aprovada, por função: gráfico de pontos (Cleveland), custo ou tokens
  let mode = "cost";
  const effort = {};
  for (const t of targets) for (const c of C) {
    const xs = att.filter(a => a.target === t.id && a.condition === c), ok = xs.filter(a => a.approved).length;
    const complete = xs.every(a => a.input_tokens !== null);
    effort[t.id + c] = ok && complete ? {cost: xs.reduce((n, a) => n + a.cost, 0) / ok,
                                          tokens: xs.reduce((n, a) => n + a.input_tokens, 0) / ok, ok} : null;
  }
  function drawEffort() {
    const box = document.getElementById("exp-effort"), W = Math.max(300, box.clientWidth - 32), row = 26, narrow = W < 520, left = narrow ? 132 : 170, right = 20;
    const vals = Object.values(effort).filter(Boolean).map(v => v[mode]);
    const step = mode === "cost" ? .05 : 50000, max = Math.ceil(Math.max(...vals) / step) * step;
    const x = v => left + v / max * (W - left - right), H = row * targets.length;
    const svg = s("svg", {viewBox: `0 0 ${W} ${H + 26}`, role: "img", "aria-label": "Esforço por suíte aprovada em cada função"});
    for (let t = 0; t <= max + 1e-9; t += step) {
      s("line", {class: "grid", x1: x(t), x2: x(t), y1: 0, y2: H}, svg);
      txt(svg, x(t), H + 18, mode === "cost" ? usd(t, 2) : (t ? nf(t / 1000) + " mil" : "0"), {"text-anchor": "middle"});
    }
    targets.forEach((t, i) => {
      const yc = i * row + row / 2, pts = C.map(c => [c, effort[t.id + c]]).filter(([, v]) => v);
      txt(svg, 0, yc + 4, label(t), {class: "ink", style: `font-family: var(--mono); font-size: ${narrow ? 9.5 : 11.5}px`});
      if (pts.length > 1) {
        const xs = pts.map(([, v]) => x(v[mode]));
        s("line", {x1: Math.min(...xs), x2: Math.max(...xs), y1: yc, y2: yc, stroke: "var(--line)", "stroke-width": 2}, svg);
      }
      if (!pts.length) txt(svg, left + 4, yc + 4, narrow ? "indefinida" : "sem razão definida em nenhuma estratégia");
      for (const [c, v] of pts) {
        const g = s("g", {class: "mark"}, svg);
        s("circle", {cx: x(v[mode]), cy: yc, r: 12, class: "hit"}, g);
        s("circle", {cx: x(v[mode]), cy: yc, r: 5, fill: color(c), stroke: "var(--panel)", "stroke-width": 2}, g);
        hover(g, [mode === "cost" ? usd(v.cost) + " por suíte aprovada" : mil(v.tokens) + " tokens por suíte aprovada",
          `${label(t)} · ${NAME[c]}`, `${v.ok} de 3 aprovadas`], c);
      }
    });
    box.replaceChildren(svg);
  }
  document.getElementById("exp-effort-legend").replaceChildren(...C.map(c => el("span", {}, el("i", {style: `--c: ${color(c)}; border-radius: 50%`}), `${c} · ${NAME[c]}`)));
  document.getElementById("exp-effort-note").textContent =
    `Esforço = consumo de todas as tentativas da estratégia na função ÷ suítes aprovadas. Uma estratégia sem suíte aprovada, ou com tentativa sem contagem de tokens, fica sem ponto. ` +
    `No geral: L ${usd(stats.L.perOk.cost)}, R ${usd(stats.R.perOk.cost)} e A ${usd(stats.A.perOk.cost)} por suíte aprovada.`;
  document.getElementById("exp-effort-table").replaceChildren(table(["Função", "L custo", "R custo", "A custo", "L tokens", "R tokens", "A tokens"],
    targets.map(t => [label(t), ...C.map(c => effort[t.id + c] ? usd(effort[t.id + c].cost) : "—"), ...C.map(c => effort[t.id + c] ? mil(effort[t.id + c].tokens) : "—")]),
    [1, 2, 3, 4, 5, 6]));
  for (const b of document.querySelectorAll("#exp-effort-mode button")) b.addEventListener("click", () => {
    mode = b.dataset.m;
    for (const o of document.querySelectorAll("#exp-effort-mode button")) o.setAttribute("aria-pressed", String(o === b));
    drawEffort();
  });

  // ---- Tabelas: consumo e causas
  const avg = (c, f, d = 0) => { const v = mean(num(by(c).map(f))); return v === null ? "—" : nf(v, d); };
  document.getElementById("exp-resources").replaceChildren(table(["Medida", "L", "R", "A"], [
    ["Tokens de entrada", ...C.map(c => avg(c, a => a.input_tokens))],
    ["Entrada vinda do cache", ...C.map(c => pct(num(by(c).map(a => a.cached_input_tokens)).reduce((x, y) => x + y, 0) / stats[c].tok.reduce((x, y) => x + y, 0)))],
    ["Tokens de saída", ...C.map(c => avg(c, a => a.output_tokens))],
    ["Caracteres de contexto", ...C.map(c => avg(c, a => a.context_chars))],
    ["Consultas às ferramentas", ...C.map(c => avg(c, a => a.tool_calls, 1))],
    ["Geração (s)", ...C.map(c => avg(c, a => a.generation_seconds, 1))],
    ["Avaliação inicial (s)", ...C.map(c => avg(c, a => a.evaluation_seconds, 2))],
    ["Custo estimado por tentativa", ...C.map(c => usd(mean(stats[c].cost)))],
  ], [1, 2, 3]));
  document.getElementById("exp-resources-note").textContent = EXP.pricing
    ? `Custo em preço de API do ${cfg.model} (US$ ${nf(EXP.rates.entrada, 2)} entrada, ${nf(EXP.rates.entrada_cache, 2)} em cache e ${nf(EXP.rates.saida, 2)} saída por milhão de tokens; consulta de ${EXP.pricing.consulta.split("-").reverse().join("/")}). A coleta usou assinatura: não é a despesa efetiva.`
    : "";
  const causes = [...new Set(att.filter(a => !a.approved).map(a => a.outcome))];
  document.getElementById("exp-failures").replaceChildren(table(["Causa", "L", "R", "A"],
    [...causes.map(k => [k, ...C.map(c => String(by(c).filter(a => !a.approved && a.outcome === k).length))]),
     ["Total não aprovadas", ...C.map(c => String(stats[c].n - stats[c].ok))]], [1, 2, 3]));

  // ---- Achados e configuração
  const findings = [
    `L e A tiveram suítes aprovadas em ${stats.L.ok} das 36 tentativas cada; R, em ${stats.R.ok}. As diferenças se concentraram em três funções: find_insert_position, VersionConfig.parse e group_entries_by_account.`,
    "Onde o teste precisa construir objetos definidos fora do arquivo da função e das dependências diretas (registros do Beancount, partes de uma versão), A aprovou 4 de 6 tentativas, R 1 (usando o analisador do Beancount) e L nenhuma.",
    "Nas outras dez funções, L aprovou todas as repetições: o contexto local bastou, e A acrescentou consumo sem aumentar a aprovação.",
    `Toda suíte aprovada cobriu a função inteira e detectou todos os defeitos controlados: efeito de teto nessas duas medidas.`,
    `Por suíte aprovada, L foi a mais econômica na maioria das funções; o cache reduz a desvantagem de A em custo (${nf(mean(stats.A.tok) / mean(stats.L.tok), 1)}× os tokens, ${nf(mean(stats.A.cost) / mean(stats.L.cost), 1)}× o custo).`,
    "Três suítes de L substituíram por dublês a função que identifica as contas de um registro, ausente do pacote L; foram aprovadas e marcadas na revisão.",
  ];
  document.getElementById("exp-findings").replaceChildren(...findings.map(t => el("li", {text: t})));
  const L = cfg.limits;
  const kv = [["Modelo", `${cfg.model}, esforço de raciocínio ${cfg.reasoning_effort === "medium" ? "médio" : cfg.reasoning_effort}`],
    ["Cliente", cfg.client], ["ContextLab", cfg.contextlab], ["Projetos", EXP.projects.map(p => p.name).join(" · ")],
    ["Desenho", `12 funções × L/R/A × ${cfg.repetitions} repetições = ${att.length} tentativas, ordem sorteada com semente ${cfg.seed}`],
    ["Limites", `${nf(L.context_chars)} caracteres de contexto · ${L.tool_calls} consultas · ${L.generation_seconds} s de geração · ${L.evaluation_seconds} s de avaliação`],
    ["Avaliação", `Docker sem rede, imagem ${cfg.image.slice(0, 19)}…, uma entrega por tentativa, sem retorno de erros ao agente`],
    ["Revisão", "humana, com critérios de asserções comportamentais, alvo real, produção intacta e marcação de dublês"]];
  document.getElementById("exp-config").replaceChildren(...kv.flatMap(([k, v]) => [el("dt", {text: k}), el("dd", {text: v})]));

  // ---- Navegação: Documentação ↔ Experimento, com endereço próprio (#experimento)
  const views = {docs: document.getElementById("view-docs"), exp: document.getElementById("view-exp")};
  const buttons = {docs: document.getElementById("nav-docs"), exp: document.getElementById("nav-exp")};
  let drawn = false;
  function drawAll() { drawApproval(); drawTokens(); drawEffort(); drawn = true; }
  function go(page, push) {
    for (const k of ["docs", "exp"]) {
      views[k].hidden = k !== page;
      if (k === page) buttons[k].setAttribute("aria-current", "page"); else buttons[k].removeAttribute("aria-current");
    }
    if (page === "exp" && !drawn) drawAll();
    if (push) history.replaceState(null, "", page === "exp" ? "#experimento" : location.pathname);
    window.scrollTo(0, 0);
  }
  buttons.exp.addEventListener("click", () => go("exp", true));
  buttons.docs.addEventListener("click", () => go("docs", true));
  new ResizeObserver(() => { if (drawn && !views.exp.hidden) { drawApproval(); drawTokens(); drawEffort(); } }).observe(views.exp);
  if (location.hash === "#experimento") go("exp", false);
})();
