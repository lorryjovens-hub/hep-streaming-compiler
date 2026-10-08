/* HEP 浏览器运行时 —— RenderOp 流的增量执行器（零依赖，~60 行）。
 *
 * 宿主无关契约的浏览器侧实现：
 *   window.HEP.attach(container)          绑定容器
 *   window.HEP.apply(ops)                 增量应用 RenderOps（逐帧生长）
 *   window.HEP.onInput(cb)                收集交互件输入（bind 字段）
 *
 * 与 Hana 卡片的关系：卡片宿主可直接消费同一 op 流
 * （card:request/response），本运行时是普通浏览器/Showcard 的挂载器。
 */
(function () {
  const state = { root: null, byId: new Map(), inputs: new Map() };
  const ECHO = "data-hep-echo";

  function el(id) { return state.byId.get(id) || null; }

  function attach(container) {
    state.root = typeof container === "string"
      ? document.querySelector(container) : container;
    state.root.id = state.root.id || "root";
    state.byId.set("root", state.root);
    return state.root;
  }

  function apply(ops) {
    for (const op of ops) {
      if (op.op === "append") {
        const host = el(op.target) || state.root;
        const tpl = document.createElement("template");
        tpl.innerHTML = op.html.trim();
        const node = tpl.content.firstElementChild;
        if (!node) continue;
        node.dataset.hepId = op.id;
        host.appendChild(node);
        state.byId.set(op.id, node);
        bindInputs(node);
      } else if (op.op === "patch") {
        const node = el(op.id);
        if (!node) continue;
        for (const [k, v] of Object.entries(op.props || {})) {
          if (k === "value") {
            const inp = node.querySelector("input");
            if (inp) { inp.value = v; state.inputs.set(inp.dataset.hepInput, v); }
            const echo = node.querySelector(`[${ECHO}]`);
            if (echo) echo.textContent = v;
          } else if (k === "text") {
            node.textContent = v;
          }
        }
      } else if (op.op === "remove") {
        const node = el(op.id);
        if (node) node.remove();
        state.byId.delete(op.id);
      }
    }
    return ops.length;
  }

  function bindInputs(scope) {
    scope.querySelectorAll("[data-hep-input]").forEach((inp) => {
      const key = inp.dataset.hepInput;
      state.inputs.set(key, inp.value);
      inp.addEventListener("input", () => {
        state.inputs.set(key, inp.value);
        const echo = scope.querySelector(`[${ECHO}="${key}"]`)
          || state.root.querySelector(`[${ECHO}="${key}"]`);
        if (echo) echo.textContent = inp.value;
      });
    });
    scope.querySelectorAll("[data-hep-action]").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (window.HEP.onAction) window.HEP.onAction(btn.dataset.hepAction, state.inputs);
      });
    });
  }

  window.HEP = {
    attach, apply,
    onAction: null,
    onInput(cb) { state.root.addEventListener("input", () => cb(state.inputs)); },
    get inputs() { return Object.fromEntries(state.inputs); },
  };
})();
