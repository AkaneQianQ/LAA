# Phase 8: MXU前端开发 - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a frontend based on **MXU (MaaFramework Next UI)** framework that provides a graphical interface for the FerrumBot automation system. The frontend must:

1. **Be compatible** with existing `assets/tasks/*.yaml` workflow scripts (via YAML→Pipeline JSON conversion)
2. **Support automatic recognition features** for game window, hardware, and account identification
3. **Integrate seamlessly** with the existing MaaEnd-style architecture (`interface.json`, agent service)

**MXU Framework**: Tauri v2 + React 19 + TypeScript GUI client that parses `interface.json` to auto-generate a ready-to-use interface for MaaFramework projects.

</domain>

<decisions>
## Implementation Decisions

### MXU Integration Approach
- **Custom fork/modify MXU** rather than bundling standalone executable
- Modify MXU source to integrate with FerrumBot's Python agent service
- Keep MXU's Tauri+React architecture but customize for project-specific needs

### YAML Workflow Compatibility
- **Retain YAML as source format** for workflow definitions (`assets/tasks/*.yaml`)
- **Convert to Pipeline JSON at build time** using existing `tools/convert_yaml_to_pipeline.py`
- Output Pipeline JSON to `assets/resource/pipeline/*.json` (MXU-compatible)
- YAML remains human-editable; JSON is runtime format

### Auto-Recognition Features
1. **Auto-detect game window**: Find and connect to Lost Ark game window automatically
2. **Auto-detect hardware**: Detect KMBox/Ferrum device connection status (COM port scanning)
3. **Auto-recognize account**: Use existing character detection to identify account from first character screenshot

### UI Preferences
- **Dark theme as default** (matches Phase 6 overlay preference)
- **Chinese language (zh_cn) as default** (consistent with existing UI)
- **Real-time log viewer** showing execution progress
- **Task-specific configuration panels** for GuildDonation, CharacterSwitch, AccountIndexing

### Frontend-Backend Integration
- Frontend communicates with `agent/py_service/main.py` via IPC/WebSocket
- MXU's task management UI triggers Python service execution
- Pipeline JSON defines task flow; Python executor handles hardware actions

### Claude's Discretion
- Exact WebSocket/IPC protocol implementation details
- Custom MXU component styling (within dark theme)
- Real-time screenshot refresh rate optimization
- Error notification UI design
- Auto-recognition retry policies and timeouts

</decisions>

<specifics>
## Specific Ideas

**MXU Repository**: https://github.com/MistEO/MXU
- Uses Tauri v2 (Rust) + React 19 + TypeScript
- Supports MaaFramework PI V2 protocol
- Has built-in i18n, theme switching, task management, multi-instance support

**Expected Directory Structure**:
```
frontend/                       # MXU-based frontend source
├── src/                        # React TypeScript source
├── src-tauri/                  # Tauri Rust backend
├── interface.json              # Points to ../assets/interface.json
└── package.json

assets/
├── interface.json              # MaaFramework PI V2 config
├── resource/pipeline/          # Pipeline JSON (converted from YAML)
└── tasks/                      # Source YAML workflows
```

**Auto-Recognition Flow**:
1. Frontend starts → Auto-scan for Lost Ark window
2. Connect to window → Auto-detect hardware (COM2 default, fallback scanning)
3. Load tasks from interface.json → Show task list
4. User starts task → Backend executor runs Pipeline JSON
5. Real-time logs stream to frontend UI

**Integration Point**:
- MXU's Rust backend (`src-tauri/src`) needs custom IPC handlers
- Python service exposes WebSocket or HTTP API for frontend
- Task execution: Frontend → Tauri → Python Service → Hardware

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tools/convert_yaml_to_pipeline.py`**: YAML→JSON conversion already implemented
- **`agent/py_service/main.py`**: Service entry point for backend integration
- **`assets/interface.json`**: Already configured for MaaFramework PI V2
- **Pipeline executor**: `agent/py_service/pkg/workflow/pipeline_executor.py` handles execution

### Established Patterns
- **MaaEnd-style architecture**: interface.json + Pipeline JSON + Agent Service
- **YAML workflow format**: Human-readable, converted to JSON at build time
- **Chinese UI text**: All user-facing messages in Chinese
- **Dark theme preference**: From Phase 6 overlay design

### Integration Points
- **Frontend → Backend**: Need IPC/WebSocket bridge between Tauri and Python
- **Task execution**: MXU task list triggers `agent/py_service/main.py --task {name}`
- **Real-time updates**: Python service streams logs to frontend via WebSocket
- **Auto-recognition**: Reuse existing `character/detector.py` for account identification

### Required New Components
1. **Tauri IPC handlers** for Python service communication
2. **WebSocket server** in Python service for frontend connection
3. **MXU custom components** for task configuration panels
4. **Auto-recognition module** (window detection, hardware scanning)

</code_context>

<deferred>
## Deferred Ideas

- **Scheduled tasks** — MXU supports this but out of scope for initial implementation
- **Multi-instance support** — Can be added later if needed for parallel accounts
- **Real-time screenshot display** — Nice-to-have feature for v2
- **MirrorChyan auto-update** — MXU feature, integrate in future release
- **PlayCover/macOS support** — Windows-only for v1

</deferred>

---

*Phase: 08-mxu-assets-tasks*
*Context gathered: 2026-03-09*
