/**
 * Hexastack Interactive In-Browser Sandbox Terminal Widget
 * Supports instant client-side CLI simulation (<1ms) and optional live Pyodide WebAssembly runtime.
 */

(function () {
  let pyodideInstance = null;
  let isPyodideLoading = false;

  function initTerminal(container) {
    const screen = container.querySelector(".hexastack-terminal-screen");
    const input = container.querySelector(".hexastack-terminal-input");
    const runBtn = container.querySelector(".hexastack-terminal-run-btn");
    const pyodideBtn = container.querySelector(".hexastack-terminal-pyodide-btn");
    const badge = container.querySelector(".hexastack-terminal-engine-badge");
    const chips = container.querySelectorAll(".hexastack-terminal-chip");

    const commandHistory = [];
    let historyIndex = -1;

    function appendLine(text, type = "output") {
      const line = document.createElement("div");
      line.className = `hexastack-terminal-line ${type}`;
      line.textContent = text;
      screen.appendChild(line);
      screen.scrollTop = screen.scrollHeight;
      return line;
    }

    function clearScreen() {
      screen.innerHTML = "";
      appendLine("Hexastack Interactive Sandbox [Instant Simulation & WASM Edge Profile]", "info");
      appendLine("Type 'help' or click any preset chip above to execute.", "info");
      appendLine("----------------------------------------------------------------", "info");
    }

    async function executeCommand(rawCommand) {
      const cmd = rawCommand.trim();
      if (!cmd) return;

      commandHistory.push(cmd);
      historyIndex = commandHistory.length;

      appendLine(`hexastack > ${cmd}`, "command");
      input.value = "";

      const lower = cmd.toLowerCase();

      if (lower === "clear" || lower === "cls") {
        clearScreen();
        return;
      }

      if (lower === "help") {
        appendLine("Available In-Browser Commands:", "info");
        appendLine("  hexastack --help                    Show Hexastack CLI help and subcommands", "output");
        appendLine("  hexastack new <service-name>        Simulate scaffolding a hexagonal microservice", "output");
        appendLine("  hexastack edge status               Inspect ADR-016 WASM & Embedded Edge Profile", "output");
        appendLine("  dispatch PostTransaction ...        Post a double-entry financial transaction", "output");
        appendLine("  python -c '<code>'                  Execute Python via live Pyodide (if loaded)", "output");
        appendLine("  clear                               Clear terminal screen", "output");
        return;
      }

      if (lower === "hexastack --help") {
        appendLine("Usage: hexastack [OPTIONS] COMMAND [ARGS]...", "output");
        appendLine("\nHexastack Enterprise Hexagonal Architecture Framework CLI.", "output");
        appendLine("\nCommands:", "output");
        appendLine("  new       Scaffold a new production microservice from copier templates.", "output");
        appendLine("  add       Add a CQRS Command, Query, Repository, or Event Handler.", "output");
        appendLine("  dispatch  Directly dispatch a CQRS Command or Query across protocols.", "output");
        appendLine("  edge      Inspect or configure the ADR-016 WASM/MicroPython edge runtime.", "output");
        appendLine("  devtools  Launch the local NiceGUI devtools inspection console.", "output");
        appendLine("\nOptions:", "output");
        appendLine("  --version  Show version and exit (v0.11.0).", "output");
        appendLine("  --help     Show this message and exit.", "output");
        return;
      }

      if (lower.startsWith("hexastack new")) {
        const parts = cmd.split(/\s+/);
        const name = parts[2] || "my-service";
        appendLine(`[+] Scaffolding hexagonal service: ${name}...`, "info");
        appendLine(`    ├── src/${name}/domain/        (pure entities, zero dependencies)`, "output");
        appendLine(`    ├── src/${name}/ports/         (abstract ABCs & repositories)`, "output");
        appendLine(`    ├── src/${name}/adapters/      (FastAPI, SQLite, gRPC, CLI)`, "output");
        appendLine(`    ├── src/${name}/infra/         (DI container, handlers, bootstrap)`, "output");
        appendLine(`    └── tests/architecture/        (import-linter boundaries suite)`, "output");
        appendLine(`[✓] Successfully scaffolded ${name} with 1:1 test parity!`, "success");
        return;
      }

      if (lower === "hexastack edge status") {
        appendLine("ADR-016 WASM & Embedded Edge Execution Profile:", "info");
        appendLine("  • Active Profile: WASM / Pyodide / MicroPython cooperative runtime", "output");
        appendLine("  • DI Container: MicroContainer (zero C-extension, <450KB footprint)", "output");
        appendLine("  • Concurrency: Cooperative Async (Event-Loop Bound)", "output");
        appendLine("  • Layer Boundary Integrity: 100% compliant with import-linter", "output");
        appendLine("  • Status: ONLINE (Execution Latency: < 0.1ms)", "success");
        return;
      }

      if (lower.startsWith("dispatch posttransaction")) {
        // Parse debit and credit
        const debitMatch = cmd.match(/--debit\s+"?([^"\s]+)"?/);
        const creditMatch = cmd.match(/--credit\s+"?([^"\s]+)"?/);

        if (!debitMatch || !creditMatch) {
          appendLine("Error: Missing required flags --debit and --credit.", "error");
          appendLine("Example: dispatch PostTransaction --debit \"Cash:500.00\" --credit \"AR:500.00\"", "warning");
          return;
        }

        const debitRaw = debitMatch[1].split(":");
        const creditRaw = creditMatch[1].split(":");

        const debitAcct = debitRaw[0];
        const debitAmt = parseFloat(debitRaw[1]);
        const creditAcct = creditRaw[0];
        const creditAmt = parseFloat(creditRaw[1]);

        if (isNaN(debitAmt) || isNaN(creditAmt)) {
          appendLine("Error: Invalid numeric amount for debit or credit.", "error");
          return;
        }

        appendLine(`[*] Dispatching PostTransactionCommand across CQRS bus...`, "info");
        appendLine(`    Debit:  ${debitAcct} -> $${debitAmt.toFixed(2)}`, "output");
        appendLine(`    Credit: ${creditAcct} -> $${creditAmt.toFixed(2)}`, "output");

        const diff = Math.abs(debitAmt - creditAmt);
        if (diff < 0.0001) {
          appendLine(`[✓] Mathematical Invariant Verified: Σ(Debits) == Σ(Credits) ($${debitAmt.toFixed(2)})`, "success");
          appendLine(`[✓] Transaction tx_${Math.random().toString(36).substring(2, 8)} committed successfully to ledger.`, "success");
          appendLine(`    Execution Time: 0.18ms | Law of Conservation of Money: PRESERVED`, "info");
        } else {
          appendLine(`[✗] Domain Invariant Violation!`, "error");
          appendLine(`    UnbalancedTransactionError: Debits (${debitAmt.toFixed(2)}) != Credits (${creditAmt.toFixed(2)})`, "error");
          appendLine(`    Rejected at domain boundary. State modification aborted.`, "warning");
        }
        return;
      }

      // Pyodide fallback or command execution
      if (pyodideInstance && (cmd.startsWith("python") || cmd.startsWith("print") || cmd.includes("="))) {
        let code = cmd;
        if (cmd.startsWith("python -c")) {
          const match = cmd.match(/python -c ["'](.*)["']/);
          if (match) code = match[1];
        }
        try {
          appendLine(`[WASM Execution...]`, "info");
          const result = await pyodideInstance.runPythonAsync(code);
          if (result !== undefined) {
            appendLine(String(result), "success");
          }
        } catch (pyErr) {
          appendLine(String(pyErr), "error");
        }
        return;
      }

      appendLine(`Command not found: ${cmd}. Type 'help' for available commands.`, "error");
    }

    // Input handlers
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        executeCommand(input.value);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (historyIndex > 0) {
          historyIndex--;
          input.value = commandHistory[historyIndex] || "";
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (historyIndex < commandHistory.length - 1) {
          historyIndex++;
          input.value = commandHistory[historyIndex] || "";
        } else {
          historyIndex = commandHistory.length;
          input.value = "";
        }
      }
    });

    if (runBtn) {
      runBtn.addEventListener("click", () => {
        executeCommand(input.value);
      });
    }

    // Chip click handlers
    chips.forEach((chip) => {
      chip.addEventListener("click", () => {
        const cmd = chip.getAttribute("data-command");
        if (cmd) {
          input.value = cmd;
          executeCommand(cmd);
        }
      });
    });

    // Pyodide live WASM loader
    if (pyodideBtn) {
      pyodideBtn.addEventListener("click", async () => {
        if (pyodideInstance) {
          appendLine("Pyodide WASM kernel already initialized and ready.", "info");
          return;
        }
        if (isPyodideLoading) {
          appendLine("Pyodide WASM kernel is currently loading...", "info");
          return;
        }

        isPyodideLoading = true;
        pyodideBtn.textContent = "⌛ Loading WASM Kernel...";
        appendLine("Downloading and initializing Pyodide WebAssembly runtime...", "info");

        try {
          if (!window.loadPyodide) {
            await new Promise((resolve, reject) => {
              const script = document.createElement("script");
              script.src = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
              script.onload = resolve;
              script.onerror = () => reject(new Error("Failed to load Pyodide CDN script."));
              document.head.appendChild(script);
            });
          }

          pyodideInstance = await window.loadPyodide({
            stdout: (text) => appendLine(text, "output"),
            stderr: (text) => appendLine(text, "error"),
          });

          isPyodideLoading = false;
          pyodideBtn.textContent = "✓ Pyodide WASM Active";
          pyodideBtn.classList.remove("hexastack-terminal-pyodide-btn");
          pyodideBtn.style.backgroundColor = "#059669";
          badge.textContent = "Pyodide WASM Live (Python 3.12)";
          badge.style.backgroundColor = "#059669";

          appendLine("[✓] Pyodide Python 3.12 WebAssembly kernel initialized!", "success");
          appendLine("    You can now run arbitrary Python: python -c \"import math; print(math.sqrt(144))\"", "info");
        } catch (err) {
          isPyodideLoading = false;
          pyodideBtn.textContent = "⚠️ WASM Load Failed";
          appendLine(`[!] Failed to initialize Pyodide WASM: ${err.message}`, "error");
          appendLine("    Client-side instant simulation remains active.", "warning");
        }
      });
    }

    clearScreen();
  }

  // Initialize on DOM load
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".hexastack-terminal-container").forEach(initTerminal);
  });
})();
