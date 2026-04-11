"""
GUI-Schicht der WRT Companion App — pywebview-basiert.
"""
import ctypes
import html as _html
import json
import os
import sys
import threading
import webview
import config as _config
import updater as _updater
import i18n as _i18n

_ICON_PATH = _config.resource_path(os.path.join("assets", "icon.png"))

# ---------------------------------------------------------------------------
# Gemeinsames CSS
# ---------------------------------------------------------------------------

_BASE_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:      #0d0d0d;
    --surface: #161616;
    --surface2:#1e1e1e;
    --border:  #252525;
    --border2: #2e2e2e;
    --gold:    #ffd200;
    --gold-h:  #ffe040;
    --text:    #e0e0e0;
    --muted:   #666;
    --error:   #f87171;
    --ok:      #4ade80;
    --warn:    #fbbf24;
    --info:    #60a5fa;
  }

  body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    overflow: hidden;
    user-select: none;
  }

  label {
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 6px;
  }

  input[type=text], input[type=password] {
    width: 100%;
    background: #0a0a0a;
    border: 1px solid var(--border);
    border-radius: 7px;
    color: var(--text);
    font-family: inherit;
    font-size: 13px;
    padding: 9px 11px;
    outline: none;
    transition: border-color 0.15s;
  }
  input:focus { border-color: var(--gold); }
  input::placeholder { color: #333; }

  .btn {
    border: none;
    border-radius: 7px;
    font-family: inherit;
    font-size: 12px;
    font-weight: 600;
    padding: 8px 14px;
    cursor: pointer;
    transition: background 0.15s, transform 0.08s, opacity 0.15s;
    letter-spacing: 0.2px;
    white-space: nowrap;
  }
  .btn:active:not(:disabled) { transform: scale(0.975); }
  .btn:disabled { opacity: 0.35; cursor: default; }

  .btn-primary { background: var(--gold); color: #080808; font-weight: 700; }
  .btn-primary:hover:not(:disabled) { background: var(--gold-h); }

  .btn-ghost {
    background: var(--surface2);
    color: #999;
    border: 1px solid var(--border);
  }
  .btn-ghost:hover:not(:disabled) { border-color: var(--border2); color: var(--text); }

  .btn-danger { background: rgba(248,113,113,0.12); color: var(--error); border: 1px solid rgba(248,113,113,0.25); }
  .btn-danger:hover:not(:disabled) { background: rgba(248,113,113,0.2); }

  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #333;
    flex-shrink: 0;
    transition: background 0.4s;
  }
  .dot.ok      { background: var(--ok);   box-shadow: 0 0 6px var(--ok); }
  .dot.error   { background: var(--error);box-shadow: 0 0 6px var(--error); }
  .dot.loading { background: var(--gold); animation: pulse 1s ease-in-out infinite; }
  .dot.warn    { background: var(--warn); box-shadow: 0 0 6px var(--warn); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

  .badge {
    display: inline-block;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.3px;
  }
  .badge-normal  { background: #1a2e1e; color: var(--ok); }
  .badge-heroic  { background: #1a2438; color: var(--info); }
  .badge-mythic  { background: #241a38; color: #a78bfa; }
  .badge-unknown { background: var(--surface2); color: var(--muted); }

  .toggle-wrap { display: flex; align-items: center; gap: 10px; }
  .toggle-label { font-size: 13px; color: var(--text); }
  .toggle-sub   { font-size: 11px; color: var(--muted); }

  .toggle {
    position: relative;
    width: 38px; height: 21px;
    flex-shrink: 0;
  }
  .toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
  .toggle-slider {
    position: absolute; inset: 0;
    background: #2a2a2a;
    border-radius: 11px;
    cursor: pointer;
    transition: background 0.2s;
  }
  .toggle-slider::before {
    content: '';
    position: absolute;
    width: 15px; height: 15px;
    left: 3px; top: 3px;
    background: #555;
    border-radius: 50%;
    transition: transform 0.2s, background 0.2s;
  }
  .toggle input:checked + .toggle-slider { background: rgba(255,210,0,0.15); }
  .toggle input:checked + .toggle-slider::before {
    transform: translateX(17px);
    background: var(--gold);
  }

  ::-webkit-scrollbar       { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #2a2a2a; border-radius: 2px; }
"""

# ---------------------------------------------------------------------------
# Hauptfenster (3 Tabs)
# ---------------------------------------------------------------------------

_MAIN_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
%%CSS%%

  body { display: flex; flex-direction: column; }

  .titlebar {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 18px 10px;
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .titlebar-logo { font-size: 10px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: var(--gold); }
  .titlebar-spacer { flex: 1; }
  .titlebar-version { font-size: 10px; color: #2e2e2e; }

  .tab-bar { display: flex; border-bottom: 1px solid var(--border); padding: 0 16px; flex-shrink: 0; }
  .tab-btn {
    background: none; border: none; color: var(--muted);
    font-family: inherit; font-size: 12px; font-weight: 600;
    padding: 9px 14px; cursor: pointer;
    border-bottom: 2px solid transparent; margin-bottom: -1px;
    transition: color 0.15s, border-color 0.15s; letter-spacing: 0.3px;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--gold); border-bottom-color: var(--gold); }

  .tab-content { flex: 1; overflow: hidden; position: relative; }
  .tab-pane { display: none; flex-direction: column; position: absolute; inset: 0; overflow-y: auto; padding: 16px; gap: 12px; }
  .tab-pane.active { display: flex; }

  .status-main { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; gap: 12px; box-shadow: inset 0 1px 0 rgba(255,210,0,0.1); }
  .status-info { flex: 1; min-width: 0; }
  .status-label { font-size: 14px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .status-sub { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .data-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .data-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; }
  .data-card-title { font-size: 11px; font-weight: 600; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
  .data-card-time  { font-size: 13px; color: var(--text); }
  .data-card-state { font-size: 11px; margin-top: 3px; }
  .data-card-state.ok   { color: var(--ok); }
  .data-card-state.error{ color: var(--error); }
  .data-card-state.none { color: var(--muted); }
  .status-actions { display: flex; gap: 8px; }

  .raid-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  .raid-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
  .raid-name { font-size: 15px; font-weight: 700; flex: 1; }
  .raid-date { font-size: 11px; color: var(--muted); }
  .raid-meta { display: flex; gap: 16px; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
  .meta-item { display: flex; flex-direction: column; gap: 3px; }
  .meta-key  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
  .meta-val  { font-size: 13px; font-weight: 600; }
  .meta-val.ok    { color: var(--ok); }
  .meta-val.error { color: var(--error); }
  .meta-val.warn  { color: var(--warn); }
  .meta-val.muted { color: var(--muted); }
  .prio-group { margin-bottom: 12px; }
  .prio-group-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--gold); margin-bottom: 6px; }
  .prio-item { display: flex; align-items: center; gap: 10px; padding: 5px 0; border-bottom: 1px solid var(--border); }
  .prio-item:last-child { border-bottom: none; }
  .prio-num { font-size: 10px; font-weight: 700; color: var(--muted); width: 42px; flex-shrink: 0; }
  .prio-item-name { font-size: 13px; color: var(--text); }
  .raid-actions { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
  .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: var(--muted); }
  .empty-state-icon { font-size: 32px; }
  .empty-state-text { font-size: 13px; text-align: center; }

  .settings-section { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  .section-title { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); margin-bottom: 14px; }
  .settings-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border); }
  .settings-row:last-child { border-bottom: none; }
  .settings-row-label { flex: 1; font-size: 13px; color: var(--text); }
  .input-row { display: flex; gap: 6px; align-items: stretch; }
  .input-row input { flex: 1; }
  .btn-icon { background: var(--surface2); color: #888; border: 1px solid var(--border); border-radius: 7px; font-family: inherit; font-size: 12px; padding: 0 12px; cursor: pointer; white-space: nowrap; transition: border-color 0.15s, color 0.15s; }
  .btn-icon:hover { border-color: var(--gold); color: var(--gold); }
  .account-row { display: flex; align-items: center; gap: 10px; padding: 6px 0; }
  .account-status { font-size: 13px; color: var(--text); flex: 1; }
  .account-sub    { font-size: 11px; color: var(--muted); }
  .version-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid var(--border); }
  .version-row:last-child { border-bottom: none; }
  .version-info { flex: 1; }
  .version-current { font-size: 13px; color: var(--text); }
  .version-latest  { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .version-latest.uptodate { color: var(--ok); }
  .version-latest.outdated { color: var(--warn); }

  .lang-btns { display: flex; gap: 6px; }
  .lang-btn { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; color: var(--muted); font-family: inherit; font-size: 12px; padding: 6px 14px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
  .lang-btn.active { border-color: var(--gold); color: var(--gold); }
  .lang-btn:hover:not(.active) { border-color: var(--border2); color: var(--text); }

  /* ── Charakterliste ─────────────────────────────── */
  .char-card { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .char-card:last-child { border-bottom: none; }
  .char-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .char-info { flex: 1; min-width: 0; }
  .char-name { font-size: 13px; font-weight: 600; }
  .char-spec { font-size: 11px; color: var(--muted); margin-top: 1px; }
  .char-active-badge { font-size: 10px; font-weight: 700; color: var(--ok); border: 1px solid var(--ok); border-radius: 5px; padding: 2px 7px; white-space: nowrap; }
  .char-actions { display: flex; gap: 6px; flex-shrink: 0; }

  /* Char-Modal Formular */
  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
  .form-select { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; color: var(--text); font-family: inherit; font-size: 13px; padding: 7px 10px; width: 100%; }
  .form-error { color: var(--error); font-size: 12px; display: none; }

  /* ── Modals ─────────────────────────────────────── */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.78); display: flex; align-items: center; justify-content: center; z-index: 100; }
  .modal-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 12px; max-height: 94vh; }
  .modal-title { font-size: 14px; font-weight: 700; color: var(--text); }
  .modal-actions { display: flex; gap: 8px; justify-content: flex-end; padding-top: 4px; }
  .deadline-msg { color: var(--error); font-size: 12px; background: rgba(220,50,47,0.1); border: 1px solid rgba(220,50,47,0.4); border-radius: 7px; padding: 8px 12px; }

  /* Signup modal */
  .signup-options { display: flex; flex-direction: column; gap: 6px; }
  .signup-opt { display: flex; align-items: center; background: var(--surface2); border: 2px solid var(--border); border-radius: 8px; padding: 10px 14px; cursor: pointer; font-family: inherit; font-size: 13px; color: var(--text); text-align: left; transition: border-color 0.15s, color 0.15s; width: 100%; }
  .signup-opt:hover { border-color: var(--border2); }
  .signup-opt.selected.s-ok    { border-color: var(--ok);    color: var(--ok); }
  .signup-opt.selected.s-warn  { border-color: var(--warn);  color: var(--warn); }
  .signup-opt.selected.s-muted { border-color: var(--muted); color: var(--muted); }
  .signup-opt.selected.s-error { border-color: var(--error); color: var(--error); }

  /* Prio modal */
  .prio-modal-box { width: 840px; }
  .prio-modal-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .diff-tabs { display: flex; gap: 5px; }
  .diff-tab { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; color: var(--muted); font-family: inherit; font-size: 11px; font-weight: 700; padding: 5px 12px; cursor: pointer; transition: border-color 0.15s, color 0.15s; }
  .diff-tab.active { border-color: var(--gold); color: var(--gold); }
  .diff-tab-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--ok); margin-left: 5px; vertical-align: middle; margin-bottom: 1px; }
  .superprio-badge { background: rgba(255,210,0,0.12); border: 1px solid var(--gold); border-radius: 6px; color: var(--gold); font-size: 11px; font-weight: 700; padding: 4px 10px; }
  .char-filter-label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--muted); cursor: pointer; margin-left: auto; }
  .prio-summary { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
  .prio-sum-slot { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px 12px; min-width: 0; }
  .prio-sum-label { font-size: 10px; font-weight: 700; text-transform: uppercase; color: var(--muted); margin-bottom: 3px; letter-spacing: 0.5px; }
  .prio-sum-val { font-size: 12px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
  .prio-sum-val.passed { color: var(--muted); font-style: italic; }
  .prio-columns { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  .prio-col { display: flex; flex-direction: column; gap: 6px; }
  .prio-col-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--gold); text-align: center; padding: 4px 0; }
  .prio-pass-btn { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; color: var(--muted); font-family: inherit; font-size: 12px; padding: 7px 10px; cursor: pointer; width: 100%; transition: border-color 0.15s, color 0.15s; text-align: center; }
  .prio-pass-btn.active { border-color: var(--error); color: var(--error); background: rgba(220,50,47,0.08); }
  .boss-select { position: relative; }
  .boss-sel-val { background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; color: var(--text); font-size: 12px; padding: 5px 10px; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 6px; user-select: none; }
  .boss-sel-val::after { content: "▾"; color: var(--muted); font-size: 10px; flex-shrink: 0; }
  .boss-sel-opts { position: absolute; top: calc(100% + 3px); left: 0; right: 0; background: var(--surface); border: 1px solid var(--border); border-radius: 7px; z-index: 300; overflow-y: auto; max-height: 200px; display: none; box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
  .boss-sel-opts.open { display: block; }
  .boss-sel-opt { padding: 7px 10px; font-size: 12px; cursor: pointer; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .boss-sel-opt:hover { background: var(--surface2); }
  .boss-sel-opt.active { color: var(--gold); }
  .prio-item-list { display: flex; flex-direction: column; gap: 3px; overflow-y: auto; max-height: 290px; }
  .pi-btn { display: block; background: var(--surface2); border: 1px solid var(--border); border-radius: 7px; padding: 7px 10px; cursor: pointer; text-align: left; width: 100%; transition: border-color 0.15s; }
  .pi-btn:hover:not(.pi-disabled) { border-color: var(--border2); }
  .pi-btn.pi-selected { border-color: var(--ok); background: rgba(63,185,80,0.08); }
  .pi-btn.pi-disabled { opacity: 0.35; cursor: not-allowed; }
  .pi-btn.pi-hidden { display: none; }
  .pi-btn a { color: inherit; text-decoration: none; font-size: 12px; }

  .prio-item-name a { text-decoration: none; }
  .prio-item-name a:hover { text-decoration: underline; }
  .wh-tooltip-shown { z-index: 9999 !important; }

  /* ── Admin-Tab ─────────────────────────────────── */
  .admin-sub-bar { display: flex; gap: 0; border-bottom: 1px solid var(--border); flex-shrink: 0; margin-bottom: 2px; }
  .admin-sub-btn { background: none; border: none; border-bottom: 2px solid transparent; color: var(--muted); font-family: inherit; font-size: 12px; font-weight: 600; padding: 7px 16px; cursor: pointer; margin-bottom: -1px; transition: color 0.15s, border-color 0.15s; }
  .admin-sub-btn:hover { color: var(--text); }
  .admin-sub-btn.active { color: var(--gold); border-bottom-color: var(--gold); }
  .admin-sub-pane { display: none; flex-direction: column; gap: 8px; flex: 1; overflow-y: auto; }
  .admin-sub-pane.active { display: flex; }
  .admin-raid-row { background: var(--surface); border: 1px solid var(--border); border-radius: 9px; padding: 11px 14px; display: flex; align-items: center; gap: 10px; }
  .admin-raid-row:hover { border-color: var(--border2); }
  .admin-raid-info { flex: 1; min-width: 0; }
  .admin-raid-name { font-size: 13px; font-weight: 600; }
  .admin-raid-meta { font-size: 11px; color: var(--muted); margin-top: 2px; display: flex; align-items: center; gap: 6px; }
  .admin-raid-actions { display: flex; gap: 5px; flex-shrink: 0; }
  .pub-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .pub-dot.yes { background: var(--ok);    box-shadow: 0 0 5px var(--ok); }
  .pub-dot.no  { background: var(--muted); }
  .admin-user-table { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  .admin-user-head, .admin-user-row { display: grid; grid-template-columns: 1fr 130px 120px 100px auto; gap: 8px; align-items: center; padding: 8px 14px; }
  .admin-user-head { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); background: var(--surface2); }
  .admin-user-row { border-top: 1px solid var(--border); font-size: 12px; }
  .admin-user-row:hover { background: rgba(255,255,255,0.015); }
  .admin-sel { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-family: inherit; font-size: 11px; padding: 4px 6px; width: 100%; }
  .admin-sub-header { display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
  input[type=date], input[type=time], textarea { color-scheme: dark; }
  textarea { width: 100%; background: #0a0a0a; border: 1px solid var(--border); border-radius: 7px; color: var(--text); font-family: inherit; font-size: 13px; padding: 9px 11px; outline: none; resize: vertical; min-height: 60px; transition: border-color 0.15s; }
  textarea:focus { border-color: var(--gold); }
  .patch-list { display: flex; flex-direction: column; gap: 4px; max-height: 130px; overflow-y: auto; border: 1px solid var(--border); border-radius: 7px; padding: 8px 10px; background: #0a0a0a; }
  .patch-item { display: flex; align-items: center; gap: 8px; font-size: 12px; cursor: pointer; padding: 2px 0; }
  .patch-item input[type=checkbox] { accent-color: var(--gold); width: 14px; height: 14px; flex-shrink: 0; }
  .inline-row { display: flex; align-items: center; gap: 8px; }
  .inline-row input[type=number] { width: 70px; }
  .raid-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }

  /* ── Statistik-Tab ──────────────────────────────── */
  .stats-filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; flex-shrink: 0; }
  .stats-filters .boss-select { min-width: 160px; }
  .stats-card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .stats-card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  .stats-card-title { font-size: 14px; font-weight: 700; flex: 1; }

  .lh-table { display: flex; flex-direction: column; }
  .lh-head, .lh-entry { display: grid; grid-template-columns: 52px 140px 1fr 120px 45px; gap: 8px; align-items: center; padding: 5px 0; }
  .lh-head { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 2px; }
  .lh-entry { font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .lh-entry:last-child { border-bottom: none; }
  .lh-time { color: var(--muted); }
  .lh-boss { color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .lh-type { font-weight: 700; font-size: 11px; text-align: right; }
  .lh-item a { text-decoration: none; }
  .lh-item a:hover { text-decoration: underline; }

  .ps-table { display: flex; flex-direction: column; }
  .ps-head, .ps-row { display: grid; grid-template-columns: 1fr 55px 50px 50px 80px 70px 55px; gap: 8px; align-items: center; padding: 6px 0; }
  .ps-head { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 2px; }
  .ps-head span:not(:first-child) { text-align: right; }
  .ps-row { font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .ps-row:last-child { border-bottom: none; }
  .ps-row span:not(:first-child) { text-align: right; color: var(--muted); }

  .dc-table { display: flex; flex-direction: column; }
  .dc-head, .dc-row { display: grid; grid-template-columns: 1fr 60px 60px 70px; gap: 8px; align-items: center; padding: 5px 0; }
  .dc-head { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); border-bottom: 1px solid var(--border); padding-bottom: 6px; margin-bottom: 2px; }
  .dc-head span:not(:first-child) { text-align: right; }
  .dc-row { font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .dc-row:last-child { border-bottom: none; }
  .dc-row span:not(:first-child) { text-align: right; }
  .dc-item a { text-decoration: none; }
  .dc-item a:hover { text-decoration: underline; }
</style>
<script>var whTooltips = {colorLinks: true, iconizeLinks: true, renameLinks: true};</script>
<script src="https://wow.zamimg.com/js/tooltips.js"></script>
</head>
<body>

  <div class="titlebar">
    <span class="titlebar-logo">WeltenWandler</span>
    <span class="titlebar-spacer"></span>
    <span class="titlebar-version" id="appVersion"></span>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" data-tab="status"   onclick="switchTab('status')"   data-i18n="tab.status">Status</button>
    <button class="tab-btn"        data-tab="raids"    onclick="switchTab('raids')"    data-i18n="tab.raids">Raids</button>
    <button class="tab-btn"        data-tab="profil"   onclick="switchTab('profil')"   data-i18n="tab.profil">Profil</button>
    <button class="tab-btn"        data-tab="stats"    onclick="switchTab('stats')"    data-i18n="tab.stats">Statistik</button>
    <button class="tab-btn"        data-tab="admin"     onclick="switchTab('admin')"     data-i18n="tab.admin" style="display:none">Admin</button>
    <button class="tab-btn"        data-tab="blacklist" onclick="switchTab('blacklist')" data-i18n="tab.blacklist" style="display:none">Blacklist</button>
    <button class="tab-btn"        data-tab="settings"  onclick="switchTab('settings')"  data-i18n="tab.settings">Einstellungen</button>
  </div>

  <div class="tab-content">

    <div id="tab-status" class="tab-pane active">
      <div class="status-main">
        <div class="dot" id="dot"></div>
        <div class="status-info">
          <div class="status-label" id="statusLabel"></div>
          <div class="status-sub"   id="statusSub"></div>
        </div>
      </div>
      <div class="data-cards">
        <div class="data-card">
          <div class="data-card-title" data-i18n="status.card_raid">Raid-Daten</div>
          <div class="data-card-time"  id="raidTime">&#8211;</div>
          <div class="data-card-state" id="raidState"></div>
        </div>
        <div class="data-card">
          <div class="data-card-title" data-i18n="status.card_stats">Statistiken</div>
          <div class="data-card-time"  id="statsTime">&#8211;</div>
          <div class="data-card-state" id="statsState"></div>
        </div>
      </div>
      <div class="status-actions">
        <button class="btn btn-ghost"   onclick="doRefresh()"           data-i18n="btn.refresh">Aktualisieren</button>
        <button class="btn btn-primary" onclick="switchTab('settings')" data-i18n="btn.settings">Einstellungen</button>
      </div>
    </div>

    <div id="tab-raids" class="tab-pane">
      <div id="raidsContent"></div>
    </div>

    <div id="tab-profil" class="tab-pane">

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.account">Account</div>
        <div class="account-row">
          <div class="dot" id="profilAccountDot"></div>
          <div class="status-info">
            <div class="account-status" id="profilAccountStatus"></div>
            <div class="account-sub"    id="profilDiscord"></div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" style="display:flex;align-items:center;justify-content:space-between">
          <span data-i18n="chars.title">Charaktere</span>
          <button class="btn-icon" onclick="openCharModal(null)" data-i18n="chars.new">Neuer Charakter</button>
        </div>
        <div id="charList"></div>
      </div>

    </div>

    <div id="tab-settings" class="tab-pane">

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.account">Account</div>
        <div class="account-row">
          <div class="dot" id="accountDot"></div>
          <div class="status-info">
            <div class="account-status" id="accountStatus"></div>
            <div class="account-sub"    id="accountSub"></div>
          </div>
          <button class="btn btn-danger" id="logoutBtn" onclick="doLogout()" style="display:none" data-i18n="btn.logout">Abmelden</button>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.addon_path">Addon-Pfad</div>
        <div class="settings-row" style="border:none;padding:0">
          <div style="flex:1">
            <div class="input-row">
              <input type="text" id="addonPath" placeholder="E:\\...\\World of Warcraft\\_retail_">
              <button class="btn-icon" onclick="browseAddon()" data-i18n="btn.browse">Durchsuchen</button>
            </div>
            <div style="font-size:11px;color:var(--muted);margin-top:5px" data-i18n="settings.addon_path_hint">
              Nur bis _retail_ — der Rest wird automatisch ergänzt
            </div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.app">App-Einstellungen</div>
        <div class="settings-row">
          <div class="settings-row-label" data-i18n="settings.run_on_startup">Beim Windows-Start ausführen</div>
          <label class="toggle">
            <input type="checkbox" id="runOnStartup" onchange="saveSetting('run_on_startup', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
        <div class="settings-row">
          <div class="settings-row-label" data-i18n="settings.close_to_tray">In Tray minimieren beim Schließen</div>
          <label class="toggle">
            <input type="checkbox" id="closeToTray" onchange="saveSetting('close_to_tray', this.checked)">
            <span class="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.language">Sprache</div>
        <div class="settings-row" style="border:none;padding:4px 0 0">
          <div class="lang-btns">
            <button class="lang-btn" id="lang-de" onclick="setLanguage('de')">&#127465;&#127466; Deutsch</button>
            <button class="lang-btn" id="lang-en" onclick="setLanguage('en')">&#127468;&#127463; English</button>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.addon_update">Addon-Update</div>
        <div class="version-row">
          <div class="version-info">
            <div class="version-current">WeltenWandler Raid Tool</div>
            <div class="version-latest" id="addonVersionInfo" data-i18n="settings.checking">Prüfe...</div>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <label class="toggle">
              <input type="checkbox" id="addonAutoUpdate" onchange="saveSetting('addon_autoupdate', this.checked)">
              <span class="toggle-slider"></span>
            </label>
            <span style="font-size:12px;color:var(--muted)" data-i18n="settings.auto_update">Auto Update</span>
          </div>
          <button class="btn btn-ghost" id="addonUpdateBtn" onclick="doAddonUpdate()" data-i18n="btn.update_now">Jetzt updaten</button>
        </div>
        <div id="addonBranchRow" class="settings-row" style="display:none;margin-top:8px">
          <div class="settings-row-label" data-i18n="settings.addon_branch">Branch</div>
          <div class="lang-btns">
            <button class="lang-btn" id="branch-master" onclick="setAddonBranch('master')">master</button>
            <button class="lang-btn" id="branch-dev"    onclick="setAddonBranch('dev')">dev</button>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.app_update">App-Update</div>
        <div class="version-row">
          <div class="version-info">
            <div class="version-current">WRT Companion App</div>
            <div class="version-latest" id="appVersionInfo" data-i18n="settings.checking">Prüfe...</div>
          </div>
          <button class="btn btn-ghost" id="appUpdateBtn" onclick="doAppUpdate()" data-i18n="btn.update_now">Jetzt updaten</button>
        </div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="settings.lootliste">Lootliste (Addon-Sync)</div>
        <div class="settings-row" style="border:none;padding:4px 0 0">
          <button class="btn btn-secondary" id="lootlistePickerBtn" onclick="openLootlisteModal()" style="flex:1;text-align:left;justify-content:space-between">
            <span id="lootlisteBtnLabel">–</span>
            <span style="color:var(--muted);font-size:12px">&#9660;</span>
          </button>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:6px" data-i18n="settings.lootliste_hint">
          Legt fest welche Lootlisten ans Addon übertragen werden
        </div>
      </div>

      <div style="display:flex;justify-content:flex-end;padding-top:4px">
        <button class="btn btn-primary" onclick="saveAddonPath()" data-i18n="btn.save">Speichern</button>
      </div>

    </div>

    <!-- Statistik-Tab -->
    <div id="tab-stats" class="tab-pane">
      <div class="stats-filters">

        <div class="boss-select">
          <div class="boss-sel-val" id="statsTypeSel" onclick="toggleStatsFilterDd('statsTypeDd')"></div>
          <div class="boss-sel-opts stats-dd" id="statsTypeDd">
            <div class="boss-sel-opt active" data-val="loothistorie" onclick="selectStatsType('loothistorie')" data-i18n="stats.loothistorie">Loothistorie</div>
            <div class="boss-sel-opt"        data-val="player_stats" onclick="selectStatsType('player_stats')" data-i18n="stats.player_stats">Loot pro Spieler</div>
            <div class="boss-sel-opt"        data-val="dropchance"   onclick="selectStatsType('dropchance')"   data-i18n="stats.dropchance">Dropchance</div>
          </div>
        </div>

        <div class="boss-select">
          <div class="boss-sel-val" id="statsPatchSel" onclick="toggleStatsFilterDd('statsPatchDd')"></div>
          <div class="boss-sel-opts stats-dd" id="statsPatchDd"></div>
        </div>

        <div class="boss-select">
          <div class="boss-sel-val" id="statsDiffSel" onclick="toggleStatsFilterDd('statsDiffDd')"></div>
          <div class="boss-sel-opts stats-dd" id="statsDiffDd">
            <div class="boss-sel-opt active" data-val="all"    onclick="selectStatsDiff('all')"    data-i18n="stats.all_diff">Alle</div>
            <div class="boss-sel-opt"        data-val="normal" onclick="selectStatsDiff('normal')">Normal</div>
            <div class="boss-sel-opt"        data-val="heroic" onclick="selectStatsDiff('heroic')">Heroic</div>
            <div class="boss-sel-opt"        data-val="mythic" onclick="selectStatsDiff('mythic')">Mythic</div>
          </div>
        </div>

        <div class="boss-select" id="statsScopeWrap">
          <div class="boss-sel-val" id="statsScopeSel" onclick="toggleStatsFilterDd('statsScopeDd')"></div>
          <div class="boss-sel-opts stats-dd" id="statsScopeDd">
            <div class="boss-sel-opt active" data-val="all" onclick="selectStatsScope('all')" data-i18n="stats.scope_all">Alle</div>
            <div class="boss-sel-opt"        data-val="ms"  onclick="selectStatsScope('ms')"  data-i18n="stats.scope_ms">Main-Spec</div>
            <div class="boss-sel-opt"        data-val="os"  onclick="selectStatsScope('os')"  data-i18n="stats.scope_os">Off-Spec</div>
          </div>
        </div>

      </div>
      <div id="statsContent" style="display:flex;flex-direction:column;gap:10px;flex:1"></div>
    </div>

    <!-- Admin-Tab -->
    <div id="tab-admin" class="tab-pane">

      <div class="admin-sub-bar">
        <button class="admin-sub-btn active" data-sub="raids"   onclick="switchAdminSub('raids')"   data-i18n="admin.raids">Raids</button>
        <button class="admin-sub-btn"        data-sub="archive" onclick="switchAdminSub('archive')" data-i18n="admin.archive">Archiv</button>
        <button class="admin-sub-btn"        data-sub="users"   onclick="switchAdminSub('users')"   data-i18n="admin.users">Benutzer</button>
      </div>

      <div id="admin-raids" class="admin-sub-pane active">
        <div class="admin-sub-header">
          <span style="font-size:11px;color:var(--muted)" id="adminRaidsCount"></span>
          <button class="btn btn-primary" onclick="openRaidModal(null)" data-i18n="admin.new_raid">+ Neuer Raid</button>
        </div>
        <div id="admin-raids-list"></div>
      </div>

      <div id="admin-archive" class="admin-sub-pane">
        <div id="admin-archive-list"></div>
      </div>

      <div id="admin-users" class="admin-sub-pane">
        <div id="admin-users-list"></div>
      </div>

    </div>

    <!-- Blacklist-Tab -->
    <div id="tab-blacklist" class="tab-pane">

      <div class="settings-section">
        <div class="section-title" data-i18n="blacklist.add_title">Item zur Blacklist hinzufügen</div>
        <div class="settings-row" style="border:none;padding:0;gap:8px;flex-wrap:wrap">
          <input type="number" id="blItemId" placeholder="Item ID" style="width:120px;flex-shrink:0">
          <input type="text"   id="blNote"   placeholder="Notiz (optional)" style="flex:1;min-width:120px">
          <button class="btn btn-primary" onclick="blAddItem()" data-i18n="blacklist.add_btn">Hinzufügen</button>
        </div>
        <div id="blAddError" style="color:var(--error);font-size:12px;margin-top:6px;display:none"></div>
      </div>

      <div class="settings-section">
        <div class="section-title" data-i18n="blacklist.list_title">Blacklisted Items</div>
        <div id="blList" style="display:flex;flex-direction:column;gap:4px"></div>
      </div>

    </div>

  </div>

  <!-- Raid erstellen/bearbeiten Modal -->
  <div id="raidModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closeRaidModal()">
    <div class="modal-box" style="width:560px;gap:12px;overflow-y:auto;max-height:92vh">
      <div class="modal-title" id="raidModalTitle" data-i18n="admin.create_raid">Raid erstellen</div>
      <div class="raid-form-grid">
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label" data-i18n="admin.raid_name">Raid-Name</label>
          <input type="text" id="raidName" placeholder="z.B. Nerub'ar Palast">
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="admin.difficulty_label">Schwierigkeitsgrad</label>
          <select id="raidDifficulty" class="form-select">
            <option value="normal">Normal</option>
            <option value="heroic" selected>Heroisch</option>
            <option value="mythic">Mythisch</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="admin.date">Datum</label>
          <input type="date" id="raidDate" class="form-select" style="padding:7px 10px">
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="admin.time">Uhrzeit</label>
          <input type="time" id="raidTime" value="20:00" class="form-select" style="padding:7px 10px">
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="admin.deadline_enabled">Anmeldefrist</label>
          <div class="inline-row" style="margin-top:2px">
            <label class="toggle" style="flex-shrink:0">
              <input type="checkbox" id="raidDeadlineChk" onchange="toggleDeadlineHours()">
              <span class="toggle-slider"></span>
            </label>
            <input type="number" id="raidDeadlineHours" value="24" min="1" max="168" disabled
              style="width:70px;opacity:0.4;transition:opacity 0.15s">
            <span style="font-size:11px;color:var(--muted)" data-i18n="admin.deadline_hours">Std. vor Raidbeginn</span>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label" data-i18n="admin.superprio">Superprio</label>
          <div style="margin-top:6px">
            <label class="toggle">
              <input type="checkbox" id="raidSuperprio">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label" data-i18n="admin.patches">Lootlisten</label>
          <div class="patch-list" id="raidPatchList">
            <span style="color:var(--muted);font-size:12px">Lade…</span>
          </div>
        </div>
        <div class="form-group" style="grid-column:1/-1">
          <label class="form-label" data-i18n="admin.notes">Notizen</label>
          <textarea id="raidNotes" rows="3" placeholder="Optional…"></textarea>
        </div>
      </div>
      <div class="form-error" id="raidFormError"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost"   onclick="closeRaidModal()" data-i18n="btn.cancel">Abbrechen</button>
        <button class="btn btn-primary" onclick="submitRaidModal()" data-i18n="btn.save">Speichern</button>
      </div>
    </div>
  </div>

  <!-- Passwort-Reset Ergebnis Modal -->
  <div id="pwModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closePwModal()">
    <div class="modal-box" style="width:340px;gap:14px;align-items:center">
      <div class="modal-title" data-i18n="admin.temp_pw">Temporäres Passwort</div>
      <div style="font-size:11px;color:var(--muted);text-align:center">Bitte sofort weiterleiten und sichern.</div>
      <div id="pwResult" style="font-family:monospace;font-size:18px;letter-spacing:3px;color:var(--gold);background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px 20px;text-align:center;width:100%"></div>
      <button class="btn btn-primary" onclick="closePwModal()">OK</button>
    </div>
  </div>

  <!-- Lootliste Picker Modal -->
  <div id="lootlisteModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closeLootlisteModal()">
    <div class="modal-box" style="width:400px;gap:14px">
      <div class="modal-title" data-i18n="settings.lootliste">Lootliste (Addon-Sync)</div>
      <div style="display:flex;gap:8px">
        <button class="btn btn-secondary" style="flex:1" onclick="lootlisteSelectAll()" data-i18n="settings.ll_all_on">Alle aktivieren</button>
        <button class="btn btn-secondary" style="flex:1" onclick="lootlisteSelectNone()" data-i18n="settings.ll_all_off">Alle deaktivieren</button>
      </div>
      <div id="lootlisteChecklist" style="display:flex;flex-direction:column;gap:6px;max-height:320px;overflow-y:auto;padding-right:4px"></div>
      <button class="btn btn-primary" onclick="saveLootlisteModal()" data-i18n="btn.save">Speichern</button>
    </div>
  </div>

  <!-- Ersteinrichtung Modal (kein Schließen per Klick außen) -->
  <div id="setupModal" class="modal-overlay" style="display:none">
    <div class="modal-box" style="width:460px;gap:16px">
      <div style="font-size:28px;text-align:center">&#127981;</div>
      <div class="modal-title" data-i18n="setup.title">Willkommen!</div>
      <div style="font-size:13px;color:var(--muted);text-align:center;line-height:1.5" data-i18n="setup.desc">
        Bitte wähle den Pfad zu deiner World of Warcraft Installation aus, damit das Addon synchronisiert werden kann.
      </div>
      <div class="form-group">
        <label data-i18n="settings.addon_path">Addon-Pfad</label>
        <div class="input-row">
          <input type="text" id="setupAddonPath" placeholder="E:\\...\\World of Warcraft\\_retail_" style="flex:1">
          <button class="btn-icon" onclick="browseSetupAddon()" data-i18n="btn.browse">Durchsuchen</button>
        </div>
        <div style="font-size:11px;color:var(--muted);margin-top:5px" data-i18n="settings.addon_path_hint">
          Nur bis _retail_ — der Rest wird automatisch ergänzt
        </div>
      </div>
      <div id="setupError" style="display:none;color:var(--error);font-size:12px;text-align:center"></div>
      <button class="btn btn-primary" style="width:100%" onclick="saveSetupAddon()" data-i18n="setup.save">Speichern &amp; Fortfahren</button>
    </div>
  </div>

  <!-- Charakter Modal -->
  <div id="charModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closeCharModal()">
    <div class="modal-box" style="width:380px;gap:14px">
      <div class="modal-title" id="charModalTitle" data-i18n="chars.modal_create">Charakter erstellen</div>
      <div class="form-group">
        <label class="form-label" data-i18n="chars.name">Charaktername</label>
        <input type="text" id="charNameInput" class="input" placeholder="Charaktername" style="font-size:13px">
      </div>
      <div class="form-group">
        <label class="form-label" data-i18n="chars.class">Klasse</label>
        <select id="charClassSelect" class="form-select" onchange="updateSpecOptions()"></select>
      </div>
      <div class="form-group">
        <label class="form-label" data-i18n="chars.spec">Spezialisierung</label>
        <select id="charSpecSelect" class="form-select"></select>
      </div>
      <div class="form-error" id="charFormError"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeCharModal()" data-i18n="btn.cancel">Abbrechen</button>
        <button class="btn btn-primary" onclick="submitCharModal()" data-i18n="btn.save">Speichern</button>
      </div>
    </div>
  </div>

  <!-- News Modal -->
  <div id="newsModal" class="modal-overlay" style="display:none">
    <div class="modal-box" style="width:520px">
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:18px">&#128226;</span>
        <span class="modal-title" data-i18n="news.title">Wichtige Mitteilung</span>
      </div>
      <div id="newsMetaLine" style="font-size:11px;color:var(--muted)"></div>
      <div id="newsHeadline" style="font-size:15px;font-weight:700;color:var(--gold)"></div>
      <div id="newsBody" style="font-size:13px;color:var(--text);line-height:1.6;max-height:280px;overflow-y:auto;white-space:pre-wrap;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px"></div>
      <div class="modal-actions">
        <button class="btn btn-primary" onclick="confirmNews()" data-i18n="news.confirm">Gelesen und bestätigt</button>
      </div>
    </div>
  </div>

  <!-- Signup Modal -->
  <div id="signupModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closeSignupModal()">
    <div class="modal-box" style="width:320px">
      <div class="modal-title" data-i18n="signup.modal_title">Anmeldestatus ändern</div>
      <div id="signupDeadlineMsg" class="deadline-msg" style="display:none" data-i18n="signup.deadline_msg">Anmeldefrist abgelaufen.</div>
      <div id="signupOptions" class="signup-options"></div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closeSignupModal()" data-i18n="btn.cancel">Abbrechen</button>
        <button class="btn btn-primary" id="signupSaveBtn" onclick="submitSignup()" data-i18n="btn.save">Speichern</button>
      </div>
    </div>
  </div>

  <!-- Prio Modal -->
  <div id="prioModal" class="modal-overlay" style="display:none" onclick="if(event.target===this)closePrioModal()">
    <div class="modal-box prio-modal-box">
      <div class="prio-modal-header">
        <span class="modal-title" data-i18n="prio.title">Prioauswahl bearbeiten</span>
        <div class="diff-tabs" id="prioDiffTabs"></div>
        <div id="superPrioBadge" class="superprio-badge" style="display:none" data-i18n="prio.superprio">Superprio aktiv</div>
        <label class="char-filter-label">
          <input type="checkbox" id="charFilterChk" onchange="applyCharFilter()">
          <span data-i18n="prio.char_filter">Char-Filter</span>
        </label>
      </div>
      <div class="prio-summary" id="prioSummary"></div>
      <div class="prio-columns" id="prioColumns"></div>
      <div id="prioErrorMsg" class="deadline-msg" style="display:none" data-i18n="prio.error_two_slots">Ein Item darf nicht auf genau 2 Slots liegen.</div>
      <div class="modal-actions">
        <button class="btn btn-ghost" onclick="closePrioModal()" data-i18n="btn.cancel">Abbrechen</button>
        <button class="btn btn-primary" onclick="submitPrio()" data-i18n="btn.save">Speichern</button>
      </div>
    </div>
  </div>

  <script>
    const TRANSLATIONS = %%TRANSLATIONS%%;
    let LANG = "%%LANG%%";

    function t(key) {
      return (TRANSLATIONS[LANG] && TRANSLATIONS[LANG][key]) || key;
    }

    function applyLocale() {
      document.documentElement.lang = LANG;
      document.querySelectorAll("[data-i18n]").forEach(el => {
        el.textContent = t(el.dataset.i18n);
      });
      document.querySelectorAll(".lang-btn[id^='lang-']").forEach(b => {
        b.classList.toggle("active", b.id === "lang-" + LANG);
      });
      if (document.getElementById("tab-raids").classList.contains("active")) loadRaids();
      if (document.getElementById("tab-stats") && document.getElementById("tab-stats").classList.contains("active")) {
        _initStatsFilterLabels();
      }
    }

    async function setLanguage(lang) {
      LANG = lang;
      applyLocale();
      await window.pywebview.api.save_setting("language", lang);
      if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
    }

    async function setAddonBranch(branch) {
      document.querySelectorAll(".lang-btn[id^='branch-']").forEach(b => {
        b.classList.toggle("active", b.id === "branch-" + branch);
      });
      await window.pywebview.api.save_setting("addon_branch", branch);
      loadVersionInfos();
    }

    function switchTab(name) {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.toggle("active", p.id === "tab-" + name));
      if (name === "raids")    { checkPendingNews().then(ok => { if (ok) loadRaids(); }); }
      if (name === "profil")   loadProfileAndChars();
      if (name === "stats")    loadStats();
      if (name === "admin")     { switchAdminSub("raids"); }
      if (name === "blacklist") loadBlacklist();
      if (name === "settings")  loadSettings();
    }

    function setStatus(labelKey, subKey, state) {
      document.getElementById("statusLabel").textContent = t(labelKey) || labelKey;
      const sub = subKey ? (t(subKey) || subKey) : "";
      document.getElementById("statusSub").textContent   = sub;
      document.getElementById("dot").className = "dot " + (state || "");
    }

    function setLastUpdate(text) {}

    function setDataCards(raidTime, statsTime) {
      const rt = document.getElementById("raidTime");
      const st = document.getElementById("statsTime");
      const rs = document.getElementById("raidState");
      const ss = document.getElementById("statsState");
      if (raidTime && raidTime !== "–") {
        rt.textContent = raidTime;
        rs.textContent = t("status.card_current"); rs.className = "data-card-state ok";
      } else {
        rt.textContent = "–"; rs.textContent = t("status.card_not_loaded"); rs.className = "data-card-state none";
      }
      if (statsTime && statsTime !== "–") {
        st.textContent = statsTime;
        ss.textContent = t("status.card_current"); ss.className = "data-card-state ok";
      } else {
        st.textContent = "–"; ss.textContent = t("status.card_not_loaded"); ss.className = "data-card-state none";
      }
    }

    async function doRefresh() { await window.pywebview.api.refresh(); }

    const SIGNUP_KEYS = {
      "angemeldet": { key: "signup.angemeldet", cls: "ok"    },
      "spaeter":    { key: "signup.spaeter",    cls: "warn"  },
      "vorlaeufig": { key: "signup.vorlaeufig", cls: "warn"  },
      "bench":      { key: "signup.bench",      cls: "muted" },
      "abgelehnt":  { key: "signup.abgelehnt",  cls: "error" },
    };
    const WOW_CLASS_COLORS = {
      "Krieger":       "#C69B3A", "Warrior":       "#C69B3A",
      "Paladin":       "#F48CBA",
      "Jäger":         "#AAD372", "Hunter":        "#AAD372",
      "Schurke":       "#FFF468", "Rogue":         "#FFF468",
      "Priester":      "#FFFFFF", "Priest":        "#FFFFFF",
      "Todesritter":   "#C41E3A", "Death Knight":  "#C41E3A",
      "Schamane":      "#0070DD", "Shaman":        "#0070DD",
      "Magier":        "#3FC7EB", "Mage":          "#3FC7EB",
      "Hexenmeister":  "#8788EE", "Warlock":       "#8788EE",
      "Mönch":         "#00FF98", "Monk":          "#00FF98",
      "Druide":        "#FF7C0A", "Druid":         "#FF7C0A",
      "Dämonenjäger":  "#A330C9", "Demon Hunter":  "#A330C9",
      "Rufer":         "#33937F", "Evoker":        "#33937F",
    };

    const DIFF_CLASS = {
      "Normal":   "badge-normal",
      "Heroisch": "badge-heroic",
      "Mythisch": "badge-mythic",
    };

    function formatDate(ts) { return _fmtDateTime(ts); }

    async function loadRaids() {
      const data = await window.pywebview.api.get_raid_data();
      const el   = document.getElementById("raidsContent");
      if (!data || !data.raids || data.raids.length === 0) {
        el.innerHTML = `<div class="empty-state">
          <div class="empty-state-icon">&#9876;</div>
          <div class="empty-state-text">${t("raids.empty")}<br>${t("raids.empty_hint")}</div>
        </div>`;
        return;
      }
      el.innerHTML = data.raids.map(renderRaid).join("");
      if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
    }

    function wowheadLink(item) {
      if (!item.itemID) return item.itemName || "–";
      const base  = LANG === "de" ? "https://www.wowhead.com/de" : "https://www.wowhead.com";
      const href  = base + "/item=" + item.itemID + "?ilvl=289";
      const label = item.itemName || "Item #" + item.itemID;
      return `<a href="${href}" data-wowhead="item=${item.itemID}&ilvl=289" target="_blank">${label}</a>`;
    }

    function renderRaid(r) {
      const su      = SIGNUP_KEYS[r.signupStatus] || { key: "signup.none", cls: "muted" };
      const suLabel = t(su.key) || (r.signupStatus || "–");
      const diffCls = DIFF_CLASS[r.difficulty] || "badge-unknown";
      const prio    = r.prioFilled
        ? `<span class="meta-val ok">${t("raids.prio_filled")}</span>`
        : `<span class="meta-val warn">${t("raids.prio_empty")}</span>`;

      const groups = {};
      (r.prioItems || []).forEach(item => {
        const d = item.difficulty || "–";
        if (!groups[d]) groups[d] = [];
        groups[d].push(item);
      });
      Object.values(groups).forEach(arr => arr.sort((a, b) => (a.priority ?? 9) - (b.priority ?? 9)));

      const prioHtml = Object.entries(groups).map(([diff, items]) =>
        `<div class="prio-group">
          <div class="prio-group-title">${t("raids.prio_sel")} ${diff}</div>
          ${items.map(i =>
            `<div class="prio-item">
              <span class="prio-num">${t("raids.prio_label")} ${i.priority ?? "–"}</span>
              <span class="prio-item-name">${wowheadLink(i)}</span>
            </div>`).join("")}
        </div>`).join("");

      return `<div class="raid-card">
        <div class="raid-header">
          <span class="raid-name">${r.raidName || "–"}</span>
          <span class="badge ${diffCls}">${r.difficulty || "–"}</span>
          <span class="raid-date">${formatDate(r.scheduledAt)}</span>
        </div>
        <div class="raid-meta">
          <div class="meta-item">
            <span class="meta-key">${t("raids.signup")}</span>
            <span class="meta-val ${su.cls}">${suLabel}</span>
            ${r.characterName ? `<span style="display:flex;align-items:center;gap:4px;margin-top:3px">
              ${classIcon(r.wowClass, 14)}${specIcon(r.wowClass, r.wowSpec, 12)}
              <span style="font-size:11px;font-weight:600;color:${WOW_CLASS_COLORS[r.wowClass] || "var(--muted)"}">${r.characterName}</span>
            </span>` : ""}
          </div>
          <div class="meta-item">
            <span class="meta-key">${t("raids.prio_list")}</span>
            ${prio}
          </div>
        </div>
        ${prioHtml}
        <div class="raid-actions">
          <button class="btn btn-ghost" ${r.deadlinePassed ? 'disabled title="Anmeldefrist abgelaufen"' : ''}
            onclick="openSignupModal(${r.raidID}, '${r.signupStatus || ""}', ${!!r.deadlinePassed})">
            ${t("btn.change_signup")}
          </button>
          <button class="btn btn-ghost" onclick="openPrioModal(${r.raidID})">${t("btn.edit_prio")}</button>
        </div>
      </div>`;
    }

    async function loadSettings() {
      const s = await window.pywebview.api.get_settings_extended();
      document.getElementById("addonPath").value         = s.addon_path_base || "";
      document.getElementById("runOnStartup").checked    = !!s.run_on_startup;
      document.getElementById("closeToTray").checked     = s.close_to_tray !== false;
      document.getElementById("addonAutoUpdate").checked = !!s.addon_autoupdate;

      // Branch-Selector initialisieren
      const branch = s.addon_branch || "master";
      document.querySelectorAll(".lang-btn[id^='branch-']").forEach(b => {
        b.classList.toggle("active", b.id === "branch-" + branch);
      });

      API_URL = s.api_url || "";
      LANG = s.language || "de";
      applyLocale();

      // Lootliste Multi-Select
      const savedIds = s.excluded_patch_ids || [];
      _excludedPatchIds = new Set(savedIds);
      if (!_settingsPatches) {
        window.pywebview.api.get_patches().then(patches => {
          _settingsPatches = patches || [];
          _updateLootlisteBtnLabel(_settingsPatches);
        });
      } else {
        _updateLootlisteBtnLabel(_settingsPatches);
      }

      const accountDot = document.getElementById("accountDot");
      const accountSt  = document.getElementById("accountStatus");
      const accountSub = document.getElementById("accountSub");
      const logoutBtn  = document.getElementById("logoutBtn");
      if (s.logged_in) {
        accountDot.className   = "dot ok";
        accountSt.textContent  = t("settings.connected");
        accountSub.textContent = s.api_url || "";
        logoutBtn.style.display = "";
      } else {
        accountDot.className   = "dot error";
        accountSt.textContent  = t("settings.not_logged_in");
        accountSub.textContent = "";
        logoutBtn.style.display = "none";
      }
      document.getElementById("appVersion").textContent = "v" + (s.app_version || "0.1.0");
      loadVersionInfos();
    }

    async function loadVersionInfos() {
      document.getElementById("addonVersionInfo").textContent = t("settings.checking");
      document.getElementById("appVersionInfo").textContent   = t("settings.checking");
      const [av, sv] = await Promise.all([
        window.pywebview.api.check_addon_version(),
        window.pywebview.api.check_app_version(),
      ]);
      const addonEl = document.getElementById("addonVersionInfo");
      addonEl.textContent = av.upToDate
        ? `v${av.current} — ${t("settings.up_to_date")}`
        : `v${av.current} → v${av.latest}`;
      addonEl.className = "version-latest " + (av.upToDate ? "uptodate" : "outdated");
      const appEl = document.getElementById("appVersionInfo");
      appEl.textContent = sv.upToDate
        ? `v${sv.current} — ${t("settings.up_to_date")}`
        : `v${sv.current} → v${sv.latest}`;
      appEl.className = "version-latest " + (sv.upToDate ? "uptodate" : "outdated");
    }

    async function browseAddon() {
      const result = await window.pywebview.api.browse_folder();
      if (result) document.getElementById("addonPath").value = result;
    }
    async function saveAddonPath() {
      await window.pywebview.api.save_addon_path(document.getElementById("addonPath").value.trim());
    }
    async function saveSetting(key, value) { await window.pywebview.api.save_setting(key, value); }
    async function doLogout()      { await window.pywebview.api.logout(); }
    async function doAddonUpdate() {
      document.getElementById("addonUpdateBtn").disabled = true;
      document.getElementById("addonVersionInfo").textContent = t("settings.checking");
      await window.pywebview.api.update_addon_now();
      setTimeout(loadVersionInfos, 3000);
      document.getElementById("addonUpdateBtn").disabled = false;
    }
    async function doAppUpdate() {
      document.getElementById("appUpdateBtn").disabled = true;
      document.getElementById("appVersionInfo").textContent = t("settings.checking");
      await window.pywebview.api.update_app_now();
    }

    // ── Charakterverwaltung ───────────────────────────────
    let API_URL = "";

    const WOW_CLASSES_DATA = {
      "Todesritter":  { color:"#C41E3A", icon:"deathknight", specs:{"Blut":"deathknight_blood","Frost":"deathknight_frost","Unheilig":"deathknight_unholy"} },
      "Dämonenjäger": { color:"#A330C9", icon:"demonhunter",  specs:{"Verwüstung":"demonhunter_havoc","Rachsucht":"demonhunter_vengeance","Verschlinger":"demonhunter_devourer"} },
      "Krieger":      { color:"#C69B6D", icon:"warrior",      specs:{"Waffen":"warrior_arms","Furor":"warrior_fury","Schutz":"warrior_protection"} },
      "Mönch":        { color:"#00FF98", icon:"monk",         specs:{"Braumeister":"monk_brewmaster","Nebelwirker":"monk_mistweaver","Windläufer":"monk_windwalker"} },
      "Druide":       { color:"#FF7C0A", icon:"druid",        specs:{"Gleichgewicht":"druid_balance","Wildheit":"druid_feral","Wächter":"druid_guardian","Wiederherstellung":"druid_restoration"} },
      "Paladin":      { color:"#F48CBA", icon:"paladin",      specs:{"Heilig":"paladin_holy","Schutz":"paladin_protection","Vergeltung":"paladin_retribution"} },
      "Schurke":      { color:"#FFF468", icon:"rogue",        specs:{"Meucheln":"rogue_assassination","Gesetzlosigkeit":"rogue_outlaw","Täuschung":"rogue_subtlety"} },
      "Jäger":        { color:"#AAD372", icon:"hunter",       specs:{"Tierherrschaft":"hunter_beast_mastery","Treffsicherheit":"hunter_marksmanship","Überleben":"hunter_survival"} },
      "Magier":       { color:"#3FC7EB", icon:"mage",         specs:{"Arkan":"mage_arcane","Feuer":"mage_fire","Frost":"mage_frost"} },
      "Hexenmeister": { color:"#8788EE", icon:"warlock",      specs:{"Gebrechen":"warlock_affliction","Dämonologie":"warlock_demonology","Zerstörung":"warlock_destruction"} },
      "Priester":     { color:"#FFFFFF", icon:"priest",       specs:{"Disziplin":"priest_discipline","Heilig":"priest_holy","Schatten":"priest_shadow"} },
      "Schamane":     { color:"#0070DD", icon:"shaman",       specs:{"Elementar":"shaman_elemental","Verstärkung":"shaman_enhancement","Wiederherstellung":"shaman_restoration"} },
      "Rufer":        { color:"#33937F", icon:"evoker",       specs:{"Verheerung":"evoker_devastation","Bewahrung":"evoker_preservation","Verstärkung":"evoker_augmentation"} },
    };

    function classIcon(wowClass, size=22) {
      const d = WOW_CLASSES_DATA[wowClass];
      if (!d || !API_URL) return "";
      return `<img src="${API_URL}/static/icons/wow/classes/${d.icon}.png" width="${size}" height="${size}" style="border-radius:4px;flex-shrink:0" onerror="this.style.display='none'">`;
    }
    function specIcon(wowClass, wowSpec, size=18) {
      const d = WOW_CLASSES_DATA[wowClass];
      if (!d || !API_URL) return "";
      const key = d.specs[wowSpec];
      if (!key) return "";
      return `<img src="${API_URL}/static/icons/wow/specs/${key}.png" width="${size}" height="${size}" style="border-radius:3px;flex-shrink:0" onerror="this.style.display='none'">`;
    }

    let _editingCharId = null;

    function renderCharList(chars) {
      const el = document.getElementById("charList");
      if (!chars || !chars.length) {
        el.innerHTML = `<div style="font-size:12px;color:var(--muted);padding:8px 0">${t("chars.new")}…</div>`;
        return;
      }
      el.innerHTML = chars.map(c => {
        const cls = WOW_CLASSES_DATA[c.wow_class] || {};
        const col = cls.color || "var(--muted)";
        const esc = v => String(v).replace(/&/g,"&amp;").replace(/"/g,"&quot;");
        return `<div class="char-card"
            data-char-id="${c.id}"
            data-char-name="${esc(c.name)}"
            data-char-class="${esc(c.wow_class)}"
            data-char-spec="${esc(c.wow_spec)}">
          ${classIcon(c.wow_class, 28)}
          ${specIcon(c.wow_class, c.wow_spec, 20)}
          <div class="char-info">
            <div class="char-name" style="color:${col}">${c.name}</div>
            <div class="char-spec">${c.wow_class} · ${c.wow_spec}</div>
          </div>
          ${c.is_active
            ? `<span class="char-active-badge">${t("chars.active")}</span>`
            : `<button class="btn-icon" onclick="activateChar(${c.id})">${t("chars.activate")}</button>`}
          <button class="btn-icon" onclick="openCharModalFromCard(this)">${t("chars.edit")}</button>
        </div>`;
      }).join("");
    }

    async function loadProfileAndChars() {
      const [profile, chars] = await Promise.all([
        window.pywebview.api.get_profile(),
        window.pywebview.api.get_characters(),
      ]);
      if (profile) {
        const dot = document.getElementById("profilAccountDot");
        const st  = document.getElementById("profilAccountStatus");
        const sub = document.getElementById("profilDiscord");
        if (dot) dot.className = "dot ok";
        if (st)  st.textContent = profile.username || "";
        if (sub) sub.innerHTML = profile.discordLinked
          ? `<span style="color:var(--ok)">&#9679;</span> ${t("chars.discord_linked")}: <strong>${profile.discordName}</strong>`
          : `<span style="color:var(--muted)">&#9679;</span> ${t("chars.discord_unlinked")}`;
        showAdminTab(profile.role || "", profile.id || null);
      }
      renderCharList(chars);
    }

    async function activateChar(charId) {
      await window.pywebview.api.activate_character(charId);
      loadProfileAndChars();
    }

    function openCharModalFromCard(btn) {
      const card = btn.closest(".char-card");
      openCharModal(
        Number(card.dataset.charId),
        card.dataset.charName,
        card.dataset.charClass,
        card.dataset.charSpec,
      );
    }

    function openCharModal(charId, name, wowClass, wowSpec) {
      _editingCharId = charId || null;
      const title = document.getElementById("charModalTitle");
      title.textContent = charId ? t("chars.modal_edit") : t("chars.modal_create");
      document.getElementById("charNameInput").value = name || "";
      document.getElementById("charFormError").style.display = "none";
      document.querySelectorAll("#charModal [data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));

      // Klassen-Dropdown befüllen
      const classSelect = document.getElementById("charClassSelect");
      classSelect.innerHTML = Object.keys(WOW_CLASSES_DATA).map(cls =>
        `<option value="${cls}" ${cls===wowClass?"selected":""}>${cls}</option>`
      ).join("");
      updateSpecOptions(wowSpec);
      document.getElementById("charModal").style.display = "flex";
    }

    function updateSpecOptions(preselect) {
      const cls   = document.getElementById("charClassSelect").value;
      const specs = Object.keys((WOW_CLASSES_DATA[cls] || {}).specs || {});
      document.getElementById("charSpecSelect").innerHTML = specs.map(s =>
        `<option value="${s}" ${s===preselect?"selected":""}>${s}</option>`
      ).join("");
    }

    function closeCharModal() {
      document.getElementById("charModal").style.display = "none";
    }

    async function submitCharModal() {
      const name     = document.getElementById("charNameInput").value.trim();
      const wowClass = document.getElementById("charClassSelect").value;
      const wowSpec  = document.getElementById("charSpecSelect").value;
      const errEl    = document.getElementById("charFormError");
      if (!name) { errEl.textContent = t("chars.name"); errEl.style.display = ""; return; }

      let res;
      if (_editingCharId) {
        res = await window.pywebview.api.update_character(_editingCharId, name, wowClass, wowSpec);
      } else {
        res = await window.pywebview.api.create_character(name, wowClass, wowSpec);
      }

      if (res && res.success) {
        closeCharModal();
        loadProfileAndChars();
      } else {
        const msg = (res && res.error === "name_taken") ? t("chars.error_name_taken") : (res && res.error) || "Fehler";
        errEl.textContent = msg;
        errEl.style.display = "";
      }
    }

    // ── News Modal ────────────────────────────────────────
    let _pendingNewsId   = null;
    let _newsResolve     = null;

    async function checkPendingNews() {
      const news = await window.pywebview.api.get_pending_news();
      if (!news) return true;  // keine News → weiter
      return new Promise(resolve => {
        _pendingNewsId = news.id;
        _newsResolve   = resolve;
        document.querySelectorAll("#newsModal [data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));
        document.getElementById("newsHeadline").textContent  = news.title || "";
        document.getElementById("newsBody").textContent      = news.content || "";
        const d = news.createdAt ? new Date(news.createdAt).toLocaleDateString(LANG==="de"?"de-DE":"en-GB") : "";
        document.getElementById("newsMetaLine").textContent  =
          `${t("news.by")} ${news.author || "–"}${d ? "  ·  " + d : ""}`;
        document.getElementById("newsModal").style.display = "flex";
      });
    }

    async function confirmNews() {
      if (_pendingNewsId) {
        await window.pywebview.api.confirm_news(_pendingNewsId);
        _pendingNewsId = null;
      }
      document.getElementById("newsModal").style.display = "none";
      if (_newsResolve) { _newsResolve(true); _newsResolve = null; }
    }

    // ── Signup Modal ──────────────────────────────────────
    const SIGNUP_OPTS = [
      { val: "angemeldet", i18n: "signup.angemeldet", api: "active",    cls: "s-ok"    },
      { val: "spaeter",    i18n: "signup.spaeter",    api: "late",      cls: "s-warn"  },
      { val: "vorlaeufig", i18n: "signup.vorlaeufig", api: "tentative", cls: "s-warn"  },
      { val: "bench",      i18n: "signup.bench",      api: "bench",     cls: "s-muted" },
      { val: "abgelehnt",  i18n: "signup.abgelehnt",  api: "absent",    cls: "s-error" },
    ];
    let _signupRaidID = null, _signupSel = null, _signupApiVal = null;

    async function openSignupModal(raidID, currentStatus, deadlinePassed) {
      if (!await checkPendingNews()) return;
      _signupRaidID = raidID;
      _signupSel    = currentStatus;
      const dlMsg = document.getElementById("signupDeadlineMsg");
      const opts  = document.getElementById("signupOptions");
      const btn   = document.getElementById("signupSaveBtn");
      document.querySelectorAll("#signupModal [data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));
      if (deadlinePassed) {
        dlMsg.style.display = ""; opts.innerHTML = ""; btn.disabled = true;
      } else {
        dlMsg.style.display = "none"; btn.disabled = false;
        opts.innerHTML = SIGNUP_OPTS.map(o =>
          `<button class="signup-opt ${o.cls} ${currentStatus===o.val?"selected":""}"
            data-val="${o.val}" data-api="${o.api}" onclick="selectSignupOpt(this)">
            ${t(o.i18n)}
          </button>`).join("");
        _signupApiVal = SIGNUP_OPTS.find(o => o.val === currentStatus)?.api || null;
      }
      document.getElementById("signupModal").style.display = "flex";
    }

    function selectSignupOpt(el) {
      document.querySelectorAll(".signup-opt").forEach(b => b.classList.remove("selected"));
      el.classList.add("selected");
      _signupSel    = el.dataset.val;
      _signupApiVal = el.dataset.api;
    }

    function closeSignupModal() { document.getElementById("signupModal").style.display = "none"; }

    async function submitSignup() {
      if (!_signupApiVal || !_signupRaidID) return;
      const btn = document.getElementById("signupSaveBtn");
      btn.disabled = true;
      const res = await window.pywebview.api.change_signup_status(_signupRaidID, _signupApiVal);
      btn.disabled = false;
      if (res && res.success) {
        closeSignupModal();
        const fresh = await window.pywebview.api.fetch_fresh_raid_data();
        if (fresh && fresh.raids) {
          document.getElementById("raidsContent").innerHTML = fresh.raids.map(renderRaid).join("");
          if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
        }
        window.pywebview.api.refresh();
      } else {
        const dlMsg = document.getElementById("signupDeadlineMsg");
        dlMsg.textContent = (res && res.error === "deadline_passed")
          ? t("signup.deadline_msg") : (res && res.error) || "Fehler";
        dlMsg.style.display = "";
      }
    }

    // ── Prio Modal ────────────────────────────────────────
    let _prioRaidID = null, _prioData = null, _prioDiff = null;
    let _prioEdits  = {};   // { diff: { 1: itemID|"pass"|null, 2:..., 3:... } }
    let _prioBoss   = { 1: "all", 2: "all", 3: "all" };

    async function openPrioModal(raidID) {
      if (!await checkPendingNews()) return;
      _prioRaidID = raidID;
      _prioData   = await window.pywebview.api.get_raid_loot(raidID);
      if (!_prioData) return;

      // Init edits from saved prios
      _prioEdits = {};
      for (const diff of ["normal", "heroic", "mythic"]) {
        _prioEdits[diff] = { 1: null, 2: null, 3: null };
        for (const s of ((_prioData.prios || {})[diff] || [])) {
          _prioEdits[diff][s.slot] = s.pass ? "pass" : (s.itemID ? String(s.itemID) : null);
        }
      }
      _prioBoss  = { 1: "all", 2: "all", 3: "all" };
      _prioDiff  = _prioData.raidDiff || "heroic";

      document.getElementById("charFilterChk").checked = true;
      document.getElementById("superPrioBadge").style.display = _prioData.superPrio ? "" : "none";
      document.querySelectorAll("#prioModal [data-i18n]").forEach(el => el.textContent = t(el.dataset.i18n));

      const diffLabels = {
        normal: "Normal",
        heroic: LANG === "de" ? "Heroisch" : "Heroic",
        mythic: LANG === "de" ? "Mythisch" : "Mythic",
      };
      const hasSavedPrio = d => ((_prioData.prios || {})[d] || []).some(s => !s.pass && s.itemID);
      document.getElementById("prioDiffTabs").innerHTML = ["normal","heroic","mythic"].map(d =>
        `<button class="diff-tab ${d===_prioDiff?"active":""}" data-diff="${d}" onclick="switchPrioDiff('${d}')">
          ${diffLabels[d]}${hasSavedPrio(d) ? '<span class="diff-tab-dot"></span>' : ''}
        </button>`
      ).join("");

      document.getElementById("prioModal").style.display = "flex";
      renderPrioColumns();
    }

    function closePrioModal() { document.getElementById("prioModal").style.display = "none"; }

    function switchPrioDiff(diff) {
      _prioDiff = diff;
      _prioBoss = { 1: "all", 2: "all", 3: "all" };
      document.querySelectorAll(".diff-tab").forEach(b =>
        b.classList.toggle("active", b.dataset.diff === diff));
      renderPrioColumns();
    }

    function applyCharFilter() { renderPrioColumns(); }

    function _isCharFiltered(item) {
      if (!document.getElementById("charFilterChk").checked) return false;
      const cf = _prioData.charFilter || {};
      if (!item.armorType && !item.weaponType) return false;  // trinkets/rings always show
      const armorOk  = item.armorType  && (cf.armorTypes  || []).includes(item.armorType);
      const weaponOk = item.weaponType && (cf.weaponTypes || []).includes(item.weaponType);
      return !(armorOk || weaponOk);
    }

    function _isItemDisabled(slot, itemID) {
      if (_prioData.superPrio) return false;  // superPrio: freie Auswahl, Validierung erst beim Speichern
      const sel = _prioEdits[_prioDiff];
      const others = [1,2,3].filter(s => s !== slot);
      return others.some(s => sel[s] === itemID);  // kein superPrio: kein doppeltes Item
    }

    function renderPrioColumns() {
      const sel    = _prioEdits[_prioDiff];
      const bosses = (_prioData.bosses || []).map(b => b.bossName);
      const base   = LANG === "de" ? "https://www.wowhead.com/de" : "https://www.wowhead.com";

      // Summary
      document.getElementById("prioSummary").innerHTML = [1,2,3].map(slot => {
        const v = sel[slot];
        let valHtml;
        if (v === "pass") {
          valHtml = `<span class="prio-sum-val passed">${t("prio.passed")}</span>`;
        } else if (v) {
          valHtml = `<span class="prio-sum-val"><a href="${base}/item=${v}?ilvl=289" data-wowhead="item=${v}&ilvl=289" onclick="return false">Item #${v}</a></span>`;
        } else {
          valHtml = `<span class="prio-sum-val" style="color:var(--muted)">–</span>`;
        }
        return `<div class="prio-sum-slot">
          <div class="prio-sum-label">${t("raids.prio_label")} ${slot}</div>${valHtml}</div>`;
      }).join("");

      // Columns
      document.getElementById("prioColumns").innerHTML = [1,2,3].map(slot => {
        const isPass = sel[slot] === "pass";
        const currentBossLabel = _prioBoss[slot] === "all" ? t("prio.all_bosses") : _prioBoss[slot];
        const bossOpts = [`<div class="boss-sel-opt ${_prioBoss[slot]==="all"?"active":""}" data-boss="all" onclick="selectBossOpt(this,${slot})">${t("prio.all_bosses")}</div>`]
          .concat(bosses.map(b => `<div class="boss-sel-opt ${_prioBoss[slot]===b?"active":""}" data-boss="${b.replace(/"/g,'&quot;')}" onclick="selectBossOpt(this,${slot})">${b}</div>`))
          .join("");

        const EXCLUDED_CLASSES = ["housing", "recipes"];
        const items = [];
        for (const boss of (_prioData.bosses || [])) {
          if (_prioBoss[slot] !== "all" && boss.bossName !== _prioBoss[slot]) continue;
          for (const item of (boss.items || [])) {
            if (EXCLUDED_CLASSES.includes(item.itemClass)) continue;
            items.push({...item, id: String(item.itemID)});
          }
        }

        const itemsHtml = items.map(item => {
          const disabled = _isItemDisabled(slot, item.id);
          const selected = sel[slot] === item.id;
          const hidden   = _isCharFiltered(item) ? "pi-hidden" : "";
          const click    = disabled ? "" : `onclick="selectPrioItem(${slot},'${item.id}')"`;
          return `<div class="pi-btn ${selected?"pi-selected":""} ${disabled?"pi-disabled":""} ${hidden}" ${click}>
            <a href="${base}/item=${item.id}?ilvl=289" data-wowhead="item=${item.id}&ilvl=289" onclick="event.preventDefault()">Item #${item.id}</a>
          </div>`;
        }).join("");

        return `<div class="prio-col">
          <div class="prio-col-title">${t("raids.prio_label")} ${slot}</div>
          <button class="prio-pass-btn ${isPass?"active":""}" onclick="togglePrioPass(${slot})">${t("prio.pass")}</button>
          <div class="boss-select">
            <div class="boss-sel-val" onclick="toggleBossDd(this)">${currentBossLabel}</div>
            <div class="boss-sel-opts">${bossOpts}</div>
          </div>
          <div class="prio-item-list">${itemsHtml}</div>
        </div>`;
      }).join("");

      if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
    }

    function selectPrioItem(slot, itemID) {
      const sel = _prioEdits[_prioDiff];
      sel[slot] = (sel[slot] === itemID) ? null : itemID;
      renderPrioColumns();
    }

    function togglePrioPass(slot) {
      const sel = _prioEdits[_prioDiff];
      sel[slot] = (sel[slot] === "pass") ? null : "pass";
      renderPrioColumns();
    }

    function toggleBossDd(el) {
      const opts = el.nextElementSibling;
      const isOpen = opts.classList.contains("open");
      document.querySelectorAll(".boss-sel-opts.open").forEach(o => o.classList.remove("open"));
      if (!isOpen) opts.classList.add("open");
    }

    function selectBossOpt(el, slot) {
      const boss = el.dataset.boss;
      el.closest(".boss-sel-opts").querySelectorAll(".boss-sel-opt").forEach(o => o.classList.remove("active"));
      el.classList.add("active");
      el.closest(".boss-sel-opts").previousElementSibling.textContent = el.textContent;
      el.closest(".boss-sel-opts").classList.remove("open");
      setBossFilter(slot, boss);
    }

    document.addEventListener("click", e => {
      if (!e.target.closest(".boss-select"))
        document.querySelectorAll(".boss-sel-opts.open").forEach(o => o.classList.remove("open"));
    });

    function setBossFilter(slot, boss) {
      _prioBoss[slot] = boss;
      renderPrioColumns();
    }

    async function submitPrio() {
      const sel = _prioEdits[_prioDiff];

      // Validierung: bei SuperPrio darf kein Item genau 2x vorkommen
      if (_prioData.superPrio) {
        const counts = {};
        [1,2,3].forEach(s => {
          if (sel[s] && sel[s] !== "pass") counts[sel[s]] = (counts[sel[s]] || 0) + 1;
        });
        if (Object.values(counts).some(c => c === 2)) {
          document.getElementById("prioErrorMsg").style.display = "";
          return;
        }
      }
      document.getElementById("prioErrorMsg").style.display = "none";

      const slots = [1,2,3].map(slot => ({
        slot,
        itemID: (sel[slot] && sel[slot] !== "pass") ? Number(sel[slot]) : null,
        pass:   sel[slot] === "pass",
      }));
      try {
        const res = await window.pywebview.api.save_prio(Number(_prioRaidID), _prioDiff, slots);
        if (res && res.success) {
          closePrioModal();
          const fresh = await window.pywebview.api.fetch_fresh_raid_data();
          if (fresh && fresh.raids) {
            document.getElementById("raidsContent").innerHTML = fresh.raids.map(renderRaid).join("");
            if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
          }
          window.pywebview.api.refresh();
        } else {
          console.error("save_prio failed:", res);
        }
      } catch(e) {
        console.error("save_prio error:", e);
      }
    }

    // ── Lootliste (Settings) ──────────────────────────
    let _settingsPatches = null;
    let _excludedPatchIds = new Set();  // leere Set = alle ausgewählt

    function _updateLootlisteBtnLabel(patches) {
      const btn = document.getElementById("lootlisteBtnLabel");
      if (!btn) return;
      const total = (patches || []).length;
      if (!total) { btn.textContent = "–"; return; }
      if (_excludedPatchIds.size === 0) {
        btn.textContent = t("settings.ll_all_selected") || "Alle ausgewählt";
      } else {
        const selectedCount = total - _excludedPatchIds.size;
        const label = LANG === "en" ? "selected" : "ausgewählt";
        btn.textContent = `${selectedCount} / ${total} ${label}`;
      }
    }

    async function openLootlisteModal() {
      if (!_settingsPatches) {
        _settingsPatches = await window.pywebview.api.get_patches();
      }
      const patches = _settingsPatches || [];
      const list = document.getElementById("lootlisteChecklist");
      list.innerHTML = patches.map(p => {
        const checked = !_excludedPatchIds.has(p.id) ? "checked" : "";
        const label   = p.name + (p.is_archived ? " \u2713" : "");
        return `<label style="display:flex;align-items:center;gap:10px;cursor:pointer;padding:6px 0;border-bottom:1px solid var(--border)">
          <input type="checkbox" data-pid="${p.id}" ${checked}
            style="width:16px;height:16px;accent-color:var(--gold);cursor:pointer;flex-shrink:0">
          <span style="font-size:13px">${label}</span>
        </label>`;
      }).join("");
      document.getElementById("lootlisteModal").style.display = "flex";
    }

    function closeLootlisteModal() {
      document.getElementById("lootlisteModal").style.display = "none";
    }

    function lootlisteSelectAll() {
      document.querySelectorAll("#lootlisteChecklist input[type=checkbox]")
        .forEach(cb => cb.checked = true);
    }

    function lootlisteSelectNone() {
      document.querySelectorAll("#lootlisteChecklist input[type=checkbox]")
        .forEach(cb => cb.checked = false);
    }

    async function saveLootlisteModal() {
      const patches = _settingsPatches || [];
      const excluded = [...document.querySelectorAll("#lootlisteChecklist input[type=checkbox]")]
        .filter(cb => !cb.checked).map(cb => Number(cb.dataset.pid));
      _excludedPatchIds = new Set(excluded);
      await window.pywebview.api.save_setting("excluded_patch_ids", excluded);
      _updateLootlisteBtnLabel(patches);
      closeLootlisteModal();
    }

    // ── Statistik-Tab ─────────────────────────────────
    let _statsType    = "loothistorie";
    let _statsPatchId = null;
    let _statsDiff    = "all";
    let _statsScope   = "all";
    let _statsPatches = null;

    function toggleStatsFilterDd(ddId) {
      const dd     = document.getElementById(ddId);
      const isOpen = dd.classList.contains("open");
      document.querySelectorAll(".stats-dd.open,.boss-sel-opts.open").forEach(o => o.classList.remove("open"));
      if (!isOpen) dd.classList.add("open");
    }

    function selectStatsType(val) {
      _statsType = val;
      document.querySelectorAll("#statsTypeDd .boss-sel-opt").forEach(o =>
        o.classList.toggle("active", o.dataset.val === val));
      document.getElementById("statsTypeDd").classList.remove("open");
      const sel = document.getElementById("statsTypeSel");
      const map = { loothistorie: "stats.loothistorie", player_stats: "stats.player_stats", dropchance: "stats.dropchance" };
      sel.textContent = t(map[val] || val);
      document.getElementById("statsScopeWrap").style.display = val === "dropchance" ? "none" : "";
      loadStats();
    }

    function selectStatsDiff(val) {
      _statsDiff = val;
      document.querySelectorAll("#statsDiffDd .boss-sel-opt").forEach(o =>
        o.classList.toggle("active", o.dataset.val === val));
      document.getElementById("statsDiffDd").classList.remove("open");
      const diffLabels = { all: t("stats.all_diff"), normal: "Normal",
        heroic: LANG==="de" ? "Heroisch" : "Heroic",
        mythic: LANG==="de" ? "Mythisch" : "Mythic" };
      document.getElementById("statsDiffSel").textContent = diffLabels[val] || val;
      loadStats();
    }

    function selectStatsScope(val) {
      _statsScope = val;
      document.querySelectorAll("#statsScopeDd .boss-sel-opt").forEach(o =>
        o.classList.toggle("active", o.dataset.val === val));
      document.getElementById("statsScopeDd").classList.remove("open");
      const keyMap = { all: "stats.scope_all", ms: "stats.scope_ms", os: "stats.scope_os" };
      document.getElementById("statsScopeSel").textContent = t(keyMap[val] || val);
      loadStats();
    }

    function selectStatsPatch(patchId, label) {
      _statsPatchId = patchId;
      document.querySelectorAll("#statsPatchDd .boss-sel-opt").forEach(o =>
        o.classList.toggle("active", String(o.dataset.val) === String(patchId)));
      document.getElementById("statsPatchDd").classList.remove("open");
      document.getElementById("statsPatchSel").textContent = label;
      loadStats();
    }

    async function _ensureStatsPatches() {
      if (_statsPatches !== null) return;
      _statsPatches = await window.pywebview.api.get_patches();
      const dd = document.getElementById("statsPatchDd");
      const allLabel = t("stats.all_patches");
      dd.innerHTML = [`<div class="boss-sel-opt ${_statsPatchId===null?"active":""}" data-val="null" onclick="selectStatsPatch(null,'${allLabel}')">${allLabel}</div>`]
        .concat((_statsPatches || []).map(p => {
          const label = p.name + (p.is_archived ? " (\u2713)" : "");
          return `<div class="boss-sel-opt ${_statsPatchId===p.id?"active":""}" data-val="${p.id}" onclick="selectStatsPatch(${p.id},'${p.name.replace(/'/g,"\\'")}')">
            ${label}
          </div>`;
        })).join("");
      document.getElementById("statsPatchSel").textContent =
        _statsPatchId ? (_statsPatches||[]).find(p=>p.id===_statsPatchId)?.name || "–" : allLabel;
    }

    function _initStatsFilterLabels() {
      const typeSel  = document.getElementById("statsTypeSel");
      const diffSel  = document.getElementById("statsDiffSel");
      const scopeSel = document.getElementById("statsScopeSel");
      const typeMap  = { loothistorie: "stats.loothistorie", player_stats: "stats.player_stats", dropchance: "stats.dropchance" };
      if (typeSel)  typeSel.textContent  = t(typeMap[_statsType] || "stats.loothistorie");
      const diffLabels = { all: t("stats.all_diff"), normal: "Normal",
        heroic: LANG==="de" ? "Heroisch" : "Heroic",
        mythic: LANG==="de" ? "Mythisch" : "Mythic" };
      if (diffSel)  diffSel.textContent  = diffLabels[_statsDiff] || _statsDiff;
      if (scopeSel) {
        const scopeMap = { all: "stats.scope_all", ms: "stats.scope_ms", os: "stats.scope_os" };
        scopeSel.textContent = t(scopeMap[_statsScope] || "stats.scope_all");
      }
    }

    async function loadStats() {
      _initStatsFilterLabels();
      await _ensureStatsPatches();
      const el = document.getElementById("statsContent");
      el.innerHTML = `<div class="empty-state"><div class="empty-state-text">${t("stats.loading")}</div></div>`;
      const data = await window.pywebview.api.get_stats_filtered(_statsPatchId, _statsDiff, _statsScope);
      if (!data || (!data.lootHistory && !data.playerStats && !data.dropchance)) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-text">${t("stats.no_data")}</div></div>`;
        return;
      }
      if (_statsType === "loothistorie") el.innerHTML = _renderLootHistory(data.lootHistory || []);
      else if (_statsType === "player_stats") el.innerHTML = _renderPlayerStats(data.playerStats || []);
      else el.innerHTML = _renderDropchance(data.dropchance || []);
      if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
    }

    document.addEventListener("click", e => {
      if (!e.target.closest(".boss-select") && !e.target.closest(".stats-dd"))
        document.querySelectorAll(".stats-dd.open").forEach(o => o.classList.remove("open"));
    });

    function _parseDate(val) {
      if (!val) return null;
      const d = typeof val === "number" ? new Date(val * 1000) : new Date(val);
      return isNaN(d.getTime()) ? null : d;
    }
    function _fmtDate(val) {
      const d = _parseDate(val);
      return d ? d.toLocaleDateString(LANG==="de"?"de-DE":"en-GB",{day:"2-digit",month:"2-digit",year:"numeric"}) : "–";
    }
    function _fmtDateTime(val) {
      const d = _parseDate(val);
      if (!d) return "–";
      return d.toLocaleDateString(LANG==="de"?"de-DE":"en-GB",{day:"2-digit",month:"2-digit",year:"numeric"})
           + "  " + d.toLocaleTimeString(LANG==="de"?"de-DE":"en-GB",{hour:"2-digit",minute:"2-digit"});
    }
    function _fmtTime(val) {
      const d = _parseDate(val);
      return d ? d.toLocaleTimeString(LANG==="de"?"de-DE":"en-GB",{hour:"2-digit",minute:"2-digit"}) : "";
    }

    function _wowheadLink(itemID, itemName) {
      if (!itemID) return itemName || "–";
      const base  = LANG === "de" ? "https://www.wowhead.com/de" : "https://www.wowhead.com";
      return `<a href="${base}/item=${itemID}?ilvl=289" data-wowhead="item=${itemID}&ilvl=289" target="_blank">${itemName || "Item #"+itemID}</a>`;
    }

    function _renderLootHistory(history) {
      if (!history.length) return `<div class="empty-state"><div class="empty-state-text">${t("stats.no_data")}</div></div>`;
      const cards = history.map(raid => {
        const diffBadge = raid.difficulty ? `<span class="badge ${DIFF_CLASS[raid.difficulty]||"badge-unknown"}">${raid.difficulty}</span>` : "";
        const dateDisp  = _fmtDateTime(raid.date || raid.raid_date || raid.timestamp);
        let filteredEntries = raid.entries || [];
        const _isMS = e => { const t = (e.lootType||"").toLowerCase(); return t === "ms" || t === "main" || t === "mainspec"; };
        if (_statsScope === "ms") filteredEntries = filteredEntries.filter(_isMS);
        else if (_statsScope === "os") filteredEntries = filteredEntries.filter(e => !_isMS(e));
        if (!filteredEntries.length) return "";
        const entries   = filteredEntries.map(e => {
          const timeStr = _fmtTime(e.timestamp);
          const typeCls = _isMS(e) ? "var(--ok)" : "var(--muted)";
          return `<div class="lh-entry">
            <span class="lh-time">${timeStr}</span>
            <span class="lh-boss">${e.boss || "–"}</span>
            <span class="lh-item">${_wowheadLink(e.itemID, e.itemName)}</span>
            <span>${e.player || "–"}</span>
            <span class="lh-type" style="color:${typeCls}">${e.lootType || "–"}</span>
          </div>`;
        }).join("");
        return `<div class="stats-card">
          <div class="stats-card-header">
            <span class="stats-card-title">${raid.raidName || "–"}</span>
            <span class="raid-date">${dateDisp}</span>
            ${diffBadge}
          </div>
          <div class="lh-table">
            <div class="lh-head">
              <span>${t("stats.time")}</span>
              <span>${t("stats.boss")}</span>
              <span>${t("stats.item")}</span>
              <span>${t("stats.player")}</span>
              <span>${t("stats.type")}</span>
            </div>
            ${entries}
          </div>
        </div>`;
      }).join("");
      return cards || `<div class="empty-state"><div class="empty-state-text">${t("stats.no_data")}</div></div>`;
    }

    function _renderPlayerStats(stats) {
      if (!stats.length) return `<div class="empty-state"><div class="empty-state-text">${t("stats.no_data")}</div></div>`;
      const rows = stats.map(ps => {
        const color      = WOW_CLASS_COLORS[ps.wowClass] || "var(--text)";
        const avg        = ps.avgPerRaid !== undefined ? Number(ps.avgPerRaid).toFixed(2) : "–";
        const pct        = ps.percentage !== undefined ? Number(ps.percentage).toFixed(1)+"%" : "–";
        const raidsTotal    = ps.raidsTotal ?? ps.raids_total ?? ps.totalRaids ?? ps.total_raids;
        const raidsAttended = ps.raidsAttended ?? ps.raids_attended ?? ps.attended ?? ps.raids;
        const raidsFmt      = raidsTotal !== undefined && raidsTotal !== null
          ? `${raidsAttended ?? "–"}/${raidsTotal}` : `${raidsAttended ?? "–"}`;
        return `<div class="ps-row">
          <span style="color:${color};font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${ps.playerName || ps.player_name || "–"}</span>
          <span>${ps.lootTotal ?? ps.loot_total ?? "–"}</span>
          <span style="color:var(--ok)!important">${ps.lootMS ?? ps.loot_ms ?? "–"}</span>
          <span>${ps.lootOS ?? ps.loot_os ?? "–"}</span>
          <span>${raidsFmt}</span>
          <span>${avg}</span>
          <span>${pct}</span>
        </div>`;
      }).join("");
      return `<div class="stats-card">
        <div class="ps-table">
          <div class="ps-head">
            <span>${t("stats.player")}</span>
            <span>${t("stats.total")}</span>
            <span>${t("stats.ms")}</span>
            <span>${t("stats.os")}</span>
            <span>${t("stats.raids_col")}</span>
            <span>${t("stats.avg")}</span>
            <span>%</span>
          </div>
          ${rows}
        </div>
      </div>`;
    }

    function _renderDropchance(dc) {
      if (!dc.length) return `<div class="empty-state"><div class="empty-state-text">${t("stats.no_data")}</div></div>`;
      return dc.map(boss => {
        const items = (boss.items || []).map(item => {
          // field may be "chance", "dropchance", or calculated from drops/kills
          let rawChance = item.chance ?? item.dropchance;
          if (rawChance === undefined || rawChance === null) {
            rawChance = item.kills > 0 ? (item.drops / item.kills * 100) : 0;
          }
          // some backends return 0–1 decimal instead of 0–100
          if (rawChance > 0 && rawChance < 1) rawChance *= 100;
          const chancePct = Number(rawChance).toFixed(1);
          return `<div class="dc-row">
            <span class="dc-item">${_wowheadLink(item.itemID, item.itemName)}</span>
            <span>${item.drops ?? 0}</span>
            <span>${item.kills ?? 0}</span>
            <span style="color:var(--gold)">${chancePct}%</span>
          </div>`;
        }).join("");
        return `<div class="stats-card">
          <div class="stats-card-header">
            <span class="stats-card-title">${boss.bossName || "–"}</span>
          </div>
          <div class="dc-table">
            <div class="dc-head">
              <span>${t("stats.item")}</span>
              <span>${t("stats.drops")}</span>
              <span>${t("stats.kills")}</span>
              <span>${t("stats.chance")}</span>
            </div>
            ${items || `<div style="color:var(--muted);font-size:12px;padding:6px 0">${t("stats.no_data")}</div>`}
          </div>
        </div>`;
      }).join("");
    }

    // ── Admin-Tab ─────────────────────────────────────
    let _adminSubTab    = "raids";
    let _adminPatches   = null;   // patches for raid form
    let _raidModalId    = null;
    let _adminSelfRole  = null;
    let _adminSelfId    = null;

    const DIFF_CLASS_RAW = { normal: "badge-normal", heroic: "badge-heroic", mythic: "badge-mythic" };
    function diffLabel(d) {
      const de = { normal:"Normal", heroic:"Heroisch", mythic:"Mythisch" };
      const en = { normal:"Normal", heroic:"Heroic",   mythic:"Mythic"   };
      return (LANG === "de" ? de : en)[d] || d;
    }
    function diffBadge(d) {
      return `<span class="badge ${DIFF_CLASS_RAW[d]||"badge-unknown"}">${diffLabel(d)}</span>`;
    }
    function raidDateStr(ts) { return _fmtDateTime(ts); }

    function showAdminTab(role, userId) {
      _adminSelfRole = role;
      _adminSelfId   = userId;
      const visible = ["admin","superadmin"].includes(role);
      document.querySelectorAll("[data-tab='admin']").forEach(el => el.style.display = visible ? "" : "none");
      document.querySelectorAll("[data-tab='blacklist']").forEach(el => el.style.display = visible ? "" : "none");
      const branchRow = document.getElementById("addonBranchRow");
      if (branchRow) branchRow.style.display = visible ? "" : "none";
    }

    // ── Blacklist ─────────────────────────────────────
    async function loadBlacklist() {
      const el = document.getElementById("blList");
      el.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:8px 0">${t("stats.loading")}</div>`;
      const data  = await window.pywebview.api.get_blacklist();
      const items = data || [];
      if (!items.length) {
        el.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:8px 0">${t("blacklist.empty")}</div>`;
        return;
      }
      el.innerHTML = items.map(it => `
        <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="min-width:160px">${_wowheadLink(it.item_id, null)}</span>
          <span style="flex:1;color:var(--muted);font-size:12px">${it.note || ""}</span>
          <span style="font-size:11px;color:var(--muted)">${it.added_by || ""}</span>
          <button class="btn btn-danger" style="padding:3px 10px;font-size:11px" onclick="blRemoveItem(${it.id})">${t("btn.delete")}</button>
        </div>`).join("");
      if (typeof $WowheadPower !== "undefined") $WowheadPower.refreshLinks();
    }

    async function blAddItem() {
      const errEl  = document.getElementById("blAddError");
      const itemId = parseInt(document.getElementById("blItemId").value, 10);
      const note   = document.getElementById("blNote").value.trim();
      errEl.style.display = "none";
      if (!itemId || itemId <= 0) {
        errEl.textContent = t("blacklist.error_id");
        errEl.style.display = "";
        return;
      }
      const res = await window.pywebview.api.add_blacklist_item(itemId, note);
      if (res && res.success) {
        document.getElementById("blItemId").value = "";
        document.getElementById("blNote").value   = "";
        loadBlacklist();
      } else {
        errEl.textContent = (res && res.error) || t("blacklist.error_add");
        errEl.style.display = "";
      }
    }

    async function blRemoveItem(blId) {
      await window.pywebview.api.remove_blacklist_item(blId);
      loadBlacklist();
    }

    function switchAdminSub(name) {
      _adminSubTab = name;
      document.querySelectorAll(".admin-sub-btn").forEach(b =>
        b.classList.toggle("active", b.dataset.sub === name));
      document.querySelectorAll(".admin-sub-pane").forEach(p =>
        p.classList.toggle("active", p.id === "admin-" + name));
      if (name === "raids")   loadAdminRaids();
      else if (name === "archive") loadAdminArchive();
      else if (name === "users")   loadAdminUsers();
    }

    // ── Raids ────────────────────────────────────────
    async function loadAdminRaids() {
      const el = document.getElementById("admin-raids-list");
      el.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:8px 0">${t("stats.loading")}</div>`;
      const data  = await window.pywebview.api.admin_get_raids();
      const raids = (data && data.raids) || [];
      document.getElementById("adminRaidsCount").textContent = raids.length ? raids.length + " Raids" : "";
      if (!raids.length) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-text">${t("admin.no_raids")}</div></div>`;
        return;
      }
      el.innerHTML = raids.map(r => `
        <div class="admin-raid-row">
          <div class="pub-dot ${r.is_published?"yes":"no"}" title="${t(r.is_published?"admin.published":"admin.unpublished")}"></div>
          <div class="admin-raid-info">
            <div class="admin-raid-name">${r.name || "–"}</div>
            <div class="admin-raid-meta">${raidDateStr(r.raid_date)} ${diffBadge(r.difficulty)}</div>
          </div>
          <div class="admin-raid-actions">
            <button class="btn-icon" onclick="openRaidModal(${r.id})">${t("admin.edit")}</button>
            <button class="btn-icon" onclick="adminTogglePublish(${r.id}, this)">
              ${r.is_published ? t("admin.unpublish") : t("admin.publish")}
            </button>
            <button class="btn-icon" style="color:var(--warn)" onclick="adminArchiveRaid(${r.id}, this)">${t("admin.archive_action")}</button>
          </div>
        </div>`).join("");
    }

    async function adminTogglePublish(raidId, btn) {
      btn.disabled = true;
      const res = await window.pywebview.api.admin_toggle_publish(raidId);
      btn.disabled = false;
      if (res && res.success) loadAdminRaids();
    }

    function _confirmBtn(btn, label, cb) {
      if (btn.dataset.confirming) return;
      btn.dataset.confirming = "1";
      const orig = btn.textContent;
      btn.textContent = t(label) + " ✓";
      btn.style.color = "var(--error)";
      const t2 = setTimeout(() => {
        delete btn.dataset.confirming;
        btn.textContent = orig;
        btn.style.color = "";
      }, 2500);
      btn.onclick = async () => {
        clearTimeout(t2);
        btn.onclick = null;
        btn.disabled = true;
        await cb();
      };
    }

    function adminArchiveRaid(raidId, btn) {
      _confirmBtn(btn, "admin.confirm_archive", async () => {
        const res = await window.pywebview.api.admin_archive_raid(raidId);
        if (res && res.success) loadAdminRaids();
      });
    }

    // ── Archiv ───────────────────────────────────────
    async function loadAdminArchive() {
      const el = document.getElementById("admin-archive-list");
      el.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:8px 0">${t("stats.loading")}</div>`;
      const data  = await window.pywebview.api.admin_get_archive();
      const raids = (data && data.raids) || [];
      if (!raids.length) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-text">${t("admin.no_raids")}</div></div>`;
        return;
      }
      el.innerHTML = raids.map(r => `
        <div class="admin-raid-row">
          <div class="admin-raid-info">
            <div class="admin-raid-name">${r.name || "–"}</div>
            <div class="admin-raid-meta">${raidDateStr(r.raid_date)} ${diffBadge(r.difficulty)}</div>
          </div>
          <div class="admin-raid-actions">
            <button class="btn-icon" onclick="adminUnarchiveRaid(${r.id}, this)">${t("admin.unarchive")}</button>
            <button class="btn-icon" style="color:var(--error)" onclick="adminDeleteRaid(${r.id}, this)">${t("admin.delete")}</button>
          </div>
        </div>`).join("");
    }

    function adminUnarchiveRaid(raidId, btn) {
      _confirmBtn(btn, "admin.unarchive", async () => {
        const res = await window.pywebview.api.admin_unarchive_raid(raidId);
        if (res && res.success) loadAdminArchive();
      });
    }

    function adminDeleteRaid(raidId, btn) {
      _confirmBtn(btn, "admin.confirm_delete", async () => {
        const res = await window.pywebview.api.admin_delete_raid(raidId);
        if (res && res.success) loadAdminArchive();
      });
    }

    // ── Benutzer ─────────────────────────────────────
    const ROLE_OPTS     = ["superadmin","admin","officer","raider","inactive","pending"];
    const PRIO_CAP_OPTS = ["standard","max_prio_2","max_prio_3"];
    const ROLE_COLORS   = {
      superadmin: "var(--gold)", admin: "var(--info)", officer: "var(--warn)",
      raider: "var(--ok)", inactive: "var(--muted)", pending: "var(--error)",
    };

    async function loadAdminUsers() {
      const el = document.getElementById("admin-users-list");
      el.innerHTML = `<div style="color:var(--muted);font-size:12px;padding:8px 0">${t("stats.loading")}</div>`;
      const data  = await window.pywebview.api.admin_get_users();
      const users = (data && data.users) || [];
      if (!users.length) {
        el.innerHTML = `<div class="empty-state"><div class="empty-state-text">${t("admin.no_users")}</div></div>`;
        return;
      }
      const isSuperadmin = _adminSelfRole === "superadmin";
      el.innerHTML = `<div class="admin-user-table">
        <div class="admin-user-head">
          <span>${t("admin.username")}</span>
          <span>${t("admin.role")}</span>
          <span>${t("admin.prio_cap")}</span>
          <span>${t("admin.discord")}</span>
          <span></span>
        </div>
        ${users.map(u => {
          const isSelf     = u.id === _adminSelfId;
          const isSuper    = u.role === "superadmin";
          const roleColor  = ROLE_COLORS[u.role] || "var(--text)";
          const disableRole = isSelf || (!isSuperadmin && isSuper);
          const roleOpts   = ROLE_OPTS.filter(r => r !== "superadmin" || isSuperadmin);
          return `<div class="admin-user-row">
            <span style="color:${roleColor};font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${u.username || "–"}</span>
            <select class="admin-sel" onchange="adminSetRole(${u.id},this.value)" ${disableRole?"disabled":""}>
              ${roleOpts.map(r=>`<option value="${r}" ${r===u.role?"selected":""}>${r}</option>`).join("")}
            </select>
            <select class="admin-sel" onchange="adminSetPrioCap(${u.id},this.value)">
              ${PRIO_CAP_OPTS.map(p=>`<option value="${p}" ${p===u.prio_cap?"selected":""}>${p}</option>`).join("")}
            </select>
            <span style="color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${u.discord_name||"–"}</span>
            <div style="display:flex;gap:5px;justify-content:flex-end;flex-shrink:0">
              <button class="btn-icon" onclick="adminResetPw(${u.id})" title="${t("admin.reset_pw")}">&#128273;</button>
              ${!isSelf && !isSuper ? `<button class="btn-icon" style="color:var(--error)" onclick="adminDeleteUser(${u.id},this)" title="${t("admin.delete")}">&#10005;</button>` : ""}
            </div>
          </div>`;
        }).join("")}
      </div>`;
    }

    async function adminSetRole(userId, role) {
      await window.pywebview.api.admin_set_role(userId, role);
    }
    async function adminSetPrioCap(userId, prioCap) {
      await window.pywebview.api.admin_set_prio_cap(userId, prioCap);
    }
    async function adminResetPw(userId) {
      const res = await window.pywebview.api.admin_reset_password(userId);
      if (res && res.temp_password) {
        document.getElementById("pwResult").textContent = res.temp_password;
        document.getElementById("pwModal").style.display = "flex";
      }
    }
    function closePwModal() { document.getElementById("pwModal").style.display = "none"; }

    function adminDeleteUser(userId, btn) {
      _confirmBtn(btn, "admin.confirm_delete", async () => {
        const res = await window.pywebview.api.admin_delete_user(userId);
        if (res && res.success) loadAdminUsers();
      });
    }

    // ── Raid Modal ───────────────────────────────────
    function toggleDeadlineHours() {
      const chk = document.getElementById("raidDeadlineChk");
      const inp = document.getElementById("raidDeadlineHours");
      inp.disabled = !chk.checked;
      inp.style.opacity = chk.checked ? "1" : "0.4";
    }

    async function _ensureAdminPatches() {
      if (_adminPatches !== null) return;
      _adminPatches = await window.pywebview.api.admin_get_form_patches();
    }

    function _renderPatchList(selectedIds) {
      const el = document.getElementById("raidPatchList");
      if (!(_adminPatches && _adminPatches.length)) {
        el.innerHTML = `<span style="color:var(--muted);font-size:12px">Keine Lootlisten vorhanden.</span>`;
        return;
      }
      el.innerHTML = _adminPatches.map(p =>
        `<label class="patch-item">
          <input type="checkbox" value="${p.id}" ${(selectedIds||[]).includes(p.id)?"checked":""}>
          <span>${p.name}</span>
        </label>`
      ).join("");
    }

    async function openRaidModal(raidId) {
      _raidModalId = raidId || null;
      const titleEl = document.getElementById("raidModalTitle");
      titleEl.textContent = raidId ? t("admin.edit_raid") : t("admin.create_raid");
      document.getElementById("raidFormError").style.display = "none";

      await _ensureAdminPatches();
      let selectedPatchIds = [];

      if (raidId) {
        const data = await window.pywebview.api.admin_get_raid(raidId);
        const r    = (data && data.raid) || {};
        document.getElementById("raidName").value           = r.name || "";
        document.getElementById("raidDifficulty").value     = r.difficulty || "heroic";
        if (r.raid_date) {
          const d = typeof r.raid_date === "number" ? new Date(r.raid_date*1000) : new Date(r.raid_date);
          document.getElementById("raidDate").value = d.toISOString().slice(0,10);
          document.getElementById("raidTime").value = d.toISOString().slice(11,16);
        } else {
          document.getElementById("raidDate").value = "";
          document.getElementById("raidTime").value = "20:00";
        }
        const dlChk = r.signup_deadline_enabled || false;
        document.getElementById("raidDeadlineChk").checked   = dlChk;
        document.getElementById("raidDeadlineHours").value   = r.signup_deadline_hours || 24;
        document.getElementById("raidDeadlineHours").disabled = !dlChk;
        document.getElementById("raidDeadlineHours").style.opacity = dlChk ? "1" : "0.4";
        document.getElementById("raidSuperprio").checked     = r.superprio_enabled || false;
        document.getElementById("raidNotes").value           = r.note || "";
        selectedPatchIds = (r.patches || []).map(p => p.id);
      } else {
        document.getElementById("raidName").value           = "";
        document.getElementById("raidDifficulty").value     = "heroic";
        document.getElementById("raidDate").value           = "";
        document.getElementById("raidTime").value           = "20:00";
        document.getElementById("raidDeadlineChk").checked  = false;
        document.getElementById("raidDeadlineHours").value  = 24;
        document.getElementById("raidDeadlineHours").disabled = true;
        document.getElementById("raidDeadlineHours").style.opacity = "0.4";
        document.getElementById("raidSuperprio").checked    = false;
        document.getElementById("raidNotes").value          = "";
      }

      _renderPatchList(selectedPatchIds);
      document.getElementById("raidModal").style.display = "flex";
    }

    function closeRaidModal() { document.getElementById("raidModal").style.display = "none"; }

    async function submitRaidModal() {
      const name    = document.getElementById("raidName").value.trim();
      const dateVal = document.getElementById("raidDate").value;
      const errEl   = document.getElementById("raidFormError");

      if (!name || !dateVal) {
        errEl.textContent = t("admin.required_fields");
        errEl.style.display = "";
        return;
      }

      const timeVal  = document.getElementById("raidTime").value || "20:00";
      const dt       = new Date(`${dateVal}T${timeVal}:00`);
      const raidDate = Math.floor(dt.getTime() / 1000);
      const dlChk    = document.getElementById("raidDeadlineChk").checked;
      const patchIds = [...document.querySelectorAll("#raidPatchList input:checked")].map(i => Number(i.value));

      const payload = {
        name,
        difficulty:               document.getElementById("raidDifficulty").value,
        raid_date:                raidDate,
        signup_deadline_enabled:  dlChk,
        signup_deadline_hours:    dlChk ? (Number(document.getElementById("raidDeadlineHours").value) || 24) : 0,
        superprio_enabled:        document.getElementById("raidSuperprio").checked,
        note:                     document.getElementById("raidNotes").value.trim(),
        patch_ids:                patchIds,
      };

      const res = _raidModalId
        ? await window.pywebview.api.admin_update_raid(_raidModalId, payload)
        : await window.pywebview.api.admin_create_raid(payload);

      if (res && res.success) {
        closeRaidModal();
        loadAdminRaids();
      } else {
        errEl.textContent = (res && res.error) || "Fehler";
        errEl.style.display = "";
      }
    }

    // ── Ersteinrichtung ───────────────────────────────
    async function browseSetupAddon() {
      const result = await window.pywebview.api.browse_folder();
      if (result) document.getElementById("setupAddonPath").value = result;
    }

    async function saveSetupAddon() {
      const path = document.getElementById("setupAddonPath").value.trim();
      const err  = document.getElementById("setupError");
      if (!path) {
        err.textContent = t("setup.path_required") || "Bitte einen Pfad angeben.";
        err.style.display = "";
        return;
      }
      await window.pywebview.api.save_addon_path(path);
      // auch im Einstellungen-Tab aktualisieren
      document.getElementById("addonPath").value = path;
      document.getElementById("setupModal").style.display = "none";
      // Sofort Daten laden und Status aktualisieren
      doRefresh();
    }

    window.addEventListener("pywebviewready", async () => {
      applyLocale();
      const cfg = await window.pywebview.api.get_settings_extended();
      API_URL = cfg.api_url || "";
      // Branch-Buttons beim Start initialisieren
      const branch = cfg.addon_branch || "master";
      document.querySelectorAll(".lang-btn[id^='branch-']").forEach(b => {
        b.classList.toggle("active", b.id === "branch-" + branch);
      });
      // Ersteinrichtung: Pfad fehlt → Modal zeigen
      if (!cfg.addon_path_base) {
        document.getElementById("setupModal").style.display = "flex";
      }

      const s = await window.pywebview.api.get_status();
      setStatus(s.label, s.sub, s.state);
      const u = await window.pywebview.api.get_last_updates();
      setDataCards(u.raid, u.stats);
      // Show admin tab if user has admin role
      const profile = await window.pywebview.api.get_profile();
      if (profile && profile.role) showAdminTab(profile.role, profile.id || null);
    });
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Update-Benachrichtigung
# ---------------------------------------------------------------------------

_UPDATE_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
{css}
  body {{
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 28px; gap: 16px; text-align: center;
  }}
  .update-icon {{ font-size: 28px; }}
  .update-title {{ font-size: 15px; font-weight: 700; color: var(--gold); }}
  .update-text  {{ font-size: 13px; color: var(--muted); line-height: 1.5; }}
  .update-actions {{ display: flex; gap: 8px; margin-top: 4px; }}
  .update-actions .btn {{ flex: 1; }}
</style>
</head>
<body>
  <div class="update-icon">⬆</div>
  <div class="update-title">Update verfügbar</div>
  <div class="update-text">
    WRT Companion App {new_version} ist verfügbar.<br>
    Aktuelle Version: {current_version}
  </div>
  <div class="update-actions">
    <button class="btn btn-ghost"   onclick="window.pywebview.api.dismiss()">Später</button>
    <button class="btn btn-primary" onclick="window.pywebview.api.update()">Jetzt updaten</button>
  </div>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Login-Fenster
# ---------------------------------------------------------------------------

_LOGIN_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
{css}
  body {{
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
  }}
  .eyebrow {{
    font-size: 10px; font-weight: 700;
    letter-spacing: 3.5px; text-transform: uppercase;
    color: #333; margin-bottom: 7px;
  }}
  h1 {{
    font-size: 21px; font-weight: 700;
    color: var(--gold); letter-spacing: -0.3px;
    margin-bottom: 28px;
  }}
  .card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 14px; padding: 26px 28px 22px; width: 340px;
    box-shadow: inset 0 1px 0 0 rgba(255,210,0,0.2), 0 12px 40px rgba(0,0,0,0.7);
  }}
  .field {{ margin-bottom: 13px; }}
  .btn-primary {{ width: 100%; font-size: 13px; padding: 10px; }}
  #status {{
    font-size: 12px; min-height: 20px;
    margin-bottom: 10px; text-align: center;
    color: var(--error);
  }}
  .divider {{ border: none; border-top: 1px solid #1e1e1e; margin: 14px 0; }}
</style>
</head>
<body>
  <div class="eyebrow">WeltenWandler</div>
  <h1>Companion App</h1>
  <div class="card">
    <div class="field">
      <label>Benutzername</label>
      <input type="text" id="username" autocomplete="username">
    </div>
    <div class="field">
      <label>Passwort</label>
      <input type="password" id="password" autocomplete="current-password">
    </div>
    <div id="status"></div>
    <button class="btn btn-primary" id="loginBtn" onclick="doLogin()">Einloggen</button>
  </div>
  <script>
    document.getElementById('password').addEventListener('keydown', e => {{
      if (e.key === 'Enter') doLogin();
    }});
    async function doLogin() {{
      const btn = document.getElementById('loginBtn');
      btn.disabled = true; btn.textContent = 'Verbinde\u2026';
      const status = document.getElementById('status');
      status.textContent = '';
      const r = await window.pywebview.api.login(
        document.getElementById('username').value.trim(),
        document.getElementById('password').value
      ).catch(() => ({{ success: false, error: 'Verbindungsfehler.' }}));
      if (r.success) {{
        status.style.color = 'var(--ok)'; status.textContent = 'Erfolgreich!';
      }} else {{
        status.style.color = 'var(--error)';
        status.textContent = r.error || 'Login fehlgeschlagen.';
        btn.disabled = false; btn.textContent = 'Einloggen';
      }}
    }}
  </script>
</body>
</html>"""


def _render(template: str, **kwargs) -> str:
    """Für einfache Templates (Login, Update-Popup): CSS + HTML-escape."""
    safe = {k: _html.escape(str(v), quote=True) for k, v in kwargs.items()}
    return template.format(css=_BASE_CSS, **safe)


def _render_main(lang: str = "de") -> str:
    """
    Hauptfenster rendern: CSS und Translations-JSON werden direkt eingesetzt
    (kein HTML-Escape, da kontrollierte Inhalte).
    """
    trans_json = json.dumps(_i18n.TRANSLATIONS, ensure_ascii=False)
    html = _MAIN_HTML
    html = html.replace("%%CSS%%",          _BASE_CSS)
    html = html.replace("%%TRANSLATIONS%%", trans_json)
    html = html.replace("%%LANG%%",         lang)
    return html


# ---------------------------------------------------------------------------
# JS-Bridges
# ---------------------------------------------------------------------------

class _MainApi:
    def __init__(self, gui_manager):
        self._gui   = gui_manager
        self.window = None

    # Status
    def get_status(self):
        ctrl = self._gui.ctrl
        if not ctrl.api.is_logged_in():
            return {"label": "Nicht eingeloggt", "sub": "", "state": "error"}
        if not ctrl.cfg.get("addon_path_base", ""):
            return {"label": "Addon-Pfad fehlt", "sub": "Bitte in Einstellungen setzen", "state": "error"}
        return {"label": "Verbunden", "sub": _config.API_URL, "state": "ok"}

    def get_last_updates(self):
        ctrl = self._gui.ctrl
        return {"raid": ctrl.last_update_raid, "stats": ctrl.last_update_stats}

    # Raid-Daten
    def get_raid_data(self):
        return self._gui.ctrl.last_raid_data or {}

    def fetch_fresh_raid_data(self):
        """Holt frische Raid-Daten direkt von der API (synchron, kein lua-Write)."""
        import main as _main
        raw = self._gui.ctrl.api.get_raid()
        if raw:
            data = _main._normalize_raid(raw)
            self._gui.ctrl.last_raid_data = data
            return data
        return self._gui.ctrl.last_raid_data or {}

    # Einstellungen
    def get_settings_extended(self):
        cfg = self._gui.ctrl.cfg
        return {
            "api_url":            _config.API_URL,
            "addon_path_base":    cfg.get("addon_path_base", ""),
            "run_on_startup":     _config.get_run_on_startup(),
            "close_to_tray":      cfg.get("close_to_tray", True),
            "addon_autoupdate":   cfg.get("addon_autoupdate", False),
            "logged_in":          self._gui.ctrl.api.is_logged_in(),
            "app_version":        _updater.CURRENT_VERSION,
            "language":           cfg.get("language", "de"),
            "excluded_patch_ids":  cfg.get("excluded_patch_ids", []),
            "addon_branch":        cfg.get("addon_branch", "master"),
        }

    def save_addon_path(self, path: str):
        cfg = self._gui.ctrl.cfg
        cfg["addon_path_base"] = path.strip()
        _config.save(cfg)

    def save_setting(self, key: str, value):
        cfg = self._gui.ctrl.cfg
        cfg[key] = value
        _config.save(cfg)
        if key == "run_on_startup":
            _config.set_run_on_startup(bool(value))

    def browse_folder(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def logout(self):
        self._gui.ctrl.api.logout()
        self._gui.ctrl.sse.stop()
        # Login-HTML ins bestehende Fenster laden (kein neues Fenster nötig)
        html = _render(_LOGIN_HTML)
        self.window.load_html(html)

    def login(self, username, password):
        """Wird von der Login-Seite nach einem Logout aufgerufen."""
        success, err = self._gui.ctrl.api.login(username, password)
        if success:
            html = _render_main(self._gui.ctrl.cfg.get("language", "de"))
            self.window.load_html(html)
            threading.Thread(target=self._gui._post_login, daemon=True).start()
        return {"success": bool(success), "error": err or ""}

    # Aktionen
    def refresh(self):
        threading.Thread(target=self._gui.ctrl.refresh, daemon=True).start()

    def hide_window(self):
        if self.window:
            self.window.hide()

    # Updates
    def check_addon_version(self):
        cfg         = self._gui.ctrl.cfg
        addon_path  = _config.get_addon_full(cfg)
        branch      = cfg.get("addon_branch", "master")
        avail, ver  = _updater.check_addon_update(addon_path, branch=branch)
        local_ver   = _updater._toc_version_local(addon_path)
        return {"current": local_ver, "latest": ver, "upToDate": not avail}

    def check_app_version(self):
        avail, ver = _updater.check_self_update()
        return {"current": _updater.CURRENT_VERSION, "latest": ver, "upToDate": not avail}

    def update_addon_now(self):
        threading.Thread(target=self._gui.ctrl.update_addon, daemon=True).start()

    def update_app_now(self):
        threading.Thread(target=self._gui.ctrl.update_self, daemon=True).start()

    def get_profile(self):
        return self._gui.ctrl.api.get_profile() or {}

    def get_characters(self):
        return self._gui.ctrl.api.get_characters()

    def create_character(self, name: str, wow_class: str, wow_spec: str):
        return self._gui.ctrl.api.create_character(name, wow_class, wow_spec)

    def update_character(self, char_id: int, name: str, wow_class: str, wow_spec: str):
        return self._gui.ctrl.api.update_character(char_id, name, wow_class, wow_spec)

    def activate_character(self, char_id: int):
        return self._gui.ctrl.api.activate_character(char_id)

    def get_pending_news(self):
        return self._gui.ctrl.api.get_pending_news()

    def confirm_news(self, news_id: int):
        return self._gui.ctrl.api.confirm_news(news_id)

    def change_signup_status(self, raid_id: int, status: str):
        return self._gui.ctrl.api.change_signup(raid_id, status)

    def get_raid_loot(self, raid_id: int):
        return self._gui.ctrl.api.get_raid_loot(raid_id) or {}

    def save_prio(self, raid_id: int, difficulty: str, slots: list):
        return self._gui.ctrl.api.save_prio(raid_id, difficulty, slots)

    def get_patches(self):
        return self._gui.ctrl.api.get_patches()

    # Admin
    def admin_get_raids(self):         return self._gui.ctrl.api.admin_get_raids() or {}
    def admin_get_raid(self, rid):     return self._gui.ctrl.api.admin_get_raid(rid) or {}
    def admin_create_raid(self, d):    return self._gui.ctrl.api.admin_create_raid(d)
    def admin_update_raid(self, rid, d): return self._gui.ctrl.api.admin_update_raid(rid, d)
    def admin_toggle_publish(self, rid): return self._gui.ctrl.api.admin_toggle_publish(rid)
    def admin_archive_raid(self, rid): return self._gui.ctrl.api.admin_archive_raid(rid)
    def admin_get_archive(self):       return self._gui.ctrl.api.admin_get_archive() or {}
    def admin_unarchive_raid(self, rid): return self._gui.ctrl.api.admin_unarchive_raid(rid)
    def admin_delete_raid(self, rid):  return self._gui.ctrl.api.admin_delete_raid(rid)
    def admin_get_users(self):         return self._gui.ctrl.api.admin_get_users() or {}
    def admin_set_role(self, uid, role): return self._gui.ctrl.api.admin_set_role(uid, role)
    def admin_set_prio_cap(self, uid, p): return self._gui.ctrl.api.admin_set_prio_cap(uid, p)
    def admin_reset_password(self, uid): return self._gui.ctrl.api.admin_reset_password(uid)
    def admin_delete_user(self, uid):  return self._gui.ctrl.api.admin_delete_user(uid)
    def admin_get_form_patches(self):  return self._gui.ctrl.api.admin_get_form_patches()

    def get_stats_filtered(self, patch_id, difficulty: str, loot_scope: str):
        return self._gui.ctrl.api.get_stats(
            patch_id=patch_id,
            difficulty=difficulty,
            loot_scope=loot_scope,
        ) or {}

    # Blacklist
    def get_blacklist(self):
        return self._gui.ctrl.api.get_blacklist()

    def add_blacklist_item(self, item_id: int, note: str = ""):
        return self._gui.ctrl.api.add_blacklist_item(item_id, note)

    def remove_blacklist_item(self, bl_id: int):
        return self._gui.ctrl.api.remove_blacklist_item(bl_id)


class _LoginApi:
    def __init__(self, on_login):
        self._on_login = on_login
        self.window    = None

    def login(self, username, password):
        success, err = self._on_login(username, password)
        return {"success": bool(success), "error": err or ""}


class _UpdateApi:
    def __init__(self, win_ref):
        self._win = win_ref

    def dismiss(self):
        self._win.destroy()

    def update(self):
        self._win.destroy()
        threading.Thread(target=_updater.update_self, daemon=True).start()


# ---------------------------------------------------------------------------
# GuiManager
# ---------------------------------------------------------------------------

class GuiManager:
    def __init__(self, ctrl):
        self.ctrl          = ctrl
        self._main_win     = None
        self._main_api     = None
        self._login_win    = None

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def launch(self):
        """Startet den GUI-Event-Loop. Blockiert bis App beendet."""
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "WeltenWandler.CompanionApp"
            )
        except Exception:
            pass

        # Qt WebEngine: selbst-signierte Zertifikate für Bilder/Ressourcen erlauben
        os.environ.setdefault(
            "QTWEBENGINE_CHROMIUM_FLAGS", "--ignore-certificate-errors"
        )

        if self.ctrl.api.is_logged_in():
            self._create_main_window()
        else:
            self._create_login_window()

        threading.Thread(target=self.ctrl.tray.run, daemon=True).start()
        icon = _ICON_PATH if os.path.isfile(_ICON_PATH) else None
        webview.start(self._on_start, gui="qt", icon=icon)

    def show_main(self):
        """Hauptfenster anzeigen (aus Tray-Thread)."""
        if self._main_win:
            try:
                if self._main_win in webview.windows:
                    self._main_win.show()
                    return
            except Exception:
                pass
        self._create_main_window()

    def show_settings(self):
        """Zum Einstellungen-Tab wechseln."""
        self.show_main()
        try:
            self._main_win.evaluate_js("switchTab('settings')")
        except Exception:
            pass

    def set_status(self, label: str, sub: str = "", state: str = "ok", last_update: str = ""):
        """Status im Hauptfenster aktualisieren (threadsafe)."""
        if not self._main_win:
            return
        try:
            def _esc(s):
                return s.replace("\\", "\\\\").replace("'", "\\'")
            self._main_win.evaluate_js(
                f"setStatus('{_esc(label)}', '{_esc(sub)}', '{state}');"
                f"setDataCards('{_esc(self.ctrl.last_update_raid)}', '{_esc(self.ctrl.last_update_stats)}');"
            )
        except Exception:
            pass

    def quit(self):
        """App sauber beenden."""
        self.ctrl.stop()
        # Tray-Icon stoppen
        try:
            if self.ctrl.tray.icon:
                self.ctrl.tray.icon.stop()
        except Exception:
            pass
        # Alle Fenster schließen
        for win in list(webview.windows):
            try:
                win.destroy()
            except Exception:
                pass
        # Prozess forciert beenden (pystray-Threads sind nicht daemon)
        sys.exit(0)

    # ------------------------------------------------------------------
    # Intern
    # ------------------------------------------------------------------

    def _on_start(self):
        if self.ctrl.api.is_logged_in():
            threading.Thread(target=self._post_login, daemon=True).start()

    def _create_main_window(self):
        api = _MainApi(self)
        win = webview.create_window(
            "WeltenWandler Companion",
            html=_render_main(self.ctrl.cfg.get("language", "de")),
            js_api=api,
            width=900, height=650,
            resizable=True,
        )
        win.events.closing += self._on_main_closing
        api.window     = win
        self._main_api = api
        self._main_win = win

    def _on_main_closing(self):
        if self.ctrl.cfg.get("close_to_tray", True):
            self._main_win.hide()
            return False
        self.ctrl.quit()
        return True

    def _create_login_window(self):
        html = _render(_LOGIN_HTML)
        api  = _LoginApi(self._handle_login)
        win  = webview.create_window(
            "WeltenWandler Companion – Login",
            html=html, js_api=api,
            width=420, height=420,
            resizable=False,
        )
        api.window      = win
        self._login_win = win

    def _handle_login(self, username, password):
        success, err = self.ctrl.api.login(username, password)
        if success:
            self._login_win.destroy()
            self._create_main_window()
            threading.Thread(target=self._post_login, daemon=True).start()
        return success, err

    def _show_login(self):
        """Login-Fenster anzeigen und Hauptfenster verstecken."""
        if self._main_win:
            try:
                self._main_win.hide()
            except Exception:
                pass
        self._create_login_window()

    def _post_login(self):
        self.ctrl.tray.set_status("Verbunden")
        threading.Thread(target=self.ctrl.refresh, daemon=True).start()
        self.ctrl.sse.start()
        # Update-Check im Hintergrund
        threading.Thread(target=self._check_startup_updates, daemon=True).start()

    def _check_startup_updates(self):
        try:
            avail, new_ver = _updater.check_self_update()
            if avail:
                self._show_update_notification(new_ver)
        except Exception:
            pass

    def _show_update_notification(self, new_version: str):
        html = _render(
            _UPDATE_HTML,
            new_version     = new_version,
            current_version = _updater.CURRENT_VERSION,
        )
        api = _UpdateApi(None)
        win = webview.create_window(
            "Update verfügbar – WRT Companion",
            html=html, js_api=api,
            width=380, height=240,
            resizable=False, on_top=True,
        )
        api._win = win
