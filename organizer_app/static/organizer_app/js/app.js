/**
 * Smart File Organizer - Frontend Controller
 */

document.addEventListener('DOMContentLoaded', () => {
    // State
    const state = {
        currentPath: '',
        scannedFiles: [],
        categories: {},
        customRules: {},
        isOrganizing: false,
    };

    // DOM Elements
    const inputTargetDir = document.getElementById('input-target-dir');
    const btnClearPath = document.getElementById('btn-clear-path');
    const shortcutPills = document.querySelectorAll('.shortcut-pill');
    const strategyCards = document.querySelectorAll('.strategy-card');
    const selectDupStrategy = document.getElementById('select-duplicate-strategy');
    const checkRecursive = document.getElementById('check-recursive');
    const checkCleanEmpty = document.getElementById('check-clean-empty');
    const checkDryRun = document.getElementById('check-dry-run');
    
    // Action Buttons
    const btnScan = document.getElementById('btn-scan');
    const btnOrganize = document.getElementById('btn-organize');
    const btnUndoQuick = document.getElementById('btn-undo-quick');
    const btnDemoSandbox = document.getElementById('btn-demo-sandbox');
    const btnViewHistory = document.getElementById('btn-view-history');
    const btnCustomRules = document.getElementById('btn-custom-rules');
    
    // Metrics
    const statTotalFiles = document.getElementById('stat-total-files');
    const statTotalSize = document.getElementById('stat-total-size');
    const statTotalCategories = document.getElementById('stat-total-categories');
    const statActiveStatus = document.getElementById('stat-active-status');
    const badgeCategoryCount = document.getElementById('badge-category-count');
    
    // Category & Files Table
    const categoryCardsGrid = document.getElementById('category-cards-grid');
    const filesTableBody = document.getElementById('files-table-body');
    const tableSearch = document.getElementById('table-search');
    const filesTableSubtitle = document.getElementById('files-table-subtitle');
    
    // Terminal Logs
    const terminalConsole = document.getElementById('terminal-console');
    const btnClearLogs = document.getElementById('btn-clear-logs');
    const btnExportLogs = document.getElementById('btn-export-logs');
    
    // Modals
    const historyModal = document.getElementById('history-modal');
    const btnCloseHistory = document.getElementById('btn-close-history');
    const historyList = document.getElementById('history-list');
    
    const rulesModal = document.getElementById('rules-modal');
    const btnCloseRules = document.getElementById('btn-close-rules');
    const customRuleCat = document.getElementById('custom-rule-cat');
    const customRuleExts = document.getElementById('custom-rule-exts');
    const btnAddCustomRule = document.getElementById('btn-add-custom-rule');
    const customRulesList = document.getElementById('custom-rules-list');

    // -------------------------------------------------------------
    // Helper: Toast Notifications
    // -------------------------------------------------------------
    function showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        let icon = 'ℹ️';
        if (type === 'success') icon = '✅';
        if (type === 'error') icon = '❌';
        if (type === 'warning') icon = '⚠️';

        toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // -------------------------------------------------------------
    // Helper: Logger Terminal
    // -------------------------------------------------------------
    function appendLog(message, level = 'INFO') {
        const entry = document.createElement('div');
        let levelClass = 'log-info';
        if (level === 'ERROR') levelClass = 'log-error';
        if (level === 'WARNING') levelClass = 'log-warning';
        if (level === 'SUCCESS') levelClass = 'log-success';
        if (level === 'DRY') levelClass = 'log-dry';

        entry.className = `log-entry ${levelClass}`;
        entry.textContent = message;
        terminalConsole.appendChild(entry);
        terminalConsole.scrollTop = terminalConsole.scrollHeight;
    }

    function appendLogsArray(logs) {
        if (!logs || !Array.isArray(logs)) return;
        logs.forEach(msg => {
            let level = 'INFO';
            if (msg.includes('[ERROR]')) level = 'ERROR';
            else if (msg.includes('[WARNING]')) level = 'WARNING';
            else if (msg.includes('[SUCCESS]') || msg.includes('Moved:') || msg.includes('Restored:')) level = 'SUCCESS';
            else if (msg.includes('[DRY-RUN]') || msg.includes('[DRY RUN]')) level = 'DRY';
            appendLog(msg, level);
        });
    }

    // -------------------------------------------------------------
    // Strategy Card Selection
    // -------------------------------------------------------------
    strategyCards.forEach(card => {
        card.addEventListener('click', () => {
            strategyCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const radio = card.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    });

    function getSelectedStrategy() {
        const checked = document.querySelector('input[name="strategy"]:checked');
        return checked ? checked.value : 'by_category';
    }

    // -------------------------------------------------------------
    // Shortcuts & Path Input
    // -------------------------------------------------------------
    shortcutPills.forEach(pill => {
        pill.addEventListener('click', () => {
            const p = pill.getAttribute('data-path');
            if (p) {
                inputTargetDir.value = p;
                state.currentPath = p;
                triggerScan();
            }
        });
    });

    btnClearPath.addEventListener('click', () => {
        inputTargetDir.value = '';
        state.currentPath = '';
    });

    // -------------------------------------------------------------
    // Render Functions
    // -------------------------------------------------------------
    function renderCategoryCards(categoriesCount, categoriesSizeHuman) {
        categoryCardsGrid.innerHTML = '';
        const cats = Object.keys(categoriesCount || {});
        
        if (cats.length === 0) {
            categoryCardsGrid.innerHTML = '<div class="empty-state-mini">No files or categories detected.</div>';
            badgeCategoryCount.textContent = '0 Categories';
            statTotalCategories.textContent = '0';
            return;
        }

        badgeCategoryCount.textContent = `${cats.length} Categories`;
        statTotalCategories.textContent = cats.length;

        const iconMap = {
            'Documents': '📄', 'Images': '🖼️', 'Videos': '🎥', 'Audio': '🎵',
            'Archives': '📦', 'Spreadsheets': '📊', 'Presentations': '📑',
            'Code & Dev': '💻', 'Executables & Installers': '⚙️', 'Books & Reading': '📚',
            'Design & 3D': '🎨', 'Fonts': '🔤', 'Others': '📁', '_Duplicates': '👥'
        };

        cats.forEach(cat => {
            const count = categoriesCount[cat];
            const sizeH = categoriesSizeHuman ? categoriesSizeHuman[cat] : '';
            const icon = iconMap[cat] || '📁';

            const card = document.createElement('div');
            card.className = 'cat-pill-card';
            card.innerHTML = `
                <div class="cat-pill-icon">${icon}</div>
                <div class="cat-pill-info">
                    <span class="cat-pill-title">${cat}</span>
                    <span class="cat-pill-stats">${count} files ${sizeH ? '• ' + sizeH : ''}</span>
                </div>
            `;
            
            // Clicking category filters table
            card.addEventListener('click', () => {
                tableSearch.value = cat;
                filterTable(cat);
            });

            categoryCardsGrid.appendChild(card);
        });
    }

    function renderFilesTable(files, isOrganized = false, isDryRun = false) {
        filesTableBody.innerHTML = '';
        
        if (!files || files.length === 0) {
            filesTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="table-empty-cell">
                        <div class="empty-state-content">
                            <span class="empty-icon">📂</span>
                            <h4>No files found in directory</h4>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        files.forEach((file, index) => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            if (isOrganized) {
                if (isDryRun) {
                    statusBadge = '<span class="badge-tag badge-simulated">Simulated</span>';
                } else if (file.renamed) {
                    statusBadge = '<span class="badge-tag badge-renamed">Renamed Duplicate</span>';
                } else {
                    statusBadge = '<span class="badge-tag badge-success">Moved</span>';
                }
            } else {
                statusBadge = '<span class="badge-tag" style="background: rgba(255,255,255,0.08);">Planned</span>';
            }

            const targetName = file.target_folder || file.target_folder_name || 'Others';
            const icon = file.category_icon || '📄';

            tr.innerHTML = `
                <td>${index + 1}</td>
                <td>
                    <div class="table-file-cell">
                        <span>${icon}</span>
                        <span>${file.filename}</span>
                    </div>
                </td>
                <td>${file.category || '-'}</td>
                <td>${file.size_human}</td>
                <td><code style="color: #38bdf8;">${targetName}/</code></td>
                <td>${statusBadge}</td>
            `;
            filesTableBody.appendChild(tr);
        });

        filesTableSubtitle.textContent = `Showing ${files.length} mapped file items`;
    }

    function filterTable(query) {
        const q = query.toLowerCase().trim();
        if (!q) {
            renderFilesTable(state.scannedFiles);
            return;
        }

        const filtered = state.scannedFiles.filter(f => 
            (f.filename && f.filename.toLowerCase().includes(q)) ||
            (f.category && f.category.toLowerCase().includes(q)) ||
            (f.extension && f.extension.toLowerCase().includes(q)) ||
            (f.target_folder_name && f.target_folder_name.toLowerCase().includes(q))
        );
        renderFilesTable(filtered);
    }

    tableSearch.addEventListener('input', (e) => {
        filterTable(e.target.value);
    });

    // -------------------------------------------------------------
    // API: Scan Directory
    // -------------------------------------------------------------
    async function triggerScan() {
        const path = inputTargetDir.value.trim();
        if (!path) {
            showToast('Please enter or select a directory path.', 'warning');
            return;
        }

        btnScan.disabled = true;
        btnScan.innerHTML = '<span class="btn-icon">⏳</span><span>Scanning...</span>';
        statActiveStatus.textContent = 'Scanning...';

        appendLog(`[REQUEST] Scanning directory: ${path}...`);

        try {
            const res = await fetch('/api/scan/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: path,
                    strategy: getSelectedStrategy(),
                    recursive: checkRecursive.checked,
                    custom_rules: state.customRules,
                })
            });

            const data = await res.json();

            if (!data.success) {
                showToast(data.error || 'Scan failed', 'error');
                appendLog(`[ERROR] ${data.error}`, 'ERROR');
                statActiveStatus.textContent = 'Error';
                return;
            }

            state.currentPath = data.source_dir;
            state.scannedFiles = data.files || [];
            
            // Update Stats
            statTotalFiles.textContent = data.total_files;
            statTotalSize.textContent = data.total_size_human;
            statActiveStatus.textContent = 'Ready to Organize';

            // Render Views
            renderCategoryCards(data.categories_count, data.categories_size_human);
            renderFilesTable(data.files);
            appendLogsArray(data.logs);

            showToast(`Scan complete: ${data.total_files} files found.`, 'success');
        } catch (err) {
            showToast(`Network error: ${err.message}`, 'error');
            appendLog(`[ERROR] ${err.message}`, 'ERROR');
            statActiveStatus.textContent = 'Error';
        } finally {
            btnScan.disabled = false;
            btnScan.innerHTML = '<span class="btn-icon">🔍</span><span>Scan & Preview</span>';
        }
    }

    btnScan.addEventListener('click', triggerScan);

    // -------------------------------------------------------------
    // API: Organize / Dry-Run Directory
    // -------------------------------------------------------------
    async function triggerOrganize(isDryRun = false) {
        const path = inputTargetDir.value.trim();
        if (!path) {
            showToast('Please enter or select a directory path.', 'warning');
            return;
        }

        const dryRunFinal = isDryRun || checkDryRun.checked;

        btnOrganize.disabled = true;
        btnOrganize.innerHTML = `<span class="btn-icon">⏳</span><span>${dryRunFinal ? 'Simulating...' : 'Organizing...'}</span>`;
        statActiveStatus.textContent = dryRunFinal ? 'Simulating...' : 'Moving Files...';

        appendLog(`[EXECUTE] ${dryRunFinal ? 'Simulating organization' : 'Organizing directory'}: ${path}...`);

        try {
            const res = await fetch('/api/organize/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    path: path,
                    strategy: getSelectedStrategy(),
                    duplicate_strategy: selectDupStrategy.value,
                    recursive: checkRecursive.checked,
                    dry_run: dryRunFinal,
                    clean_empty_folders: checkCleanEmpty.checked,
                    custom_rules: state.customRules,
                })
            });

            const data = await res.json();

            if (!data.success) {
                showToast(data.error || 'Operation failed', 'error');
                appendLog(`[ERROR] ${data.error}`, 'ERROR');
                statActiveStatus.textContent = 'Error';
                return;
            }

            appendLogsArray(data.logs);

            const msg = dryRunFinal 
                ? `[Simulation] Would move ${data.successful_moves} files across ${data.created_folders.length} folders.`
                : `Successfully organized ${data.successful_moves} files!`;

            showToast(msg, 'success');
            statActiveStatus.textContent = dryRunFinal ? 'Simulation Done' : 'Organized';

            // Update Table with executed moves
            if (data.files && data.files.length > 0) {
                renderFilesTable(data.files, true, dryRunFinal);
            }

            if (!dryRunFinal) {
                // Trigger fresh scan to show clean organized directory state
                setTimeout(() => triggerScan(), 1200);
            }
        } catch (err) {
            showToast(`Network error: ${err.message}`, 'error');
            appendLog(`[ERROR] ${err.message}`, 'ERROR');
            statActiveStatus.textContent = 'Error';
        } finally {
            btnOrganize.disabled = false;
            btnOrganize.innerHTML = '<span class="btn-icon">🚀</span><span>Organize Now</span>';
        }
    }

    btnOrganize.addEventListener('click', () => triggerOrganize(false));

    // -------------------------------------------------------------
    // API: Undo Last Operation
    // -------------------------------------------------------------
    async function triggerUndo(batchId = null) {
        const path = inputTargetDir.value.trim();
        appendLog(`[UNDO] Reversing operation ${batchId || '(last batch)'}...`);

        try {
            const res = await fetch('/api/undo/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    batch_id: batchId,
                    path: path || null,
                })
            });

            const data = await res.json();

            if (!data.success) {
                showToast(data.message || 'Undo failed', 'warning');
                appendLog(`[WARNING] ${data.message}`, 'WARNING');
                return;
            }

            showToast(`Rollback complete: ${data.restored_count} files restored.`, 'success');
            appendLogsArray(data.activity_logs);
            statActiveStatus.textContent = 'Rolled Back';

            // Refresh directory view
            if (path) {
                setTimeout(() => triggerScan(), 800);
            }
            if (historyModal.classList.contains('active')) {
                loadHistory();
            }
        } catch (err) {
            showToast(`Undo error: ${err.message}`, 'error');
            appendLog(`[ERROR] ${err.message}`, 'ERROR');
        }
    }

    btnUndoQuick.addEventListener('click', () => triggerUndo(null));

    // -------------------------------------------------------------
    // API: Generate Demo Sandbox
    // -------------------------------------------------------------
    btnDemoSandbox.addEventListener('click', async () => {
        btnDemoSandbox.disabled = true;
        btnDemoSandbox.innerHTML = '<span class="btn-icon">⏳</span><span>Creating Mock Folder...</span>';

        try {
            const res = await fetch('/api/create-demo/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            const data = await res.json();

            if (data.success && data.sandbox_path) {
                inputTargetDir.value = data.sandbox_path;
                state.currentPath = data.sandbox_path;
                showToast('Demo Sandbox created! Scanning...', 'success');
                appendLog(`[SANDBOX] Created sandbox directory: ${data.sandbox_path}`, 'SUCCESS');
                triggerScan();
            } else {
                showToast(data.error || 'Could not create demo sandbox', 'error');
            }
        } catch (err) {
            showToast(`Error creating sandbox: ${err.message}`, 'error');
        } finally {
            btnDemoSandbox.disabled = false;
            btnDemoSandbox.innerHTML = '<span class="btn-icon">🧪</span><span>Generate Demo Sandbox</span>';
        }
    });

    // -------------------------------------------------------------
    // History Modal & Rollback Center
    // -------------------------------------------------------------
    async function loadHistory() {
        historyList.innerHTML = '<div class="history-loading">Loading transaction history...</div>';
        try {
            const res = await fetch('/api/history/');
            const data = await res.json();

            if (!data.success || !data.history || data.history.length === 0) {
                historyList.innerHTML = '<div class="empty-state-mini">No organization operations recorded yet.</div>';
                return;
            }

            historyList.innerHTML = '';
            data.history.forEach(op => {
                const item = document.createElement('div');
                item.className = 'history-item-card';

                const statusTag = op.undone 
                    ? '<span class="badge-tag" style="background: rgba(239, 68, 68, 0.2); color: #f87171;">UNDONE</span>'
                    : '<span class="badge-tag badge-success">ACTIVE</span>';

                const undoBtnHtml = !op.undone 
                    ? `<button class="btn btn-warning btn-xs btn-batch-undo" data-batch="${op.batch_id}">↩️ Rollback</button>`
                    : '';

                item.innerHTML = `
                    <div class="history-item-details">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span class="history-item-batch">${op.batch_id}</span>
                            ${statusTag}
                        </div>
                        <div class="history-item-path">📂 ${op.source_dir}</div>
                        <div class="history-item-meta">
                            <span>Strategy: <strong>${op.strategy}</strong></span> • 
                            <span>Files: <strong>${op.successful_moves}</strong></span> • 
                            <span>Time: ${op.timestamp.replace('T', ' ').slice(0, 19)}</span>
                        </div>
                    </div>
                    <div>${undoBtnHtml}</div>
                `;

                const btnBatchUndo = item.querySelector('.btn-batch-undo');
                if (btnBatchUndo) {
                    btnBatchUndo.addEventListener('click', () => {
                        triggerUndo(op.batch_id);
                    });
                }

                historyList.appendChild(item);
            });
        } catch (err) {
            historyList.innerHTML = `<div class="log-error">Failed to load history: ${err.message}</div>`;
        }
    }

    btnViewHistory.addEventListener('click', () => {
        historyModal.classList.add('active');
        loadHistory();
    });

    btnCloseHistory.addEventListener('click', () => {
        historyModal.classList.remove('active');
    });

    // -------------------------------------------------------------
    // Custom Rules Modal
    // -------------------------------------------------------------
    function renderCustomRules() {
        customRulesList.innerHTML = '';
        const keys = Object.keys(state.customRules);
        if (keys.length === 0) {
            customRulesList.innerHTML = '<div class="empty-state-mini">No custom rules added yet.</div>';
            return;
        }

        keys.forEach(cat => {
            const exts = state.customRules[cat].join(', ');
            const div = document.createElement('div');
            div.className = 'custom-rule-item';
            div.innerHTML = `
                <div>
                    <strong>${cat}</strong>: <code>${exts}</code>
                </div>
                <button class="btn-xs" style="color: #ef4444;" data-remove-cat="${cat}">Remove</button>
            `;
            div.querySelector('[data-remove-cat]').addEventListener('click', () => {
                delete state.customRules[cat];
                renderCustomRules();
            });
            customRulesList.appendChild(div);
        });
    }

    btnAddCustomRule.addEventListener('click', () => {
        const cat = customRuleCat.value.trim();
        const extsRaw = customRuleExts.value.trim();
        if (!cat || !extsRaw) {
            showToast('Please enter both Category Name and Extensions.', 'warning');
            return;
        }

        const extList = extsRaw.split(',').map(e => e.trim().replace(/^\./, '')).filter(Boolean);
        if (extList.length === 0) return;

        state.customRules[cat] = extList;
        customRuleCat.value = '';
        customRuleExts.value = '';
        renderCustomRules();
        showToast(`Added custom rule: ${cat}`, 'success');
    });

    btnCustomRules.addEventListener('click', () => {
        rulesModal.classList.add('active');
        renderCustomRules();
    });

    btnCloseRules.addEventListener('click', () => {
        rulesModal.classList.remove('active');
    });

    // Close modals when clicking overlay
    window.addEventListener('click', (e) => {
        if (e.target === historyModal) historyModal.classList.remove('active');
        if (e.target === rulesModal) rulesModal.classList.remove('active');
    });

    // -------------------------------------------------------------
    // Terminal Log Actions
    // -------------------------------------------------------------
    btnClearLogs.addEventListener('click', () => {
        terminalConsole.innerHTML = '<div class="log-entry log-info">[SYSTEM] Logs cleared.</div>';
    });

    btnExportLogs.addEventListener('click', () => {
        const text = terminalConsole.innerText;
        const blob = new Blob([text], { type: 'text/plain' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `SmartOrganizer_Log_${new Date().toISOString().slice(0, 10)}.txt`;
        a.click();
    });
});
