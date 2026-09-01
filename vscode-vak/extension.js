"use strict";
// वाक् — VS Code support.
//
// The analyser already exists and already reports code, line and message, so
// this file does not re-implement any of it: it runs the real toolchain and
// turns what it prints into editor diagnostics.
const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");
const { devanagari } = require("./translit");

let diagnostics;
let statusBar;
let typing = false;      // देवनागरी-लेखनम् — convert romanised words as they finish

/** How to invoke Vāk: the native binary if configured, else `python -m vak`. */
function toolchain(args) {
  const cfg = vscode.workspace.getConfiguration("vak");
  const exe = (cfg.get("executable") || "").trim();
  if (exe) return { cmd: exe, args };
  return { cmd: cfg.get("pythonPath") || "python", args: ["-m", "vak", ...args] };
}

/*  अर्थदोषः lines look like:
 *    दोषः [नामदोषः] path/to/file.vak:7 — अपरिभाषितम् नाम 'x' / undefined name 'x'
 *  and a सूचना is advice rather than an error.                                */
const LINE = /^\s*(दोषः|सूचना)\s+\[([^\]]+)\]\s+.*?:(\d+)\s+—\s+(.*)$/;

function parse(output, document) {
  const found = [];
  for (const raw of output.split(/\r?\n/)) {
    const m = LINE.exec(raw);
    if (!m) continue;
    const [, kind, code, lineNo, message] = m;
    const index = Math.max(0, parseInt(lineNo, 10) - 1);
    const textLine = index < document.lineCount ? document.lineAt(index) : null;
    const range = textLine
      ? new vscode.Range(index, textLine.firstNonWhitespaceCharacterIndex,
                         index, textLine.range.end.character)
      : new vscode.Range(index, 0, index, 1);
    const severity = kind === "दोषः"
      ? vscode.DiagnosticSeverity.Error
      : vscode.DiagnosticSeverity.Warning;
    const d = new vscode.Diagnostic(range, message, severity);
    d.source = "वाक्";
    d.code = code;
    found.push(d);
  }
  return found;
}

function check(document) {
  if (document.languageId !== "vak") return;
  if (!vscode.workspace.getConfiguration("vak").get("checkOnSave")) return;

  const { cmd, args } = toolchain(["--check", document.fileName]);
  cp.execFile(cmd, args, { cwd: path.dirname(document.fileName),
                           env: { ...process.env, PYTHONIOENCODING: "utf-8" } },
    (err, stdout, stderr) => {
      const text = `${stdout || ""}\n${stderr || ""}`;
      if (err && !text.trim()) {
        // the toolchain itself could not be started — say so once, quietly
        diagnostics.set(document.uri, []);
        return;
      }
      diagnostics.set(document.uri, parse(text, document));
    });
}

function run(document) {
  const terminal =
    vscode.window.terminals.find((t) => t.name === "वाक्") ||
    vscode.window.createTerminal("वाक्");
  const { cmd, args } = toolchain([document.fileName]);
  terminal.show(true);
  terminal.sendText([cmd, ...args].map(quote).join(" "));
}

function quote(s) {
  return /[\s"]/.test(s) ? `"${s.replace(/"/g, '\\"')}"` : s;
}

/* ------------------------------------------------------- लिप्यन्तरणम्
 * Vāk never transliterates identifiers — `नाम` and `naam` are two different
 * names, deliberately.  This converts what you *type*, so you end up writing
 * one consistent spelling instead of two that look alike.
 */
const ROMAN_WORD = /[A-Za-z~^.]+$/;

/** Convert the selection, or the word the cursor is in. */
function transliterateSelection(editor) {
  editor.edit((edit) => {
    for (const sel of editor.selections) {
      let range = sel;
      if (sel.isEmpty) {
        const found = editor.document.getWordRangeAtPosition(sel.active, /[A-Za-z~^.]+/);
        if (!found) continue;
        range = found;
      }
      const text = editor.document.getText(range);
      const out = devanagari(text, true);
      if (out !== text) edit.replace(range, out);
    }
  });
}

/** Live mode: when a word is finished, convert the word just typed. */
function onType(event) {
  if (!typing) return;
  const editor = vscode.window.activeTextEditor;
  if (!editor || event.document !== editor.document) return;
  if (event.document.languageId !== "vak") return;
  if (event.contentChanges.length !== 1) return;

  const change = event.contentChanges[0];
  // only react to a single character that ends a word
  if (change.text.length !== 1 || /[A-Za-z~^.]/.test(change.text)) return;

  const pos = change.range.start;
  const before = event.document.getText(
    new vscode.Range(new vscode.Position(pos.line, 0), pos));
  const m = ROMAN_WORD.exec(before);
  if (!m) return;

  const word = m[0];
  const out = devanagari(word, true);
  if (out === word) return;
  const range = new vscode.Range(
    new vscode.Position(pos.line, pos.character - word.length), pos);
  editor.edit((edit) => edit.replace(range, out),
              { undoStopBefore: false, undoStopAfter: false });
}

function showStatus() {
  if (!statusBar) return;
  statusBar.text = typing ? "$(check) देवनागरी" : "देवनागरी";
  statusBar.tooltip = typing
    ? "Devanagari typing is on — romanised words convert as you finish them. Ctrl+Alt+T"
    : "Devanagari typing is off. Ctrl+Alt+T to turn it on";
  const editor = vscode.window.activeTextEditor;
  if (editor && editor.document.languageId === "vak") statusBar.show();
  else statusBar.hide();
}

function activate(context) {
  diagnostics = vscode.languages.createDiagnosticCollection("vak");
  context.subscriptions.push(diagnostics);

  typing = vscode.workspace.getConfiguration("vak").get("devanagariTyping") || false;
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.command = "vak.toggleTyping";
  context.subscriptions.push(statusBar);
  showStatus();

  context.subscriptions.push(
    vscode.commands.registerCommand("vak.transliterate", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) transliterateSelection(ed);
    }),
    vscode.commands.registerCommand("vak.toggleTyping", () => {
      typing = !typing;
      showStatus();
      vscode.window.setStatusBarMessage(
        typing ? "देवनागरी-लेखनम् आरब्धम् / Devanagari typing on"
               : "देवनागरी-लेखनम् स्थगितम् / Devanagari typing off", 2000);
    }),
    vscode.workspace.onDidChangeTextDocument(onType),
    vscode.window.onDidChangeActiveTextEditor(showStatus)
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("vak.run", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) ed.document.save().then(() => run(ed.document));
    }),
    vscode.commands.registerCommand("vak.check", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) ed.document.save().then(() => check(ed.document));
    }),
    vscode.workspace.onDidSaveTextDocument(check),
    vscode.workspace.onDidOpenTextDocument(check),
    vscode.workspace.onDidCloseTextDocument((d) => diagnostics.delete(d.uri))
  );
  vscode.workspace.textDocuments.forEach(check);
}

function deactivate() {
  if (diagnostics) diagnostics.dispose();
  if (statusBar) statusBar.dispose();
}

module.exports = { activate, deactivate };
